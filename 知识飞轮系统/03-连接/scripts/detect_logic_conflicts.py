#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法理逻辑冲突 · 候选检测（D）

思路：同一法条下，不同卡片若作出**相反取向**的结论，即为潜在法理逻辑冲突。
      1) 取 裁判规则库 / 经验卡片 的卡片（含结论句）
      2) 按 (法, 条) 聚类
      3) 抽取含"取向极性"的结论句（支持/不支持、应当/不应、有效/无效…）
      4) 同条号下出现相反极性 → 输出候选对，供人工裁定

⚠️ 本检测只产出**候选**，不自动定性（严禁误报）：相反极性可能是
   "不同情形下的不同结论"（合法），需人工读原文裁定。
输出: /tmp/lawkb_audit/logic_conflicts.json
"""
import json
import os
import re
import sys
from collections import defaultdict

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT = "/tmp/lawkb_audit/logic_conflicts.json"

# 极性词表：(正向词, 负向词, 概念名)
POLARITY = [
    (r"予以支持|应予支持|应当支持|支持(?!.*不予)", r"不予支持|不支持|驳回", "支持/驳回"),
    (r"应当(?!不)", r"不应当|不应", "应当/不应"),
    (r"可以(?!不)", r"不可以|不得", "可以/不得"),
    (r"有效", r"无效", "有效/无效"),
    (r"应当承担|应承担责任|承担赔偿责任", r"不承担|免责|免除责任", "承担/免责"),
    (r"解除(?!不予)", r"不予解除|不予支持解除|不解除", "解除/不解除"),
    (r"采信|采纳", r"不采信|不予采信|不采纳", "采信/不采信"),
    (r"构成(?!不)", r"不构成", "构成/不构成"),
    (r"准许|准予", r"不准许|不予准许", "准许/不准许"),
]

CITE_RE = re.compile(
    r"《([^》]{2,60})》\s*第\s*([0-9〇一二三四五六七八九十百千万零两]{1,12})\s*条")
CN = {"零": 0, "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
      "六": 6, "七": 7, "八": 8, "九": 9, "两": 2}
UNIT = {"十": 10, "百": 100, "千": 1000}


def cn2int(s):
    if s.isdigit():
        return int(s)
    tot = sec = num = 0
    for ch in s:
        if ch in CN:
            num = CN[ch]
        elif ch in UNIT:
            sec += (num or 1) * UNIT[ch]
            num = 0
        elif ch == "万":
            sec = (sec + num) * 10000
            tot += sec
            sec = num = 0
        else:
            return None
    return tot + sec + num


CONCL_KEYS = ("结论", "裁判规则", "规则", "要点", "裁判要点", "要旨")


def extract_conclusions(text):
    """抓取含取向极性的结论性句子"""
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if not s or s.startswith(("#", "|", "-", "*", ">", "```")):
            continue
        for pos, neg, name in POLARITY:
            hit_p = re.search(pos, s)
            hit_n = re.search(neg, s)
            if hit_p and not hit_n:
                out.append((name, "+", s[:180]))
            elif hit_n and not hit_p:
                out.append((name, "-", s[:180]))
    return out


def main():
    cards = []
    targets = []
    for base in ("06-沉淀/裁判规则库", "02-提炼/经验卡片", "02-提炼/律师实务指引"):
        p = os.path.join(ROOT, base)
        if os.path.isdir(p):
            targets.append(p)

    for base in targets:
        for dp, dns, fns in os.walk(base):
            dns[:] = [d for d in dns if not d.startswith(".") and not d.startswith("_backup")]
            for fn in fns:
                if not fn.endswith(".md"):
                    continue
                # 剔除索引/聚合页（天然同时含正反结论，必为误报）
                if re.search(r"(索引|MOC|index|清单|目录|README|汇总|台账)", fn, re.I):
                    continue
                fp = os.path.join(dp, fn)
                if os.path.basename(fn).replace(".md", "") in ("裁判规则库",):
                    continue
                try:
                    txt = open(fp, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                arts = set()
                for m in CITE_RE.finditer(txt):
                    a = cn2int(m.group(2))
                    if a:
                        arts.add((m.group(1), a))
                if not arts:
                    continue
                concl = extract_conclusions(txt)
                if not concl:
                    continue
                cards.append({
                    "file": os.path.relpath(fp, ROOT),
                    "title": fn.replace(".md", ""),
                    "arts": sorted(arts),
                    "concl": concl,
                })

    # 按 (法,条) 聚类
    by_art = defaultdict(list)
    for c in cards:
        for a in c["arts"]:
            by_art[a].append(c)

    # 严格口径：按 (法, 条, 概念) 聚类，且正/反必须来自**不同卡片**
    # （同一卡片针对不同情形给出不同结论属正常法理，不算冲突）
    by_key = defaultdict(lambda: {"+": [], "-": []})
    for (law, art), group in by_art.items():
        for c in group:
            seen = set()
            for name, sign, s in c["concl"]:
                k = (name, sign)
                if k in seen:          # 同卡同概念同取向只记一次
                    continue
                seen.add(k)
                by_key[(law, art, name)][sign].append(
                    {"file": c["file"], "title": c["title"], "text": s})

    conflicts = []
    for (law, art, name), d in by_key.items():
        pf = {x["file"] for x in d["+"]}
        nf = {x["file"] for x in d["-"]}
        if not pf or not nf:
            continue
        if not (pf - nf) and not (nf - pf):   # 正反完全来自同一批文件 → 非跨卡冲突
            continue
        if len(pf | nf) < 2:
            continue
        conflicts.append({
            "law": law, "art": art, "concept": name,
            "n_cards": len(pf | nf),
            "positive": d["+"][:3], "negative": d["-"][:3],
        })

    conflicts.sort(key=lambda x: -x["n_cards"])
    json.dump(conflicts, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print("=" * 72)
    print("D 法理逻辑冲突 · 候选（同条号下出现相反取向结论）")
    print("=" * 72)
    print(f"纳入卡片      : {len(cards)}")
    print(f"候选冲突条号  : {len(conflicts)}")
    print("=" * 72)
    for c in conflicts[:12]:
        print(f"\n《{c['law']}》第{c['art']}条 ·【{c['concept']}】—— 跨 {c['n_cards']} 张卡取向相反")
        for x in c["positive"][:2]:
            print(f"   [+] {x['title'][:44]}")
            print(f"       {x['text'][:92]}")
        for x in c["negative"][:2]:
            print(f"   [-] {x['title'][:44]}")
            print(f"       {x['text'][:92]}")
    if len(conflicts) > 12:
        print(f"\n  …另有 {len(conflicts)-12} 条号存在相反取向")
    print("\n明细:", OUT)


if __name__ == "__main__":
    sys.exit(main())
