#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地法条源索引器（存量卡质量巡检配套）
- 扫描 LawKB 全库含「第X条」密集的 md，建立 (法规名, 条号) -> 正文 索引
- 自适应多种条号样式：**第X条** / 第X条　/ 第X条+U+2002 / 第X条 空格
- 落持久目录：02-提炼/审判要件卡/
"""
import os, re, json, glob

ROOT = "/Users/chenyouqiang/Documents/LawKB"
OUT = os.path.join(ROOT, "知识飞轮系统/02-提炼/审判要件卡/本地法条源索引-20260912.json")
MIN_SIZE = 3000          # 小于此字节视为指针页，跳过
MIN_ARTICLES = 8         # 条文数少于此数视为非全文

D = "零一二三四五六七八九"


def cn2num(s):
    """中文数字 -> int（支持 十/百/千）"""
    if not s:
        return None
    if s.isdigit():
        return int(s)
    v, cur = 0, 0
    for c in s:
        if c == "零":
            cur = 0
        elif c == "十":
            cur = (cur or 1) * 10
            v += cur
            cur = 0
        elif c == "百":
            cur = (cur or 1) * 100
            v += cur
            cur = 0
        elif c == "千":
            cur = (cur or 1) * 1000
            v += cur
            cur = 0
        elif c in D:
            cur = D.index(c)
        else:
            return None
    return v + cur


# 条号样式：行首 可选** 第X条 可选**
ART_RE = re.compile(
    r"(?m)^[\s>]*\*{0,2}第\s*([零一二三四五六七八九十百千]+)\s*条\*{0,2}[^\S\n]*(.*)$"
)


def parse_law(path):
    try:
        t = open(path, encoding="utf-8").read()
    except Exception:
        return None
    if len(t) < MIN_SIZE:
        return None
    hits = ART_RE.findall(t)
    if len(hits) < MIN_ARTICLES:
        return None
    arts = {}
    # 用位置切分取正文（到下一条或空行*2）
    marks = [(m.start(), m.end(), cn2num(m.group(1)), m.group(2).strip())
             for m in ART_RE.finditer(t)]
    marks = [x for x in marks if x[2] and x[2] > 0]
    if len(marks) < MIN_ARTICLES:
        return None
    for i, (st, en, num, head) in enumerate(marks):
        nxt = marks[i + 1][0] if i + 1 < len(marks) else len(t)
        body = t[en:nxt].strip()
        # 正文过长则截断（避免把整章吞进来）
        if len(body) > 800:
            body = body[:800] + "…"
        full = (head + " " + body).strip()
        if num not in arts or len(full) > len(arts[num]):
            arts[num] = full
    return arts


def main():
    cands = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames
                       if d not in {".git", "Backups", "node_modules", ".backup_link_20260830_152052"}]
        for fn in filenames:
            if fn.endswith(".md"):
                cands.append(os.path.join(dirpath, fn))
    idx = {}
    for p in cands:
        arts = parse_law(p)
        if not arts:
            continue
        rel = os.path.relpath(p, ROOT)
        base = os.path.basename(p)
        name = re.sub(r"\.md$", "", base)
        name = re.sub(r"（[^）]*）|\[[^\]]*\]|\([^)]*\)", "", name).strip()
        idx[rel] = {"name": name, "n_arts": len(arts), "arts": {str(k): v for k, v in arts.items()}}

    json.dump(idx, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"✅ 本地法条源索引已建：{len(idx)} 部法规 → {OUT}")
    print(f"   条文总数：{sum(v['n_arts'] for v in idx.values())}")
    print("\n=== 法规清单（按条文数降序，前 30）===")
    for rel, v in sorted(idx.items(), key=lambda kv: -kv[1]["n_arts"])[:30]:
        print(f"  {v['n_arts']:>4} 条  {v['name'][:40]:<42} {rel[:60]}")


if __name__ == "__main__":
    main()
