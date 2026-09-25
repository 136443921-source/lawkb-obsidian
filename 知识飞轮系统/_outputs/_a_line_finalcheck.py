#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A 线 · 最终核对：重编号卡 rule_id / 全局唯一性 / 残留 canonical"""
import os, re, collections

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
RID = re.compile(r"^rule_id:\s*(\S+)", re.M)
ALIAS = re.compile(r"^aliases:", re.M)
SKIP = [".backup", ".trash", "_quarantine", ".backup_link", "__pycache__"]

def fm(p):
    h = open(p, encoding="utf-8", errors="ignore").read(2500)
    rid = RID.search(h)
    rid = rid.group(1).strip() if rid else None
    als = []
    if ALIAS.search(h):
        for line in h.splitlines():
            if re.match(r"^\s+-\s+\S+", line):
                als.append(line.strip())
    return rid, als

print("=== ① 三张重编号卡实测 ===")
expect = {
    "06-沉淀/合同风险规则库/R-HT-102-合同相对性实际交易方认定.md": "R-HT-299",
    "06-沉淀/人伤法域库/R-PI-157-医疗告知义务代签与举证不能.md": "R-PI-425",
    "06-沉淀/裁判规则库/合同风险/R-HT-101-代理意见写作规范.md": "R-LN-118",
}
for rel, exp in expect.items():
    p = os.path.join(ROOT, rel)
    rid, als = fm(p)
    ok = "✅" if rid == exp else "❌"
    print(f"  {ok} 期望 {exp} | 实测 rule_id={rid} | aliases={als[:4]}")

print("\n=== ② 5 个新库内 rule_id 全局唯一性（frontmatter 维度）===")
libs = ["人伤法域库", "合同风险规则库", "案由路由卡族", "慈善合规域库", "证据规则卡族"]
allrid = []
for lib in libs:
    d = os.path.join(ROOT, "06-沉淀", lib)
    for dp, dn, fn in os.walk(d):
        if any(x in dp for x in SKIP):
            continue
        for f in fn:
            if f.endswith(".md"):
                rid, _ = fm(os.path.join(dp, f))
                if rid:
                    allrid.append(rid)
c = collections.Counter(allrid)
dups = {k: v for k, v in c.items() if v > 1}
print(f"  含 rule_id 主卡: {len(allrid)} 张")
print(f"  重复 rule_id（真冲突）: {len(dups)} -> {dups if dups else '无 ✅'}")

print("\n=== ③ 指针 canonical 仍指向 裁判规则库 的残留 ===")
stale = []
for d in ["03-连接", "02-提炼"]:
    for dp, dn, fn in os.walk(os.path.join(ROOT, d)):
        if any(x in dp for x in SKIP):
            continue
        for f in fn:
            if not f.endswith(".md"):
                continue
            t = open(os.path.join(dp, f), encoding="utf-8", errors="ignore").read()
            m = re.search(r"^canonical:\s*(06-沉淀/裁判规则库/\S+)", t, re.M)
            if m:
                stale.append((os.path.relpath(os.path.join(dp, f), ROOT), m.group(1)))
print(f"  残留指向 裁判规则库 的指针: {len(stale)} 张")
for rel, t in stale:
    print(f"    [残留] {rel} → {t}")

print("\n=== ④ R-CF-173 A 删除确认 ===")
gone = not os.path.exists(os.path.join(ROOT, "06-沉淀/裁判规则库/慈善/R-CF-173-捐赠财产指定专项基金用途不能实现捐赠人可撤销并请求返还.md"))
trash = os.path.exists(os.path.join(ROOT, "06-沉淀/裁判规则库/.trash_a/R-CF-173-捐赠财产指定专项基金用途不能实现捐赠人可撤销并请求返还.md"))
print(f"  原位置缺失: {'✅' if gone else '❌'} | 已进入.trash_a: {'✅' if trash else '❌'}")
print("\n[最终核对完成]")
