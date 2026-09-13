#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第十六批（R-JG-034~035 / R-PI-371）交付校验器
跑法（坑15）：必须用 /Users/chenyouqiang/.workbuddy/binaries/python/envs/default/bin/python
且必须看输出里的 ERROR / WARN 行，不能只看退出码。
"""
import os, re, json, glob

try:
    import yaml
except ImportError:
    print('FATAL: 缺 pyyaml —— 请改用 envs/default/bin/python'); raise SystemExit(2)

ROOT = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库'
MAP = json.load(open('/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/审判要件卡/贵州类案指南第二卷-页码映射表.json', encoding='utf-8'))
TARGETS = ['R-JG-034', 'R-JG-035', 'R-PI-371']

ERRORS, WARNS = [], []
files = sorted(glob.glob(f'{ROOT}/**/R-*.md', recursive=True))
cand = [f for f in files if os.path.basename(f)[:8] in TARGETS]

print(f'候选卡片：{len(cand)} 张')
if len(cand) != 3:
    ERRORS.append(f'[E0] 候选卡数 {len(cand)} ≠ 计划 3 张')

seen_ids = {}
for f in cand:
    b = os.path.basename(f)
    t = open(f, encoding='utf-8').read()

    # E1 YAML 合法性
    if not t.startswith('---'):
        ERRORS.append(f'[E1] {b}: 无 frontmatter'); continue
    try:
        d = yaml.safe_load(t.split('---')[1])
    except Exception as e:
        ERRORS.append(f'[E1] {b}: YAML 解析失败 {str(e)[:80]}'); continue
    if not isinstance(d, dict):
        ERRORS.append(f'[E1] {b}: frontmatter 非 dict'); continue

    rid = d.get('rule_id')
    # E2 编号唯一
    if rid in seen_ids:
        ERRORS.append(f'[E2] {b}: rule_id 重复 {rid}')
    seen_ids[rid] = b
    # E3 必填字段
    for k in ['title', 'rule_id', 'card_type', 'source', 'created', 'geo_scope',
              'elements', 'ruling', 'burden_of_proof', 'review_step']:
        if k not in d or d[k] in (None, '', []):
            ERRORS.append(f'[E3] {b}: 缺必填字段 {k}')
    # E4 card_type
    if d.get('card_type') != '审判要件卡':
        ERRORS.append(f'[E4] {b}: card_type={d.get("card_type")}')
    # E5 rule_id 与文件名一致
    if rid and not b.startswith(rid):
        ERRORS.append(f'[E5] {b}: rule_id {rid} 与文件名不符')
    # E6 elements 结构
    els = d.get('elements')
    if isinstance(els, list):
        for e in els:
            if not all(k in e for k in ('id', 'name', 'desc')):
                ERRORS.append(f'[E6] {b}: elements 项缺字段 {e}')
    else:
        ERRORS.append(f'[E6] {b}: elements 非列表')
    # E7 ruling.support / reject 双双非空
    r = d.get('ruling') or {}
    if not (r.get('support') or '').strip():
        ERRORS.append(f'[E7] {b}: ruling.support 为空')
    if not (r.get('reject') or '').strip():
        ERRORS.append(f'[E7] {b}: ruling.reject 为空')
    # E8 正文八段
    for seg in ['## 一、裁判规则', '## 二、审查要点', '## 三、构成要件与举证',
                '## 四、法条依据', '## 五、抗辩与但书', '## 六、翻车标本',
                '## 七、来源与地域效力', '## 八、关联']:
        if seg not in t:
            ERRORS.append(f'[E8] {b}: 正文缺段 {seg}')
    # E9 法条依据段有权威源标注
    seg4 = t.split('## 四、法条依据')[1].split('\n## ')[0] if '## 四、法条依据' in t else ''
    if '效力状态' not in seg4:
        ERRORS.append(f'[E9] {b}: 法条块无效力状态标注')
    if '官方核验指引' not in seg4:
        ERRORS.append(f'[E9] {b}: 法条段缺官方核验指引子节')
    # E10 页码 0-based 校验（坑26）
    for mm in re.finditer(r'PDF页\s*(\d+)(?:\s*[-–]\s*(\d+))?（书页\s*(\d+)(?:\s*[-–]\s*(\d+))?）', d.get('source', '')):
        pa, sa = int(mm.group(1)), int(mm.group(3))
        exp = MAP.get(str(pa - 1))
        if exp is None:
            ERRORS.append(f'[E10] {b}: 映射表缺 key {pa-1}')
        elif exp != sa:
            ERRORS.append(f'[E10] {b}: 页码偏差 PDF{pa} 书页标注{sa} 应为{exp}')
    # E11 铁律 R2 标注
    if '【候选·待人工确认】' not in t and '铁律 R2' not in t:
        ERRORS.append(f'[E11] {b}: 缺铁律 R2 候选标注')

    # W1 四星号（坑23）
    if '****' in t:
        WARNS.append(f'[W1] {b}: 存在四星号')
    # W2 双书名号（坑20）
    if re.search(r'《《', t):
        WARNS.append(f'[W2] {b}: 双书名号嵌套')
    # W3 占位符
    for ph in ['TODO', 'TBD', 'XXX', '待补']:
        if ph in t:
            WARNS.append(f'[W3] {b}: 含占位符 {ph}')
    # W4 related_links 目标是否存在（坑9）
    for lnk in (d.get('related_links') or []):
        if isinstance(lnk, str) and lnk.startswith('R-'):
            if not glob.glob(f'{ROOT}/**/{lnk}.md', recursive=True):
                WARNS.append(f'[W4] {b}: related_links 可能死链 {lnk}')
    # W5 拉丁串污染
    for w in ['beautiful', 'marshalling', 'exegetical', 'undefined', 'None',
              'Unsupported', 'metallic', '春雨西路']:
        if re.search(rf'\b{w}\b', t):
            WARNS.append(f'[W5] {b}: 疑似污染串 {w}')

print(f'\n{"="*60}')
print(f'ERROR：{len(ERRORS)}')
for e in ERRORS: print('  ❌', e)
print(f'WARN ：{len(WARNS)}')
for w in WARNS: print('  ⚠️ ', w)
print('='*60)
print('结论：', '✅ 通过' if not ERRORS and not WARNS else '❌ 须返工')
