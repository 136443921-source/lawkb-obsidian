#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复案由路由卡 version_delta 块标量未缩进导致的 YAML 解析失败
根因：生成器写 `version_delta: |` 但内容行顶格（未缩进）→ YAML 视为块结束，
      后续顶格长行被当 simple key 扫描，触发 "while scanning a simple key"
修法：把 `version_delta: |` 之后、下一个已知顶格 key 之前的行统一缩进 2 空格
用法：
  python _fix_ay_blockscalar_20260913.py --dry-run
  python _fix_ay_blockscalar_20260913.py --apply
"""
import os, re, sys, glob, hashlib
import yaml

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库/案由路由"
# version_delta 之后的合法顶格 key（出现即视为块内容结束）
NEXT_KEYS = re.compile(
    r'^(来源|关联|tags|created|updated|review_date|aliases|geo_scope|library|'
    r'card_subtype|domain|code_2020|code_2025|version_status|title|rule_id|card_type)\s*:'
)
VD_RE = re.compile(r'^version_delta:\s*\|[+-]?\s*$', re.M)


def parse_ok(text: str) -> bool:
    if not text.startswith('---'):
        return False
    end = text.find('\n---', 3)
    if end < 0:
        return False
    fm = text[3:end]
    try:
        yaml.safe_load(fm)
        return True
    except Exception:
        return False


def fix_text(text: str):
    """返回 (新文本, 是否改动)"""
    lines = text.split('\n')
    m = None
    for i, l in enumerate(lines):
        if VD_RE.match(l):
            m = i
            break
    if m is None:
        return text, False
    # 从 m+1 开始扫描块内容边界
    j = m + 1
    while j < len(lines):
        l = lines[j]
        if l.strip() == '':
            j += 1
            continue
        if NEXT_KEYS.match(l):
            break
        j += 1
    if j == m + 1:
        return text, False  # 块内容为空，不处理
    changed = False
    for k in range(m + 1, j):
        if lines[k].strip() == '':
            continue
        if not lines[k].startswith((' ', '\t')):
            lines[k] = '  ' + lines[k]
            changed = True
    if not changed:
        return text, False
    return '\n'.join(lines), True


def main():
    apply = '--apply' in sys.argv
    files = sorted(glob.glob(os.path.join(BASE, 'R-AY-*.md')))
    n_bad_before = 0
    n_fix = 0
    n_fixed_ok = 0
    n_still_bad = []
    samples = []
    for f in files:
        s = open(f, encoding='utf-8').read()
        ok0 = parse_ok(s)
        if not ok0:
            n_bad_before += 1
        s2, ch = fix_text(s)
        if not ch:
            if not ok0:
                n_still_bad.append(os.path.basename(f))
            continue
        ok1 = parse_ok(s2)
        n_fix += 1
        if ok1:
            n_fixed_ok += 1
            if apply:
                open(f, 'w', encoding='utf-8').write(s2)
        else:
            n_still_bad.append(os.path.basename(f))
        if len(samples) < 2:
            samples.append(os.path.basename(f))
    print(f"目录卡数: {len(files)}")
    print(f"修前 YAML 解析失败: {n_bad_before}")
    print(f"命中块标量缺陷并改写: {n_fix}（其中改写后通过: {n_fixed_ok}）")
    print(f"仍失败: {len(n_still_bad)}")
    for x in n_still_bad[:10]:
        print("   ❌", x)
    print("样例:", samples)
    print("模式:", "APPLY" if apply else "DRY-RUN")


if __name__ == '__main__':
    main()
