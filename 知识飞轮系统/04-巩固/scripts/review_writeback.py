#!/usr/bin/env python3
"""
复习批量回写脚本（SM-2 评分回写）
功能：根据用户提供的 [笔记名:评分] 列表，批量更新笔记 frontmatter 的 5 个 SM-2 字段。
用法：
  python3 review_writeback.py --pairs "笔记A:4,笔记B:5,笔记C:2"          # dry-run 预览
  python3 review_writeback.py --pairs "笔记A:4,笔记B:5" --apply          # 正式写入（自动备份）
  python3 review_writeback.py --file scores.json --apply                 # 从 JSON 读入
scores.json 格式: [{"name": "笔记A", "q": 4}, ...]

安全铁律（对齐知识飞轮「六-B 安全铁律」）：
  1. 默认 dry-run，不写盘；
  2. --apply 前自动备份所有将被修改的文件到 .review-backup-<日期>/（与源文件同相对路径）；
  3. 备份成功后打印数量确认，再逐个写入。
"""

import os, re, sys, json, shutil, datetime, argparse
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent  # 知识飞轮系统/
BACKUP_ROOT = BASE / f'.review-backup-{datetime.date.today().strftime("%Y%m%d")}'

FM_PATTERN = re.compile(r'^---\n(.*?)\n---', re.DOTALL)
RD_PATTERN = re.compile(r'review_date:\s*["\']?(\d{4}-\d{2}-\d{2})')
IMP_PATTERN = re.compile(r'importance:\s*(\d+)')
REP_PATTERN = re.compile(r'repetition:\s*(\d+)')
EF_PATTERN = re.compile(r'ease_factor:\s*([\d.]+)')
INT_PATTERN = re.compile(r'interval:\s*(\d+)')


def sm2(q, old_rep, old_interval, old_ef, min_interval=1):
    """SM-2 核心算法，返回 (new_rep, new_interval, new_ef)。
    标准规则：首次通过（repetition=0 且 q>=3）interval 固定为 1；
    二次及以后按 q 分档。min_interval 为首次间隔下限，可调大以放宽节奏。
    """
    if q < 3:
        return old_rep, 1, max(1.3, round(old_ef - 0.2, 2))
    if old_rep == 0:  # 首次通过
        return 1, max(1, min_interval), old_ef
    if q == 3:
        return old_rep + 1, old_interval, old_ef
    if q == 4:
        return old_rep + 1, max(1, round(old_interval * old_ef)), old_ef
    # q == 5
    return old_rep + 1, max(1, round(old_interval * old_ef * 1.1)), old_ef


def find_note(name):
    """按文件名（不含扩展名）全库查找笔记，返回 (path, content, frontmatter) 或 None。"""
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'node_modules']
        for f in files:
            if not f.endswith('.md'):
                continue
            base = f[:-3]
            if base != name:
                continue
            fp = os.path.join(root, f)
            try:
                content = Path(fp).read_text(encoding='utf-8')
            except Exception:
                continue
            fm_match = FM_PATTERN.match(content)
            if not fm_match or not RD_PATTERN.search(fm_match.group(1)):
                continue  # 无 review_date 的笔记不参与回写
            return fp, content, fm_match
    return None


def apply_to_frontmatter(content, fm_match, new_fields):
    """在 frontmatter 内更新/新增字段，保留其余内容不变。"""
    fm = fm_match.group(1)
    lines = fm.split('\n')
    existing = {m.group(1): m for m in
                (re.match(r'([a-z_]+):\s*(.*)', ln) for ln in lines if ln.strip() and not ln.startswith('-'))}
    # 逐行替换
    for i, ln in enumerate(lines):
        m = re.match(r'([a-z_]+):\s*(.*)', ln)
        if m and m.group(1) in new_fields:
            lines[i] = f"{m.group(1)}: {new_fields[m.group(1)]}"
    # 追加不存在的字段
    present = set(m.group(1) for m in (re.match(r'([a-z_]+):\s*(.*)', ln) for ln in lines) if m)
    for k, v in new_fields.items():
        if k not in present:
            lines.append(f'{k}: {v}')
    new_fm = '\n'.join(lines)
    new_content = '---\n' + new_fm + '---' + content[len(fm_match.group(0)):]
    return new_content


