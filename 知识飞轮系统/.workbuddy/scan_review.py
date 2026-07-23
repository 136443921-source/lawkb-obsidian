#!/usr/bin/env python3
"""Scan all .md files for review_date in YAML frontmatter and identify pending reviews."""
import os
import re
import json
import sys
from datetime import date, datetime

TODAY = date.today()
ROOT = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统'
OUTPUT = f'/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/04-巩固/今日待复习笔记-{TODAY.isoformat()}.json'
SKIP_DIRS = {'.workbuddy', '.git', 'node_modules', '__pycache__'}

def parse_frontmatter(text):
    """Extract YAML frontmatter from markdown text. Returns dict or None."""
    match = re.match(r'^---\s*\n(.*?)\n---', text, re.DOTALL)
    if not match:
        return None
    fm_text = match.group(1)
    result = {}
    for line in fm_text.split('\n'):
        line = line.strip()
        if ':' in line:
            key, _, val = line.partition(':')
            result[key.strip()] = val.strip().strip('"').strip("'")
    return result

def main():
    files_scanned = 0
    has_review_date = 0
    no_review_date = 0
    pending_notes = []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        # Skip hidden/output dirs
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        for fname in filenames:
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(dirpath, fname)
            files_scanned += 1
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                print(f"WARN: Cannot read {fpath}: {e}", file=sys.stderr)
                continue

            fm = parse_frontmatter(content)
            if fm is None:
                no_review_date += 1
                continue

            rd = fm.get('review_date', '').strip()
            if not rd:
                no_review_date += 1
                continue

            has_review_date += 1
            try:
                rd_date = datetime.strptime(rd, '%Y-%m-%d').date()
            except ValueError:
                print(f"WARN: Invalid review_date '{rd}' in {fpath}", file=sys.stderr)
                continue

            days_overdue = (TODAY - rd_date).days
            if days_overdue < 0:
                continue  # Not yet due

            title = fm.get('title', os.path.splitext(fname)[0])
            rel_path = os.path.relpath(fpath, ROOT)

            pending_notes.append({
                'file': rel_path,
                'title': title,
                'review_date': rd,
                'days_overdue': days_overdue,
                'status': '今日到期' if days_overdue == 0 else f'逾期 {days_overdue} 天'
            })

    # Sort: most overdue first
    pending_notes.sort(key=lambda x: x['days_overdue'], reverse=True)

    overdue_count = sum(1 for n in pending_notes if n['days_overdue'] > 0)
    today_due_count = sum(1 for n in pending_notes if n['days_overdue'] == 0)

    report = {
        'date': TODAY.isoformat(),
        'total_md_files_scanned': files_scanned,
        'has_review_date': has_review_date,
        'no_review_date': no_review_date,
        'pending_count': len(pending_notes),
        'overdue_count': overdue_count,
        'today_due_count': today_due_count,
        'pending_notes': pending_notes
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Files scanned: {files_scanned}")
    print(f"  with review_date: {has_review_date}")
    print(f"  without review_date: {no_review_date}")
    print(f"Pending: {len(pending_notes)} (overdue: {overdue_count}, today: {today_due_count})")
    print(f"Output: {OUTPUT}")

if __name__ == '__main__':
    main()
