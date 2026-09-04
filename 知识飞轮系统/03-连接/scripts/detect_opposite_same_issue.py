#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法理逻辑冲突 · 精筛（D-2）
只比对「同一议题」却结论相反的卡片对：
  - 标题字符 2-gram Jaccard 相似度 >= 阈值 → 判定同一议题
  - 且两者在同一概念上取向相反 → 输出候选
目的：排除审判要件卡 support/reject 分情形字段造成的海量误报
输出: /tmp/lawkb_audit/issue_opposites.json
"""
import json
import os
import re
import sys
from collections import defaultdict
from itertools import combinations

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT = "/tmp/lawkb_audit/issue_opposites.json"

POLARITY = [
    (r"予以支持|应予支持|应当支持|支持(?!.*不予)|成立", r"不予支持|不支持|驳回|不成立", "支持/驳回"),
    (r"应当(?!不)", r"不应当|不应", "应当/不应"),
    (r"可以(?!不)", r"不可以|不得", "可以/不得"),
    (r"有效(?!.*不)", r"无效", "有效/无效"),
    (r"应当承担|应承担责任|承担赔偿责任", r"不承担|免责|免除责任", "承担/免责"),
    (r"适用(?!.*不)", r"不适用", "适用/不适用"),
    (r"构成(?!不)", r"不构成", "构成/不构成"),
    (r"采信|采纳", r"不采信|不予采信", "采信/不采信"),
]
def real_title(txt, fn):
    """取卡片真实描述性标题：frontmatter title: > 首个 # 标题 > 文件名
    （文件名常为裸编号 R-SH-020，拿它算相似度会全是假信号）"""
    m = re.search(r"^\s*title\s*:\s*(.+)$", txt, re.M)
    if m:
        t = m.group(1).strip().strip("'\"")
        if t and not re.fullmatch(r"R-[A-Z]{2}-\d{3}", t):
            return t
    for line in txt.split("\n"):
        s = line.strip()
        if s.startswith("# ") and len(s) > 3:
            return s.lstrip("# ").strip()
    return fn.replace(".md", "")


STOP = re.compile(r"[^\u4e00-\u9fa5A-Za-z0-9]")


def bigrams(s):
    s = STOP.sub("", s)
    return {s[i:i + 2] for i in range(len(s) - 1)} or {s}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def polarity_of(text):
    """返回 {概念: 取向集合}"""
    res = defaultdict(set)
    for line in text.split("\n"):
        s = line.strip()
        if not s or s.startswith(("#", "|", "-", "*", ">", "```")):
            continue
        for pos, neg, name in POLARITY:
            hp, hn = re.search(pos, s), re.search(neg, s)
            if hp and not hn:
                res[name].add("+")
            elif hn and not hp:
                res[name].add("-")
    return res


def main():
    cards = []
    for base in ("06-沉淀/裁判规则库", "02-提炼/经验卡片", "02-提炼/律师实务指引"):
        p = os.path.join(ROOT, base)
        if not os.path.isdir(p):
            continue
        for dp, dns, fns in os.walk(p):
            dns[:] = [d for d in dns if not d.startswith(".") and not d.startswith("_backup")]
            for fn in fns:
                if not fn.endswith(".md"):
                    continue
                if re.search(r"(索引|MOC|index|清单|目录|README|汇总|台账)", fn, re.I):
                    continue
                fp = os.path.join(dp, fn)
                try:
                    txt = open(fp, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                pol = polarity_of(txt)
                if not pol:
                    continue
                # 裸编号文件名无描述力，须取真实标题
                if re.fullmatch(r"R-[A-Z]{2}-\d{3}", fn.replace(".md", "")):
                    pass                      # 允许，标题由 real_title 提升
                title = real_title(txt, fn)
                if re.fullmatch(r"R-[A-Z]{2}-\d{3}", title):
                    continue                  # 仍取不到描述性标题 → 无法判议题，跳过
                cards.append({"file": os.path.relpath(fp, ROOT),
                              "title": title, "pol": {k: sorted(v) for k, v in pol.items()},
                              "bg": bigrams(title), "txt": txt})

    pairs = []
    for a, b in combinations(cards, 2):
        sim = jaccard(a["bg"], b["bg"])
        if sim < 0.34:                      # 不同议题，跳过
            continue
        for concept in set(a["pol"]) & set(b["pol"]):
            pa, pb = set(a["pol"][concept]), set(b["pol"][concept])
            # 一方纯正、另一方纯负 → 明确相反
            if (pa == {"+"} and pb == {"-"}) or (pa == {"-"} and pb == {"+"}):
                pairs.append({
                    "sim": round(sim, 3), "concept": concept,
                    "a": {"file": a["file"], "title": a["title"]},
                    "b": {"file": b["file"], "title": b["title"]},
                    "a_sign": "".join(sorted(pa)), "b_sign": "".join(sorted(pb)),
                })

    pairs.sort(key=lambda x: -x["sim"])
    json.dump(pairs, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("=" * 72)
    print("D-2 法理逻辑冲突 · 精筛（同一议题 + 结论相反）")
    print("=" * 72)
    print(f"纳入卡片 : {len(cards)}")
    print(f"同议题相反结论候选 : {len(pairs)} 对")
    print("=" * 72)
    for p in pairs[:15]:
        print(f"\n[相似 {p['sim']}] 概念【{p['concept']}】  {p['a_sign']} vs {p['b_sign']}")
        print(f"   A(+) {p['a']['title'][:56]}")
        print(f"        {p['a']['file']}")
        print(f"   B(-) {p['b']['title'][:56]}")
        print(f"        {p['b']['file']}")
    if len(pairs) > 15:
        print(f"\n  …另有 {len(pairs)-15} 对")
    print("\n明细:", OUT)


if __name__ == "__main__":
    sys.exit(main())
