#!/usr/bin/env python3
"""
修复脚本：处理 stagger 脚本漏掉的残留 2026-09-27 笔记。
精确匹配行首 review_date（不误匹配 last_review_date）。
按 importance 分配到合理区间（避免单日超 35）。
"""
import os, re, json, shutil, argparse
from datetime import datetime, timedelta
from collections import defaultdict

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
TARGET_DATE = "2026-09-27"
REVIEW_RE = re.compile(r'((?<!last_)review_date:\s*)(\d{4}-\d{2}-\d{2})')

# 残留 18 篇全为 5星，补到 9/27~10/1（5天）叠加在原 5星区间
FIX_SCHEDULE = {5: ("2026-09-27", 5)}  # 18篇 / 5天 ≈ 4/天

def find_residual():
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
            # 仅匹配行首 review_date
            m = REVIEW_RE.search(content)
            if m and m.group(2) == TARGET_DATE:
                imp_m = re.search(r'^\s*importance:\s*(\d+)', content, re.MULTILINE)
                imp = int(imp_m.group(1)) if imp_m else 0
                notes.append({"path": fp, "importance": imp, "content": content})
    return notes

def assign(notes):
    groups = defaultdict(list)
    for n in notes:
        groups[n["importance"]].append(n)
    assignments = []
    for imp in sorted(groups.keys(), reverse=True):
        group = sorted(groups[imp], key=lambda x: x["path"])
        start_str, days = FIX_SCHEDULE.get(imp, ("2026-10-24", 3))
        start = datetime.strptime(start_str, "%Y-%m-%d")
        per_day = max(1, len(group) // days)
        remainder = len(group) % days
        idx = 0
        for off in range(days):
            cnt = per_day + (1 if off < remainder else 0)
            d = (start + timedelta(days=off)).strftime("%Y-%m-%d")
            for _ in range(cnt):
                if idx >= len(group):
                    break
                assignments.append({"path": group[idx]["path"], "importance": imp, "new_date": d})
                idx += 1
    return assignments

def dry_run(assignments):
    print(f"【Fix Dry Run】残留待处理: {len(assignments)} 篇")
    by_date = defaultdict(int)
    for a in assignments:
        by_date[a["new_date"]] += 1
    for d in sorted(by_date):
        print(f"  {d}: +{by_date[d]} 篇")
    return True

def apply(assignments):
    backup_dir = os.path.join(BASE, ".backup", "错峰分散-修复-20260827")
    os.makedirs(backup_dir, exist_ok=True)
    manifest = []
    changed = 0
    failed = 0
    for a in assignments:
        fp = a["path"]
        try:
            with open(fp, 'r', encoding='utf-8') as fh:
                content = fh.read()
            rel = os.path.relpath(fp, BASE)
            bak_fp = os.path.join(backup_dir, rel)
            os.makedirs(os.path.dirname(bak_fp), exist_ok=True)
            shutil.copy2(fp, bak_fp)
            new_content = REVIEW_RE.sub(lambda m: m.group(1) + a["new_date"], content, count=1)
            if new_content != content:
                with open(fp, 'w', encoding='utf-8') as fh:
                    fh.write(new_content)
                changed += 1
                manifest.append({"file": rel, "old_date": TARGET_DATE, "new_date": a["new_date"], "importance": a["importance"]})
            else:
                failed += 1
                print(f"  ⚠️  未变更(可能正则未匹配): {fp}")
        except Exception as e:
            failed += 1
            print(f"  ❌ 失败: {fp} -> {e}")
    with open(os.path.join(backup_dir, "manifest.json"), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 修复完成: {changed} 篇已修改, 失败 {failed} 篇")
    print(f"🗄  备份: {backup_dir}")
    return changed, failed

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    notes = find_residual()
    if not notes:
        print("✅ 无残留 2026-09-27 笔记")
        exit(0)
    assignments = assign(notes)
    if args.dry_run or not args.apply:
        dry_run(assignments)
        if not args.apply:
            print("\n加 --apply 执行实际写入")
    else:
        apply(assignments)
