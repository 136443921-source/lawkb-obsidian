#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LawKB 知识飞轮系统 · 法条冲突检测（A/B/C 三类）

A 条号越界     : 引用条号 > 权威索引该法总条数 → 必错
B 同条异文     : 同一 (法,条) 在库内被不同文件引用成不同逐字内容 → 库内自相矛盾
C 引文不符权威 : 卡片的逐字引文 与 权威索引正文 不匹配（含版本错引）

输出: /tmp/lawkb_audit/conflicts_ABC.json + 控制台报告
"""
import json
import os
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_exempt import is_exempt  # 豁免前置（测试夹具/工具元数据/历史法条）

IDX = "/Users/chenyouqiang/.workbuddy/skills/LTI文本监控器/references/provision_index"
CITES = "/tmp/lawkb_audit/citations.json"
OUT = "/tmp/lawkb_audit/conflicts_ABC.json"

PUNCT = re.compile(r"[\s，。；：、？！“”‘’（）()《》〈〉\"'.,;:?!\-—_·　]+")


def norm(s: str) -> str:
    return PUNCT.sub("", s or "")


def ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def best_containment(frag, body):
    """片段在正文中的最佳滑窗相似度（应对摘录式引用）"""
    nb = body
    if not frag or not nb:
        return 0.0
    if frag in nb:
        return 1.0
    step = 40
    best = 0.0
    for i in range(0, max(1, len(nb) - len(frag)), step):
        r = ratio(frag, nb[i:i + len(frag) + 25])
        if r > best:
            best = r
        if best >= 0.97:
            break
    return best


def load_index():
    laws = {}
    mf = json.load(open(os.path.join(IDX, "manifest.json"), encoding="utf-8"))
    for law, meta in mf["laws"].items():
        fp = os.path.join(IDX, meta["file"])
        if not os.path.isfile(fp):
            continue
        d = json.load(open(fp, encoding="utf-8"))
        laws[law] = {
            "version": meta.get("version"),
            "title": meta.get("title"),
            "count": meta.get("article_count"),
            "articles": d.get("articles", {}),
        }
    return laws


def main():
    laws = load_index()
    cites = json.load(open(CITES, encoding="utf-8"))

    out_of_range = []      # A
    same_art_diff = []     # B
    quote_mismatch = []    # C

    # —— A 条号越界 ——
    for c in cites:
        law = c.get("law")
        art_num = c.get("art_num")
        if not law or art_num is None or law not in laws:
            continue
        # 豁免前置：测试夹具 / 工具元数据 / 历史法条正确引用 → 跳过
        if is_exempt(law, c.get("art"), c.get("file", ""), c.get("ctx", ""), c.get("quote", "")):
            continue
        cnt = laws[law]["count"]
        if art_num > cnt:
            out_of_range.append({**c, "max": cnt,
                                 "version": laws[law]["version"]})

    # —— B 同条异文：按 (law,art) 聚类逐字引文 ——
    by_key = defaultdict(list)
    for c in cites:
        # 豁免前置：测试夹具 / 工具元数据 / 历史法条正确引用 → 跳过
        if is_exempt(c.get("law"), c.get("art"), c.get("file", ""),
                     c.get("ctx", ""), c.get("quote", "")):
            continue
        if c.get("law") and c.get("quote") and len(c["quote"]) >= 10:
            by_key[(c["law"], c["art"])].append(c)

    for (law, art), group in sorted(by_key.items(), key=lambda x: (x[0][0], x[0][1] or 0)):
        if law not in laws:          # 跳过未建索引的旧法/非覆盖法（如侵权责任法→现民法典）
            continue
        auth_nb = norm(laws[law]["articles"].get(str(art), {}).get("body", ""))
        # 同条异文收窄（2026-10 补丁，v2）：
        # 仅在「≥2 个不同文件」对同一条文给出「非本条权威正文干净摘录」且「彼此内容确属不同」时，
        # 才判为潜在异文。排除：同文件重复摘录、同条不同摘录（均属权威正文）、grab_quote 单文件误抓。
        by_file = {}
        for c in group:
            nq = norm(c["quote"])
            if len(nq) < 20:
                continue
            # 干净摘录（整体属本条权威正文）→ 排除，非异文
            if auth_nb and (nq in auth_nb or best_containment(nq, auth_nb) >= 0.97):
                continue
            by_file[c["file"]] = nq  # 同文件仅取其一
        reps = []
        for nq in by_file.values():
            if not any(ratio(nq, r) >= 0.60 for r in reps):
                reps.append(nq)
        if len(reps) > 1:
            same_art_diff.append({
                "law": law, "art": art, "variants": len(reps),
                "items": [{"file": c["file"], "line": c["line"],
                           "quote": c["quote"][:160]}
                          for c in group if norm(c["quote"]) in by_file.values()]
            })

    # —— C 引文 vs 权威正文 ——
    for c in cites:
        law, art, q = c.get("law"), c.get("art"), c.get("quote")
        if not law or art is None or not q or law not in laws:
            continue
        # 豁免前置：测试夹具 / 工具元数据 / 历史法条正确引用 → 跳过
        if is_exempt(law, art, c.get("file", ""), c.get("ctx", ""), c.get("quote", "")):
            continue
        nq = norm(q)
        if len(nq) < 10:
            continue
        # 纯交叉引用豁免（2026-10 补丁）：引文仅为「XX法第N条」形式、无实质法条内容 → 跳过
        # 例：民诉法解释第466条 引文「民事诉讼法第二百四十六条」系参引而非引文，误报。
        if re.match(r'^[一-龥]{0,14}第[0-9〇一二三四五六七八九十百千万零两]+条$', nq):
            continue
        body = laws[law]["articles"].get(str(art), {}).get("body")
        if not body:
            continue
        nq, nb = norm(q), norm(body)
        if nq in nb:
            continue                       # 片段命中权威正文 → 通过
        r = ratio(nq, nb)
        # 引文可能是正文前段的截取，做一次滑窗容错
        best = max([ratio(nq, nb[i:i + len(nq) + 20])
                    for i in range(0, max(1, len(nb) - 20), 40)] or [0])
        score = max(r, best)
        if score >= 0.55:
            continue                       # 仍与所挂条足够相似 → 通过
        # 反向定位：引文最可能属于本法哪一条？
        best_k, best_s = None, 0.0
        for k, b in laws[law]["articles"].items():
            s = best_containment(nq, norm(b.get("body", "")))
            if s > best_s:
                best_s, best_k = s, k
        # 若最佳匹配即所引条本身 → 引文确属本法该条（仅因摘录/归一化致相似度偏低），
        # 判定通过，非真实错配。仅当最佳匹配指向「另一条」(best_k≠art) 且足够相似时，
        # 才视为「引文挂错条号」的真实候选（2026-10 补丁，消除正确引用被误报）。
        if best_k is not None and str(best_k) == str(art):
            continue
        if best_s < 0.55:
            continue
        quote_mismatch.append({
            "law": law, "art": art, "score": round(score, 3),
            "version": laws[law]["version"],
            "file": c["file"], "line": c["line"],
            "quote": q[:200],
            "auth": body[:200],
        })

    quote_mismatch.sort(key=lambda x: x["score"])
    out_of_range.sort(key=lambda x: (x["law"], x["art"]))

    res = {"A_out_of_range": out_of_range, "B_same_art_diff": same_art_diff,
           "C_quote_mismatch": quote_mismatch}
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("=" * 70)
    print("法条冲突检测 A/B/C")
    print("=" * 70)
    print(f"A 条号越界      : {len(out_of_range)} 处")
    print(f"B 同条异文      : {len(same_art_diff)} 组（同一法条库内被引用成不同内容）")
    print(f"C 引文不符权威  : {len(quote_mismatch)} 处（相似度<0.55）")
    print("=" * 70)

    if out_of_range:
        print("\n【A】条号越界（必错，优先修）")
        for x in out_of_range[:30]:
            print(f"  《{x['law_raw']}》第{x['art']}条  (该法共{x['max']}条/{x['version']})")
            print(f"     {x['file']}:{x['line']}")
        if len(out_of_range) > 30:
            print(f"  …另有 {len(out_of_range)-30} 处")

    if same_art_diff:
        print("\n【B】同条异文（同一条文在库内出现多种逐字内容）")
        for x in same_art_diff[:15]:
            print(f"  《{x['law']}》第{x['art']}条 —— {x['variants']} 种版本")
            for it in x["items"][:3]:
                print(f"     · {it['file']}:{it['line']}  “{it['quote'][:70]}…”")
        if len(same_art_diff) > 15:
            print(f"  …另有 {len(same_art_diff)-15} 组")

    if quote_mismatch:
        print("\n【C】引文与权威正文不符（含版本错引，按相似度升序）")
        for x in quote_mismatch[:15]:
            print(f"  《{x['law']}》第{x['art']}条  score={x['score']}  权威版本={x['version']}")
            print(f"     {x['file']}:{x['line']}")
            print(f"     卡片引文: {x['quote'][:90]}")
            print(f"     权威正文: {x['auth'][:90]}")
        if len(quote_mismatch) > 15:
            print(f"  …另有 {len(quote_mismatch)-15} 处")

    print("\n明细:", OUT)


if __name__ == "__main__":
    sys.exit(main())
