#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spaced Repetition 复习提醒 - 扫描脚本
扫描 /Users/chenyouqiang/Documents/LawKB/ 下所有 .md 笔记，
识别 frontmatter 中 review_date <= 今日 的笔记，生成待复习列表。
"""
import datetime
import json
import os
import re
import sys
from pathlib import Path

VAULT_ROOT = Path("/Users/chenyouqiang/Documents/LawKB")
TRACKER_DIR = VAULT_ROOT / "task-tracker"
EXCLUDE_DIRS = {".workbuddy", ".git", ".obsidian", ".trash", "node_modules"}

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
FIELD_RE = re.compile(r"^review_date\s*:\s*['\"]?(\d{4}-\d{2}-\d{2})['\"]?\s*$", re.MULTILINE)


def iter_md_files(root: Path):
    for path in root.rglob("*.md"):
        # 排除系统/隐藏目录
        parts = set(path.relative_to(root).parts)
        if parts & EXCLUDE_DIRS:
            continue
        yield path


def parse_review_date(text: str):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm = m.group(1)
    fm_match = FIELD_RE.search(fm)
    if not fm_match:
        return None
    try:
        return datetime.datetime.strptime(fm_match.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_title(text: str, fallback: str):
    m = FRONTMATTER_RE.match(text)
    if m:
        title_match = re.search(r"^title\s*:\s*['\"]?(.+?)['\"]?\s*$", m.group(1), re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()
    # 退化：取第一行非空文本
    for line in text.splitlines():
        line = line.strip().lstrip("#").strip()
        if line:
            return line[:80]
    return fallback


def main():
    today = datetime.date.today()
    today_str = today.isoformat()

    total = 0
    with_review = 0
    pending = []
    overdue = 0
    today_due = 0

    for path in iter_md_files(VAULT_ROOT):
        total += 1
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        rd = parse_review_date(text)
        if rd is None:
            continue
        with_review += 1
        if rd <= today:
            days_overdue = (today - rd).days
            if days_overdue > 0:
                overdue += 1
            else:
                today_due += 1
            try:
                rel = path.relative_to(VAULT_ROOT).as_posix()
            except ValueError:
                rel = str(path)
            title = parse_title(text, path.stem)
            pending.append({
                "title": title,
                "path": str(path),
                "rel_path": rel,
                "review_date": rd.isoformat(),
                "days_overdue": days_overdue,
                "today_due": days_overdue == 0,
            })

    # 按逾期天数降序排序（最该复习的排前面）
    pending.sort(key=lambda x: -x["days_overdue"])

    payload = {
        "date": today_str,
        "total_md_files": total,
        "notes_with_review_date": with_review,
        "pending_count": len(pending),
        "overdue_count": overdue,
        "today_due_count": today_due,
        "pending_reviews": pending,
    }

    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    out_path = TRACKER_DIR / f"今日待复习笔记-{today_str}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 简洁的 stdout 摘要
    print(f"日期: {today_str}")
    print(f"扫描笔记: {total} 篇")
    print(f"含 review_date: {with_review} 篇")
    print(f"待复习: {len(pending)} 篇 (今日到期 {today_due} / 逾期 {overdue})")
    if pending:
        print("\n今日待复习笔记列表：")
        for i, p in enumerate(pending, 1):
            tag = "【今日到期】" if p["today_due"] else f"【逾期 {p['days_overdue']} 天】"
            print(f"  {i}. {tag} {p['title']}")
            print(f"     -> {p['rel_path']}")
    print(f"\n结果文件: {out_path}")


if __name__ == "__main__":
    main()
