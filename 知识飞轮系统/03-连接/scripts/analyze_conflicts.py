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
        art = c.get("art")
        if not law or art is None or law not in laws:
            continue
        cnt = laws[law]["count"]
        if art > cnt:
            out_of_range.append({**c, "max": cnt,
                                 "version": laws[law]["version"]})

    # —— B 同条异文：按 (law,art) 聚类逐字引文 ——
    by_key = defaultdict(list)
    for c in cites:
        if c.get("law") and c.get("quote") and len(c["quote"]) >= 10:
            by_key[(c["law"], c["art"])].append(c)

    for (law, art), group in sorted(by_key.items(), key=lambda x: (x[0][0], x[0][1] or 0)):
        reps = []
        for c in group:
            nq = norm(c["quote"])
            if not any(ratio(nq, norm(r["quote"])) >= 0.92 for r in reps):
                reps.append(c)
        if len(reps) > 1:
            same_art_diff.append({
                "law": law, "art": art, "variants": len(reps),
                "items": [{"file": r["file"], "line": r["line"],
                           "quote": r["quote"][:160]} for r in reps]
            })

    # —— C 引文 vs 权威正文 ——
    for c in cites:
        law, art, q = c.get("law"), c.get("art"), c.get("quote")
        if not law or art is None or not q or law not in laws:
            continue
        if len(norm(q)) < 10:
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
        if score < 0.55:
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
