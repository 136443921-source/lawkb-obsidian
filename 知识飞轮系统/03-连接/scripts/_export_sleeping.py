# -*- coding: utf-8 -*-
"""导出 16 张沉睡 R-* 规则卡激活清单 CSV。
口径与 lawkb_drill.py 完全一致：全库 .md（排除 .backup）扫描编号引用，
ref = 引用文件数（排除卡自身）。筛 ref==0 且 kind=='R' 且 cluster in (C1,C3,C4,C5)。
"""
import re, csv, sys
from pathlib import Path

LAWKB = Path("/Users/chenyouqiang/Documents/LawKB")
ROOT = LAWKB / "知识飞轮系统"
ID_RE = re.compile(r'R-[A-Z]{2}-\d{2,4}|WD-\d{1,2}|LC-\d{3}')
OUT_CSV = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/03-连接/scripts/沉睡规则卡激活清单_全量25.csv'

def read(p):
    try:
        return p.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return ''

def fm(txt):
    d = {}
    m = re.match(r'^---\n(.*?)\n---', txt, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                d[k.strip()] = v.strip().strip('"').strip("'")
    return d

# 1. 全库编号引用索引
ref_index = {}
for p in LAWKB.rglob('*.md'):
    if '.backup' in p.parts:
        continue
    t = read(p)
    for mid in set(ID_RE.findall(t)):
        ref_index.setdefault(mid, set()).add(str(p))

# 2. R 卡收集
rule_dir = ROOT / '06-沉淀' / '裁判规则库'
cards = []
for p in rule_dir.rglob('*.md'):
    txt = read(p); d = fm(txt)
    rid = d.get('rule_id') or d.get('title')
    if not rid or not rid.startswith('R-'):
        continue
    ct = d.get('card_type') or '未标注'
    domain = rid.split('-')[1] if len(rid.split('-')) > 1 else ''
    gen = '二代' if (d.get('geo_scope') or d.get('library')) else '一代'
    cards.append({'id': rid, 'title': d.get('title') or p.stem, 'card_type': ct,
                  'domain': domain, 'gen': gen, 'file': str(p), 'kind': 'R'})

# 3. 引用次数
for c in cards:
    refs = {r for r in ref_index.get(c['id'], set()) if r != c['file']}
    c['ref'] = len(refs)

# 4. 集群归属（复制 drill 的 assign）
def assign(c):
    ct = c['card_type']; dom = c['domain']; title = c['title']; kind = c['kind']
    if kind == 'WD': return 'C7'
    if kind == 'LC': return 'C8'
    if kind == 'DEC': return 'C8'
    if kind == 'EXP':
        if '小德' in title or '厚德' in title: return 'C6'
        return 'C8'
    if ct == '案由路由卡' or dom == 'AY': return 'C1'
    if '请求权基础' in title or '定性分野' in title or ('定性' in title and dom in ('HT', 'PI')): return 'C1'
    if ct == '审判要件卡' or ct == '裁量尺度卡' or ct == '庭审主持卡': return 'C2'
    if ct == '证据规则卡' or dom == 'PR': return 'C3'
    if ct == '实务规则卡':
        if any(k in title for k in ['举证', '质证', '证据', '证明责任', '举证责任', '认证', '高度盖然']): return 'C3'
        return 'C4'
    if ct == '文书范式卡': return 'C4'
    if ct == '赔偿计算卡' or dom == 'LD': return 'C5'
    if ct == '工程事故卡': return 'C5'
    if ct == '合规审查卡' or dom == 'CF': return 'C6'
    if ct == '规范要点卡': return 'C6'
    if ct == '请求权基础卡': return 'C1'
    if ct == '通用裁判规则卡': return 'SHARED'
    if ct == '案例规则卡': return 'SHARED'
    return 'SHARED'

for c in cards:
    c['cluster'] = assign(c)

CLUSTER_META = {
    'C1': ('立案定性集群', '事实 → 案由 + 请求权基础', '把「案件事实」精准映射到「案由 + 请求权基础」，从源头杜绝定性错误与条号漂移。'),
    'C2': ('审判裁判集群', '法官心智三位一体', '正向裁判规则 + 量化锚点 + 主持话术，构成 AI 法官的完整心智与行为底座。'),
    'C3': ('举证质证集群', '事实精度防线', '举证责任分配、证据能力、质证要点落地，把「事实精度」从口号变成可执行清单。'),
    'C4': ('文书生成集群', '起草提速降错', '要素式模板 + 操作指引 + 精算，三件套直接提速降错，固化最高法格式铁律。'),
    'C5': ('赔偿精算集群', '人伤/建工定损', '公式+基数+顺位+抗辩扣减，承载贵州地域基数滚动，支撑人伤与建工定损。'),
    'C6': ('合规审查集群', '慈善双线合规', '业务 + 财务双线慈善合规审查，配合厚德基金会 7 章 139 条合规手册。'),
    'C7': ('法条核验集群', '防条号漂移', '新旧条号对照 + 检索激活触发 + 负向拦截，三层防护杜绝「引了旧条号」。'),
    'C8': ('跨案模式识别集群', '飞轮+分身进化', '类案弹药 + 经验母体 + 思维回放，驱动知识飞轮运转与数字分身持续进化。'),
}

# 接驳建议
DISPATCH = {
    'C1': '接驳到案由路由卡/请求权基础调用面：蓝队定性分野、起诉状起草、吊顶案/雅菲案案由定性复盘',
    'C3': '接驳到证据规则调用面：质证提纲、红蓝对抗举证要点、韩杰医疗事故罪再审证据梳理',
    'C4': '接驳到文书范式调用面：代理词/答辩状要素式模板、文书生成流水线挂载',
    'C5': '接驳到赔偿计算调用面：人伤定损清单、工伤/交通赔偿精算、航合物流事故定损',
}

# 主派发目标：C1/C3/C4/C5 操作集群卡
dispatch = [c for c in cards if c['kind'] == 'R' and c['ref'] == 0 and c['cluster'] in ('C1', 'C3', 'C4', 'C5')]
# 共享公地/异常卡：SHARED（含未标注异常）
shared_zero = [c for c in cards if c['kind'] == 'R' and c['ref'] == 0 and c['cluster'] == 'SHARED']
dispatch.sort(key=lambda x: (x['cluster'], x['id']))
shared_zero.sort(key=lambda x: x['id'])

# 写 CSV（完整清单：主派发 + 共享公地/异常，单列打标不隐瞒）
with open(OUT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['序号', '是否派发接驳目标', '卡号', '标题', '卡型', '域码', '代际',
                '所属集群', '集群名称', '文件路径', '当前ref', '建议接驳方向'])
    i = 0
    for c in dispatch:
        i += 1
        cid = c['cluster']
        w.writerow([i, '是', c['id'], c['title'], c['card_type'], c['domain'], c['gen'],
                    cid, CLUSTER_META[cid][0], c['file'], c['ref'], DISPATCH[cid]])
    for c in shared_zero:
        i += 1
        if c['card_type'] == '未标注':
            note = '异常待核查：卡型未标注、标题形如交叉引用，疑似误建/重名，先人工triag再决定是否接驳'
        else:
            note = '否（共享公地弹药）：通用裁判规则卡为多集群共享，按既有 shared_pool 机制调用，不单点派发'
        w.writerow([i, '否', c['id'], c['title'], c['card_type'], c['domain'], c['gen'],
                    'SHARED', '共享公地弹药池', c['file'], c['ref'], note])

print(f"R 卡总数: {len(cards)}")
print(f"主派发目标(操作集群 C1/C3/C4/C5, ref=0): {len(dispatch)}")
print(f"共享公地/异常(SHARED, ref=0): {len(shared_zero)}  (其中未标注异常 {sum(1 for c in shared_zero if c['card_type']=='未标注')})")
print("主派发按集群:", {cl: sum(1 for c in dispatch if c['cluster'] == cl) for cl in ('C1','C3','C4','C5')})
print("CSV ->", OUT_CSV)
for c in dispatch:
    print(f"  [派发] {c['cluster']} {c['id']:14s} {c['title']}")
for c in shared_zero:
    print(f"  [公地] {c['id']:14s} {c['card_type']:10s} {c['title']}")
