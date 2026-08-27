#!/usr/bin/env python3
"""
批量顺延逾期复习日期脚本（2026-08-27 一次性使用）
功能：将所有 review_date < today 的逾期笔记的 review_date 统一顺延至下月同日（2026-09-27）。
安全机制：
  1. --dry-run 模式：只统计不写入
  2. manifest JSON 记录每篇笔记原始 review_date，可用于回滚
  3. 物理备份：按原目录结构 copy 到备份目录（cp -n 防覆盖语义，用 shutil.copy2 + exists 检查）
用法：
  python3 defer_overdue_20260827.py --dry-run   # 演练
  python3 defer_overdue_20260827.py --apply     # 正式执行
"""

import os, re, sys, json, shutil, datetime
from pathlib import Path

BASE = Path('/Users/chenyouqiang/Documents/LawKB/知识飞轮系统')
BACKUP_DIR = BASE / '.backup' / '批量顺延-20260827'
MANIFEST = BASE / '.backup' / '批量顺延-20260827' / 'manifest.json'

NEW_DATE = '2026-09-27'  # 下月同日
TODAY = datetime.date(2026, 8, 27)

FM_PATTERN = re.compile(r'^---\n(.*?)\n---', re.DOTALL)
RD_LINE_PATTERN = re.compile(r'(review_date:\s*["\']?)(\d{4}-\d{2}-\d{2})')

def scan_overdue():
    """扫描所有逾期笔记，返回 (path, old_date, overdue_days) 列表"""
    overdue = []
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if not d.startswith('.') or d == '.']
        for f in files:
            if not f.endswith('.md'):
                continue
            fp = Path(root) / f
            try:
                content = fp.read_text(encoding='utf-8')
            except Exception:
                continue
            fm_match = FM_PATTERN.match(content)
            if not fm_match:
                continue
            fm = fm_match.group(1)
            rd_match = RD_LINE_PATTERN.search(fm)
            if not rd_match:
                continue
            old_date_str = rd_match.group(2)
            try:
                old_date = datetime.datetime.strptime(old_date_str, '%Y-%m-%d').date()
            except ValueError:
                continue
            overdue_days = (TODAY - old_date).days
            if overdue_days > 0:
                overdue.append((fp, old_date_str, overdue_days))
    return overdue

def apply_defer(overdue):
    """备份 + 修改 review_date"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    changed, failed, skipped_backup = 0, 0, 0
    for fp, old_date, od_days in overdue:
        rel = fp.relative_to(BASE)
        # 物理备份（已存在则跳过，防覆盖）
        bak_path = BACKUP_DIR / rel
        if bak_path.exists():
            skipped_backup += 1
        else:
            bak_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fp, bak_path)
        manifest.append({
            'path': str(rel),
            'old_review_date': old_date,
            'new_review_date': NEW_DATE,
            'overdue_days': od_days,
        })
        # 修改原文：仅替换 frontmatter 内第一个 review_date 日期
        try:
            content = fp.read_text(encoding='utf-8')
            fm_match = FM_PATTERN.match(content)
            fm_new, n = RD_LINE_PATTERN.subn(
                lambda m: m.group(1) + NEW_DATE, fm_match.group(1), count=1)
            if n != 1:
                failed += 1
                continue
            new_content = '---\n' + fm_new + '\n---' + content[fm_match.end():]
            fp.write_text(new_content, encoding='utf-8')
            changed += 1
        except Exception as e:
            print(f'  [FAIL] {rel}: {e}')
            failed += 1
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return changed, failed, skipped_backup, len(manifest)

if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else '--dry-run'
    overdue = scan_overdue()
    print(f'扫描完成：逾期笔记 {len(overdue)} 篇')
    if not overdue:
        print('无逾期笔记，无需处理。')
        sys.exit(0)
    # 按逾期天数分布统计
    dist = {}
    for _, _, d in overdue:
        bucket = '1-7天' if d <= 7 else '8-14天' if d <= 14 else '15-30天' if d <= 30 else '30天以上'
        dist[bucket] = dist.get(bucket, 0) + 1
    print('逾期分布：', ' | '.join(f'{k}: {v}篇' for k, v in sorted(dist.items())))
    print('示例（前5篇）：')
    for fp, old_date, od in overdue[:5]:
        print(f'  {fp.relative_to(BASE)} : {old_date} → {NEW_DATE}')

    if mode == '--dry-run':
        print(f'\n[DRY-RUN] 未写入任何文件。将把 {len(overdue)} 篇 review_date 统一顺延至 {NEW_DATE}。')
    elif mode == '--apply':
        changed, failed, skipped_backup, total = apply_defer(overdue)
        print(f'\n[APPLY] 完成：修改 {changed} 篇 / 失败 {failed} 篇')
        print(f'备份目录：{BACKUP_DIR}（已存在跳过 {skipped_backup} 篇）')
        print(f'Manifest：{MANIFEST}（共 {total} 条记录，可用于回滚）')
    else:
        print('未知参数，使用 --dry-run 或 --apply')
        sys.exit(1)
