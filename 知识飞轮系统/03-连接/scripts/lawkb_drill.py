# -*- coding: utf-8 -*-
"""钻取 8 战术集群 -> 真实卡号清单 + 调用记录覆盖率。
覆盖率口径（诚实代理）：
- 编号卡(R/WD/LC)：全库 .md（排除 .backup）扫描其编号 R-XX-NNN / WD-NN / LC-NNN 出现，
  排除卡自身文件后，引用文件数 = ref。ref>=1 即视为"被调用/被链接"。
- 经验卡片/决策卡：无统一编号，用其 title 在"消费侧"目录(04-LOG/模拟法庭/案件管理/技能库/02-提炼除自身)
  出现次数近似。
通用裁判规则卡(549) 为多集群共享公地，单独列 shared_pool，不参与单一集群覆盖。
"""
import re, json, sys
from pathlib import Path

OUT = '/tmp/clusters_detail.json'
if '--out' in sys.argv:
    OUT = sys.argv[sys.argv.index('--out') + 1]

LAWKB = Path("/Users/chenyouqiang/Documents/LawKB")
ROOT = LAWKB / "知识飞轮系统"

ID_RE = re.compile(r'R-[A-Z]{2}-\d{2,4}|WD-\d{1,2}|LC-\d{3}')

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

# ---------- 1. 全库编号引用索引（排除 .backup） ----------
ref_index = {}  # id -> set(relpath)
files_all = []
for p in LAWKB.rglob('*.md'):
    if '.backup' in p.parts:
        continue
    files_all.append(p)
    t = read(p)
    for mid in set(ID_RE.findall(t)):
        ref_index.setdefault(mid, set()).add(str(p))

# ---------- 2. 消费侧文本（用于经验/决策卡标题提及近似） ----------
CONSUMER_DIRS = [
    ROOT / '04-LOG',
    LAWKB / '模拟法庭管理系统',
    LAWKB / '案件生命周期管理系统',
    LAWKB / '智能体技能库',
    ROOT / '02-提炼',
    ROOT / '03-连接',
    LAWKB / '小德合规管理系统',   # v2: 小德中枢为慈法合规卡真实消费面（此前盲区）
    ROOT / '05-调用',             # v2: 调用记录为红蓝对抗/模拟法庭真实消费面（此前盲区）
]
consumer_texts = {}  # relpath -> text
for base in CONSUMER_DIRS:
    if not base.exists():
        continue
    for p in base.rglob('*.md'):
        if '.backup' in p.parts:
            continue
        consumer_texts[str(p)] = read(p)

# ---------- 3. 收集所有卡 ----------
cards = []

rule_dir = ROOT / '06-沉淀' / '裁判规则库'
for p in rule_dir.rglob('*.md'):
    txt = read(p); d = fm(txt)
    rid = d.get('rule_id') or d.get('title')
    if not rid:
        continue
    ct = d.get('card_type') or '未标注'
    domain = rid.split('-')[1] if rid.startswith('R-') and len(rid.split('-')) > 1 else ''
    gen = '二代' if (d.get('geo_scope') or d.get('library')) else '一代'
    cards.append({'id': rid, 'title': d.get('title') or p.stem, 'card_type': ct,
                  'domain': domain, 'gen': gen, 'file': str(p), 'kind': 'R', 'sub': None})

wd_dir = ROOT / '06-沉淀' / '条号位移卡族'
for p in wd_dir.glob('WD-*.md'):
    txt = read(p); d = fm(txt)
    m = re.search(r'WD-\d{1,2}', p.name)
    rid = m.group() if m else (d.get('rule_id') or p.stem)
    cards.append({'id': rid, 'title': d.get('title') or p.stem, 'card_type': '条号位移卡',
                  'domain': 'WD', 'gen': '-', 'file': str(p), 'kind': 'WD', 'sub': None})

