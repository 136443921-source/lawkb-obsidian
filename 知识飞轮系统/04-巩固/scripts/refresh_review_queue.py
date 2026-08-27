#!/usr/bin/env python3
"""
复习队列自动刷新脚本
功能：扫描知识飞轮系统中所有设置 review_date 的笔记，生成/更新复习队列 Markdown 文件。
使用：python3 refresh_review_queue.py
自动化：可由 Spaced Repetition 复习提醒（automation-1783209043138）或每日知识摄入任务调用。
"""

import os, re, datetime, json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent  # 知识飞轮系统/
QUEUE_PATH = BASE / '04-巩固' / 'Spaced-Repetition' / '复习队列.md'

FM_PATTERN = re.compile(r'^---\n(.*?)\n---', re.DOTALL)
RD_PATTERN = re.compile(r'review_date:\s*["\']?(\d{4}-\d{2}-\d{2})')
IMP_PATTERN = re.compile(r'importance:\s*(\d+)')
REP_PATTERN = re.compile(r'repetition:\s*(\d+)')
EF_PATTERN = re.compile(r'ease_factor:\s*([\d.]+)')
INT_PATTERN = re.compile(r'interval:\s*(\d+)')

def categorize(rel_path):
    if '经验卡片' in rel_path: return '经验卡片'
    if '裁判规则' in rel_path: return '裁判规则'
    if '05-调用' in rel_path or '案件管理' in rel_path: return '案件管理'
    if '人伤法' in rel_path or '医疗' in rel_path: return '人伤法'
    if '慈法' in rel_path: return '慈法合规'
    if '合同' in rel_path: return '合同文书'
    if '学习笔记' in rel_path: return '学习笔记'
    if '案例' in rel_path: return '案例摘要'
    if '法律法规' in rel_path: return '法律法规'
    return '其他'

def scan_notes():
    notes = []
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if not d.startswith('.')]  # 排除 .workbuddy/.backup/.trash/.cache 等隐藏目录
        for f in files:
            if not f.endswith('.md'): continue
            fp = os.path.join(root, f)
            try:
                with open(fp, 'r', encoding='utf-8') as fh:
                    content = fh.read(4096)
                fm_match = FM_PATTERN.match(content)
                if not fm_match: continue
                fm = fm_match.group(1)
                rd_match = RD_PATTERN.search(fm)
                if not rd_match: continue
                review_date_str = rd_match.group(1)
                try:
                    review_date = datetime.datetime.strptime(review_date_str, '%Y-%m-%d').date()
                except: continue

                imp_m = IMP_PATTERN.search(fm)
                importance = int(imp_m.group(1)) if imp_m else 3
                rep_m = REP_PATTERN.search(fm)
                repetition = int(rep_m.group(1)) if rep_m else 0
                ef_m = EF_PATTERN.search(fm)
                ease_factor = float(ef_m.group(1)) if ef_m else 2.5
                int_m = INT_PATTERN.search(fm)
                interval = int(int_m.group(1)) if int_m else 1

                rel = os.path.relpath(fp, BASE)
                name = f.replace('.md', '')
                today = datetime.date.today()
                overdue = (today - review_date).days

                notes.append({
                    'name': name, 'path': rel, 'review_date': review_date_str,
                    'overdue_days': overdue, 'importance': importance,
                    'repetition': repetition, 'ease_factor': ease_factor,
                    'interval': interval, 'category': categorize(rel),
                })
            except: pass
    notes.sort(key=lambda x: x['review_date'])
    return notes

