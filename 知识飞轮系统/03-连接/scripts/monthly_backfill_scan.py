#!/usr/bin/env python3
# monthly_backfill_scan.py — 修正版月度回灌扫描（created 优先 + 排除 08-27 批量污染戳）
# 仅只读扫描，产出候选清单；不写入 self.md（写入由 automation 主流程在 v2.1 上限内执行：绝对1200/单轮150）
# 用法: python3 monthly_backfill_scan.py [YYYY-MM-01]
import os, re, sys, json, datetime

KB = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统'
CARD_DIR = os.path.join(KB, '02-提炼/经验卡片')
RULE_DIR = os.path.join(KB, '06-沉淀/裁判规则库')
SELF = '/Users/chenyouqiang/.workbuddy/skills/xiaoqianglvshi/self.md'
BULK_STAMP = '2026-08-27T17:34'  # 批量重新链接污染戳（同日同时改写 created/updated）

def parse_fm(path):
    try:
        raw = open(path, encoding='utf-8').read()
    except Exception:
        return {}, ''
    fm = {}; body = raw
    if raw.startswith('---'):
        rest = raw.split('\n', 1)[1]
        m = re.match(r'(.*?)\n---\n?', rest, re.S)
        if m:
            for line in m.group(1).split('\n'):
                if ':' in line:
                    k, v = line.split(':', 1)
                    fm[k.strip()] = v.strip()
            body = rest[m.end():]
    return fm, body

def d(s):
    if not s:
        return None
    try:
        return datetime.datetime.strptime(s[:10], '%Y-%m-%d').date()
    except Exception:
        return None

def effective_date(fm):
    # created 优先；若 created 或 updated 是批量污染戳则跳过该戳
    c = fm.get('created'); u = fm.get('updated')
    c_is_stamp = (c and BULK_STAMP in c)
    u_is_stamp = (u and BULK_STAMP in u)
    if c and not c_is_stamp:
        return d(c), 'created'
    if u and not u_is_stamp:
        return d(u), 'updated(fallback)'
    return None, 'stamped-unknown'  # 两者皆戳 → 无法判定，交一次性回填/人工

def main():
    today = datetime.date.today()
    if len(sys.argv) > 1:
        ms = datetime.datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
    else:
        ms = today.replace(day=1)

    # 读取 self.md 已索引路径
    text = open(SELF, encoding='utf-8').read()
    already = set(); in_tbl = False
    for ln in text.split('\n'):
        if ln.strip().startswith('### 当前索引'):
            in_tbl = True; continue
        if in_tbl:
            if ln.strip().startswith('|') and '`' in ln:
                for mm in re.findall(r'`([^`]+)`', ln):
                    # 仅收录知识库相对路径（排除正文代码块反引号误收，如 sys.path.insert）
                    if mm.startswith('02-提炼') or mm.startswith('06-沉淀'):
                        already.add(mm)
            if ln.strip().startswith('>'):
                in_tbl = False

    cands = []; stamped_unknown = 0
    for base, kind in ((CARD_DIR, 'card'), (RULE_DIR, 'rule')):
        for root, dirs, files in os.walk(base):
            for f in files:
                if not f.endswith('.md') or f in ('_template.md', 'README.md') or f.startswith('README'):
                    continue
                path = os.path.join(root, f)
                fm, body = parse_fm(path)
                ed, src = effective_date(fm)
                if ed is None:
                    stamped_unknown += 1; continue
                if ed < ms:
                    continue
                rel = os.path.relpath(path, KB)
                if rel in already:
                    continue
                title = fm.get('title', '').strip() or next(
                    (l[2:].strip() for l in body.split('\n') if l.startswith('# ')),
                    os.path.splitext(f)[0])
                summary = fm.get('summary', '').strip()
                if not summary:
                    for l in body.split('\n'):
                        s = l.strip()
                        if not s or s.startswith('#') or s.startswith('>') or s.startswith('|') or s.startswith('-') or s.startswith('```'):
                            continue
                        summary = re.sub(r'[#*`_\[\]]', '', s).replace('\n', ' ').replace('|', '／')[:80]
                        break
                prefix = ('经验卡片-%s' % title) if kind == 'card' else ('裁判规则-%s' % title)
                cands.append({'prefix': prefix, 'rel': rel, 'summary': summary, 'kind': kind, 'date_src': src})

    out = {'month_start': ms.isoformat(), 'candidates': cands,
           'stamped_unknown': stamped_unknown, 'already': len(already)}
    json.dump(out, open('/tmp/backfill_created_scan.json', 'w'), ensure_ascii=False, indent=2)
    nc = sum(1 for c in cands if c['kind'] == 'card')
    nr = sum(1 for c in cands if c['kind'] == 'rule')
    print('created优先扫描(排除08-27戳) 月份=%s' % ms.isoformat())
    print('  候选总数=%d | 卡片=%d | 规则=%d' % (len(cands), nc, nr))
    print('  批量戳无法判定(跳过)=%d' % stamped_unknown)
    print('  self.md 已索引=%d' % len(already))
    total_lines = len(text.split('\n'))
    per_run_abort = len(cands) > 150
    abs_abort = total_lines + len(cands) + 2 > 1200
    print('  self.md 当前总行=%d' % total_lines)
    print('  预测追加后行数= %d + %d + 2 = %d (v2.1 上限: 单轮>150中止=%s / 总行>1200中止=%s)'
          % (total_lines, len(cands), total_lines + len(cands) + 2, per_run_abort, abs_abort))

if __name__ == '__main__':
    main()
