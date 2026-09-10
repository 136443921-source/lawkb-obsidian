#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YAML alias 冲突修复器 v1.0.0（2026-09-08）
==========================================
病灶：frontmatter 标量值以 `*` 开头（markdown 加粗 `**粗体**` 写在值首），
      YAML 把 `*` 解析为 **alias 锚点引用** → `while scanning an alias`。
      实测样本：02-提炼/经验卡片/思维轨迹/轨迹卡-习水光伏项目合同审查整链推理路径-20260907.md
                key_leverage: **投标文件公益捐赠环节是整个交易结构最薄弱的一环**……

修法：给以 `*` 开头的标量值加双引号（YAML 单引号内 `**` 无特殊含义）。
      只动 frontmatter，只动值以 `*` 开头的行，逐行最小改动。

注意与坑 1（YAML 半角引号）的关系：本修复**主动**给值加半角双引号，
      前提是该值内部不含双引号；含则改用单引号包裹。

用法：
    python3 _fix_yaml_alias_20260908.py --dry-run
    python3 _fix_yaml_alias_20260908.py --apply
"""
import io
import os
import re
import shutil
import sys

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
SKIP = {".git", "node_modules", "__pycache__", ".workbuddy"}
apply = "--apply" in sys.argv

import yaml

# 顶格键：值以 * 开头（前面至少一个空格）
STAR_VAL = re.compile(r"^([A-Za-z_\u4e00-\u9fa5][^\s:]*:\s+)(\*[^\n]*)$", re.M)


def targets():
    for r, d, fs in os.walk(ROOT):
        d[:] = [x for x in d if x not in SKIP and not x.startswith(".")
                and x not in {"node_modules"}]
        for f in fs:
            if f.endswith(".md"):
                yield os.path.join(r, f)


def yaml_err(text):
    if not text.startswith("---"):
        return None
    try:
        yaml.safe_load(text.split("---")[1])
        return None
    except Exception as e:
        return e


def fix(text):
    """返回 (新文本, 修改行数)"""
    head, sep, rest = text[3:].partition("\n---")
    if not sep:
        return text, 0
    n = 0

    def rep(m):
        nonlocal n
        val = m.group(2).rstrip()
        if '"' in val:
            new = "'" + val + "'"
        else:
            new = '"' + val + '"'
        n += 1
        return m.group(1) + new
    new_head = STAR_VAL.sub(rep, head)
    return ("---" + new_head + "\n---" + rest), n


plan = []
for p in targets():
    t = io.open(p, encoding="utf-8").read()
    e = yaml_err(t)
    if not e or "alias" not in str(e):
        continue
    new, n = fix(t)
    if n and yaml_err(new) is None:
        plan.append((p, new, n, str(e)[:60]))

print(f"📊 待修复 {len(plan)} 个文件\n")
for p, _, n, e in plan:
    print(f"   {n} 行  {p.replace(ROOT + '/', '')}")
    print(f"        原错误：{e}")

if not plan:
    print("\n✅ 无 alias 冲突")
    sys.exit(0)

if not apply:
    print("\n⏸ DRY-RUN 结束，未写入")
    sys.exit(0)

BK = "/tmp/yaml_alias修复备份_20260908"
os.makedirs(BK, exist_ok=True)
for p, _, _, _ in plan:
    shutil.copy2(p, os.path.join(BK, os.path.relpath(p, ROOT).replace("/", "__")))
print(f"\n💾 已备份 → {BK}")

for p, new, _, _ in plan:
    io.open(p, "w", encoding="utf-8").write(new)
print(f"✏️  已写入 {len(plan)} 个")

left = sum(1 for p in targets()
           if (e := yaml_err(io.open(p, encoding="utf-8").read())) and "alias" in str(e))
print(f"🔁 复验：残留 alias 错误 {left} 个 {'✅ 归零' if left == 0 else '❌'}")
