#!/usr/bin/env python3
# monthly_backfill_missing_cards.py — 补填 21 张漏网卡片（2026-08-28 用户追加授权）
# 目标：将「8 月新建、尚未入 self.md 经验索引区」的经验卡片全部补进索引（不限 importance 字段）。
# 复用受控回填的已验证逻辑：锚点前最后一条 | 数据行之后插入 + 每批校验 + 异常回滚到备份。
# 默认 dry-run 仅统计；--apply 才分批写入。
import os, re, sys, json, datetime, shutil

KB = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统'
CARD_DIR = os.path.join(KB, '02-提炼/经验卡片')
SELF = '/Users/chenyouqiang/.workbuddy/skills/xiaoqianglvshi/self.md'
MONTH = datetime.date(2026, 8, 1)
BACKUP = '/Users/chenyouqiang/WorkBuddy/Claw/backups/xiaoqiang_self/self_backup_20260828-104222/self.md.bak'
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
    # 与受控回填一致口径：created>=08-01 或 created 缺且 updated>=08-01
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
    rows = []
    for root, dirs, files in os.walk(CARD_DIR):
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
            if not summary:
                summary = title  # 兜底：正文首段纯结构块时回退到标题，避免空单元格
            rows.append('| 经验卡片-%s | `%s` | %s |' % (title, rel, summary))
    return rows, already, total_lines


def main():
    rows, already, total_lines = build_rows()
    pred = total_lines + len(rows)
    print('=== 补填漏网卡片 DRY-RUN (month>=%s) ===' % MONTH.isoformat())
    print('  self.md 当前总行=%d | 已索引(KB路径)=%d' % (total_lines, len(already)))
    print('  待补卡片(8月新建且未入索引)=%d' % len(rows))
    print('  预测 self.md 总行≈%d (原%d + 写入%d)' % (pred, total_lines, len(rows)))
    for r in rows:
        print('  +', r[:120])
    json.dump({'rows': rows, 'pred_total': pred, 'total_lines': total_lines},
              open('/tmp/missing_cards_plan.json', 'w'), ensure_ascii=False, indent=2)

    if '--apply' not in sys.argv:
        print('\n[DRY-RUN] 未写入。加 --apply 执行分批写入。')
        return

    # ---- APPLY ----
    assert os.path.exists(BACKUP), '备份缺失! 中止'
    original = open(SELF, encoding='utf-8').read()
    sec_count = sum(1 for l in original.split('\n') if l.startswith('## '))
    total_before = len(original.split('\n'))
    print('\n[APPLY] 备份校验通过, 起始章节数=%d, 总行=%d' % (sec_count, total_before))

    inserted = 0
    for bi in range(0, len(rows), BATCH):
        chunk = rows[bi:bi + BATCH]
        cur = open(SELF, encoding='utf-8').read().split('\n')
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
            print('  批 %d-%d: 写 %d 行, 现总行 %d' % (bi + 1, bi + len(chunk), len(chunk), total_before))
        except AssertionError as e:
            open(SELF, 'w', encoding='utf-8').write(original)
            print('  ❌ 校验失败: %s — 已回滚' % e)
            raise
    print('[APPLY] 完成: 共写入 %d 行' % inserted)


if __name__ == '__main__':
    main()
