#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_match_pending_v2_20260916.py  v1.0
待回源条文本地核填匹配器（根治坑 53 后的可用版本）

与旧版 _match_pending_20260912.py 的关键差别：
  🔴 旧提取器用「顺序索引」定位条文 → 恒定 +111 偏移（坑 53），导致 18 条候选
     12 条错配、本轮被迫核填 0 条。
  ✅ 新版改用「条号文本直接定位」：正则行首锚定 `第X条`，建 {条号: (start,end)}
     映射，取文按条号查表。实测民法典 1260/1260 唯一、最大条号 1260，逐条内容
     校验 7/7 正确（§172 表见代理 / §584 可预见规则均对）。

版本门禁（坑 33）：本地源 frontmatter 须含 version / sxx: 现行有效 /
  source: 元典权威回填 之一；三者皆无的旧网页抓取源一律拒绝。
  🔴 已知雷区：智能体技能库/红队出庭律师/常用法律法规库/中华人民共和国刑法.md
     为 1997 原版（§17「投毒罪」），硬排除。
"""
import json
import os
import re
import sys

LAWKB = "/Users/chenyouqiang/Documents/LawKB"
ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"

APPLY = "--apply" in sys.argv

CN = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}


def cn2num(s):
    s = s.replace('〇', '零')
    if s in CN:
        return CN[s]
    total, section, num = 0, 0, 0
    for ch in s:
        if ch in CN:
            num = CN[ch]
        elif ch == '十':
            section += (num if num else 1) * 10
            num = 0
        elif ch == '百':
            section += (num if num else 1) * 100
            num = 0
        elif ch == '千':
            section += (num if num else 1) * 1000
            num = 0
    return section + num


ART_PAT = re.compile(r'(?m)^[\s\*　 ]{0,6}第([零一二三四五六七八九十百千]+)条')

# 硬排除（坑 33 雷区）
BANNED = (
    "智能体技能库/红队出庭律师/常用法律法规库/中华人民共和国刑法.md",
)


def split_fm(t):
    if not t.startswith('---'):
        return None, t
    e = t.find('\n---', 3)
    if e < 0:
        return None, t
    return t[:e + 4], t[e + 4:]


def norm_law(s):
    """坑 50：剥公共前缀后再比，禁止前 N 字匹配"""
    s = re.sub(r'[（(]\s*(?:\d{4}\s*)?(?:修正|修订|修正版|修订版|全文|草案|征求意见稿?)\s*[)）]', '', s)
    s = re.sub(r'^中华人民共和国', '', s)
    return re.sub(r'[\s（）()·、,，《》]', '', s)


def build_index():
    """扫本地法律法规库，建 {norm_law: {'path','arts':{n:(s,e)},'ok':bool,'why':str,'text':str}}"""
    idx = {}
    for dirpath, dirnames, filenames in os.walk(os.path.join(LAWKB, "法律法规库")):
        if '.backup' in dirpath:
            continue
        for fn in filenames:
            if not fn.endswith('.md'):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, LAWKB)
            if any(b in rel for b in BANNED):
                continue
            try:
                t = open(p, encoding='utf-8').read()
            except Exception:
                continue
            fm, body = split_fm(t)
            # 版本门禁（坑 33）
            ok, why = True, ""
            if fm:
                has = ('version' in fm) or re.search(r'(?m)^sxx:\s*现行有效', fm) \
                      or ('元典权威回填' in fm) or ('元典核填' in fm)
                if not has:
                    ok, why = False, "无版本元数据（version/sxx/source 三者皆无）"
            else:
                ok, why = False, "无 frontmatter"
            hits = [(m.start(), cn2num(m.group(1))) for m in ART_PAT.finditer(t)]
            arts = {}
            for i, (pos, n) in enumerate(hits):
                if n and n not in arts:
                    arts[n] = (pos, hits[i + 1][0] if i + 1 < len(hits) else len(t))
            key = norm_law(fn.replace('.md', ''))
            if key not in idx or len(arts) > len(idx[key]['arts']):
                idx[key] = {'path': rel, 'arts': arts, 'ok': ok, 'why': why, 'text': t, 'n': len(arts)}
    return idx


# 卡内待回源条目正则
PENDING_PAT = re.compile(
    r'(?:待回源|待核)[^。\n]{0,80}?《([^》]{2,60})》[^。\n]{0,20}?第?\s*([零一二三四五六七八九十百千\d]{1,8})\s*条')


def main():
    idx = build_index()
    ok_idx = {k: v for k, v in idx.items() if v['ok']}
    print(f"本地法源：{len(idx)} 部（唯一法规名）｜版本门禁准入 {len(ok_idx)} 部")
    print(f"被拒 {len(idx) - len(ok_idx)} 部（无版本元数据，坑 33）\n")

    # 扫待回源卡
    cards = []
    for dirpath, _, filenames in os.walk(os.path.join(ROOT, "06-沉淀/裁判规则库")):
        if '.backup' in dirpath:
            continue
        for fn in filenames:
            if not (fn.startswith('R-') and fn.endswith('.md')):
                continue
            p = os.path.join(dirpath, fn)
            t = open(p, encoding='utf-8').read()
            fm, _ = split_fm(t)
            if not fm or not re.search(r'(?m)^statute_text_pending:\s*true', fm):
                continue
            cards.append((os.path.relpath(p, ROOT), t))

    print(f"待回源卡：{len(cards)} 张\n")

    matched, blocked, nosrc = [], [], []
    for rel, t in cards:
        for m in PENDING_PAT.finditer(t):
            law, art_raw = m.group(1), m.group(2)
            n = cn2num(art_raw) if not art_raw.isdigit() else int(art_raw)
            if not n:
                continue
            key = norm_law(law)
            src = idx.get(key)
            if not src:
                # 坑 65：禁止子串匹配——「公司法」是「公司法司法解释（三）」的子串、
                # 「民法典」是「民法典合同编通则解释」的子串，子串会把司法解释误配到法律本体。
                # 仅允许「剥离年份/版本括号后精确相等」这一等价形态。
                alt = re.sub(r'[（(]\s*(?:\d{4}\s*)?[^）)]{0,10}\s*[)）]$', '', key)
                src = idx.get(alt) if alt != key else None
            if not src:
                cands = [k for k in idx if k and (k in key or key in k)]
                if cands:
                    blocked.append((rel, law, n, f"疑似子串误配→{cands[0][:30]}",
                                    "坑65：司法解释名含法律名，禁止子串匹配"))
                    continue
                nosrc.append((rel, law, n))
                continue
            if not src['ok']:
                blocked.append((rel, law, n, src['path'], src['why']))
                continue
            if n not in src['arts']:
                blocked.append((rel, law, n, src['path'], f"条号越界（该源仅 {src['n']} 条）"))
                continue
            s, e = src['arts'][n]
            text = src['text'][s:e].strip()
            text = re.sub(r'\s+', ' ', text)[:400]
            matched.append({'card': rel, 'law': law, 'art': n, 'src': src['path'], 'text': text})

    print(f"✅ 可核填 {len(matched)} 条")
    print(f"🔴 拦截 {len(blocked)} 条（版本门禁/条号越界）")
    print(f"⬜ 本地无源 {len(nosrc)} 条\n")

    print("=== 可核填清单 ===")
    for m in matched[:25]:
        print(f"  {m['card'][:52]}")
        print(f"    《{m['law']}》§{m['art']}  ← {m['src'][:45]}")
        print(f"    {m['text'][:100]}")

    print("\n=== 拦截（前12）===")
    for b in blocked[:12]:
        print(f"  {b[0][:45]} 《{b[1]}》§{b[2]} → {b[3][:40]}｜{b[4]}")

    out = os.path.join(ROOT, "02-提炼/审判要件卡/_pending_match_20260916.json")
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({'matched': matched,
                   'blocked': [{'card': b[0], 'law': b[1], 'art': b[2], 'src': b[3], 'why': b[4]} for b in blocked],
                   'nosrc': [{'card': n[0], 'law': n[1], 'art': n[2]} for n in nosrc]},
                  f, ensure_ascii=False, indent=2)
    print(f"\n已落：{out}")


if __name__ == "__main__":
    main()
