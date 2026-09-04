#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
商品房买卖审判要件卡 交付校验器（2026-09-04）
目标：ERROR 0 / WARN 0 才准交付
校验项：
  E1  YAML frontmatter 可被 pyyaml 解析
  E2  card_type == 审判要件卡
  E3  rule_id 与文件名前缀一致 且 编号唯一
  E4  必填字段齐全
  E5  ruling.support / ruling.reject 双双非空
  E6  elements 非空且每项含 id/name/desc
  E7  正文八段标题齐全
  E8  法条依据段：每条法条块标权威源（元典核填 / 本地·）+ 效力状态现行有效
  E9  无占位符（TODO / 待回填 / 待核填）
  W1  source 同时含 PDF页 与 书页
  W2  review_date == created + 6个月
  W3  related_links 非空且链接目标文件实地存在
  W4  正文含「铁律 R2」提示
  W5  法条条数 >= 1
"""
import os, re, sys, glob
from datetime import date
import yaml

BASE = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统'
CARD_DIR = os.path.join(BASE, '06-沉淀/裁判规则库/合同风险')
LINK_DIRS = [
    os.path.join(BASE, '06-沉淀/裁判规则库'),
    os.path.join(BASE, '03-连接/概念页'),
    os.path.join(BASE, '03-连接'),
]

NUMBERS = list(range(151, 179))  # R-HT-151 ~ R-HT-178

REQUIRED_FIELDS = [
    'title', 'rule_id', 'card_type', 'source', 'type', 'created', 'date',
    'created_month', 'review_date', 'updated', 'geo_scope',
    'library', 'aliases', 'review_step', 'elements',
    'ruling', 'burden_of_proof', 'negative_sample', 'negative_note',
    'related_links',
]

SECTIONS = [
    '## 一、裁判规则',
    '## 二、审查要点',
    '## 三、构成要件与举证',
    '## 四、法条依据',
    '## 五、抗辩与但书',
    '## 六、翻车标本',
    '## 七、来源与地域效力',
    '## 八、关联',
]

PLACEHOLDERS = ['TODO', '待回填', '待核填', '【占位', 'XXX']

errors, warns = [], []
def E(tag, msg): errors.append(f'[{tag}] {msg}')
def W(tag, msg): warns.append(f'[{tag}] {msg}')

def split_front(text):
    if not text.startswith('---'):
        return None, text
    parts = text.split('\n')
    if parts[0].strip() != '---':
        return None, text
    for i in range(1, len(parts)):
        if parts[i].strip() == '---':
            return '\n'.join(parts[1:i]), '\n'.join(parts[i+1:])
    return None, text

def add_months(d, n):
    y, m = d.year, d.month + n
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    import calendar
    dd = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, dd)

# 预建链接索引（基名 -> 路径）
link_index = {}
for d in LINK_DIRS:
    for p in glob.glob(os.path.join(d, '**', '*.md'), recursive=True):
        link_index[os.path.splitext(os.path.basename(p))[0]] = p

files = {}
for n in NUMBERS:
    pat = os.path.join(CARD_DIR, f'R-HT-{n}-*.md')
    got = glob.glob(pat)
    if len(got) == 0:
        E('E3', f'缺卡 R-HT-{n}')
    elif len(got) > 1:
        E('E3', f'编号 R-HT-{n} 存在 {len(got)} 个文件（重复）')
    else:
        files[n] = got[0]

seen_ids = {}
for n, path in sorted(files.items()):
    fn = os.path.basename(path)
    with open(path, encoding='utf-8') as f:
        raw = f.read()
    fm_text, body = split_front(raw)
    if fm_text is None:
        E('E1', f'{fn}: 无 YAML frontmatter')
        continue
    try:
        fm = yaml.safe_load(fm_text)
    except Exception as e:
        E('E1', f'{fn}: YAML 解析失败 {e}')
        continue
    if not isinstance(fm, dict):
        E('E1', f'{fn}: frontmatter 非字典')
        continue

    # E2 卡型
    if fm.get('card_type') != '审判要件卡':
        E('E2', f'{fn}: card_type={fm.get("card_type")} ≠ 审判要件卡')

    # E3 编号
    rid = fm.get('rule_id')
    if rid != f'R-HT-{n}':
        E('E3', f'{fn}: rule_id={rid} 与文件名不符（应为 R-HT-{n}）')
    if rid in seen_ids:
        E('E3', f'{fn}: rule_id {rid} 与 {seen_ids[rid]} 重复')
    seen_ids[rid] = fn

    # E4 必填
    miss = [k for k in REQUIRED_FIELDS if k not in fm or fm[k] in (None, '', [])]
    if miss:
        E('E4', f'{fn}: 缺必填字段 {miss}')

    # E5 ruling 双向
    rul = fm.get('ruling') or {}
    sup = (rul.get('support') or '').strip()
    rej = (rul.get('reject') or '').strip()
    if not sup:
        E('E5', f'{fn}: ruling.support 为空')
    if not rej:
        E('E5', f'{fn}: ruling.reject 为空')

    # E6 elements
    els = fm.get('elements') or []
    if not els:
        E('E6', f'{fn}: elements 为空')
    for el in els:
        if not all(k in el and el[k] for k in ('id', 'name', 'desc')):
            E('E6', f'{fn}: element {el.get("id")} 缺 id/name/desc')

    # E7 八段
    for s in SECTIONS:
        if s not in body:
            E('E7', f'{fn}: 缺正文段落「{s}」')

    # E8 法条块权威源（按块向下扫描）
    m4 = re.search(r'## 四、法条依据(.*?)(?=\n## )', body, re.S)
    if not m4:
        E('E8', f'{fn}: 未定位到「四、法条依据」段')
    else:
        seg = m4.group(1)
        blocks = re.split(r'\n(?=\*\*《)', seg)
        law_blocks = [b for b in blocks if b.strip().startswith('**《')]
        if not law_blocks:
            E('E8', f'{fn}: 法条依据段无「**《…》」法条标题块')
        for b in law_blocks:
            title_line = b.strip().split('\n')[0]
            if '*效力状态：' not in b:
                E('E8', f'{fn}: 法条块「{title_line[:40]}」未标效力状态')
            elif '现行有效' not in b:
                E('E8', f'{fn}: 法条块「{title_line[:40]}」效力状态非现行有效')
            if ('元典核填' not in b) and ('本地·' not in b):
                E('E8', f'{fn}: 法条块「{title_line[:40]}」未标权威源（元典核填/本地·）')
            if 'W5' not in b and len([x for x in law_blocks]) < 1:
                pass
        if len(law_blocks) < 1:
            W('W5', f'{fn}: 法条条数为 0')

    # E9 占位符
    for ph in PLACEHOLDERS:
        if ph in raw:
            E('E9', f'{fn}: 检出占位符「{ph}」')

    # W1 source 页码
    src = str(fm.get('source') or '')
    if 'PDF页' not in src:
        W('W1', f'{fn}: source 缺 PDF页')
    if '书页' not in src:
        W('W1', f'{fn}: source 缺书页')

    # W2 review_date
    try:
        c = fm.get('created')
        r = fm.get('review_date')
        if isinstance(c, date) and isinstance(r, date):
            if r != add_months(c, 6):
                W('W2', f'{fn}: review_date {r} ≠ created {c} +6个月（应为 {add_months(c,6)}）')
        else:
            W('W2', f'{fn}: created/review_date 非 date 类型（{type(c)}/{type(r)}）')
    except Exception as e:
        W('W2', f'{fn}: review_date 校验异常 {e}')

    # W3 链接
    rl = fm.get('related_links') or []
    if not rl:
        W('W3', f'{fn}: related_links 为空')
    for link in rl:
        base = str(link).strip().strip('[]')
        if base not in link_index:
            W('W3', f'{fn}: 链接「{base}」目标文件不存在')

    # W4 铁律 R2
    if '铁律 R2' not in body:
        W('W4', f'{fn}: 正文缺「铁律 R2」候选推理提示')

print('=' * 60)
print(f'校验卡数：{len(files)} / 应到 28')
print(f'ERROR: {len(errors)}   WARN: {len(warns)}')
print('=' * 60)
if errors:
    print('--- ERROR 明细 ---')
    for e in errors:
        print('  ' + e)
if warns:
    print('--- WARN 明细 ---')
    for w in warns:
        print('  ' + w)
if not errors and not warns:
    print('✅ 交付校验通过：ERROR 0 / WARN 0')
print('=' * 60)
sys.exit(1 if (errors or warns) else 0)
