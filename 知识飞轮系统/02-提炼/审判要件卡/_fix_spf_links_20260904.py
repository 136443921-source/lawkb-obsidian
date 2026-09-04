#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 28 张商品房买卖审判要件卡 related_links / 正文[[链接]] 的死链
问题：生成器写链接名时对文件名做了标点清洗（去「、」「：」及后缀），
      导致链接名 ≠ 实际文件名基名。
策略：行级正则，仅修正 R-HT-151~178 的链接（其余域不动）
用法： python3 _fix_spf_links_20260904.py [apply]
      不带 apply = dry-run（只打印将要改的内容，不写盘）
"""
import os, re, sys, glob

BASE = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统'
CARD_DIR = os.path.join(BASE, '06-沉淀/裁判规则库/合同风险')
TARGET_RANGE = set(range(151, 179))

APPLY = len(sys.argv) > 1 and sys.argv[1] == 'apply'

# 建 151~178 编号 -> 实际文件名基名 映射
real = {}
for n in TARGET_RANGE:
    got = glob.glob(os.path.join(CARD_DIR, f'R-HT-{n}-*.md'))
    if len(got) == 1:
        real[n] = os.path.splitext(os.path.basename(got[0]))[0]
    elif len(got) > 1:
        print(f'!! R-HT-{n} 有 {len(got)} 个文件，跳过修正：{[os.path.basename(x) for x in got]}')

# frontmatter 行：  - "R-HT-数字-名字"
FM_RE = re.compile(r'^(\s*-\s*")(R-HT-(\d+)-[^"]*)(")\s*$')
# 正文链接： [[R-HT-数字-名字]]
BODY_RE = re.compile(r'\[\[(R-HT-(\d+)-[^\]\[]*)\]\]')

changed_files, changes = 0, []

for n, path in sorted([(int(k.split('-')[2]), v) for k, v in
                       [(os.path.splitext(os.path.basename(g))[0], g)
                        for g in glob.glob(os.path.join(CARD_DIR, 'R-HT-1[5-7][0-9]-*.md'))]]):
    fn = os.path.basename(path)
    with open(path, encoding='utf-8') as f:
        lines = f.read().split('\n')

    out, touched = [], False
    in_fm = False
    fm_seen = 0
    for line in lines:
        # frontmatter 边界
        if line.strip() == '---' and not in_fm and fm_seen == 0:
            fm_seen = 1
            in_fm = True
            out.append(line); continue
        if line.strip() == '---' and in_fm:
            in_fm = False
            out.append(line); continue

        new_line = line

        if in_fm:
            m = FM_RE.match(line)
            if m:
                num = int(m.group(3))
                old = m.group(2)
                if num in TARGET_RANGE and num in real and real[num] != old:
                    new_line = f'{m.group(1)}{real[num]}{m.group(4)}'
        else:
            def rep(mm):
                num = int(mm.group(2))
                old = mm.group(1)
                if num in TARGET_RANGE and num in real and real[num] != old:
                    return f'[[{real[num]}]]'
                return mm.group(0)
            new_line = BODY_RE.sub(rep, line)

        if new_line != line:
            changes.append(f'{fn}\n    - {line.strip()}\n    + {new_line.strip()}')
            touched = True
        out.append(new_line)

    if touched:
        changed_files += 1
        if APPLY:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(out))

print('=' * 60)
print(f'模式：{"APPLY（已写盘）" if APPLY else "DRY-RUN（未写盘）"}')
print(f'待改文件数：{changed_files}   改动条数：{len(changes)}')
print('=' * 60)
for c in changes:
    print(c)
if not APPLY and changes:
    print('\n>> 确认无误后加参数 apply 实改')
