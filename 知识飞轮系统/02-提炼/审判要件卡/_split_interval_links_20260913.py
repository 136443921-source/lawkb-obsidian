#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
区间引用拆分器  v1.0 / 2026-09-13

把 `[[R-AY-096~097-著作权商标权权属侵权]]` 这类「族」区间引用，
拆成逐条真实存在的链接：`[[R-AY-096-...]] · [[R-AY-097-...]]`

安全前提（已验证）：区间内**每个**编号都能在全库唯一命中一张卡，
否则宁可不拆（拆开会制造新死链）。

用法：python _split_interval_links_20260913.py [--apply]
"""
import json, os, re, glob, shutil, datetime, sys

ROOT = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统'
APPLY = '--apply' in sys.argv
STAMP = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
BK = f'/tmp/区间引用拆分_{STAMP}'

INTER = json.load(open('/tmp/inter_ok_0913.json', encoding='utf-8'))

# 预建替换映射：死链名 -> 拆分后的串（正文用 wikilink）
REPL = {}
# 拆分后的真实卡名列表（frontmatter 用裸名多行）
REPL_PARTS = {}
for it in INTER:
    name = it['name']
    parts = [c for n, c in it['map']]
    REPL[name] = ' · '.join(f'[[{c}]]' for c in parts)
    REPL_PARTS[name] = parts
    bare = name.split('~')[0] + '~' + name.split('~')[1].split('-')[0]
    if bare != name:
        REPL[bare] = ' · '.join(f'[[{c}]]' for c in parts)
        REPL_PARTS[bare] = parts


def main():
    files = []
    for pat in ('06-沉淀/**/*.md', '02-提炼/**/*.md', '03-连接/**/*.md'):
        files += glob.glob(os.path.join(ROOT, pat), recursive=True)

    if APPLY:
        os.makedirs(BK, exist_ok=True)

    total = 0
    touched = []
    for p in files:
        try:
            t = open(p, encoding='utf-8').read()
        except Exception:
            continue
        o = t
        n = 0

        # ---- 分区处理：frontmatter 内禁止 wikilink（[[ 会被 YAML 当流样式序列）----
        fm, body = '', t
        if t.startswith('---'):
            e = t.find('\n---', 3)
            if e > 0:
                fm, body = t[:e + 4], t[e + 4:]

        # ① frontmatter：列表项形态 `  - R-AY-079~083（…）` → 拆成多行裸名列表项
        for k in sorted(REPL_PARTS, key=len, reverse=True):
            pat = re.compile(r'^([ \t]*)-[ \t]*' + re.escape(k) + r'.*$', re.M)

            def _rep(mo, parts=REPL_PARTS[k]):
                ind = mo.group(1)
                return '\n'.join(f'{ind}- {c}' for c in parts)

            fm2 = pat.sub(_rep, fm)
            if fm2 != fm:
                n += len(pat.findall(fm))
                fm = fm2

        # ② 正文：wikilink 与裸名 → `[[A]] · [[B]]`
        for k in sorted(REPL, key=len, reverse=True):
            if k in body:
                n += body.count(k)
                body = body.replace(k, REPL[k])

        t = fm + body if fm else body
        if t == o:
            continue
        total += n
        touched.append((p, n))
        if APPLY:
            shutil.copy2(p, os.path.join(BK, os.path.basename(p)))
            open(p, 'w', encoding='utf-8').write(t)

    print(f'{"[APPLY]" if APPLY else "[DRY-RUN]"} 区间拆分映射 {len(REPL)} 条 | 命中文件 {len(touched)} | 替换 {total} 处')
    for p, n in sorted(touched, key=lambda x: -x[1])[:8]:
        print(f'   {n:3d} 处  {os.path.relpath(p, ROOT)}')
    if APPLY:
        print(f'备份：{BK}（{len(os.listdir(BK))} 份）')


if __name__ == '__main__':
    main()
