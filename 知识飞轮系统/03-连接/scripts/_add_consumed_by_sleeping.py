# -*- coding: utf-8 -*-
"""给 14 张沉睡规则卡反向加 consumed_by（双向链接，最小侵入、幂等）。
消费面映射按 cluster + 卡号从建议接驳方向推导，与 05-调用/沉睡规则卡接驳清册/ 一一对应。
支持 --dry 预演。
"""
import csv, re, sys, os

CSV = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/03-连接/scripts/沉睡规则卡激活清单_全量25.csv'
DRY = '--dry' in sys.argv

CONSUMERS = {
    'R-PI-364': ['蓝队出庭律师', '文书生成流水线'],
    'R-LN-101': ['红队出庭律师', '蓝队出庭律师'],
    'R-LN-103': ['红队出庭律师', '蓝队出庭律师'],
    'R-PI-356': ['红队出庭律师', '蓝队出庭律师'],
    'R-PI-365': ['红队出庭律师', '蓝队出庭律师'],
    'R-PR-084': ['红队出庭律师', '蓝队出庭律师'],
    'R-LN-097': ['文书生成流水线'],
    'R-LN-098': ['文书生成流水线'],
    'R-LN-099': ['文书生成流水线'],
    'R-LN-100': ['文书生成流水线'],
    'R-LN-102': ['文书生成流水线'],
    'R-LN-104': ['文书生成流水线'],
    'R-PI-366': ['文书生成流水线'],
    'R-LN-105': ['人伤定损'],
}

def add_consumed_by(path, consumers):
    txt = open(path, encoding='utf-8').read()
    m = re.match(r'^---\n(.*?)\n---\n', txt, re.S)
    if not m:
        return 'NO_FM(隔离未改)'
    fm = m.group(1)
    if re.search(r'^consumed_by:', fm, re.M):
        return 'SKIP(已有)'
    line = 'consumed_by: [' + ', '.join(consumers) + ']'
    new_fm = fm + '\n' + line
    new_txt = '---\n' + new_fm + '\n---\n' + txt[m.end():]
    if not DRY:
        open(path, 'w', encoding='utf-8').write(new_txt)
    return 'ADDED: ' + line

rows = list(csv.DictReader(open(CSV, encoding='utf-8-sig')))
targets = [r for r in rows if r['是否派发接驳目标'] == '是']
cnt = {'ADDED': 0, 'SKIP': 0, 'NO_FM': 0, 'MISSING': 0}
for r in targets:
    rid = r['卡号']; p = r['文件路径']; cons = CONSUMERS.get(rid, [])
    if not os.path.isfile(p):
        print(f"MISSING {rid} -> {p}"); cnt['MISSING'] += 1; continue
    res = add_consumed_by(p, cons)
    tag = res.split(':')[0].split('(')[0]
    cnt[tag if tag in cnt else 'ADDED'] = cnt.get(tag if tag in cnt else 'ADDED', 0) + 1
    print(f"{'[DRY] ' if DRY else ''}{rid:12s} {res}")

print('-' * 50)
print(f"模式: {'DRY-RUN(未写入)' if DRY else 'REAL(已写入)'} | 结果: {cnt}")
