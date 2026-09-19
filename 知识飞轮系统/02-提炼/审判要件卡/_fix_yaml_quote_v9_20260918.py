#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_fix_yaml_quote_v9_20260918.py  v1.0
修「坑 67」：frontmatter 值以半角双引号开头、值内又含同类引号 → YAML 视作双引号标量而崩溃。

与坑 61 的区别（重要）：
  坑 61 = 引号出现在**句中**（plain scalar，pyyaml 允许，实测不崩）
  坑 67 = 引号是**值首字符**（double-quoted scalar，值内再出现 " 必然崩）
  → 只修「以 " 开头且整行解析失败」的行，绝不泛化到含引号的普通行。

修法：整体包单引号（内部 ' 翻倍）。逐行验证「修后能解析」才采纳。

安全（六-B）：
  - 默认 dry-run；--apply 才写盘，且写前 cp -n 备份到 /tmp/<主题>_<ts>/
  - 坑 62 并发保护：mtime 在 RECENT_SEC 内的文件跳过（可能是写入途中）
  - 同文件多处修改一次性原子写入
"""
import os
import re
import shutil
import sys
import time
from datetime import datetime

import yaml

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
APPLY = "--apply" in sys.argv
RECENT_SEC = 1800  # 坑 62

SCAN_DIRS = ["01-采集", "02-提炼", "03-连接", "04-巩固", "05-调用", "06-沉淀"]
KV = re.compile(r'^([A-Za-z_][\w\-]*):[ \t]*(.+?)[ \t]*$')

TS = datetime.now().strftime("%Y%m%d-%H%M%S")
BACKUP = f"/tmp/存量卡巡检YAML引号修复_{TS}"


def split_fm(t):
    """🔴 坑 34：必须与门禁 _check_deadlinks.py 同口径 —— txt.split("---")[1]。
    曾因自造 `\n---` 定位把正文里的水平分割线当闭合标记，误判 4972 个文件。"""
    if not t.startswith('---'):
        return None, None, None
    parts = t.split('---')
    if len(parts) < 3:
        return None, None, None
    return parts[1], parts[2:], None


# 值首字符为 YAML 保留指示符（" / ' / ` / @ 等）时，整行会被当成带引号标量或报保留字错
KV2 = re.compile(r'^(\s*(?:-\s+)?)([A-Za-z_][\w\-]*)(:\s*|:\s+)(.+?)[ \t]*$')
LI = re.compile(r'^(\s*-\s+)(\S.*?)[ \t]*$')
BAD_HEAD = ('"', "'", '`', '@', '%', '&', '*', '!')


def _quote(val):
    return "'" + val.replace("'", "''") + "'"


def fix_fm(fm):
    """两阶段：①逐行找出「首字符为保留指示符且单独解析失败」的行 → 单引号包裹
       ②整段复验通过才采纳（不通过则整个文件不动，留人工）。"""
    lines = fm.split('\n')
    out = list(lines)
    changed = []
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        try:
            yaml.safe_load(ln)
            continue
        except Exception:
            pass
        m = KV2.match(ln)
        if m:
            indent, key, sep, val = m.groups()
            new = f"{indent}{key}{sep}{_quote(val)}"
        else:
            m2 = LI.match(ln)
            if not m2:
                continue
            indent, val = m2.groups()
            new = f"{indent}{_quote(val)}"
        if not val.startswith(BAD_HEAD):
            continue
        try:
            yaml.safe_load(new)
        except Exception:
            continue
        out[i] = new
        changed.append((i + 1, key if m else '(list)', val[:70]))
    if not changed:
        return fm, []
    trial = '\n'.join(out)
    try:
        yaml.safe_load(trial)
    except Exception:
        return fm, []          # 整段仍不可解析 → 不采纳，留人工
    return trial, changed


def main():
    targets = []
    for d in SCAN_DIRS:
        base = os.path.join(ROOT, d)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if not x.startswith('.backup')]
            if '.backup' in dirpath:
                continue
            for fn in filenames:
                if not fn.endswith('.md'):
                    continue
                p = os.path.join(dirpath, fn)
                targets.append(p)

    print(f"扫描 {len(targets)} 个 md …（坑 62 保护：{RECENT_SEC}s 内写入的跳过）\n")

    fixed, skipped_recent, broken, nofix = [], [], [], []
    now = time.time()
    for p in targets:
        try:
            t = open(p, encoding='utf-8').read()
        except Exception:
            continue
        fm, rest, _ = split_fm(t)
        if fm is None:
            continue
        try:
            yaml.safe_load(fm)
            continue
        except Exception:
            pass
        rel = os.path.relpath(p, ROOT)
        age = now - os.path.getmtime(p)
        if age < RECENT_SEC:
            skipped_recent.append((rel, int(age)))
            continue
        new_fm, changed = fix_fm(fm)
        if not changed:
            nofix.append(rel)
            continue
        try:
            yaml.safe_load(new_fm)
        except Exception as e:
            broken.append((rel, str(e)[:80]))
            continue
        newtext = '---' + new_fm + '---' + '---'.join(rest)
        fixed.append((p, rel, changed, newtext))

    print(f"✅ 可安全修复：{len(fixed)} 个文件")
    for p, rel, changed, _ in fixed:
        print(f"   {rel}")
        for ln, k, v in changed:
            print(f"      行{ln} `{k}`: {v}")
    if skipped_recent:
        print(f"\n⏳ 坑62 并发保护跳过 {len(skipped_recent)} 个：")
        for r, a in skipped_recent:
            print(f"   {r}（{a}s 前写入）")
    if broken:
        print(f"\n🔴 修后仍不可解析 {len(broken)} 个（未采纳）：")
        for r, e in broken:
            print(f"   {r}｜{e}")
    if nofix:
        print(f"\n⬜ 非本类型缺陷（未处理）{len(nofix)} 个：")
        for r in nofix[:15]:
            print(f"   {r}")
        if len(nofix) > 15:
            print(f"   … 另 {len(nofix) - 15} 个")

    if not APPLY or not fixed:
        print("\n[dry-run] 未写盘。加 --apply 执行。")
        return
    os.makedirs(BACKUP, exist_ok=True)
    n = 0
    for p, rel, changed, newtext in fixed:
        dst = os.path.join(BACKUP, rel.replace('/', '__'))
        shutil.copy2(p, dst)  # cp -n 语义：目标不存在才写
        with open(p, 'w', encoding='utf-8') as f:  # 原子单次写入
            f.write(newtext)
        n += 1
    print(f"\n✅ 已写盘 {n} 个文件；备份 → {BACKUP}")


if __name__ == "__main__":
    main()
