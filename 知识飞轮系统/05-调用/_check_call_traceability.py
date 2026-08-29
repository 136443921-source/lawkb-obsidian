#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
05-调用 留痕合规核验器 v1.0.0
用途：核验每条调用记录的 frontmatter `knowledge_called` 是否非空，落实「调用留痕」常态纪律。

⚠️ 关键：必须同时支持两种 YAML 写法，否则会大规模误判——
   ① inline：  knowledge_called: [R-HT-109, 经验卡片-XX]
   ② 块状：    knowledge_called:
                 - 经验卡片-XX
   （2026-08-28 教训：用 `grep '^knowledge_called:'` 取值会把块状格式全判成"无字段"，
     曾误报 12 条合规记录为不合规。）

用法：
   python3 _check_call_traceability.py          # 核验并打印报告
   python3 _check_call_traceability.py --quiet  # 仅打印汇总（供自动化）
退出码：0=全合规  1=存在不合规
"""
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
QUIET = "--quiet" in sys.argv

# 非调用记录文件（规范/索引/日志模板等），不纳入核验分母
EXCLUDE_NAMES = {
    '_template.md', 'README.md',
    '调用记录规范.md', '调用记录缺口-2026-08.md',
    '合同文书台账索引.md',
}
EXCLUDE_DIRS = {'协同命中'}          # 协同命中有独立字段规范
# 仅"未复核"类值判定为不合规（亮红，逼人工处置）；
# "无"/none/NA 属"已复核、确无飞轮资产命中"的诚实状态，视为合规（字段存在且非空占位）。
EMPTY_VALUES = {'待人工补登', '待补登', '未复核', 'tbd', 'TODO', 'xxx', '待定', '[]', '空', '-', 'null', 'None', ''}


def parse_knowledge_called(text: str):
    """返回 (状态, 值摘要)：状态 ∈ {'ok','empty','missing','no_frontmatter'}"""
    if not text.startswith('---'):
        return 'no_frontmatter', ''
    end = text.find('\n---', 3)
    if end < 0:
        return 'no_frontmatter', ''
    fm = text[3:end]

    lines = fm.split('\n')
    for i, ln in enumerate(lines):
        m = re.match(r'^knowledge_called:\s*(.*)$', ln)
        if not m:
            continue
        inline = m.group(1).strip()
        if inline:
            # ① inline 写法
            cleaned = inline.strip('[]').strip()
            if not cleaned or inline in EMPTY_VALUES or cleaned in EMPTY_VALUES:
                return 'empty', inline
            return 'ok', inline
        # ② 块状写法：向下收集 "- xxx"
        items = []
        for nxt in lines[i + 1:]:
            if re.match(r'^\s+-\s+\S', nxt):
                items.append(nxt.strip().lstrip('-').strip())
            elif re.match(r'^\S', nxt):
                break
        if items and not all(x in EMPTY_VALUES for x in items):
            return 'ok', f'{len(items)} 项: ' + '; '.join(items[:3])
        return 'empty', '(块状为空)'
    return 'missing', ''


def main():
    stats = {'ok': [], 'empty': [], 'missing': [], 'no_frontmatter': []}
    for f in sorted(BASE.rglob('*.md')):
        if f.name in EXCLUDE_NAMES or f.name.startswith('.'):
            continue
        if any(part in EXCLUDE_DIRS for part in f.relative_to(BASE).parts[:-1]):
            continue
        if '.bak' in f.name:
            continue
        try:
            txt = f.read_text(encoding='utf-8')
        except Exception:
            continue
        st, val = parse_knowledge_called(txt)
        stats[st].append((str(f.relative_to(BASE)), val))

    total = sum(len(v) for v in stats.values())
    ok = len(stats['ok'])
    bad = total - ok

    if not QUIET:
        print("=" * 62)
        print("  05-调用 留痕合规核验报告")
        print("=" * 62)
        for rel, val in stats['ok']:
            print(f"  ✅ {rel}\n       → {val[:90]}")
        for key, icon, label in [('empty', '🔴', '值为空/占位'),
                                 ('missing', '⬜', '缺 knowledge_called 字段'),
                                 ('no_frontmatter', '⛔', '无 frontmatter')]:
            for rel, val in stats[key]:
                print(f"  {icon} [{label}] {rel} {val}")
        print("-" * 62)

    rate = ok / total * 100 if total else 100.0
    print(f"汇总：总记录 {total} | 合规 {ok} | 不合规 {bad} | 合规率 {rate:.1f}%")
    if bad:
        print("处置：为不合规记录补 frontmatter `knowledge_called`，"
              "列出本次真实命中的经验卡/规则卡（无命中则写明原因，禁止伪造）。")
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
