#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方案 C · 逻辑拆分标记器（幂等）
========================================================
给 06-沉淀/人伤法域库 每张 R-PI 卡写入 sub_domain 字段（不移动文件、不破坏链接）。
- 分类来源：人伤法域库-分类映射.csv（逐卡建议归属）
- 5 张待定已人工判定为 其它人损（R-PI-032/093/116/117/420）
- 幂等：已存在 sub_domain 则替换为目标值；缺失则插入到 rule_id 之后
- 双模式：默认 dry-run（只打印计划），加 --apply 才落盘

用法：
  python3 apply_subdomain_C.py            # dry-run
  python3 apply_subdomain_C.py --apply   # 写入
"""
import re, glob, os, csv, sys
from collections import Counter

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
D = os.path.join(ROOT, "06-沉淀/人伤法域库")
CSV = os.path.join(ROOT, "人伤法域库-分类映射.csv")
VALID = {"医疗人损", "交通人损", "工伤人损", "其它人损"}

def norm_key(s):
    m = re.match(r"(R-PI-\d+)", s)
    return m.group(1) if m else s

# 加载映射（待定 -> 其它人损）
mapping = {}
with open(CSV, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        k = norm_key(row["rule_id"])
        b = row["proposed_bucket"]
        if b.startswith("待定") or b not in VALID:
            b = "其它人损"
        mapping[k] = b

def insert_sub(fm, bucket):
    if re.search(r"^sub_domain:", fm, re.M):
        return re.sub(r"^sub_domain:.*$", f"sub_domain: {bucket}", fm, flags=re.M), "replaced"
    lines = fm.split("\n")
    out, done = [], False
    for ln in lines:
        out.append(ln)
        if not done and ln.startswith("rule_id:"):
            out.append(f"sub_domain: {bucket}")
            done = True
    if not done:
        return "\n".join(["---", f"sub_domain: {bucket}"] + lines[1:]), "inserted-top"
    return "\n".join(out), "inserted"

DRY = "--apply" not in sys.argv
log, fallback, errors = [], [], []
for path in sorted(glob.glob(os.path.join(D, "**", "R-PI-*.md"), recursive=True)):
    rid_full = os.path.basename(path)
    key = norm_key(rid_full)
    bucket = mapping.get(key, "其它人损")
    if bucket not in VALID:
        bucket = "其它人损"
    if key not in mapping:
        fallback.append(rid_full)
    txt = open(path, encoding="utf-8").read()
    m = re.search(r"^---\n(.*?)\n---", txt, re.S)
    if not m:
        errors.append((rid_full, "no-frontmatter")); continue
    new_fm, status = insert_sub(m.group(1), bucket)
    if DRY:
        log.append((key, bucket, status))
    else:
        open(path, "w", encoding="utf-8").write(txt[:m.start()+4] + new_fm + "\n" + txt[m.end()-3:])
        log.append((key, bucket, status))

cnt = Counter(b for _, b, _ in log)
print(("【DRY-RUN】" if DRY else "【APPLIED】") + f" 处理卡片数: {len(log)}")
for k, v in cnt.most_common():
    print(f"  {v:4d}  {k}")
if fallback:
    print(f"\n⚠️ 未命中映射、按其它人损兜底: {len(fallback)} 张 -> {fallback}")
if errors:
    print(f"\n❌ 错误: {errors}")
print("\n样例(前8):")
for r, b, s in log[:8]:
    print(f"  {r} -> {b} ({s})")
