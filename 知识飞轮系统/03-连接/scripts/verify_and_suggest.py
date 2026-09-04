#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冲突候选 · 反向定位核验
对 A/B/C 每一条候选，在该法全部条文中做反向检索：
  - 若卡片所挂条号的正文 与 引文/要点 高度不符，
    但另一条号正文高度命中 → 判定「条号错配」，并给出应改的正确条号。
  - 若该法所有条文均不命中 → 判定「内容非本法/可能引自他法或已失效法」。
排除测试夹具（运维/LTI防幻觉* 中的 9999 条为刻意构造的假条号）。
输出: /tmp/lawkb_audit/verified_findings.json
"""
import json
import os
import re
import sys
from difflib import SequenceMatcher

IDX = "/Users/chenyouqiang/.workbuddy/skills/LTI文本监控器/references/provision_index"
SRC = "/tmp/lawkb_audit/conflicts_ABC.json"
OUT = "/tmp/lawkb_audit/verified_findings.json"

PUNCT = re.compile(r"[\s，。；：、？！“”‘’（）()《》〈〉\"'.,;:?!\-—_·　*#]+")


def norm(s):
    return PUNCT.sub("", s or "")


def ratio(a, b):
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


def load_laws():
    laws = {}
    mf = json.load(open(os.path.join(IDX, "manifest.json"), encoding="utf-8"))
    for law, meta in mf["laws"].items():
        fp = os.path.join(IDX, meta["file"])
        if not os.path.isfile(fp):
            continue
        d = json.load(open(fp, encoding="utf-8"))
        arts = d.get("articles", {})
        laws[law] = {
            "version": meta.get("version"),
            "count": meta.get("article_count"),
            "body": {k: (v or {}).get("body", "") for k, v in arts.items()},
            "nb": {k: norm((v or {}).get("body", "")) for k, v in arts.items()},
        }
    return laws


def is_test_fixture(path):
    return ("LTI防幻觉" in path) or ("防幻觉能力" in path)


def main():
    laws = load_laws()
    data = json.load(open(SRC, encoding="utf-8"))

    findings = {"A_confirmed": [], "A_test_fixture": [],
                "B_confirmed": [], "C_confirmed": [], "C_uncertain": []}

    # —— A 条号越界 ——
    for x in data["A_out_of_range"]:
        item = {"law": x["law_raw"], "art": x["art"], "max": x["max"],
                "version": x["version"], "file": x["file"], "line": x["line"],
                "ctx": x.get("ctx", "")[:150]}
        (findings["A_test_fixture"] if is_test_fixture(x["file"])
         else findings["A_confirmed"]).append(item)

    # —— B 同条异文：逐个变体做反向定位，看谁对谁错 ——
    for grp in data["B_same_art_diff"]:
        law, art = grp["law"], grp["art"]
        if law not in laws:
            continue
        nb = laws[law]["nb"]
        verdicts = []
        for it in grp["items"]:
            q = norm(it["quote"])
            own = best_containment(q, nb.get(str(art), ""))
            best_k, best_s = None, 0.0
            for k, body_n in nb.items():
                s = best_containment(q, body_n)
                if s > best_s:
                    best_s, best_k = s, k
            verdicts.append({
                "file": it["file"], "line": it["line"], "quote": it["quote"][:120],
                "score_at_cited": round(own, 3),
                "best_art": best_k, "best_score": round(best_s, 3),
            })
        findings["B_confirmed"].append({
            "law": law, "art": art,
            "auth_body": laws[law]["body"].get(str(art), "")[:200],
            "variants": verdicts,
        })

    # —— C 引文不符权威 ——
    for x in data["C_quote_mismatch"]:
        law, art, q = x["law"], x["art"], norm(x["quote"])
        if law not in laws:
            continue
        nb = laws[law]["nb"]
        own = best_containment(q, nb.get(str(art), ""))
        best_k, best_s = None, 0.0
        for k, body_n in nb.items():
            s = best_containment(q, body_n)
            if s > best_s:
                best_s, best_k = s, k
        item = {
            "law": law, "cited_art": art, "quote": x["quote"][:160],
            "score_at_cited": round(own, 3),
            "best_art": best_k, "best_score": round(best_s, 3),
            "file": x["file"], "line": x["line"],
            "cited_body": laws[law]["body"].get(str(art), "")[:160],
            "suggested_body": laws[law]["body"].get(str(best_k), "")[:160] if best_k else "",
        }
        if best_k and best_k != str(art) and best_s >= 0.72 and (best_s - own) >= 0.25:
            findings["C_confirmed"].append(item)     # 明确错配，且找到正确条号
        else:
            findings["C_uncertain"].append(item)     # 待人工（可能是分析要点非引文）

    json.dump(findings, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("=" * 72)
    print("反向定位核验结果")
    print("=" * 72)
    print(f"A 条号越界(真实)  : {len(findings['A_confirmed'])}   [测试夹具豁免 {len(findings['A_test_fixture'])}]")
    print(f"B 同条异文        : {len(findings['B_confirmed'])} 组")
    print(f"C 条号错配(可定案): {len(findings['C_confirmed'])}")
    print(f"C 待人工判定      : {len(findings['C_uncertain'])}")
    print("=" * 72)

    print("\n【A】条号越界（真实）")
    for x in findings["A_confirmed"]:
        print(f"  《{x['law']}》第{x['art']}条  (共{x['max']}条/{x['version']})")
        print(f"     {x['file']}:{x['line']}")
        print(f"     上下文: {x['ctx'][:110]}")
    print(f"\n  [豁免] 测试夹具 {len(findings['A_test_fixture'])} 处（LTI防幻觉评估用刻意假条号）:")
    for x in findings["A_test_fixture"]:
        print(f"     《{x['law']}》第{x['art']}条 @ {x['file']}:{x['line']}")

    print("\n【C】条号错配 —— 已定位正确条号（可直接改）")
    for x in findings["C_confirmed"]:
        print(f"  《{x['law']}》 第{x['cited_art']}条 → 应为 第{x['best_art']}条"
              f"   (命中 {x['score_at_cited']} → {x['best_score']})")
        print(f"     卡片内容: {x['quote'][:80]}")
        print(f"     所挂条({x['cited_art']})原文: {x['cited_body'][:70]}")
        print(f"     应为条({x['best_art']})原文: {x['suggested_body'][:70]}")
        print(f"     {x['file']}:{x['line']}")
        print()

    print("明细:", OUT)


if __name__ == "__main__":
    sys.exit(main())
