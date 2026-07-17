#!/usr/bin/env python3
import os
import re
import json
from datetime import datetime, date
from pathlib import Path

ROOT = Path("/Users/chenyouqiang/Documents/LawKB")
TODAY = date(2026, 7, 13)
OUTPUT = ROOT / "task-tracker" / f"今日待复习笔记-{TODAY.isoformat()}.json"

def extract_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    return parts[1]

def parse_review_date(frontmatter: str):
    m = re.search(r"review_date:\s*(\d{4}-\d{2}-\d{2})", frontmatter)
    if m:
        return date.fromisoformat(m.group(1))
    return None

def note_title(path: Path):
    # Use first H1 if available, otherwise filename
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return path.stem

notes = []
for path in ROOT.rglob("*.md"):
    if ".git" in path.parts or ".workbuddy" in path.parts:
        continue
    fm = extract_frontmatter(path)
    if fm is None:
        continue
    rd = parse_review_date(fm)
    if rd is None:
        continue
    notes.append({
        "path": str(path),
        "title": note_title(path),
        "review_date": rd.isoformat(),
        "days_until_due": (rd - TODAY).days,
        "due_status": "今日到期" if rd == TODAY else ("逾期" if rd < TODAY else "未来")
    })

pending = [n for n in notes if n["due_status"] in ("今日到期", "逾期")]
# Sort: overdue first, then by absolute days
pending.sort(key=lambda n: (n["due_status"] != "逾期", n["days_until_due"]))

overdue_count = sum(1 for n in pending if n["due_status"] == "逾期")
today_count = sum(1 for n in pending if n["due_status"] == "今日到期")

result = {
    "date": TODAY.isoformat(),
    "scanned_files": len(list(ROOT.rglob("*.md"))),
    "notes_with_review_date": len(notes),
    "pending_count": len(pending),
    "overdue_count": overdue_count,
    "today_due_count": today_count,
    "pending_notes": pending
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"扫描文件数: {result['scanned_files']}")
print(f"含 review_date 笔记: {result['notes_with_review_date']}")
print(f"今日待复习笔记: {result['pending_count']}")
print(f"  - 逾期: {overdue_count}")
print(f"  - 今日到期: {today_count}")
print(f"输出文件: {OUTPUT}")

# Print notification preview
print("\n--- 企微通知预览 ---")
print(f"【Spaced Repetition 复习提醒】\n")
print(f"📅 日期：{TODAY.isoformat()}")
print(f"📝 待复习笔记数：{len(pending)} 篇")
print(f"⚠️ 逾期笔记：{overdue_count} 篇\n")
print(f"📋 今日待复习笔记：\n")
for idx, n in enumerate(pending, 1):
    if n["due_status"] == "逾期":
        print(f"{idx}. [[{n['title']}]]（逾期 {abs(n['days_until_due'])} 天）")
    else:
        print(f"{idx}. [[{n['title']}]]（今日到期）")
print(f"\n💡 复习建议：")
print(f"- 打开 Obsidian，搜索 `review_date:{TODAY.isoformat()}` 快速定位待复习笔记")
print(f"- 复习完成后，在 frontmatter 中更新 `review_date` 为下次复习时间（根据 SM-2 算法）")
