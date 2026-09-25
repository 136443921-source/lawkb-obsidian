#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A 线执行后最终校验：库计数 / 断链率 / 双维度撞号复核"""
import os, re, collections

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
RID_RE = re.compile(r"^rule_id:\s*(\S+)", re.M)
VALID = re.compile(r"^R-([A-Z]{2})-\d{1,3}$")
SKIP = [".backup", ".trash", "_quarantine", ".backup_link", "__pycache__", ".trash_a"]

NEWLIB = {
    "PI": "人伤法域库", "HT": "合同风险规则库", "AY": "案由路由卡族",
    "CF": "慈善合规域库", "PR": "证据规则卡族",
}

def all_md(root):
    out = []
    for dp, dn, fn in os.walk(root):
        if any(x in dp for x in SKIP):
            continue
        for f in fn:
            if f.endswith(".md"):
                out.append(os.path.join(dp, f))
    return out

# 1) 新库计数
print("=== 1) 5 个新一级库文件计数 ===")
lib_count = {}
for dom, lib in NEWLIB.items():
    d = os.path.join(ROOT, "06-沉淀", lib)
    n = len([1 for p in all_md(d)]) if os.path.exists(d) else 0
    lib_count[dom] = n
    print(f"  {lib}: {n}")
total = sum(lib_count.values())
print(f"  合计: {total}")

# 2) canonical 断链率（扫描 03-连接/02-提炼 全部 canonical）
print("\n=== 2) canonical 断链率 ===")
broken = []
checked = 0
for d in ["03-连接", "02-提炼"]:
    for p in all_md(os.path.join(ROOT, d)):
        txt = open(p, encoding="utf-8", errors="ignore").read()
        m = re.search(r"^canonical:\s*(\S+)", txt, re.M)
        if m:
            checked += 1
            target = os.path.join(ROOT, m.group(1))
            if not os.path.exists(target):
                broken.append((os.path.relpath(p, ROOT), m.group(1)))
print(f"  检查 canonical 引用 {checked} 条，断链 {len(broken)} 条")
for rel, t in broken[:20]:
    print(f"    [断链] {rel} → {t}")

# 3) 双维度撞号复核（每个新库内：文件名维度 + frontmatter rule_id 维度）
print("\n=== 3) 双维度撞号复核（新库内） ===")
conflicts = 0
for dom, lib in NEWLIB.items():
    d = os.path.join(ROOT, "06-沉淀", lib)
    if not os.path.exists(d):
        continue
    fn_rids = collections.Counter()
    fm_rids = collections.Counter()
    for p in all_md(d):
        bn = os.path.basename(p)
        m = re.match(r"(R-[A-Z]{2}-\d+)", bn)
        if m:
            fn_rids[m.group(1)] += 1
        h = open(p, encoding="utf-8", errors="ignore").read(2500)
        mr = RID_RE.search(h)
        if mr and VALID.match(mr.group(1)):
            fm_rids[mr.group(1)] += 1
    c_fn = [k for k, v in fn_rids.items() if v > 1]
    c_fm = [k for k, v in fm_rids.items() if v > 1]
    if c_fn or c_fm:
        conflicts += 1
        print(f"  [{lib}] 文件名撞号 {c_fn} | frontmatter撞号 {c_fm}")
    else:
        print(f"  [{lib}] OK（无撞号）")
print(f"  撞号库数: {conflicts}")

# 4) 关键单卡核验
print("\n=== 4) 关键单卡核验 ===")
checks = [
    ("06-沉淀/裁判规则库/慈善/R-CF-173-捐赠财产指定专项基金用途不能实现捐赠人可撤销并请求返还.md", "R-CF-173 A 应已删除(移入.trash_a)"),
    ("06-沉淀/合同风险规则库/R-HT-299-合同相对性实际交易方认定.md", "R-HT-102 B→R-HT-299 应在合同风险规则库"),
    ("06-沉淀/人伤法域库/R-PI-425-医疗告知义务代签与举证不能.md", "R-PI-157 B→R-PI-425 应在人伤法域库"),
    ("06-沉淀/合同风险规则库/R-LN-118-代理意见写作规范.md", "R-HT-101 B→R-LN-118 (LN号, 留合同风险目录)"),
]
for rel, desc in checks:
    p = os.path.join(ROOT, rel)
    print(f"  {'✅存在' if os.path.exists(p) else '❌缺失'} {rel}\n       {desc}")

# 裁判规则库剩余主卡数
remain = len([1 for p in all_md(os.path.join(ROOT, "06-沉淀", "裁判规则库"))
              if not os.path.dirname(p).endswith(".trash_a")])
print(f"\n=== 裁判规则库剩余主卡（不含.trash_a）: {remain} ===")
print("\n[校验完成]")