def generate_queue(notes):
    today = datetime.date.today()
    today_str = today.strftime('%Y-%m-%d')
    now_str = today.strftime('%Y-%m-%dT%H:%M')

    overdue = sorted([n for n in notes if n['overdue_days'] > 0],
                     key=lambda x: (-x['importance'], -x['overdue_days']))
    today_review = sorted([n for n in notes if n['overdue_days'] == 0],
                          key=lambda x: -x['importance'])
    future_7d = sorted([n for n in notes if -7 <= n['overdue_days'] < 0],
                       key=lambda x: x['review_date'])
    future_30d = [n for n in notes if -30 <= n['overdue_days'] < -7]

    cat_count = defaultdict(int)
    cat_overdue = defaultdict(int)
    for n in notes:
        cat_count[n['category']] += 1
        if n['overdue_days'] > 0: cat_overdue[n['category']] += 1

    rep_count = defaultdict(int)
    for n in notes:
        rep_count[n['repetition']] += 1

    L = []
    L.append('---')
    L.append(f'created: 2026-07-04T19:00')
    L.append(f'updated: {now_str}')
    L.append('title: 复习队列')
    L.append('tags: [Spaced-Repetition, 复习, SM-2]')
    L.append('maturity: 🌳生长')
    L.append('---')
    L.append('')
    L.append('# 复习队列')
    L.append('')
    L.append(f'> [!info] 元数据')
    L.append(f'> **创建时间**：2026-07-04')
    L.append(f'> **最后更新**：{today_str}（自动刷新）')
    L.append(f'> **笔记类型**：Spaced Repetition复习管理')
    L.append(f'> **算法**：SM-2（SuperMemo-2）')
    L.append(f'> **刷新机制**：`知识飞轮系统/04-巩固/scripts/refresh_review_queue.py`')
    L.append('')
    L.append('---')
    L.append('')

    # Overdue
    L.append(f'## 一、逾期待复习（{len(overdue)}篇）')
    L.append('')
    if overdue:
        L.append('| 笔记名称 | 分类 | 复习日期 | 逾期天数 | 重要性 | 复习次数 |')
        L.append('|----------|------|----------|----------|--------|----------|')
        for n in overdue:
            stars = min(n['importance'], 5)
            L.append(f'| [[{n["name"]}]] | {n["category"]} | {n["review_date"]} | {n["overdue_days"]}天 | {"★"*stars} | {n["repetition"]} |')
    else:
        L.append('暂无逾期笔记 ✅')
    L.append('')

    # Today
    L.append(f'## 二、今日到期（{len(today_review)}篇）')
    L.append('')
    if today_review:
        L.append('| 笔记名称 | 分类 | 重要性 | 复习次数 | 容易因子 |')
        L.append('|----------|------|--------|----------|----------|')
        for n in today_review:
            L.append(f'| [[{n["name"]}]] | {n["category"]} | {n["importance"]} | {n["repetition"]} | {n["ease_factor"]} |')
    else:
        L.append('今日无到期笔记')
    L.append('')

    # Next 7 days
    L.append(f'## 三、未来7天到期（{len(future_7d)}篇）')
    L.append('')
    if future_7d:
        L.append('| 笔记名称 | 分类 | 复习日期 | 重要性 | 距今天数 |')
        L.append('|----------|------|----------|--------|----------|')
        for n in future_7d:
            days = -n['overdue_days']
            L.append(f'| [[{n["name"]}]] | {n["category"]} | {n["review_date"]} | {n["importance"]} | {days}天 |')
    else:
        L.append('未来7天无到期笔记')
    L.append('')

    # Stats
    L.append('## 四、复习统计')
    L.append('')
    L.append('### 4.1 总体统计')
    L.append('')
    L.append('| 统计项 | 数值 |')
    L.append('|--------|------|')
    L.append(f'| 总笔记数（设置review_date） | {len(notes)} |')
    L.append(f'| 已逾期 | {len(overdue)} |')
    L.append(f'| 今日到期 | {len(today_review)} |')
    L.append(f'| 未来7天到期 | {len(future_7d)} |')
    L.append(f'| 未来30天到期 | {len(future_30d)} |')
    rate = (len(notes) - len(overdue)) / len(notes) * 100 if notes else 0
    L.append(f'| 复习完成率 | {rate:.1f}% |')
    L.append('')

    L.append('### 4.2 按分类统计')
    L.append('')
    L.append('| 分类 | 总数 | 逾期 | 完成率 |')
    L.append('|------|------|------|--------|')
    for k, v in sorted(cat_count.items(), key=lambda x: -x[1]):
        od = cat_overdue[k]
        r = (v - od) / v * 100 if v > 0 else 0
        L.append(f'| {k} | {v} | {od} | {r:.0f}% |')
    L.append('')

    L.append('### 4.3 按复习次数统计')
    L.append('')
    L.append('| 复习次数 | 笔记数 |')
    L.append('|----------|--------|')
    for k in sorted(rep_count.keys()):
        label = f'{k}次' + ('（首次）' if k == 0 else '')
        L.append(f'| {label} | {rep_count[k]} |')
    L.append('')

    # Algorithm
    L.append('## 五、SM-2算法说明')
    L.append('')
    L.append('| 评分 | 记忆质量 | 处理方式 |')
    L.append('|------|----------|----------|')
    L.append('| 0-2 | 忘记或错误 | interval重置为1，repetition不变 |')
    L.append('| 3 | 勉强记住 | interval不变，repetition+1 |')
    L.append('| 4 | 较好记住 | interval × EF，repetition+1 |')
    L.append('| 5 | 完美记住 | interval × EF × 1.1，repetition+1 |')
    L.append('')

    # Log
    L.append('## 六、更新日志')
    L.append('')
    L.append('- **2026-07-04**：初始创建复习队列，5份笔记')
    L.append(f'- **{today_str}**：自动刷新。扫描全部 {len(notes)} 篇设置 review_date 的笔记。')
    L.append('')

    return '\n'.join(L)

if __name__ == '__main__':
    notes = scan_notes()
    content = generate_queue(notes)
    QUEUE_PATH.write_text(content, encoding='utf-8')
    overdue_count = sum(1 for n in notes if n['overdue_days'] > 0)
    print(f'复习队列已刷新: {len(notes)}篇笔记, 逾期{overdue_count}')
    print(f'输出: {QUEUE_PATH}')
