#!/usr/bin/env python3
# monthly_backfill_controlled.py — 受控回填（一次性 · 用户 2026-08-28 授权 A 方案）
# 规则 402 条全填（天然指针，不过 LTI）；卡片仅索引 importance>=4 子集（用户授权放宽经验卡片 LTI 判定）。
# 默认 dry-run 仅统计；--apply 才分批写入 self.md（每批 50 行 + 校验 + 异常回滚到备份）。
import os, re, sys, json, datetime, shutil

KB = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统'
CARD_DIR = os.path.join(KB, '02-提炼/经验卡片')
RULE_DIR = os.path.join(KB, '06-沉淀/裁判规则库')
SELF = '/Users/chenyouqiang/.workbuddy/skills/xiaoqianglvshi/self.md'
MONTH = datetime.date(2026, 8, 1)
ANCHOR = '> 索引随月度蒸馏增长'
BACKUP = '/Users/chenyouqiang/WorkBuddy/Claw/backups/xiaoqiang_self/self_backup_20260828-090922/self.md.bak'
IMPORTANCE_MIN = 4
BATCH = 50


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


def in_month(fm):
    # 受控回填（宽松）：created>=08-01 或 created 缺且 updated>=08-01（含 08-27 批量戳，视作本月候选）
    c = d(fm.get('created')); u = d(fm.get('updated'))
    if c and c >= MONTH:
        return True
    if (not c) and u and u >= MONTH:
        return True
    return False


def build_rows():
    text = open(SELF, encoding='utf-8').read()
    already = set(); in_tbl = False
    for ln in text.split('\n'):
        if ln.strip().startswith('### 当前索引'):
            in_tbl = True; continue
        if in_tbl:
            if ln.strip().startswith('|') and '`' in ln:
                for mm in re.findall(r'`([^`]+)`', ln):
                    if mm.startswith('02-提炼') or mm.startswith('06-沉淀'):
                        already.add(mm)
            if ln.strip().startswith('>'):
                in_tbl = False

    total_lines = len(text.split('\n'))
    rules = []; cards_ge4 = []; cards_excluded = []
    for base, kind in ((RULE_DIR, 'rule'), (CARD_DIR, 'card')):
        for root, dirs, files in os.walk(base):
            for f in files:
                if not f.endswith('.md') or f in ('_template.md', 'README.md'):
                    continue
                path = os.path.join(root, f)
                fm, body = parse_fm(path)
                if not in_month(fm):
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
                prefix = '经验卡片' if kind == 'card' else '裁判规则'
                row = '| %s-%s | `%s` | %s |' % (prefix, title, rel, summary)
                if kind == 'rule':
                    rules.append(row)
                else:
                    imp_raw = fm.get('importance')
                    imp = None
                    if imp_raw is not None:
                        try:
                            imp = int(str(imp_raw).strip().strip('"').strip("'"))
                        except Exception:
                            imp = None
                    if imp is not None and imp >= IMPORTANCE_MIN:
                        cards_ge4.append(row)
                    else:
                        cards_excluded.append({'rel': rel, 'imp': imp})
    return rules, cards_ge4, cards_excluded, already, total_lines


def main():
    rules, cards_ge4, cards_excluded, already, total_lines = build_rows()
    plan = rules + cards_ge4
    pred = total_lines + len(plan) + 2  # +2 含表尾空行/注释前插入的结构开销近似
    print('=== 受控回填 DRY-RUN (month>=%s, importance>=%d) ===' % (MONTH.isoformat(), IMPORTANCE_MIN))
    print('  self.md 当前总行=%d | 已索引(KB路径)=%d' % (total_lines, len(already)))
    print('  裁判规则(全填)=%d' % len(rules))
    print('  经验卡片 importance>=%d=%d' % (IMPORTANCE_MIN, len(cards_ge4)))
    print('  卡片排除(无/低 importance)=%d' % len(cards_excluded))
    imp_dist = {}
    for c in cards_excluded:
        imp_dist[c['imp']] = imp_dist.get(c['imp'], 0) + 1
    print('    排除卡片 importance 分布: %s' % imp_dist)
    print('  计划写入总行=%d' % len(plan))
    print('  预测 self.md 总行≈%d (原%d + 写入%d + 结构2)' % (pred, total_lines, len(plan)))

    json.dump({'rules': rules, 'cards_ge4': cards_ge4,
               'cards_excluded': cards_excluded, 'pred_total': pred,
               'total_lines': total_lines},
              open('/tmp/backfill_plan.json', 'w'), ensure_ascii=False, indent=2)

    if '--apply' not in sys.argv:
        print('\n[DRY-RUN] 未写入。加 --apply 执行分批写入。')
        return

    # ---- APPLY ----
    assert os.path.exists(BACKUP), '备份缺失! 中止'
    original = open(SELF, encoding='utf-8').read()
    sec_count = sum(1 for l in original.split('\n') if l.startswith('## '))
    idx_rows_before = sum(1 for l in original.split('\n')
                          if l.strip().startswith('|') and '`' in l
                          and ('02-提炼' in l or '06-沉淀' in l))
    total_before = len(original.split('\n'))
    print('\n[APPLY] 备份校验通过, 起始索引行=%d, 章节数=%d' % (idx_rows_before, sec_count))

    inserted = 0
    for bi in range(0, len(plan), BATCH):
        chunk = plan[bi:bi + BATCH]
        cur = open(SELF, encoding='utf-8').read().split('\n')
        # 插入点：最后一条 `|` 数据行之后（保证表格连续，不插在注释前造成断裂）
        last_idx = None
        for i, ln in enumerate(cur):
            if ln.strip().startswith('|') and '`' in ln:
                last_idx = i
        assert last_idx is not None, '最后索引行丢失! 中止'
        new_cur = cur[:last_idx + 1] + chunk + cur[last_idx + 1:]
        try:
            open(SELF, 'w', encoding='utf-8').write('\n'.join(new_cur))
            after = open(SELF, encoding='utf-8').read()
            after_lines = after.split('\n')
            assert '## 经验索引区' in after, '经验索引区标题丢失! 回滚'
            assert sum(1 for l in after_lines if l.startswith('## ')) == sec_count, '章节数变化! 回滚'
            assert len(after_lines) == total_before + len(chunk), '行数增量异常! 回滚 idx=%d' % bi
            total_before = len(after_lines)
            inserted += len(chunk)
            print('  批 %d-%d: 写 %d 行, 现总行 %d, 索引行 %d' % (
                bi + 1, bi + len(chunk), len(chunk), total_before,
                sum(1 for l in after_lines if l.strip().startswith('|') and '`' in l and ('02-提炼' in l or '06-沉淀' in l))))
        except AssertionError as e:
            open(SELF, 'w', encoding='utf-8').write(original)
            print('  ❌ 校验失败: %s — 已回滚到备份前状态' % e)
            raise
    print('[APPLY] 完成: 共写入 %d 行 (规则%d + 卡片%d)' % (inserted, len(rules), len(cards_ge4)))


if __name__ == '__main__':
    main()
