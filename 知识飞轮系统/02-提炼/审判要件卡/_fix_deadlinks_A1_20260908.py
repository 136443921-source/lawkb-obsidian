#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A1 强匹配死链自动修复器 v1.0.0（2026-09-08）
==============================================
只修 **指纹完全相等** 的死链（差异仅在标点/空格/连字符/引号），零语义风险。

安全过滤（任一命中则跳过，转人工）：
  · 死链或目标长度 < 5        —— 排除 'x'→'X' 之类的单字符噪声
  · 含 [ ] # | 等 wiki 控制符 —— 排除嵌套错误写法（如 `第五章 [[医院…`）
  · 含 XXX / YYY / 待填 等占位符 —— 模板示例，不是真链接
  · 候选不唯一               —— 交给人工判
  · 纯数字 / 纯日期           —— 已在 A2，弱匹配不自动改

替换范围（不做裸文本全局替换，避免误伤正文叙述）：
  1. 正文 wiki 链接 [[old]] / [[old|别名]] / [[old#锚点]] / [[path/old]]
  2. frontmatter related_links 列表项（整项精确匹配，保留引号风格）

铁律：六-B —— 先备份 → dry-run → 复验至死链下降且无新增。

用法：
    python3 _fix_deadlinks_A1_20260908.py --dry-run
    python3 _fix_deadlinks_A1_20260908.py --apply
"""
import io
import json
import os
import re
import shutil
import sys

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
SKIP = {".backup", ".workbuddy", "__pycache__", ".git", "node_modules"}
JSON = os.path.join(ROOT, "02-提炼/审判要件卡/_deadlinks_20260908.json")

apply = "--apply" in sys.argv

# ── 载入 A1 映射 ───────────────────────────────────────────
data = json.load(io.open(JSON, encoding="utf-8"))
PLACEHOLD = re.compile(r"(XXX|YYY|ZZZ|待填|占位|示例|TBD|TODO)")

mapping = {}
skipped = []
for r in data["A1_强匹配"]:
    old, fix = r["link"], r.get("fix") or []
    if len(fix) != 1:
        skipped.append((old, f"候选 {len(fix)} 个，需人工")); continue
    new = fix[0]
    if len(old) < 5 or len(new) < 5:
        skipped.append((old, "过短，疑似解析噪声")); continue
    if re.search(r"[\[\]#|]", old):
        skipped.append((old, "含 wiki 控制符，疑似嵌套错误")); continue
    if PLACEHOLD.search(old) or PLACEHOLD.search(new):
        skipped.append((old, "含占位符，模板示例")); continue
    mapping[old] = new

print(f"📋 A1 强匹配 {len(data['A1_强匹配'])} 个 → 可自动修 {len(mapping)} 个，跳过 {len(skipped)} 个\n")
for o, why in skipped[:12]:
    print(f"   ⏭  跳过「{o}」：{why}")
if skipped:
    print()

# ── 替换函数 ───────────────────────────────────────────────
def fix_wiki(text, old, new):
    """[[old]] / [[old|别名]] / [[old#锚点]] / [[dir/old]] → 保留后缀"""
    pat = re.compile(r"\[\[\s*(?:[^\[\]|#]*/)?" + re.escape(old) +
                     r"\s*(\|[^\[\]]*)?(#[^\[\]]*)?\s*\]\]")
    return pat.sub(lambda m: "[[" + new + (m.group(1) or "") + (m.group(2) or "") + "]]", text)


def fix_fm(text, old, new):
    """frontmatter related_links 整项精确匹配（保留引号与行尾）"""
    pat = re.compile(r"^(\s*-\s*)(['\"]?)" + re.escape(old) + r"\2(\s*)$", re.M)
    return pat.sub(lambda m: f"{m.group(1)}{m.group(2)}{new}{m.group(2)}{m.group(3)}", text)


def process(path):
    t = io.open(path, encoding="utf-8").read()
    orig = t
    if t.startswith("---"):
        parts = t.split("---", 2)
        if len(parts) >= 3:
            fm, body = parts[1], parts[2]
            for o, n in mapping.items():
                fm = fix_fm(fm, o, n)
            t = "---" + fm + "---" + body
    for o, n in mapping.items():
        t = fix_wiki(t, o, n)
    return t, (t != orig)


# ── 扫描 ───────────────────────────────────────────────────
# 排除：备份副本 .bak*、回收站 .trash*、隐藏目录
# 教训（2026-09-08 dry-run 实测）：首版未过滤，把 .trash-dedup-20260819/
#   里的已删卡片和 *.bak_20260830 备份副本也改了 —— 改了等于没改（那些不参与
#   链接图），还白白扩大 blast radius。与「先排查确认非误报」同源。
def is_junk(p):
    rel = os.path.relpath(p, ROOT)
    parts = rel.split(os.sep)
    for x in parts:
        if x.startswith(".") and x not in {".workbuddy"}:
            return True                      # .trash* / .backup* / 其他隐藏目录
    base = os.path.basename(p)
    if ".bak" in base or base.startswith("~") or base.startswith("_backup"):
        return True
    return False


targets = []
for r, d, fs in os.walk(ROOT):
    d[:] = [x for x in d if x not in SKIP and not x.startswith(".backup")
            and not x.startswith(".trash")]
    for f in fs:
        if f.endswith(".md") and not is_junk(os.path.join(r, f)):
            targets.append(os.path.join(r, f))

changed = []
for p in targets:
    try:
        new, ch = process(p)
    except Exception as e:
        print(f"⚠️ {p}: {e}"); continue
    if ch:
        changed.append((p, new))

print(f"📊 将修改 {len(changed)} 个文件")
for p, _ in changed[:15]:
    print(f"   · {p.replace(ROOT + '/', '')}")
if len(changed) > 15:
    print(f"   … 另有 {len(changed)-15} 个")

if not apply:
    print("\n⏸ DRY-RUN 结束，未写入")
    sys.exit(0)

# ── 备份 + 写入 ────────────────────────────────────────────
BK = "/tmp/A1死链修复备份_20260908"
os.makedirs(BK, exist_ok=True)
for p, _ in changed:
    rel = p.replace(ROOT + "/", "").replace("/", "__")
    shutil.copy2(p, os.path.join(BK, rel))
print(f"\n💾 已备份 {len(changed)} 个 → {BK}")

for p, new in changed:
    io.open(p, "w", encoding="utf-8").write(new)
print(f"✏️  已写入 {len(changed)} 个文件")
print("\n🔁 请重跑 _analyze_deadlinks_20260908.py 复验")
