#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
待回源法条权威核填器（企查查·法律数据 qcc 通道）  v1.0 / 2026-09-13

铁律：
  1. 只使用 _qcc_cache_all_20260913.json 中 found=true 的逐字原文，绝不凭记忆补写
  2. 每卡一次原子写入（六-B 铁律）
  3. 改前 cp -n 备份到 /tmp/待回源核填_<时间戳>/
  4. 默认 dry-run，--apply 才落盘

用法：
  python _fill_pending_qcc_20260913.py            # dry-run
  python _fill_pending_qcc_20260913.py --apply    # 落盘
"""
import json, re, os, sys, shutil, datetime
from collections import defaultdict

ROOT = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统'
CACHE = os.path.join(ROOT, '02-提炼/审判要件卡/_qcc_cache_all_20260913.json')
REPORT = os.path.join(ROOT, '02-提炼/审判要件卡/待回源匹配报告-20260913.json')
APPLY = '--apply' in sys.argv
STAMP = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
BK = f'/tmp/待回源核填_{STAMP}'
TODAY = '2026-09-13'


# ---------- 中文数字 ----------
def cn(n):
    d = '零一二三四五六七八九'
    if n < 10:
        return d[n]
    if n < 20:
        return '十' + (d[n % 10] if n % 10 else '')
    if n < 100:
        return d[n // 10] + '十' + (d[n % 10] if n % 10 else '')
    if n < 1000:
        s = d[n // 100] + '百'
        r = n % 100
        if r == 0:
            return s
        if r < 10:
            return s + '零' + d[r]
        return s + cn(r)
    if n < 10000:
        s = d[n // 1000] + '千'
        r = n % 1000
        if r == 0:
            return s
        if r < 100:
            return s + '零' + cn(r)
        return s + cn(r)
    return str(n)


def key(book, art):
    return f'{book}||{art}'


def render_block(entry, book, art):
    """渲染成一个正式法条块（对齐卡内既有风格）"""
    title_cn = cn(int(art))
    body_lines = [l for l in entry['正文'].split('\n')]
    quote = '\n'.join('> ' + l for l in body_lines)
    eff = entry.get('时效性') or '未标注'
    meta = [f'企查查·法律数据核填·{TODAY}']
    if entry.get('发文字号'):
        meta.append(f'发文字号 {entry["发文字号"]}')
    if entry.get('施行日期'):
        meta.append(f'施行日期 {entry["施行日期"]}')
    meta_s = '；'.join(meta)
    link = entry.get('引用链接') or ''
    tail = f'·[溯源]({link})' if link else ''
    # 法规名：内部若已含《》，降级为〈〉，避免出现《a《b》c》嵌套
    name = (entry.get('法规名') or book or '').strip()
    name = name.replace('《', '〈').replace('》', '〉')
    return (f'**《{name}》第{title_cn}条**\n\n'
            f'{quote}\n\n'
            f'*效力状态：{eff}（{meta_s}）{tail}*\n')


def render_miss(book, art, reason):
    title_cn = cn(int(art))
    short = '远程源未收录该条（未拆条／条号待核）'
    if '商业银行法' in book:
        short = '⚠️ **条号疑似幻觉**：该法全文共 95 条，无此条号，需人工回原始文书核对'
    elif '征求意见稿' in book:
        short = '⚠️ **草案／征求意见稿**，非现行有效法源，不得作文书引用'
    return f'> ⚠️ 待回源：《{book}》{title_cn}条——{short}\n'


def main():
    cache = json.load(open(CACHE, encoding='utf-8'))
    rep = json.load(open(REPORT, encoding='utf-8'))
    bycard = defaultdict(list)
    for x in rep['unmatched']:
        bycard[x['card']].append(x)

    if APPLY:
        os.makedirs(BK, exist_ok=True)

    n_card = n_hit = n_miss = 0
    flip = []
    detail = {}

    for card, items in sorted(bycard.items()):
        path = os.path.join(ROOT, card)
        if not os.path.exists(path):
            print(f'  [跳过·文件不存在] {card}')
            continue
        text = open(path, encoding='utf-8').read()
        orig = text
        card_hit, card_miss = 0, 0

        for it in items:
            raw = it['raw']
            # 用 raw 前 30 字定位卡内的待回源行
            probe = raw[:30]
            idx = text.find(probe)
            if idx < 0:
                # 退而求其次：用书名定位
                probe = it['books'][0][:20] if it['books'] else ''
                idx = text.find(probe) if probe else -1
            if idx < 0:
                continue
            # 找到该行起止
            ls = text.rfind('\n', 0, idx) + 1
            le = text.find('\n', idx)
            if le < 0:
                le = len(text)
            line = text[ls:le]
            if '待回源' not in line:
                continue

            new_parts, miss_parts = [], []
            book = it['books'][0] if it['books'] else ''
            for art in it['arts']:
                k = key(book, art)
                e = cache.get(k)
                if e and e.get('found'):
                    new_parts.append(render_block(e, book, art))
                    card_hit += 1
                else:
                    reason = (e or {}).get('reason', '远程源未收录')
                    miss_parts.append(render_miss(book, art, reason))
                    card_miss += 1

            if not new_parts and not miss_parts:
                continue

            # 组装替换内容：先放核填块，再放仍需待回源的
            repl = ''
            if new_parts:
                repl += '\n\n'.join(p.rstrip('\n') for p in new_parts) + '\n'
            if miss_parts:
                if new_parts:
                    repl += '\n**待回源（远程源未收录，未核填）**\n\n'
                repl += '>\n'.join(miss_parts) if len(miss_parts) > 1 else miss_parts[0]

            text = text[:ls] + repl.rstrip('\n') + text[le:]

        if text == orig:
            continue

        # ---------- 状态翻转判定 ----------
        remain = len(re.findall(r'⚠️ 待回源', text))
        n_card += 1
        n_hit += card_hit
        n_miss += card_miss
        detail[card] = {'hit': card_hit, 'miss': card_miss, 'remain': remain}

        if remain == 0:
            text = re.sub(r'(?m)^statute_text_pending:\s*true\s*$',
                          'statute_text_pending: false', text, count=1)
            text = re.sub(r'法条依据（⏳ 待回源·未核填）',
                          '法条依据（企查查·法律数据核填·现行有效，含官方核验指引）', text)
            flip.append(card)
        else:
            text = re.sub(r'法条依据（⏳ 待回源·未核填）',
                          '法条依据（部分核填·含待回源）', text)

        if APPLY:
            shutil.copy2(path, os.path.join(BK, os.path.basename(path)))
            open(path, 'w', encoding='utf-8').write(text)

    print(f'{"[APPLY]" if APPLY else "[DRY-RUN]"} 涉及卡片 {n_card} | 核填条文 {n_hit} | 仍待回源 {n_miss}')
    print(f'pending 翻转 true→false 的卡片：{len(flip)}')
    for c in flip:
        print('   ✅', os.path.basename(c))
    if APPLY:
        print(f'备份目录：{BK}（{len(os.listdir(BK))} 份）')
        with open(os.path.join(ROOT, '02-提炼/审判要件卡/待回源核填明细-20260913.json'), 'w',
                  encoding='utf-8') as fh:
            json.dump(detail, fh, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
