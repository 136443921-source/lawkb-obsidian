#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双书名号修复器 v1.0.0（2026-09-08）
====================================
病根：渲染器 render_laws() 硬编码 f"**《{v['law']}》{v['article']}**"，
      当回填库 law 字段本身已带书名号（如「《中华人民共和国环境保护法》」）
      时，渲染成「《《中华人民共和国环境保护法》》」。

铁律遵循：
  · 六-B：先备份 → dry-run → 确认非误报 → 再批量修改 → 复验
  · Fix-the-source：修模板（渲染器）优先于修产品（md 文件）

用法：
    python3 _fix_double_booktitle_20260908.py --dry-run   # 只报不改
    python3 _fix_double_booktitle_20260908.py --apply     # 实际修复

范围：06-沉淀/裁判规则库/ 全库 *.md
"""
import os
import re
import shutil
import sys
import time

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
LIB = os.path.join(ROOT, "06-沉淀/裁判规则库")

# 两种形态（2026-09-08 实测）：
#   A 型  《《中华人民共和国环境保护法》》      law 已带书名号，article 为空
#   B 型  《《...非法集资...意见》第九条第四款》  law 已带书名号，article 非空
#   C 型  《《民法典》侵权责任编》（历史 CF 卡）  同上，article = 编名
# 统一还原为「《law》article」
PAT = re.compile(r"《《(.+?)》([^》]*)》")

apply = "--apply" in sys.argv
if not apply:
    print("🔍 DRY-RUN 模式（加 --apply 才实际写入）\n")

# ── 1. 备份 ────────────────────────────────────────────────
BK = "/tmp/双书名号修复备份_20260908"
hits = {}
total = 0
for dp, dn, fn in os.walk(LIB):
    dn[:] = [d for d in dn if d not in {".backup", ".workbuddy", "__pycache__"}]
    for f in fn:
        if not f.endswith(".md"):
            continue
        p = os.path.join(dp, f)
        try:
            s = open(p, encoding="utf-8").read()
        except Exception as e:
            print(f"⚠️ 读取失败 {p}: {e}")
            continue
        ms = PAT.findall(s)
        if ms:
            hits[p] = (s, len(ms))
            total += len(ms)

print(f"📊 扫描结果：{len(hits)} 个文件含双书名号，共 {total} 处\n")

if not hits:
    print("✅ 无双书名号，无需修复")
    sys.exit(0)

for p, (s, n) in sorted(hits.items()):
    rel = p.replace(ROOT + "/", "")
    print(f"  {n:>3} 处  {rel}")
    for m in PAT.finditer(s):
        old = m.group(0)
        new = f"《{m.group(1)}》{m.group(2)}"
        print(f"        {old}  →  {new}")

if not apply:
    print("\n⏸ DRY-RUN 结束，未写入任何文件")
    sys.exit(0)

# ── 2. 备份 ────────────────────────────────────────────────
os.makedirs(BK, exist_ok=True)
for p in hits:
    rel = p.replace(ROOT + "/", "").replace("/", "__")
    shutil.copy2(p, os.path.join(BK, rel))
print(f"\n💾 已备份 {len(hits)} 个文件 → {BK}")

# ── 3. 修改 ────────────────────────────────────────────────
fixed = 0
for p, (s, n) in hits.items():
    ns = PAT.sub(lambda m: f"《{m.group(1)}》{m.group(2)}", s)
    if ns != s:
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(ns)
        fixed += n
print(f"✏️  已修复 {fixed} 处")

# ── 4. 复验（幂等性） ──────────────────────────────────────
left = 0
for p in hits:
    s = open(p, encoding="utf-8").read()
    left += len(PAT.findall(s))
print(f"🔁 复验：残留双书名号 {left} 处 {'✅ 归零' if left == 0 else '❌ 未清干净'}")
sys.exit(0 if left == 0 else 1)