def main():
    ap = argparse.ArgumentParser(description='SM-2 复习批量回写')
    ap.add_argument('--pairs', help='"笔记名:评分,笔记名:评分" 逗号分隔')
    ap.add_argument('--file', help='JSON 文件路径 [{"name","q"}]')
    ap.add_argument('--apply', action='store_true', help='正式写入（默认 dry-run）')
    ap.add_argument('--min-interval', type=int, default=1, help='首次通过的最小间隔天数（默认1，可调大如7）')
    args = ap.parse_args()

    entries = []
    if args.file:
        entries = json.loads(Path(args.file).read_text(encoding='utf-8'))
    elif args.pairs:
        for pair in args.pairs.split(','):
            pair = pair.strip()
            if ':' not in pair:
                print(f'⚠️ 跳过无法解析项: {pair}')
                continue
            name, q = pair.rsplit(':', 1)
            entries.append({'name': name.strip(), 'q': int(q.strip())})
    else:
        print('错误：需提供 --pairs 或 --file')
        sys.exit(1)

    today = datetime.date.today()
    updated_at = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M')

    changes = []
    not_found = []
    for e in entries:
        found = find_note(e['name'])
        if not found:
            not_found.append(e['name'])
            continue
        fp, content, fm_match = found
        fm = fm_match.group(1)
        old_rep = int((REP_PATTERN.search(fm) or [None, 0])[1]) if REP_PATTERN.search(fm) else 0
        old_ef = float((EF_PATTERN.search(fm) or [None, 2.5])[1]) if EF_PATTERN.search(fm) else 2.5
        old_int = int((INT_PATTERN.search(fm) or [None, 1])[1]) if INT_PATTERN.search(fm) else 1
        new_rep, new_int, new_ef = sm2(e['q'], old_rep, old_int, old_ef, args.min_interval)
        next_date = (today + datetime.timedelta(days=new_int)).strftime('%Y-%m-%d')
        changes.append({
            'name': e['name'], 'path': fp, 'q': e['q'],
            'review_date': next_date, 'repetition': new_rep,
            'interval': new_int, 'ease_factor': new_ef,
        })

    print(f'📋 待处理 {len(entries)} 篇 | 找到 {len(changes)} | 未找到 {len(not_found)}')
    if not_found:
        print(f'❌ 未找到（无 review_date 或不存在）: {", ".join(not_found)}')

    if not changes:
        print('无变更可执行，退出')
        sys.exit(0)

    print('\n变更预览（dry-run）：')
    print(f'{"笔记":<40} {"q":<3} {"repetition":<10} {"interval":<8} {"EF":<6} 下次复习')
    print('-' * 90)
    for c in changes:
        print(f'{c["name"]:<40} {c["q"]:<3} {c["repetition"]:<10} {c["interval"]:<8} {c["ease_factor"]:<6} {c["review_date"]}')

    if not args.apply:
        print('\n⚠️ 这是 dry-run，未写盘。确认无误后加 --apply 正式写入。')
        return

    # 安全铁律：先备份
    backed = []
    for c in changes:
        src = Path(c['path'])
        dst = BACKUP_ROOT / src.relative_to(BASE)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        backed.append(str(dst))
    print(f'\n🔒 已备份 {len(backed)} 个文件 → {BACKUP_ROOT}')

    # 写入
    for c in changes:
        fp = Path(c['path'])
        content = fp.read_text(encoding='utf-8')
        fm_match = FM_PATTERN.match(content)
        new_content = apply_to_frontmatter(content, fm_match, {
            'review_date': c['review_date'],
            'repetition': c['repetition'],
            'interval': c['interval'],
            'ease_factor': c['ease_factor'],
            'updated': updated_at,
        })
        fp.write_text(new_content, encoding='utf-8')
        print(f'✅ 已更新: {c["name"]}')

    print(f'\n完成：{len(changes)} 篇已回写。备份位于 {BACKUP_ROOT}')


if __name__ == '__main__':
    main()