lc_dir = ROOT / '06-沉淀' / '类案检索报告卡族'
for p in lc_dir.glob('LC-*.md'):
    txt = read(p); d = fm(txt)
    m = re.search(r'LC-\d{3}', p.name)
    rid = m.group() if m else (d.get('rule_id') or p.stem)
    cards.append({'id': rid, 'title': d.get('title') or p.stem, 'card_type': '判例摘要卡',
                  'domain': 'LC', 'gen': '-', 'file': str(p), 'kind': 'LC', 'sub': None})

exp_dir = ROOT / '02-提炼' / '经验卡片'
if exp_dir.exists():
    for p in exp_dir.rglob('*.md'):
        txt = read(p); d = fm(txt)
        rid = d.get('rule_id') or p.stem
        rel = p.relative_to(exp_dir)
        sub = rel.parts[0] if rel.parts else ''
        title = d.get('title') or p.stem
        cards.append({'id': rid, 'title': title, 'card_type': '经验卡片',
                      'domain': 'EXP', 'gen': '-', 'file': str(p), 'kind': 'EXP', 'sub': sub})

dec_dir = ROOT / '04-LOG' / '决策日志'
if dec_dir.exists():
    for p in dec_dir.glob('决策卡-*.md'):
        txt = read(p); d = fm(txt)
        title = d.get('title') or p.stem
        cards.append({'id': p.stem, 'title': title, 'card_type': '决策卡',
                      'domain': 'DEC', 'gen': '-', 'file': str(p), 'kind': 'DEC', 'sub': None})

# ---------- 4. 引用次数 ----------
for c in cards:
    if c['kind'] in ('R', 'WD', 'LC'):
        refs = ref_index.get(c['id'], set())
        refs = {r for r in refs if r != c['file']}
        c['ref'] = len(refs)
    else:
        # 标题提及近似（消费侧，排除自身）
        title = c['title']
        cnt = 0
        for fp, tx in consumer_texts.items():
            if fp == c['file']:
                continue
            if title and title in tx:
                cnt += 1
        # 双向链接闭环：卡片自身声明了 consumed_by（接驳元数据）则视为至少被 1 方消费，
        # 防止消费方文件被误删导致 coverage 假跌；只有 consumed_by 也被清才真回落。
        # 注：fm() 简易解析器不识别 YAML 块列表，这里直接对原始文本正则检测
        #     （行内列表 [a,b,c] 与块列表 "- a\n- b" 两种形态均支持），避免双向闭环对块列表失效。
        if cnt == 0:
            raw = read(Path(c['file']))
            m_inline = re.search(r'consumed_by:\s*\[([^\]]+)\]', raw)
            m_block = re.search(r'consumed_by:\s*\n((?:\s*-\s*.+\n)+)', raw)
            if (m_inline and m_inline.group(1).strip()) or (m_block and m_block.group(1).strip()):
                cnt = 1
        c['ref'] = cnt

# ---------- 5. 集群归属 ----------
def assign(c):
    ct = c['card_type']; dom = c['domain']; title = c['title']; kind = c['kind']; sub = c['sub']
    # 通用/案例规则卡恒为共享公地，必须在 domain 判定之前返回，
    # 否则会被下方 dom=='LD'/'CF'/'PR' 等规则误分到 C5/C6，导致 shared_pool 少算。
    if ct in ('通用裁判规则卡', '案例规则卡'):
        return 'SHARED'
    if kind == 'WD':
        return 'C7'
    if kind == 'LC':
        return 'C8'
    if kind == 'DEC':
        return 'C8'
    if kind == 'EXP':
        if sub in ('慈法合规', '慈善组织合同纠纷') or '小德' in title or '厚德' in title:
            return 'C6'
        return 'C8'
    # R cards
    if ct == '案由路由卡' or dom == 'AY':
        return 'C1'
    if '请求权基础' in title or '定性分野' in title or ('定性' in title and dom in ('HT', 'PI')):
        return 'C1'
    if ct == '审判要件卡' or ct == '裁量尺度卡' or ct == '庭审主持卡':
        return 'C2'
    if ct == '证据规则卡' or dom == 'PR':
        return 'C3'
    if ct == '实务规则卡':
        if any(k in title for k in ['举证', '质证', '证据', '证明责任', '举证责任', '认证', '高度盖然']):
            return 'C3'
        return 'C4'
    if ct == '文书范式卡':
        return 'C4'
    if ct == '赔偿计算卡' or dom == 'LD':
        return 'C5'
    if ct == '工程事故卡':
        return 'C5'
    if ct == '合规审查卡' or dom == 'CF':
        return 'C6'
    if ct == '规范要点卡':
        return 'C6'
    if ct == '请求权基础卡':
        return 'C1'
    if ct == '通用裁判规则卡':
        return 'SHARED'
    if ct == '案例规则卡':
        return 'SHARED'
    return 'SHARED'

