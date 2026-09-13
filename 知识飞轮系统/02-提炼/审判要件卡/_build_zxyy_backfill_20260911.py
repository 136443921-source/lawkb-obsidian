#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第十四批（案外人执行异议之诉·程序性处理与未拆子类）法条回填库建造
铁律：法条正文绝不凭记忆，一律从权威源核填并标注来源与效力状态。
本会话通道状态（2026-09-11 实测，带时间戳）：
  - 北大法宝 pkulaw: 11:11 / 11:12 / 11:15 三次真调用均 {"error":"unauthorized"}  -> 不可用
  - 华宇元典 yuandian: get_user_balance 通（余额2点），law_vector_search 返「积分余额不足」 -> 不可用
  - 按 SKILL §5.0 第三顺位：走本地法律法规库（/Users/chenyouqiang/Documents/LawKB/法律法规库/）兜底
    本地《执行异议之诉解释》frontmatter 标 source_verified: true、
    source: 华宇元典 rh_fg_detail 权威回填（2026-09-04）-> 属「已在库权威文本」
"""
import re, json, os

LAWDIR = '/Users/chenyouqiang/Documents/LawKB/法律法规库'
OUT = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/审判要件卡/贵州类案指南第二卷-执行异议之诉补拆-法条回填库.json'


def cn2n(s):
    d = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
    sec = {'十': 10, '百': 100, '千': 1000}
    n = 0; cur = 0
    for ch in s:
        if ch in d:
            cur = d[ch]
        elif ch in sec:
            m = sec[ch]; cur = cur or 1; n += cur * m; cur = 0
    return n + cur


def load_index(path):
    lines = open(path, encoding='utf-8').read().split('\n')
    idx = []
    for i, l in enumerate(lines):
        m = re.match(r'^\s*\*{0,2}第([零一二三四五六七八九十百千]+|\d+)条\*{0,2}\s*(.*)$', l.strip())
        if m:
            raw = m.group(1)
            idx.append((int(raw) if raw.isdigit() else cn2n(raw), i))
    return lines, idx


def get_article(path, n):
    lines, idx = load_index(path)
    hit = [x for x in idx if x[0] == n]
    if not hit:
        return None
    k = idx.index(hit[0]); i = hit[0][1]
    nxt = idx[k + 1][1] if k + 1 < len(idx) else len(lines)
    b = '\n'.join(lines[i:nxt]).strip()
    b = re.sub(r'\*+', '', b)
    b = re.sub(r'\n> .*$', '', b, flags=re.M)      # 去本地批注行
    b = re.sub(r'^第[零一二三四五六七八九十百千\d]+条\s*', '', b.strip())
    return b.strip()


MSF = f'{LAWDIR}/程序法/中华人民共和国民事诉讼法（2023）.md'
ZXY = f'{LAWDIR}/司法解释/最高人民法院关于审理执行异议之诉案件适用法律问题的解释.md'

LOCAL_SRC = '本地法律法规库核填（在库权威文本）'
laws = {}


def add(key, law, article, text, note='', src=LOCAL_SRC, timeliness='现行有效', pending=False):
    laws[key] = {
        'law': law, 'article': article, 'text': text, 'source': src,
        'timeliness': timeliness, 'note': note, 'pending': pending,
        'verified_at': '2026-09-11 11:20',
    }


# ========== ① 民事诉讼法（2023 修正）==========
for n, tag in [(122, '起诉条件'), (236, '执行行为异议'), (238, '案外人执行异议')]:
    t = get_article(MSF, n)
    assert t, f'民诉法第{n}条 MISS'
    add(f'民事诉讼法§{n}', '中华人民共和国民事诉讼法', f'第{n}条', t,
        f'2023 第五次修正（2023-09-01 通过，2024-01-01 施行）；{tag}。'
        '🔴 条号核验：指南援引第236/238条与 2023 修正版现行条号一致，无位移。')

# ========== ② 执行异议之诉解释（法释〔2025〕10号）==========
ZX_META = ('法释〔2025〕10号，2024-12-14 审委会第1938次会议通过，'
           '2025-07-23 公布，2025-07-24 施行，共23条；执行异议之诉领域第一部系统性司法解释。')
ZX_SRC = '本地法律法规库核填（在库权威文本·华宇元典 rh_fg_detail 权威回填 2026-09-04，source_verified=true）'
zx_notes = {
    1: '执行异议之诉的受理条件与管辖法院；第2款援引《复议规定》第六条期限。',
    2: '轮候查封情形下被告与第三人的列明规则。',
    4: '案外人提出确权请求的，以被执行人为被告。',
    5: '案外人提出给付请求的，可以合并审理。',
    7: '执行案件已结案且未处分、措施已解除 → 终结诉讼/终结审查，原异议裁定失效。',
    8: '执行依据决定再审时，区分「可继续审理」与「应中止审理」两种情形。',
    9: '被执行人破产受理 → 中止审理/审查，管理人接管后继续。',
    13: '买受人「代为清偿」排除执行路径（全新规则，《复议规定》无对应条款）。',
    15: '以物抵债排除一般金钱债权执行的四要件。',
    17: '不动产折抵工程款排除抵押权与一般金钱债权执行的二要件；依据民法典§807。',
    18: '被拆迁人（征收补偿产权调换）排除建设工程价款优先权、抵押权及其他债权执行。',
    19: '预告登记权利人：符合停止处分 / 排除执行两档救济。',
}
for n in [1, 2, 4, 5, 7, 8, 9, 13, 15, 17, 18, 19]:
    t = get_article(ZXY, n)
    assert t, f'执行异议之诉解释第{n}条 MISS'
    add(f'执行异议之诉解释§{n}', '最高人民法院关于审理执行异议之诉案件适用法律问题的解释',
        f'第{n}条', t, f'{ZX_META}{zx_notes.get(n, "")}', src=ZX_SRC)

# ========== ③ 本地库未收 → 据实标「待回源」，不虚标 ==========
PENDING = '指南援引，本地法律法规库未收，且本会话北大法宝 unauthorized / 华宇元典积分不足，未能核填。'
for key, law, art, note in [
    ('民诉法解释§302', '最高人民法院关于适用《中华人民共和国民事诉讼法》的解释', '第302条', '执行异议之诉的管辖'),
    ('民诉法解释§303', '最高人民法院关于适用《中华人民共和国民事诉讼法》的解释', '第303条', '执行异议之诉的受理条件'),
    ('民诉法解释§305', '最高人民法院关于适用《中华人民共和国民事诉讼法》的解释', '第305条', '案外人执行异议之诉被告主体的确定'),
    ('民诉法解释§306', '最高人民法院关于适用《中华人民共和国民事诉讼法》的解释', '第306条', '申请执行人执行异议之诉被告主体的确定'),
    ('民诉法解释§308', '最高人民法院关于适用《中华人民共和国民事诉讼法》的解释', '第308条', '执行异议之诉适用普通程序审理'),
    ('民诉法解释§309', '最高人民法院关于适用《中华人民共和国民事诉讼法》的解释', '第309条', '案外人的举证责任'),
    ('复议规定§6', '最高人民法院关于人民法院办理执行异议和复议案件若干问题的规定', '第6条', '案外人提出异议的期限（执行标的执行终结前）'),
    ('复议规定§8', '最高人民法院关于人民法院办理执行异议和复议案件若干问题的规定', '第8条', '执行标的异议与执行行为异议并存的审理范围'),
    ('答复2014民立他29号', '最高人民法院关于安徽省高级人民法院《关于对执行异议之诉案件如何收取案件受理费的请示》的答复', '〔2014〕民立他字第29号', '执行异议之诉案件受理费按财产案件标准计收'),
]:
    add(key, law, art, '', PENDING + note, src='待回源', timeliness='待核', pending=True)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(laws, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
ok = sum(1 for v in laws.values() if not v['pending'])
print(f'法条库已建：{OUT}')
print(f'  合计 {len(laws)} 条 ｜ 已核填 {ok} ｜ 待回源 {len(laws) - ok}')
for k, v in laws.items():
    flag = '  ' if not v['pending'] else '⏳'
    print(f'  {flag} {k}: {v["timeliness"]} ({len(v["text"])}字)')
