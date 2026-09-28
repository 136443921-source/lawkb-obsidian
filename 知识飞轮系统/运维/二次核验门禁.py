#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
二次核验门禁 · 日期字段硬伤检查
=================================
立规来源：2026-09-27 裁决项二次核验铁律（老强拍板）
对应事故卡：经验卡-待裁决项须二次核验-未核验即输出致七处误判-20260927.md（第 7 条：日期写错）

用法：
    python3 二次核验门禁.py <file.md> [file2.md ...]
    python3 二次核验门禁.py --stdin        # 从 stdin 读路径

退出码：
    0 = 全部通过
    1 = 发现硬伤（禁止交付）

检查项（C1 输出卫生）：
    1. frontmatter 中 created / updated 的日期是否等于系统当天
    2. 「数据来源：YYYY-MM-DD」形样的正文日期是否与当天冲突
    3. 文件名中的 -YYYYMMDD / -YYYY-MM-DD 日期段是否与当天冲突
"""

import sys
import re
import datetime
from pathlib import Path

TODAY = datetime.date.today()

DATE_FM = re.compile(r'^\s*(created|updated)\s*:\s*(\d{4})-(\d{2})-(\d{2})')
DATE_BODY = re.compile(r'数据来源[：:]\s*(\d{4})-(\d{2})-(\d{2})')
DATE_NAME = re.compile(r'(\d{4})-(\d{2})-(\d{2})')
DATE_NAME_COMPACT = re.compile(r'(?<!\d)(\d{4})(\d{2})(\d{2})(?!\d)')


def parse_frontmatter(text: str) -> str:
    if not text.startswith('---'):
        return ''
    end = text.find('\n---', 3)
    return text[:end] if end != -1 else text[:2000]


def check(path: Path) -> list:
    issues = []
    raw = path.read_text(encoding='utf-8', errors='replace')
    fm = parse_frontmatter(raw)

    for line in fm.splitlines():
        m = DATE_FM.match(line)
        if not m:
            continue
        field, y, mo, d = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))
        # 判据与 date_gate_hook.py 统一：仅「未来日期」判违。
        # 历史文件的 created/updated 本就是旧日期，按「≠今天」会误伤。
        try:
            if (y, mo, d) > (TODAY.year, TODAY.month, TODAY.day):
                issues.append(
                    f"{path}: frontmatter `{field}` = {y:04d}-{mo:02d}-{d:02d} "
                    f"为未来日期（当天 {TODAY.isoformat()}）"
                )
        except ValueError:
            issues.append(f"{path}: frontmatter `{field}` 日期非法：{line.strip()}")

    for m in DATE_BODY.finditer(raw):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if (y, mo, d) > (TODAY.year, TODAY.month, TODAY.day):
            issues.append(
                f"{path}: 正文「数据来源」= {y:04d}-{mo:02d}-{d:02d} "
                f"为未来日期（当天 {TODAY.isoformat()}）"
            )

    name = path.name
    for m in DATE_NAME.finditer(name):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if (y, mo, d) > (TODAY.year, TODAY.month, TODAY.day):
            issues.append(
                f"{path}: 文件名日期段 = {y:04d}-{mo:02d}-{d:02d} "
                f"为未来日期（当天 {TODAY.isoformat()}）"
            )
        break
    else:
        for m in DATE_NAME_COMPACT.finditer(name):
            s = m.group(0)
            try:
                dt = datetime.datetime.strptime(s, '%Y%m%d').date()
            except ValueError:
                continue
            # 判据同前两处：仅「未来日期」判违（YYYYMMDD 连写形态）
            if dt > TODAY:
                issues.append(
                    f"{path}: 文件名日期段 = {dt.isoformat()} "
                    f"为未来日期（当天 {TODAY.isoformat()}）"
                )
            break

    return issues


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == '--stdin':
        paths = [l.strip() for l in sys.stdin if l.strip()]
    elif args:
        paths = args
    else:
        print(__doc__)
        return 0

    all_issues = []
    checked = 0
    for p in paths:
        path = Path(p)
        if not path.exists():
            all_issues.append(f"{path}: 文件不存在，跳过")
            continue
        checked += 1
        all_issues.extend(check(path))

    print(f"二次核验门禁 · 系统日期 {TODAY.isoformat()}")
    print(f"已检文件：{checked}")
    print("-" * 52)
    if not all_issues:
        print("✅ C1 日期字段全绿 — 可交付")
        return 0
    for i in all_issues:
        print(f"❌ {i}")
    print("-" * 52)
    print("🚫 存在硬伤，按铁律「未二次核验不出文件」，禁止交付")
    return 1


if __name__ == '__main__':
    sys.exit(main())
