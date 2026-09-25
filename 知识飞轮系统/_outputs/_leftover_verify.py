#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""遗留项修复后最终校验"""
import os, re

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
RID = re.compile(r"^rule_id:\s*(\S+)", re.M)
SKIP = [".backup", ".trash", "_quarantine", ".backup_link", "__pycache__"]

def ridof(p):
    return RID.search(open(p, encoding="utf-8", errors="ignore").read(2500))

print("=== ① 5 新库内 rule_id:- 占位卡剩余 ===")
libs = ["人伤法域库", "合同风险规则库", "案由路由卡族", "慈善合规域库", "证据规则卡族"]
ph = 0
for lib in libs:
    d = os.path.join(ROOT, "06-沉淀", lib)
    for dp, dn, fn in os.walk(d):
        if any(x in dp for x in SKIP):
            continue
        for f in fn:
            if f.endswith(".md"):
                m = ridof(os.path.join(dp, f))
                if m and m.group(1).strip() == "-":
                    ph += 1
                    print(f"  [残留] {os.path.relpath(os.path.join(dp,f), ROOT)}")
print(f"  占位卡剩余: {ph} 张 {'✅' if ph==0 else '❌'}")

print("\n=== ② R-CF-186 重编号校验 ===")
p = os.path.join(ROOT, "06-沉淀/慈善合规域库/R-CF-076-慈善合规数值红线速查-LTI映射桥.md")
if os.path.exists(p):
    h = open(p, encoding="utf-8", errors="ignore").read(2500)
    print(f"  rule_id 行: {[l for l in h.splitlines() if l.startswith('rule_id')]}")
    print(f"  aliases 行: {[l for l in h.splitlines() if l.strip().startswith('- R-CF-076')]}")
else:
    print("  ❌文件缺失")

print("\n=== ③ 5 张 LN 指针 canonical 是否指向存在的文件 ===")
pdir = os.path.join(ROOT, "02-提炼", "经验卡片", "跨案模式识别")
bad = 0
for f in sorted(os.listdir(pdir)):
    if not f.endswith(".md"):
        continue
    if not re.match(r"R-LN-0(4[5-9]|50)", f):
        continue
    t = open(os.path.join(pdir, f), encoding="utf-8", errors="ignore").read()
    m = re.search(r"^canonical:\s*(\S+)", t, re.M)
    if m:
        target = os.path.join(ROOT, m.group(1))
        ok = "✅" if os.path.exists(target) else "❌断链"
        if not os.path.exists(target):
            bad += 1
        print(f"  {ok} {f} → {m.group(1)}")
print(f"  断链: {bad} 张 {'✅' if bad==0 else '❌'}")

print("\n=== ④ CF-052/053 孤儿隔离确认 ===")
for fn in ["R-CF-052-税前扣除资格双比例红线公益支出公募70非公募8管理费10-12.md",
           "R-CF-053-基金会互捐核心真实最终受益人执行方公开遴选募捐资金非自有资金.md"]:
    active = os.path.exists(os.path.join(ROOT, "06-沉淀/慈善合规域库", fn))
    trashed = os.path.exists(os.path.join(ROOT, "06-沉淀/慈善合规域库/.trash_cf", fn))
    print(f"  活跃区缺失:{'✅' if not active else '❌'} | .trash_cf存在:{'✅' if trashed else '❌'} | {fn}")
print("\n[校验完成]")
