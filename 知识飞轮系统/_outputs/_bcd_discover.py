#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B/C/D 线侦察（只读）：基于 A 线迁移后的当前状态"""
import os, re, collections

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
RID = re.compile(r"^rule_id:\s*(\S+)", re.M)
TYPE = re.compile(r"^type:\s*(\S+)", re.M)
SKIP = [".backup", ".trash", "_quarantine", ".backup_link", "__pycache__"]

def fm(p):
    h = open(p, encoding="utf-8", errors="ignore").read(2500)
    rid = RID.search(h)
    typ = TYPE.search(h)
    return (rid.group(1).strip() if rid else None,
            typ.group(1).strip().strip('"') if typ else None)

CR = os.path.join(ROOT, "06-沉淀", "裁判规则库")

print("===== 裁判规则库 当前子目录结构（A 线后剩余）=====")
sub = collections.Counter()
sub_dom = collections.defaultdict(collections.Counter)
for dp, dn, fn in os.walk(CR):
    if any(x in dp for x in SKIP):
        continue
    rel = os.path.relpath(dp, CR)
    for f in fn:
        if f.endswith(".md"):
            sub[rel if rel != "." else "(根)"] += 1
            rid, typ = fm(os.path.join(dp, f))
            if rid and re.match(r"^R-([A-Z]{2})", rid):
                sub_dom[rel if rel != "." else "(根)"][rid[2:4]] += 1
for s, n in sorted(sub.items(), key=lambda x: -x[1]):
    doms = dict(sub_dom[s])
    print(f"  {s:24s} {n:4d}  | 域: {dict(doms)}")

print("\n===== B线：异类（非裁判规则内容）=====")
# 1) 明显异类子目录
for yilei in ["学习笔记", "公众号", "案例", "案例库"]:
    d = os.path.join(CR, yilei)
    if os.path.exists(d):
        n = sum(1 for dp, dn, fn in os.walk(d) if not any(x in dp for x in SKIP) for f in fn if f.endswith(".md"))
        print(f"  子目录 [{yilei}]: {n} 张")
# 2) DRFT 草稿（文件名或 rule_id 前缀）
drft = []
for dp, dn, fn in os.walk(CR):
    if any(x in dp for x in SKIP):
        continue
    for f in fn:
        if f.endswith(".md") and (f.startswith("R-DRFT") or "DRFT" in f):
            drft.append(os.path.relpath(os.path.join(dp, f), ROOT))
print(f"  DRFT 草稿（文件名含DRFT）: {len(drft)} 张")
for x in drft[:15]:
    print(f"      {x}")
# 3) type 非裁判规则卡 / 通用
non_cr = collections.Counter()
samples = []
for dp, dn, fn in os.walk(CR):
    if any(x in dp for x in SKIP):
        continue
    for f in fn:
        if not f.endswith(".md"):
            continue
        rid, typ = fm(os.path.join(dp, f))
        if typ and "裁判规则" not in typ and typ not in ("慈法合规",):
            non_cr[typ] += 1
            if len(samples) < 20:
                samples.append((os.path.relpath(os.path.join(dp, f), ROOT), typ))
print(f"  type 非'裁判规则卡'/慈法合规: {sum(non_cr.values())} 张 | 分布: {dict(non_cr)}")
for s, t in samples:
    print(f"      {s} [{t}]")

print("\n===== C线：跨子目录同域碎片（剩余裁判规则库内）=====")
# 按域聚合：该域分布在哪些子目录
dom_dirs = collections.defaultdict(set)
dom_count = collections.Counter()
for dp, dn, fn in os.walk(CR):
    if any(x in dp for x in SKIP):
        continue
    for f in fn:
        if not f.endswith(".md"):
            continue
        rid, typ = fm(os.path.join(dp, f))
        if rid and re.match(r"^R-([A-Z]{2})", rid):
            dom = rid[2:4]
            dom_dirs[dom].add(os.path.relpath(dp, CR) or "(根)")
            dom_count[dom] += 1
print("  跨≥2子目录的域（碎片）：")
for dom in sorted(dom_dirs, key=lambda d: -len(dom_dirs[d])):
    if len(dom_dirs[dom]) >= 2:
        print(f"    R-{dom}: {dom_count[dom]} 张，散 {len(dom_dirs[dom])} 处 -> {sorted(dom_dirs[dom])}")

print("\n===== D线：零散单卡族（<10 张的域）=====")
small = [(d, c) for d, c in dom_count.items() if c < 10]
for d, c in sorted(small, key=lambda x: x[1]):
    print(f"    R-{d}: {c} 张")
print(f"  零散域总数: {len(small)}，合计 {sum(c for _,c in small)} 张")

print("\n[侦察完成]")
