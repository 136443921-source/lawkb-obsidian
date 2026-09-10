#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
非法文件名概念页隔离器 v1.0.0（2026-09-08）
==============================================
背景：断链消解器 resolve_broken_links v1.2 把**链接原文**（含引号、换行、
      markdown 加粗）当文件名建「概念枢纽页」，产出文件名非法的垃圾页。
      其中 12 个形如 `"R-XX-NNN-标题".md`（引号包裹），与库内真卡片
      `R-XX-NNN-标题.md` 重复 → 造成死链检测器「候选 2 个」二义性。

策略（不硬删，可回滚）：
  · 去掉非法字符后，若库内已存在同名正规文件 → 判定为重复副本 → 隔离
  · 若不存在 → 重命名为清洗后的合法文件名（保住内容）
  · 清洗后仍非法（含换行等控制符）→ 隔离

隔离目录：/tmp/垃圾概念页隔离_20260908（可随时迁回）
"""
import os
import re
import shutil

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
ISO = "/tmp/垃圾概念页隔离_20260908"
os.makedirs(ISO, exist_ok=True)

BAD_CHARS = ['\n', '\r', '\t', '"', "'", '*', '`', '[[', ']]', '\\']
CTRL = re.compile(r"[\x00-\x1f\x7f]")


def clean_name(f):
    n = f[:-3] if f.endswith(".md") else f
    for c in BAD_CHARS:
        n = n.replace(c, "")
    n = CTRL.sub("", n).strip(" .-—")
    return n


# 全库合法基名集合
allbase = set()
for r, ds, fs in os.walk(ROOT):
    ds[:] = [x for x in ds if not x.startswith(".") and x != "node_modules"]
    for f in fs:
        if f.endswith(".md"):
            allbase.add(f[:-3])

targets = []
for r, ds, fs in os.walk(ROOT):
    ds[:] = [x for x in ds if not x.startswith(".") and x != "node_modules"]
    for f in fs:
        if f.endswith(".md") and any(c in f for c in BAD_CHARS):
            targets.append(os.path.join(r, f))

print(f"📊 文件名含非法字符：{len(targets)} 个\n")
dup = renamed = isolated = 0
for p in targets:
    f = os.path.basename(p)
    rel = p.replace(ROOT + "/", "")
    clean = clean_name(f)
    legal = clean and not any(c in clean for c in BAD_CHARS) and len(clean) >= 4
    if legal and clean in allbase and clean != f[:-3]:
        shutil.move(p, os.path.join(ISO, f))
        print(f"   🗑 重复副本 → 隔离  {rel[:80]}")
        dup += 1
    elif legal and clean != f[:-3]:
        np = os.path.join(os.path.dirname(p), clean + ".md")
        if not os.path.exists(np):
            shutil.move(p, np)
            print(f"   ✏️  重命名 → {clean[:60]}.md")
            renamed += 1
        else:
            shutil.move(p, os.path.join(ISO, f))
            print(f"   🗑 目标已存在 → 隔离  {rel[:60]}")
            dup += 1
    else:
        shutil.move(p, os.path.join(ISO, f))
        print(f"   🗑 清洗后仍非法 → 隔离  {rel[:60]}")
        isolated += 1

print(f"\n✅ 完成：重复隔离 {dup} / 重命名 {renamed} / 强制隔离 {isolated}")
print(f"📦 隔离目录：{ISO}（共 {len(os.listdir(ISO))} 项，可随时迁回）")
