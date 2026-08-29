#!/usr/bin/env python3
# 月度回灌 · 补填 4 张 LTI 卡（C301 误杀澄清后，用户 2026-08-28 授权显式补入）
# 设计：硬编码 4 个原始 LTI 卡路径；运行时对「已入索引」的路径自动跳过，防御性杜绝重复行。
# 仅追加新行，不删不改已有行；写入前须先 cp 备份 self.md（六-B）。
import sys, os, re
sys.path.insert(0, '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/03-连接/scripts')

SELF = '/Users/chenyouqiang/.workbuddy/skills/xiaoqianglvshi/self.md'
KB = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统'
ANCHOR = '> 索引随月度蒸馏增长'
BACKUP = '/Users/chenyouqiang/WorkBuddy/Claw/backups/xiaoqiang_self/self_backup_20260828-110547/self.md.bak'
BATCH = 50

# 4 张原始 LTI 卡（路径相对 KB）
LTI_PATHS = [
    '02-提炼/经验卡片/慈善组织合同纠纷/基金会贷款合同纠纷案.md',
    '02-提炼/经验卡片/公众号/医院捐赠合规管理-药企赞助红线.md',
    '02-提炼/经验卡片/医疗纠纷/医疗纠纷应急处置全流程模板-经验卡片.md',
    '02-提炼/经验卡片/医疗纠纷/超龄劳动者基本权益保障暂行规定-工伤保障重大变化-2026-07-23.md',
]

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
                    k, v = line.split(':', 1); fm[k.strip()] = v.strip()
            body = rest[m.end():]
    return fm, body

def get_title(fm, body, path):
    if fm.get('title'):
        t = fm['title'].strip().strip('\'"').strip()
        return t
    for ln in body.split('\n'):
        if ln.startswith('# '):
            return ln[2:].strip()
    return os.path.splitext(os.path.basename(path))[0]

def get_summary(fm, body):
    if fm.get('summary'):
        return fm['summary'].strip()
    for ln in body.split('\n'):
        s = ln.strip()
        if not s or s.startswith('#') or s.startswith('>') or s.startswith('|') or s.startswith('-') or s.startswith('```'):
            continue
        s = re.sub(r'[#*`_\[\]]', '', s).replace('\n', ' ').replace('|', '／')[:80]
        return s
    return ''

def already_paths(text):
    # 去重：捕获整条「反引号包裹的 KB 相对路径」（含前缀+中间+ .md），用于全局判定是否已索引。
    # 注意：捕获组必须包住完整路径，否则只捕获到 (02-提炼|06-沉淀) 前缀，导致去重失效、写入重复行。
    s = set(re.findall(r'`((?:02-提炼|06-沉淀)[^`]+\.md)`', text))
    return s

def build_rows():
    text = open(SELF, encoding='utf-8').read()
    existing = already_paths(text)
    rows = []
    skipped = []
    for rel in LTI_PATHS:
        abs_p = os.path.join(KB, rel)
        if not os.path.exists(abs_p):
            print('  ⚠️ 路径不存在(跳过):', rel); continue
        if rel in existing:
            skipped.append(rel); continue
        fm, body = parse_fm(abs_p)
        title = get_title(fm, body, abs_p)
        summary = get_summary(fm, body)
        rows.append('| 经验卡片-%s | `%s` | %s |' % (title, rel, summary))
    return rows, skipped

if __name__ == '__main__':
    apply = '--apply' in sys.argv
    rows, skipped = build_rows()
    print('待补行数=%d' % len(rows))
    for r in rows:
        print('  +', r[:90])
    print('已跳过(已在索引)=%d: %s' % (len(skipped), skipped))
    if not apply:
        print('[DRY-RUN] 未写入。')
        sys.exit(0)
    # ---- apply ----
    if not os.path.exists(BACKUP):
        print('❌ 备份缺失, 中止'); sys.exit(1)
    assert os.path.getsize(SELF) == os.path.getsize(BACKUP), '源/备字节不一致, 中止'
    cur = open(SELF, encoding='utf-8').read().split('\n')
    ai = None
    for i, ln in enumerate(cur):
        if ln.strip().startswith(ANCHOR):
            ai = i; break
    assert ai is not None, 'ANCHOR 丢失! 中止'
    new_cur = cur[:ai] + rows + cur[ai:]
    open(SELF, 'w', encoding='utf-8').write('\n'.join(new_cur))
    # 校验
    after = open(SELF, encoding='utf-8').read()
    assert 'Self Memory' in after, 'Self Memory 丢失! 回滚'
    assert after.count('## 经验索引区') == 1, '章节异常! 回滚'
    for rel in LTI_PATHS:
        if rel in skipped:
            continue
        if ('`%s`' % rel) not in after:
            print('❌ 行缺失, 立即回滚:', rel)
            import shutil; shutil.copy2(BACKUP, SELF); sys.exit(1)
    after_lines = after.split('\n')
    print('✅ 写入 %d 行（跳过 %d 已存在）; self.md 现 %d 行' % (len(rows), len(skipped), len(after_lines)))
