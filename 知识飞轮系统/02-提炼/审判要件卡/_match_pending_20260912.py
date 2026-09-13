#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
待回源项 × 本地法条源索引 匹配器（存量卡质量巡检·第 1 项）
- 输入：42 张 statute_text_pending:true 卡 + 本地法条源索引-20260912.json
- 输出：可核填项 / 真无源项 清单（JSON），供 dry-run 报告
- 只做匹配与报告，不写卡（写卡由 apply 脚本负责）
"""
import os, re, json, glob

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
IDX = os.path.join(BASE, "02-提炼/审判要件卡/本地法条源索引-20260912.json")
OUT = os.path.join(BASE, "02-提炼/审判要件卡/待回源匹配报告-20260912.json")

# 源优先级（同法规多份时取优先级高的）
PRIORITY = [
    ("法律法规库/", 100),
    ("智能体技能库/红队出庭律师/常用法律法规库/", 90),
    ("知识库/慈法知识库/", 70),
    ("01-采集/法律法规/", 60),
    ("01-采集/IMA缓存/", 50),
    ("02-提炼/", 40),
]
SKIP_DIR = [".backup", ".backup_link", "Backups"]


def src_score(rel):
    for k, v in PRIORITY:
        if rel.startswith(k):
            return v
    return 10


def norm(s):
    """法规名归一化：去书名号/括号/空格/简称后缀"""
    s = re.sub(r"[《》〈〉（）()\[\]【】\s]", "", s)
    s = s.replace("中华人民共和国", "")
    s = re.sub(r"（(2023修订|2021修正|2012修正|全文|节选.*?|红队)）", "", s)
    return s


def build_lookup():
    idx = json.load(open(IDX, encoding="utf-8"))
    lut = {}   # norm_name -> (score, rel, arts)
    for rel, v in idx.items():
        if any(k in rel for k in SKIP_DIR):
            continue
        sc = src_score(rel)
        for key in {norm(v["name"]), norm(os.path.basename(rel).replace(".md", ""))}:
            if not key:
                continue
            if key not in lut or sc > lut[key][0]:
                lut[key] = (sc, rel, v["arts"])
    return lut


# 待回源条目解析
PEND_RE = re.compile(r"[>→\-\s]*⚠️\s*待回源[：:]\s*(.+)")
BOOK_RE = re.compile(r"《([^》]+)》")
ART_RE = re.compile(r"第\s*([零一二三四五六七八九十百千]+|\d+)\s*条")

D = "零一二三四五六七八九"
def cn2num(s):
    if s.isdigit():
        return int(s)
    v, cur = 0, 0
    for c in s:
        if c == "十":
            cur = (cur or 1) * 10; v += cur; cur = 0
        elif c == "百":
            cur = (cur or 1) * 100; v += cur; cur = 0
        elif c == "千":
            cur = (cur or 1) * 1000; v += cur; cur = 0
        elif c in D:
            cur = D.index(c)
        else:
            return None
    return v + cur


def main():
    lut = build_lookup()
    cards = []
    for p in sorted(glob.glob(os.path.join(BASE, "06-沉淀/裁判规则库/**/R-*.md"), recursive=True)):
        t = open(p, encoding="utf-8").read()
        if not re.search(r"(?m)^statute_text_pending: true", t):
            continue
        cards.append((p, t))

    fillable, unmatched = [], []
    for p, t in cards:
        for m in PEND_RE.finditer(t):
            raw = m.group(1).strip()
            line_end = t.find("\n", m.end())
            seg = t[m.start(): line_end if line_end > 0 else len(t)]
            books = BOOK_RE.findall(raw)
            arts = [cn2num(x) for x in ART_RE.findall(raw)]
            arts = [a for a in arts if a]
            rec = {"card": os.path.relpath(p, BASE), "raw": raw[:150], "seg": seg[:300],
                   "books": books, "arts": arts, "match": None}
            hit = None
            for b in books:
                key = norm(b)
                if key in lut:
                    sc, rel, a = lut[key]
                    got = {n: a[str(n)] for n in arts if str(n) in a}
                    if got or (not arts):
                        hit = {"law": b, "src": rel, "score": sc, "arts": got,
                               "n_arts_avail": len(a)}
                        break
            if hit:
                rec["match"] = hit
                fillable.append(rec)
            else:
                unmatched.append(rec)

    json.dump({"fillable": fillable, "unmatched": unmatched,
               "n_cards": len(cards)},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"待回源卡：{len(cards)} 张 | 待回源条目：{len(fillable)+len(unmatched)} 条")
    print(f"  ✅ 本地可核填：{len(fillable)} 条")
    print(f"  ⚠️  真无源：{len(unmatched)} 条")
    print("\n=== 可核填（按卡聚合）===")
    from collections import defaultdict
    g = defaultdict(list)
    for r in fillable:
        g[r["card"]].append(f'{r["match"]["law"]}' + (f'§{",".join(map(str,r["arts"]))}' if r["arts"] else ""))
    for k, v in sorted(g.items()):
        print(f"  {os.path.basename(k)[:52]}")
        for x in v:
            print(f"      - {x}")
    print("\n=== 真无源 样例 20 ===")
    for r in unmatched[:20]:
        print(f"  [{os.path.basename(r['card'])[:34]}] {r['raw'][:70]}")


if __name__ == "__main__":
    main()
