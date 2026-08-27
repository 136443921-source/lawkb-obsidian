#!/usr/bin/env python3
"""
错峰分散脚本：将 2026-09-27 到期的笔记按重要性摊平到 9 月下旬~10 月。
策略：星级越高越靠前，每天 20~35 篇。
"""
import os, re, json, shutil, argparse
from datetime import datetime, timedelta
from collections import defaultdict

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
TARGET_DATE = "2026-09-27"

# 分散策略（importance -> 起始日期, 天数）
# 按总数量 773 调配：
# 5星36 -> 9/27-9/28 (2天)
# 4星183 -> 9/29-10/4 (6天)
# 3星37 -> 10/5 (1天)
# 0+2星517 -> 10/6-10/22 (17天)
SCHEDULE = {
    5: ("2026-09-27", 2),
    4: ("2026-09-29", 6),
    3: ("2026-10-05", 2),
    2: ("2026-10-07", 17),
    0: ("2026-10-07", 17),
}

def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d")

def find_target_notes():
    notes = []
    for root, dirs, filenames in os.walk(BASE):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in filenames:
            if not f.endswith('.md'):
                continue
            fp = os.path.join(root, f)
            try:
                with open(fp, 'r', encoding='utf-8', errors='ignore') as fh:
                    content = fh.read()
            except Exception:
                continue
            m = re.search(r'review_date:\s*(\d{4}-\d{2}-\d{2})', content)
            if m and m.group(1) == TARGET_DATE:
                imp_m = re.search(r'importance:\s*(\d+)', content)
                imp = int(imp_m.group(1)) if imp_m else 0
                notes.append({"path": fp, "importance": imp, "content": content})
    return notes

def assign_dates(notes):
    # 按 importance 分组
    groups = defaultdict(list)
    for n in notes:
        groups[n["importance"]].append(n)

    assignments = []
    for imp in sorted(groups.keys(), reverse=True):
        group = groups[imp]
        # 按文件名排序保证确定性
        group.sort(key=lambda x: x["path"])
        if imp not in SCHEDULE:
            # 未配置的 importance，挂到最后一天
            start_str, days = "2026-10-22", 1
        else:
            start_str, days = SCHEDULE[imp]
        start = parse_date(start_str)
        per_day = max(1, len(group) // days)
        remainder = len(group) % days

        idx = 0
        for day_offset in range(days):
            cnt = per_day + (1 if day_offset < remainder else 0)
            date_str = (start + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            for _ in range(cnt):
                if idx >= len(group):
                    break
                assignments.append({
                    "path": group[idx]["path"],
                    "importance": imp,
                    "new_date": date_str,
                })
                idx += 1
    return assignments

def dry_run(assignments):
    print(f"【Dry Run】总计待分散: {len(assignments)} 篇")
    by_date = defaultdict(list)
    by_imp = defaultdict(int)
    for a in assignments:
        by_date[a["new_date"]].append(a)
        by_imp[a["importance"]] += 1

    print("\n按日期分布:")
    for d in sorted(by_date.keys()):
        items = by_date[d]
        imp_breakdown = ", ".join(
            f"{k}星:{v}" for k, v in sorted(
                {a['importance']: sum(1 for x in items if x['importance']==a['importance']) for a in items}.items(),
                reverse=True
            )
        )
        print(f"  {d}: {len(items)} 篇 ({imp_breakdown})")

    print(f"\n按重要性分布:")
    for imp in sorted(by_imp.keys(), reverse=True):
        stars = '★' * imp if imp > 0 else '☆'
        print(f"  {stars} ({imp}): {by_imp[imp]} 篇")
    return True

def apply_changes(assignments):
    backup_dir = os.path.join(BASE, ".backup", "错峰分散-20260827")
    os.makedirs(backup_dir, exist_ok=True)
    manifest = []
    changed = 0
    failed = 0

    for a in assignments:
        fp = a["path"]
        new_date = a["new_date"]
        try:
            with open(fp, 'r', encoding='utf-8') as fh:
                content = fh.read()

            # 备份（按相对路径）
            rel = os.path.relpath(fp, BASE)
            bak_fp = os.path.join(backup_dir, rel)
            os.makedirs(os.path.dirname(bak_fp), exist_ok=True)
            shutil.copy2(fp, bak_fp)

            new_content = re.sub(
                r'(review_date:\s*)\d{4}-\d{2}-\d{2}',
                r'\g<1>' + new_date,
                content
            )
            if new_content != content:
                with open(fp, 'w', encoding='utf-8') as fh:
                    fh.write(new_content)
                changed += 1
                manifest.append({
                    "file": rel,
                    "old_date": TARGET_DATE,
                    "new_date": new_date,
                    "importance": a["importance"]
                })
        except Exception as e:
            failed += 1
            print(f"  ❌ 失败: {fp} -> {e}")

    manifest_path = os.path.join(backup_dir, "manifest.json")
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 完成: {changed} 篇已修改, 失败 {failed} 篇")
    print(f"🗄  备份目录: {backup_dir}")
    print(f"📋 manifest: {manifest_path}")
    return changed, failed

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写入")
    parser.add_argument("--apply", action="store_true", help="执行写入")
    args = parser.parse_args()

    notes = find_target_notes()
    if not notes:
        print("未找到 review_date=2026-09-27 的笔记")
        exit(0)

    assignments = assign_dates(notes)

    if args.dry_run or not args.apply:
        dry_run(assignments)
        if not args.apply:
            print("\n加 --apply 执行实际写入")
    else:
        apply_changes(assignments)
