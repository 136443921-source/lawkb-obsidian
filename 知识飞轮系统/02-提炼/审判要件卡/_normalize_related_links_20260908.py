#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
related_links 规范化器 v1.0.0（2026-09-08）
============================================
把不规范的 related_links 统一重写为标准 YAML 标量列表：

    related_links:
      - 项1
      - 项2

两种病灶（2026-09-08 实测，共 51 个文件）：
  ① 字符串型 18 个：related_links: "R-SH-024 R-SH-023, [xxx-原始]"
  ② 嵌套列表 33 个：related_links:\n  - - 项      （Obsidian 转坏产物，
     即记忆里 `looks_damaged()` 安全网 guarding 的 list-of-list）

为什么值得做数据层修复（不只在解析层兜底）：
  · 嵌套列表是 Obsidian 双向链接写入时转坏的，不根治会反复产生
  · 字符串型在 Obsidian 里根本不会被识别为链接（是个死字符串）
  · 规范化后 _check_deadlinks.py 的解析兜底可以退役

铁律：六-B —— 先备份 → dry-run → 幂等复验。

用法：
    python3 _normalize_related_links_20260908.py --dry-run
    python3 _normalize_related_links_20260908.py --apply
"""
import io
import os
import re
import shutil
import sys

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
SKIP = {".git", "node_modules", "__pycache__", ".workbuddy"}

sys.path.insert(0, os.path.join(ROOT, "02-提炼/审判要件卡"))
from _check_deadlinks import parse_related_links
import yaml

apply = "--apply" in sys.argv

# related_links 块：从该行起，到下一个顶格键 或 frontmatter 结束
BLOCK = re.compile(r"^related_links:.*?(?=^[A-Za-z_\u4e00-\u9fa5][^\s:]*\s*:|^---\s*$|\Z)",
                   re.M | re.S)


def is_junk(p):
    rel = os.path.relpath(p, ROOT).split(os.sep)
    for x in rel:
        if x.startswith("."):
            return True
    b = os.path.basename(p)
    return ".bak" in b or b.startswith("~")


def targets():
    for r, d, fs in os.walk(ROOT):
        d[:] = [x for x in d if x not in SKIP and not x.startswith(".backup")
                and not x.startswith(".trash")]
        for f in fs:
            if f.endswith(".md") and not is_junk(os.path.join(r, f)):
                yield os.path.join(r, f)


def needs_fix(fm):
    rl = fm.get("related_links")
    if rl is None:
        return False
    if isinstance(rl, str):
        return True
    if isinstance(rl, list):
        return any(isinstance(x, (list, tuple)) for x in rl)
    return False


def rewrite(path):
    t = io.open(path, encoding="utf-8").read()
    if not t.startswith("---"):
        return None
    head, sep, rest = t[3:].partition("\n---")
    if not sep:
        return None
    try:
        fm = yaml.safe_load(head) or {}
    except Exception:
        return None
    if not needs_fix(fm):
        return None

    items = parse_related_links(fm)
    # 去重保序
    seen, uniq = set(), []
    for x in items:
        if x not in seen:
            seen.add(x); uniq.append(x)

    if uniq:
        new_block = "related_links:\n" + "".join(f"  - {x}\n" for x in uniq)
    else:
        new_block = "related_links: []\n"

    new_head, n = BLOCK.subn(lambda m: new_block, head + "\n")
    if n != 1:
        return None
    return "---" + new_head.rstrip("\n") + "\n---" + rest, len(uniq)


plan = []
for p in targets():
    r = rewrite(p)
    if r:
        plan.append((p, r[0], r[1]))

print(f"📊 待规范化 {len(plan)} 个文件\n")
for p, _, n in plan[:20]:
    print(f"   {n:>2} 项  {p.replace(ROOT + '/', '')}")
if len(plan) > 20:
    print(f"   … 另有 {len(plan)-20} 个")

if not apply:
    print("\n⏸ DRY-RUN 结束，未写入")
    sys.exit(0)

BK = "/tmp/related_links规范化备份_20260908"
os.makedirs(BK, exist_ok=True)
for p, _, _ in plan:
    shutil.copy2(p, os.path.join(BK, os.path.relpath(p, ROOT).replace("/", "__")))
print(f"\n💾 已备份 {len(plan)} 个 → {BK}")

for p, new, _ in plan:
    io.open(p, "w", encoding="utf-8").write(new)
print(f"✏️  已写入 {len(plan)} 个文件")

# 幂等复验
left = sum(1 for p in targets() if rewrite(p))
print(f"🔁 幂等复验：仍需规范化 {left} 个 {'✅ 归零' if left == 0 else '❌'}")
