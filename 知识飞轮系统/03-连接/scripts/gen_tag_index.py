#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段4 标签体系自动生成（对齐 W31 格式）。扫描 VAULT 全库 .md，提取 frontmatter tags。"""
import os, re, json

VAULT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT = os.path.join(VAULT, "03-连接", "标签体系", "标签索引.md")
PREV = OUT  # 读旧文件取上周环比

def get_all_md():
    out = []
    for r, d, fs in os.walk(VAULT):
        d[:] = [x for x in d if not x.startswith('.')]
        for f in fs:
            if f.endswith('.md'):
                out.append(os.path.join(r, f))
    return out

def extract_tags(text):
    if not text.startswith('---'):
        return []
    end = text.find('\n---', 3)
    if end == -1:
        return []
    fm = text[3:end]
    # inline: tags: [a, b]
    m = re.search(r'^tags:\s*\[(.*?)\]', fm, re.M)
    if m:
        return [t.strip() for t in m.group(1).split(',') if t.strip()]
    # block: tags:\n  - a\n  - b
    mb = re.search(r'^tags:\s*\n((?:\s*-\s*.+\n)+)', fm, re.M)
    if mb:
        return [l.strip().lstrip('-').strip() for l in mb.group(1).splitlines() if l.strip().startswith('-')]
    return []

files = get_all_md()
tag_counter = {}
tagged = 0
total = 0
for f in files:
    total += 1
    try:
        t = open(f, encoding='utf-8', errors='ignore').read()
    except Exception:
        continue
    tags = extract_tags(t)
    if tags:
        tagged += 1
        for tg in tags:
            tag_counter[tg] = tag_counter.get(tg, 0) + 1

uniq = len(tag_counter)
uses = sum(tag_counter.values())
coverage = (tagged / total * 100) if total else 0
hhi = sum((c / uses) ** 2 for c in tag_counter.values()) if uses else 0
uniformity = (1 / hhi) if hhi else 0

# 高低频
high = {k: v for k, v in tag_counter.items() if v >= 20}
mid = {k: v for k, v in tag_counter.items() if 5 <= v < 20}
low = {k: v for k, v in tag_counter.items() if v < 5}

# 含空格的脏标签（W31 跟踪点）
dirty = [k for k in tag_counter if ' ' in k]

# 解析上周环比
def parse_prev(key):
    if not os.path.exists(PREV):
        return None
    txt = open(PREV, encoding='utf-8', errors='ignore').read()
    m = re.search(r'\|\s*' + re.escape(key) + r'\s*\|\s*([\d.]+)%?\s*\|\s*([\d.]+)%?', txt)
    if m:
        try: return float(m.group(2))
        except: return None
    return None

prev_total = parse_prev('扫描笔记数')
prev_cov = parse_prev('标签覆盖率')
prev_uniq = parse_prev('不同标签数')

def fmt_delta(cur, prev):
    if prev is None:
        return "—"
    d = cur - prev
    return f"{'🔺' if d >= 0 else '🔻'} {d:+.1f}" if isinstance(d, float) else f"{'🔺' if d >= 0 else '🔻'} {d:+d}"

top5 = sorted(tag_counter.items(), key=lambda x: -x[1])[:5]

# 生成 markdown
L = []
L.append('---\ncreated: 2026-07-27T09:47\nupdated: 2026-08-09T22:45\ntags:\n  - 标签体系\n---\n')
L.append('# 标签索引（自动生成）\n')
L.append('> 生成时间：2026-08-09 ｜ 自动化任务「周日知识维护批处理 v1.6」阶段 4')
L.append('> 扫描范围：知识飞轮系统全库 `.md`（排除 .obsidian/.workbuddy）')
L.append('> 上次生成：2026-08-02（1132 篇 / 561 标签）\n')
L.append('## 一、概览\n')
L.append('| 指标 | 本周（08-09） | 上周（08-02） | 变化 |')
L.append('|------|------|------|------|')
L.append(f'| 扫描笔记数 | {total} | 1132 | {fmt_delta(total, 1132)} |')
L.append(f'| 带标签笔记数 | {tagged} | 1101 | {fmt_delta(tagged, 1101)} |')
L.append(f'| 标签覆盖率 | **{coverage:.1f}%** | 97.3% | {fmt_delta(coverage, 97.3)}pp |')
L.append(f'| 不同标签数 | {uniq} | 561 | {fmt_delta(uniq, 561)} |')
L.append(f'| 标签总使用次数 | {uses} | 3370 | {fmt_delta(uses, 3370)} |')
L.append(f'| HHI（集中度，越低越均匀） | {hhi:.4f} | 0.0248 | {fmt_delta(hhi, 0.0248)} |')
L.append(f'| 分布均匀度（1/HHI） | {uniformity:.1f} | 40.4 | — |\n')
L.append('## 二、标签使用统计\n')
L.append(f'### 🔴 高频标签（≥20 次，{len(high)} 个）')
L.append('| 标签 | 次数 |')
L.append('|------|------|')
for k, v in sorted(high.items(), key=lambda x: -x[1])[:30]:
    L.append(f'| {k} | {v} |')
L.append('')
L.append(f'### 🟡 中频标签（5-19 次，{len(mid)} 个）')
L.append(f'> 抽样（前15）：' + '、'.join(f'{k}({v})' for k, v in sorted(mid.items(), key=lambda x: -x[1])[:15]))
L.append('')
L.append(f'### 🟢 低频标签（<5 次，{len(low)} 个）')
L.append(f'> 占比 {len(low)/uniq*100:.1f}%，长尾标签，建议定期合并或淘汰。\n')
L.append('## 三、覆盖率与集中度解读\n')
L.append(f'- 标签覆盖率 **{coverage:.1f}%**（{tagged}/{total} 篇带标签），维持高位。')
L.append(f'- HHI={hhi:.4f}（{uniformity:.1f} 均匀度）：标签体系较分散，无单一标签垄断（最高 `{top5[0][0]}` {top5[0][1]} 次，占比 {top5[0][1]/uses*100:.1f}%）。')
L.append(f'- TOP5 高频标签：' + '、'.join(f'{k}({v})' for k, v in top5) + '。\n')
L.append('## 四、推荐（基于本周扫描）\n')
if dirty:
    L.append(f'- **脏标签规整（W31 跟踪点）**：检出 {len(dirty)} 个含空格复合标签，如：' +
             '、'.join(f'`{k}`' for k in dirty[:6]) + '。建议规范为单一标签（如 `概念页`+`概念-通用` 拆为 `概念-通用`），防标签爆炸。')
else:
    L.append('- 脏标签（含空格复合标签）已清零。')
L.append('- 低频标签（<5 次，%d 个）建议季度合并：同义归并、停用词剔除。' % len(low))
L.append('- 延续"转写产物/裁判规则/经验卡片"主轴标签，保持检索可用性与分类稳定性。\n')
L.append('## 关联\n')
L.append('- [[知识盲区扫描-2026-08-09]]（阶段1）')
L.append('- [[补链日志-2026-08-09]]（阶段3）')

open(OUT, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print(f"扫描={total} 带标签={tagged} 覆盖率={coverage:.1f}% 唯一标签={uniq} 总使用={uses} HHI={hhi:.4f} 均匀度={uniformity:.1f}")
print("TOP5:", top5)
print(f"高频{len(high)} 中频{len(mid)} 低频{len(low)} 脏标签{len(dirty)}")
