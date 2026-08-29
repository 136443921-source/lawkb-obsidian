#!/usr/bin/env python3
# monthly_backfill_aug28_rerun.py — 2026-08-28 月度回灌重跑（v2.1 安全策略）
# 仅索引本自动化扫描出的、在 last_backfill(11:12) 之后新建且未入索引的裁判规则 5 条。
# 六-B 合规：先备份+字节核对 -> 插入 -> 校验 -> 失败秒级回滚。
import os, re, sys, shutil, datetime

KB = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统'
SELF = '/Users/chenyouqiang/.workbuddy/skills/xiaoqianglvshi/self.md'
BACKUP_DIR = '/Users/chenyouqiang/WorkBuddy/automation-2026-08-10-22-03-01/.workbuddy/backups/xiaoqiang_self'
DRY = '--apply' not in sys.argv

# 5 条 new 裁判规则（created 均在 2026-08-28 11:25~11:44，晚于 last_backfill 11:12）
CAND_RELS = [
    '06-沉淀/裁判规则库/商事纠纷/R-SH-032-股权转让解除通知效力与继续履行不能.md',
    '06-沉淀/裁判规则库/人伤法/R-PI-174-医疗质量安全核心制度18项违反即过错证据化.md',
    '06-沉淀/裁判规则库/人伤法/R-PI-175-医疗损害鉴定采信与术前告知阻却过错推定.md',
    '06-沉淀/裁判规则库/人伤法/R-PI-176-术中变更术式未重新告知侵害知情同意权.md',
    '06-沉淀/裁判规则库/合同风险/R-HT-109-约定违约金过高按LPR1.5倍调整.md',
]

def parse_fm(path):
    raw = open(path, encoding='utf-8').read()
    fm = {}; body = raw
    if raw.startswith('---'):
        rest = raw.split('\n', 1)[1]
        m = re.match(r'(.*?)\n---\n?', rest, re.S)
        if m:
            for line in m.group(1).split('\n'):
                if ':' in line:
                    k, v = line.split(':', 1); fm[k.strip()] = v.strip()
            body = rest[m.end():]
    return fm, body

def summary_of(fm, body):
    t = fm.get('summary', '').strip()
    if t: return re.sub(r'[#*`_\[\]]', '', t).replace('\n',' ').replace('|','／')[:120]
    for ln in body.split('\n'):
        s = ln.strip()
        if not s or s.startswith('#') or s.startswith('>') or s.startswith('|') or s.startswith('-') or s.startswith('```'):
            continue
        return re.sub(r'[#*`_\[\]]', '', s).replace('\n',' ').replace('|','／')[:120]
    return ''

def main():
    ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    rows = []
    for rel in CAND_RELS:
        p = os.path.join(KB, rel)
        fm, body = parse_fm(p)
        title = fm.get('title','').strip()
        prefix = '裁判规则-%s' % title
        summ = summary_of(fm, body)
        rows.append('| %s | `%s` | %s |' % (prefix, rel, summ))

    lines = open(SELF, encoding='utf-8').read().split('\n')
    old_n = len(lines)
    sec_old = sum(1 for l in lines if l.startswith('## '))
    # 插入点："> 索引随月度蒸馏增长" 之前
    idx = next(i for i,l in enumerate(lines) if l.startswith('> 索引随月度蒸馏增长'))
    new_lines = lines[:idx] + rows + lines[idx:]
    new_n = len(new_lines)
    sec_new = sum(1 for l in new_lines if l.startswith('## '))

    print('=== DRY-RUN ===' if DRY else '=== APPLY ===')
    print('候选行数=%d' % len(rows))
    print('self.md 旧行数=%d  新行数=%d  (Δ=%d)' % (old_n, new_n, new_n-old_n))
    print('章节数 old=%d new=%d (应相等)' % (sec_old, sec_new))
    for r in rows: print('  +', r[:80], '...')

    if DRY:
        print('[dry-run] 未写入。')
        return

    # 六-B: 备份 + 字节核对
    os.makedirs(BACKUP_DIR, exist_ok=True)
    bak = os.path.join(BACKUP_DIR, 'self_backup_%s/self.md.bak' % ts)
    os.makedirs(os.path.dirname(bak), exist_ok=True)
    shutil.copy2(SELF, bak)
    if os.path.getsize(bak) != os.path.getsize(SELF):
        print('[ABORT] 备份字节数不一致，中止'); return
    print('[backup] %s (%d bytes, 核对一致)' % (bak, os.path.getsize(bak)))

    # 写入
    open(SELF, 'w', encoding='utf-8').write('\n'.join(new_lines))
    # 校验
    v = open(SELF, encoding='utf-8').read().split('\n')
    vn = len(v); vs = sum(1 for l in v if l.startswith('## '))
    ok = (vn == new_n) and (vs == sec_old) and any(l.startswith('### 当前索引') for l in v)
    ok = ok and all(('`%s`' % rel) in open(SELF, encoding='utf-8').read() for rel in CAND_RELS)
    if ok:
        print('[verify] PASS 行数=%d 章节=%d 当前索引在 5条rel均已入表' % (vn, vs))
        print('[done] 回灌成功，self.md 末次 mtime 更新。')
    else:
        print('[FAIL] 校验失败，秒级回滚'); shutil.copy2(bak, SELF)
        print('[rollback] 已从备份恢复')

if __name__ == '__main__':
    main()
