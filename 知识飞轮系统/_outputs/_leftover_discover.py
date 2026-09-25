#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""遗留项侦察（只读）：3 张 rule_id:- 占位卡 + 6 张 LN 断链指针目标定位"""
import os, re

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
RID = re.compile(r"^rule_id:\s*(\S+)", re.M)
SKIP = [".backup", ".trash", "_quarantine", ".backup_link", "__pycache__"]

def fm_rid(p):
    h = open(p, encoding="utf-8", errors="ignore").read(2500)
    m = RID.search(h)
    return m.group(1).strip() if m else None

print("===== A. 3 张 rule_id 占位卡（5 新库内）=====")
libs = ["人伤法域库", "合同风险规则库", "案由路由卡族", "慈善合规域库", "证据规则卡族"]
placeholder = []
for lib in libs:
    d = os.path.join(ROOT, "06-沉淀", lib)
    for dp, dn, fn in os.walk(d):
        if any(x in dp for x in SKIP):
            continue
        for f in fn:
            if not f.endswith(".md"):
                continue
            p = os.path.join(dp, f)
            rid = fm_rid(p)
            if rid == "-":
                m = re.match(r"R-([A-Z]{2})-(\d+)", f)
                dom = m.group(1) if m else "?"
                num = m.group(2) if m else "?"
                placeholder.append((p, dom, num))
                print(f"  文件: {os.path.relpath(p, ROOT)}")
                print(f"    文件名域/号: {dom}-{num} | 现 rule_id: {rid}")
# 检查文件名号是否已被其他卡 rule_id 占用（双维度）
print("\n  --- 文件名号是否被他人 rule_id 占用检查 ---")
for p, dom, num in placeholder:
    cand = f"R-{dom}-{num}"
    taken = False
    for lib in libs:
        d = os.path.join(ROOT, "06-沉淀", lib)
        for dp, dn, fn in os.walk(d):
            if any(x in dp for x in SKIP):
                continue
            for f in fn:
                if f.endswith(".md") and os.path.join(dp, f) != p:
                    if fm_rid(os.path.join(dp, f)) == cand:
                        taken = True
                        print(f"    [占用] {cand} 已被 {os.path.relpath(os.path.join(dp,f), ROOT)} 使用")
    if not taken:
        print(f"    [空闲] {cand} 可用 → 拟补 rule_id: {cand}")

print("\n===== B. 6 张 LN 断链指针目标定位 =====")
ln_ids = ["R-LN-045", "R-LN-046", "R-LN-047", "R-LN-048", "R-LN-049", "R-LN-050"]
# 主卡真实位置
main_loc = {}
for dp, dn, fn in os.walk(os.path.join(ROOT, "06-沉淀")):
    if any(x in dp for x in SKIP):
        continue
    for f in fn:
        for lid in ln_ids:
            if f.startswith(lid + "-") or f.startswith(lid + "_"):
                main_loc.setdefault(lid, []).append(os.path.relpath(os.path.join(dp, f), ROOT))
print("  主卡真实位置：")
for lid in ln_ids:
    print(f"    {lid}: {main_loc.get(lid, ['⚠️未找到'])}")

# 指针当前 canonical
print("\n  指针当前 canonical：")
ptr_dir = os.path.join(ROOT, "02-提炼", "经验卡片", "跨案模式识别")
for f in sorted(os.listdir(ptr_dir)):
    if not f.endswith(".md"):
        continue
    p = os.path.join(ptr_dir, f)
    t = open(p, encoding="utf-8", errors="ignore").read()
    m = re.search(r"^canonical:\s*(\S+)", t, re.M)
    if m and "裁判规则库/学习笔记" in m.group(1):
        print(f"    {f}")
        print(f"      现 canonical: {m.group(1)}")
        # 推断正确目标：同名主卡在律师实务
        lid = re.match(r"(R-LN-\d+)", f).group(1)
        cand = [x for x in main_loc.get(lid, []) if "律师实务" in x]
        print(f"      应改指向: {cand[0] if cand else '⚠️无律师实务主卡'}")
print("\n[侦察完成]")