for c in cards:
    c['cluster'] = assign(c)

# 共享标记：裁量尺度卡 主 C2 共享 C5；赔偿计算卡 主 C5 共享 C4
def shared_with(c):
    if c['card_type'] == '裁量尺度卡':
        return 'C5'
    if c['card_type'] == '赔偿计算卡':
        return 'C4'
    return ''
for c in cards:
    c['shared'] = shared_with(c)

# ---------- 6. 聚合输出 ----------
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

clusters = []
for cid in ['C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8']:
    cs = [c for c in cards if c['cluster'] == cid]
    cs.sort(key=lambda x: (-x['ref'], x['id']))
    total = len(cs)
    covered = sum(1 for c in cs if c['ref'] >= 1)
    cov = round(covered / total * 100) if total else 0
    clusters.append({
        'id': cid,
        'title': CLUSTER_META[cid][0],
        'obj': CLUSTER_META[cid][1],
        'goal': CLUSTER_META[cid][2],
        'total': total,
        'covered': covered,
        'coverage': cov,
        'cards': [{'id': c['id'], 'title': c['title'], 'card_type': c['card_type'],
                   'domain': c['domain'], 'gen': c['gen'], 'ref': c['ref'], 'shared': c['shared']}
                  for c in cs],
    })

# 共享弹药池
shared = [c for c in cards if c['cluster'] == 'SHARED']
shared_by_domain = {}
for c in shared:
    shared_by_domain[c['domain']] = shared_by_domain.get(c['domain'], 0) + 1
shared_by_domain = dict(sorted(shared_by_domain.items(), key=lambda x: -x[1]))

out = {
    'clusters': clusters,
    'shared_pool': {
        'count': len(shared),
        'by_domain': shared_by_domain,
        'note': '通用裁判规则卡(549) + 案例规则卡(1) 为多集群共享公地弹药，哪个集群都能调，不独占。',
    },
    'ref_scanned_files': len(files_all),
    'generated_at': '2026-09-11',
}
json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

# 打印摘要
print(f"总卡数(含非R): {len(cards)} | 引用索引文件:{len(files_all)} | 消费侧文件:{len(consumer_texts)}")
print(f"共享弹药池: {len(shared)} 张 (按域: {shared_by_domain})")
print("-" * 70)
for cl in clusters:
    print(f"{cl['id']} {cl['title']:10s} 成员={cl['total']:4d} 被引>=1={cl['covered']:4d} 覆盖率={cl['coverage']:3d}%")
    # 引用次数分布
    refs = [c['ref'] for c in cl['cards']]
    hi = sum(1 for r in refs if r >= 5)
    mid = sum(1 for r in refs if 1 <= r < 5)
    zero = sum(1 for r in refs if r == 0)
    print(f"    引用分布: 高频(>=5)={hi} 低频(1-4)={mid} 零引用={zero}")
print("-" * 70)
print(f"DONE -> {OUT}")
