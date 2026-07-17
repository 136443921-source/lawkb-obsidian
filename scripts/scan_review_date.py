#!/usr/bin/env python3
"""
扫描 Markdown 笔记 frontmatter 中的 review_date 字段，生成今日待复习笔记列表。
支持可选的企业微信文本消息推送。
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path


def parse_frontmatter(content: str):
    """解析 YAML frontmatter，返回 frontmatter 文本和正文起始位置。"""
    if not content.startswith("---"):
        return None, 0
    end = content.find("---", 3)
    if end == -1:
        return None, 0
    return content[3:end], end + 3


def extract_review_date(frontmatter: str):
    """从 frontmatter 中提取 review_date 字段值。"""
    match = re.search(r"^review_date:\s*(\S+)", frontmatter, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip('"').strip("'")


def scan_notes(root: Path, today: date, exclude_dirs=None):
    """扫描 root 下所有 .md 文件，返回今日待复习笔记列表。"""
    if exclude_dirs is None:
        exclude_dirs = {".workbuddy", "task-tracker"}

    pending_notes = []
    no_review_date_count = 0
    scanned_count = 0

    for md_file in root.rglob("*.md"):
        rel_parts = md_file.relative_to(root).parts
        if any(part.startswith(".") for part in rel_parts):
            continue
        if any(part in exclude_dirs for part in rel_parts):
            continue

        scanned_count += 1
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        frontmatter, _ = parse_frontmatter(content)
        if frontmatter is None:
            no_review_date_count += 1
            continue

        review_date_str = extract_review_date(frontmatter)
        if not review_date_str:
            no_review_date_count += 1
            continue

        try:
            review_date = datetime.strptime(review_date_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        days_diff = (today - review_date).days
        if days_diff >= 0:
            pending_notes.append({
                "path": str(md_file),
                "relative_path": str(md_file.relative_to(root)),
                "title": md_file.stem,
                "review_date": review_date_str,
                "days_overdue": days_diff,
                "status": "逾期" if days_diff > 0 else "今日到期",
            })

    pending_notes.sort(key=lambda x: (-x["days_overdue"], x["title"]))
    return {
        "scanned_count": scanned_count,
        "pending_notes": pending_notes,
        "no_review_date_count": no_review_date_count,
    }


def build_notification(today: date, pending_notes: list):
    """构建企业微信通知文本。"""
    overdue_count = sum(1 for n in pending_notes if n["days_overdue"] > 0)
    lines = [
        "【Spaced Repetition 复习提醒】",
        "",
        f"📅 日期：{today.isoformat()}",
        f"📝 待复习笔记数：{len(pending_notes)} 篇",
        f"⚠️ 逾期笔记：{overdue_count} 篇",
        "",
        "📋 今日待复习笔记：",
        "",
    ]
    for idx, note in enumerate(pending_notes, 1):
        if note["days_overdue"] > 0:
            lines.append(f"{idx}. [[{note['title']}]]（逾期 {note['days_overdue']} 天）")
        else:
            lines.append(f"{idx}. [[{note['title']}]]（今日到期）")
    lines.extend([
        "",
        "💡 复习建议：",
        f"- 打开 Obsidian，搜索 `review_date:{today.isoformat()}` 快速定位待复习笔记",
        "- 复习完成后，在 frontmatter 中更新 `review_date` 为下次复习时间（根据 SM-2 算法）",
    ])
    return "\n".join(lines)


def send_wecom_message(chatid: str, content: str, chat_type: int = 1):
    """通过 wecom-cli 发送企业微信文本消息。"""
    payload = {
        "chat_type": chat_type,
        "chatid": chatid,
        "msgtype": "text",
        "text": {"content": content},
    }
    cmd = ["wecom-cli", "msg", "send_message", json.dumps(payload, ensure_ascii=False)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr


def main():
    parser = argparse.ArgumentParser(description="扫描 Markdown 笔记的 review_date 并生成复习提醒")
    parser.add_argument("--root", required=True, help="笔记根目录")
    parser.add_argument("--today", help="指定日期（YYYY-MM-DD），默认今天")
    parser.add_argument("--output", help="输出 JSON 文件路径")
    parser.add_argument("--wecom-chatid", help="企业微信接收者 chatid")
    parser.add_argument("--wecom-chat-type", type=int, default=1, help="企业微信会话类型：1 单聊，2 群聊")
    args = parser.parse_args()

    root = Path(args.root)
    today = datetime.strptime(args.today, "%Y-%m-%d").date() if args.today else date.today()

    result = scan_notes(root, today)
    pending_notes = result["pending_notes"]

    output = {
        "date": today.isoformat(),
        "total_md_files_scanned": result["scanned_count"],
        "pending_count": len(pending_notes),
        "overdue_count": sum(1 for n in pending_notes if n["days_overdue"] > 0),
        "today_due_count": sum(1 for n in pending_notes if n["days_overdue"] == 0),
        "no_review_date_count": result["no_review_date_count"],
        "pending_notes": pending_notes,
    }

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已生成待复习列表：{output_path}")

    if pending_notes and args.wecom_chatid:
        notification = build_notification(today, pending_notes)
        ok, stdout, stderr = send_wecom_message(args.wecom_chatid, notification, args.wecom_chat_type)
        output["wecom_notification"] = {
            "sent": ok,
            "stdout": stdout,
            "stderr": stderr,
        }
        if not ok:
            print(f"企微通知发送失败：{stderr}", file=sys.stderr)

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
