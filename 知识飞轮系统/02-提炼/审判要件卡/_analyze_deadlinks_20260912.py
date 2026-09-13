#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
死链 370 条 分字段 / 分类型分析器（存量卡质量巡检·第 2 项）
判定每条死链的：
  S1 来源字段：related_links(frontmatter) / 正文[[..]]
  S2 类型：A 跨库误报(法律法规库/智能体技能库存在) / B 可自动修(库内唯一定位) /
           C 待建笔记(主题名·软引用) / D 真死链(库内无且非已知法规)
"""
import os, re, sys, json, glob
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
LAWKB = "/Users/chenyouqiang/Documents/LawKB"
OUT = os.path.join(BASE, "02-提炼/审判要件卡/死链分类报告-20260912.json")

SKIP_DIRS = {"node_modules", ".git", "Backups"}


def basenames(root):
    s = set()
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".backup")]
        for f in files:
            if f.endswith(".md"):
                s.add(f[:-3])
    return s


def md_files(root):
    out = []
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".backup")]
        for f in files:
            if f.endswith(".md"):
                out.append(os.path.join(r, f))
    return out


def parse_related_links(fm):
    rl = fm.get("related_links")
    if rl is None:
        return []
    if isinstance(rl, str):
        return [x for x in re.split(r"[,，、;；\s]+", rl.strip("[]")) if x]
    out = []
    def flat(x):
        if isinstance(x, list):
            for i in x:
                flat(i)
        elif x is not None:
            out.append(str(x).strip("[]'\" "))
    flat(rl)
    return [x for x in out if x]


def norm(link):
    s = str(link).strip().strip("[]")
    s = s.split("|")[0].split("#")[0]
    s = s.split("/")[-1]
    return s.strip()


def main():
    in_sys = basenames(BASE)
    # 扩展集：法律法规库 + 智能体技能库 + 知识库
    ext = set()
    for root in [os.path.join(LAWKB, "法律法规库"),
                 os.path.join(LAWKB, "智能体技能库"),
                 os.path.join(LAWKB, "知识库")]:
        if os.path.isdir(root):
            ext |= basenames(root)

    recs = []
    for p in md_files(BASE):
        try:
            txt = open(p, encoding="utf-8").read()
        except Exception:
            continue
        if not txt.startswith("---"):
            continue
        try:
            fm = yaml.safe_load(txt.split("---")[1]) or {}
        except Exception:
            continue
        rl = [norm(x) for x in parse_related_links(fm)]
        body = [norm(x) for x in re.findall(r"\[\[([^\]]+)\]\]", txt)]
        for src_field, lst in (("related_links", rl), ("body", body)):
            for n in lst:
                if not n or len(re.sub(r"[^一-鿿a-zA-Z0-9]", "", n)) < 2:
                    continue
                if n in in_sys:
                    continue
                # 分类
                ext_hit = next((e for e in ext if e == n), None)
                in_hits = [k for k in in_sys if k == n or k.startswith(n + "-")] \
                    if re.match(r"^R-[A-Z]{2}-\d+", n) else []
                if ext_hit:
                    kind = "A 跨库误报"
                elif len(in_hits) == 1:
                    kind = "B 可自动修"
                elif re.match(r"^(R-[A-Z]{2}-\d+|LC-\d+|IMA-\d+)", n):
                    kind = "D 真死链(编号引用)"
                elif re.match(r"^20\d\d-|第[一二三四五六七八九十]+[章章节]", n) or n == ".md":
                    kind = "E 语法残片"
                else:
                    kind = "C 待建笔记/主题名"
                recs.append({"file": os.path.relpath(p, BASE), "field": src_field,
                             "name": n, "kind": kind,
                             "target": ext_hit or (in_hits[0] if in_hits else None)})

    json.dump(recs, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(f"死链条目：{len(recs)}")
    print("\n=== 按类型 ===")
    for k, v in Counter(r["kind"] for r in recs).most_common():
        print(f"  {v:>4}  {k}")
    print("\n=== 按来源字段 ===")
    for k, v in Counter(r["field"] for r in recs).most_common():
        print(f"  {v:>4}  {k}")
    print("\n=== A 跨库误报 样例 8 ===")
    for r in [x for x in recs if x["kind"].startswith("A")][:8]:
        print(f"  {r['name'][:40]:<42} <- {r['file'][:44]}")
    print("\n=== B 可自动修 样例 10 ===")
    for r in [x for x in recs if x["kind"].startswith("B")][:10]:
        print(f"  {r['name'][:26]:<28} -> {r['target'][:50]}")
    print("\n=== C 待建笔记/主题名 样例 10 ===")
    for r in [x for x in recs if x["kind"].startswith("C")][:10]:
        print(f"  {r['name'][:44]:<46} [{r['field']}]")


if __name__ == "__main__":
    main()
