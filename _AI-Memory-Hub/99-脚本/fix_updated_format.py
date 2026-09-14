#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_updated_format.py — 修复被 Obsidian「update-time-on-edit」插件污染的时间格式

背景：
  该插件的 dateFormat 默认为 `yyyy-MM-dd'T'HH:mm`，会把 frontmatter 的
  `updated: 2026-09-14` 改写成 `updated: 2026-09-14T13:02`。
  这与本中枢 Schema 要求的 `YYYY-MM-DD` 不符。

根治手段（已于 2026-09-14 实施）：
  在 `LawKB/.obsidian/plugins/update-time-on-edit/data.json` 的
  `ignoreGlobalFolder` 中加入 `_AI-Memory-Hub`，
  **重启 Obsidian 后生效**，届时插件不再染指中枢。

本脚本用途：
  把已被污染的日期字段规范化回纯日期。幂等，可反复跑。

用法：
  python3 fix_updated_format.py --dry-run   # 只列出待修复
  python3 fix_updated_format.py --apply     # 修复（改前自动备份到 /tmp）
"""
import os
import re
import io
import shutil
import argparse
import datetime

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FM_RE = re.compile(r"^(---\s*\n)(.*?)(\n---\s*\n)", re.DOTALL)
# 匹配 `updated: 2026-09-14T13:02` 这类带时间后缀的日期字段
DATE_FIELDS = ("updated", "created", "expires")
DIRTY_RE = re.compile(
    r"^(%s):\s*(\d{4}-\d{2}-\d{2})T\d{2}:\d{2}(?::\d{2})?\s*$" % "|".join(DATE_FIELDS),
    re.MULTILINE)


def backup(files):
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    d = "/tmp/hub_datefix_备份_%s" % ts
    os.makedirs(d, exist_ok=True)
    n = 0
    for p in files:
        dst = os.path.join(d, os.path.relpath(p, HUB).replace("/", "__"))
        if not os.path.exists(dst):
            shutil.copy2(p, dst)
        n += 1
    return d, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    targets = []
    for dirpath, dirnames, files in os.walk(HUB):
        if os.path.basename(dirpath) in ("99-脚本", ".git"):
            continue
        for fn in files:
            if fn.endswith(".md") and not fn.startswith("."):
                p = os.path.join(dirpath, fn)
                try:
                    txt = io.open(p, encoding="utf-8").read()
                except Exception:
                    continue
                if DIRTY_RE.search(txt):
                    targets.append((p, txt))

    if not targets:
        print("✅ 未发现被污染的时间字段，无需修复。")
        return 0

    print("🔍 发现 %d 个文件的时间格式需要规范化：" % len(targets))
    for p, txt in targets:
        hits = DIRTY_RE.findall(txt)
        print("   - %s → %s" % (os.path.relpath(p, HUB),
                                ", ".join("%s=%s" % (k, v) for k, v in hits)))

    if not args.apply:
        print()
        print("📝 DRY-RUN：未做任何修改。确认后加 --apply。")
        return 0

    bkdir, n = backup([p for p, _ in targets])
    fixed = 0
    for p, txt in targets:
        new = DIRTY_RE.sub(lambda m: "%s: %s" % (m.group(1), m.group(2)), txt)
        if new != txt:
            io.open(p, "w", encoding="utf-8").write(new)
            fixed += 1
    print()
    print("✅ 已修复 %d 个文件" % fixed)
    print("🗂 备份目录：%s（%d 个）" % (bkdir, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
