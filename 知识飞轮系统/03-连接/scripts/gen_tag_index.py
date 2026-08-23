#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段4 标签体系自动生成（v1.1 2026-08-23 修复：动态日期/真实环比/动态关联）。
扫描 VAULT 全库 .md，提取 frontmatter tags，生成/更新标签索引.md。"""
import os, re, datetime, glob

VAULT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT = os.path.join(VAULT, "03-连接", "标签体系", "标签索引.md")
PREV = OUT  # 读旧文件取上周环比基准

TODAY = datetime.datetime.now()
CUR_STR = TODAY.strftime("%Y-%m-%d")
CUR_MD = TODAY.strftime("%m-%d")
PREV_STR = None  # 旧文件"生成时间"日期（= 上周）

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

def read_prev_txt():
    if not os.path.exists(PREV):
        return None
    try:
        return open(PREV, encoding='utf-8', errors='ignore').read()
    except Exception:
        return None

def parse_prev_col(key):
    """从旧文件解析 '| key | 本周值 | ...' 的第一列数值（** 包裹兼容），作为环比基准。"""
    txt = read_prev_txt()
    if not txt:
        return None
    m = re.search(r'\|\s*' + re.escape(key) + r'\s*\|\s*\*{0,2}([\d.]+)%?\*{0,2}\s*\|', txt)
    if m:
        try:
            return float(m.group(1))
        except Exception:
            return None
    return None

def parse_prev_date():
    """解析旧文件 '> 生成时间：YYYY-MM-DD' 取上周日期。"""
    txt = read_prev_txt()
    if not txt:
        return None
    m = re.search(r'>\s*生成时间：(\d{4}-\d{2}-\d{2})', txt)
    return m.group(1) if m else None

def fmt_num(v):
    """整数浮点显示为整数，其余原样。"""
    if v is None:
        return "—"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)

def fmt_delta(cur, prev, dec=1):
    if prev is None:
        return "—"
    d = cur - prev
    if isinstance(d, float):
        if d.is_integer():
            return f"{'🔺' if d >= 0 else '🔻'} {int(d):+d}"
        return f"{'🔺' if d >= 0 else '🔻'} {d:+.{dec}f}"
    return f"{'🔺' if d >= 0 else '🔻'} {d:+d}"

def fmt_delta_pp(cur, prev):
    if prev is None:
        return "—"
    d = cur - prev
    return f"{'🔺' if d >= 0 else '🔻'} {d:+.1f}pp"

# ---------- 扫描 ----------
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

high = {k: v for k, v in tag_counter.items() if v >= 20}
mid = {k: v for k, v in tag_counter.items() if 5 <= v < 20}
low = {k: v for k, v in tag_counter.items() if v < 5}
dirty = [k for k in tag_counter if ' ' in k]
top5 = sorted(tag_counter.items(), key=lambda x: -x[1])[:5]

# ---------- 上周环比基准（解析旧文件"本周"列） ----------
prev_total = parse_prev_col('扫描笔记数')
prev_tagged = parse_prev_col('带标签笔记数')
prev_cov = parse_prev_col('标签覆盖率')
prev_uniq = parse_prev_col('不同标签数')
prev_uses = parse_prev_col('标签总使用次数')
prev_hhi = parse_prev_col('HHI（集中度，越低越均匀）')
prev_uniform = parse_prev_col('分布均匀度（1/HHI）')
prev_date_full = parse_prev_date()
prev_md = prev_date_full[5:] if prev_date_full else None  # MM-DD

# ---------- 关联（动态找最新） ----------
link_log = ""
link_gap = ""
def newest_md(pattern):
    hits = glob.glob(os.path.join(VAULT, "**", pattern), recursive=True)
    hits = [h for h in hits if '/.' not in h]
    return os.path.basename(sorted(hits)[-1]) if hits else None
bl = newest_md("补链日志-*.md")
zs = newest_md("知识盲区扫描-*.md")
if bl:
    link_log = f"- [[{bl[:-3]}]]（阶段3）"
if zs:
    link_gap = f"- [[{zs[:-3]}]]（阶段1）"

# ---------- 生成 markdown ----------
L = []
L.append(f'---\ncreated: 2026-07-27T09:47\nupdated: {TODAY.strftime("%Y-%m-%dT%H:%M")}\ntags:\n  - 标签体系\n---\n')
L.append('# 标签索引（自动生成）\n')
L.append(f'> 生成时间：{CUR_STR} ｜ 自动化任务「周日批处理·标签与质量监控」阶段 4')
L.append('> 扫描范围：知识飞轮系统全库 `.md`（排除 .obsidian/.workbuddy）')
L.append(f'> 上次生成：{prev_date_full or "—"}（{fmt_num(prev_total)} 篇 / {fmt_num(prev_uniq)} 标签）\n')
L.append('## 一、概览\n')
L.append(f'| 指标 | 本周（{CUR_MD}） | 上周（{prev_md or "—"}） | 变化 |')
L.append('|------|------|------|------|')
L.append(f'| 扫描笔记数 | {total} | {fmt_num(prev_total)} | {fmt_delta(total, prev_total)} |')
L.append(f'| 带标签笔记数 | {tagged} | {fmt_num(prev_tagged)} | {fmt_delta(tagged, prev_tagged)} |')
L.append(f'| 标签覆盖率 | **{coverage:.1f}%** | {prev_cov:.1f}% | {fmt_delta_pp(coverage, prev_cov)} |')
L.append(f'| 不同标签数 | {uniq} | {fmt_num(prev_uniq)} | {fmt_delta(uniq, prev_uniq)} |')
L.append(f'| 标签总使用次数 | {uses} | {fmt_num(prev_uses)} | {fmt_delta(uses, prev_uses)} |')
L.append(f'| HHI（集中度，越低越均匀） | {hhi:.4f} | {prev_hhi:.4f} | {fmt_delta(hhi, prev_hhi, dec=4)} |')
L.append(f'| 分布均匀度（1/HHI） | {uniformity:.1f} | {fmt_num(prev_uniform)} | — |\n')
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
L.append(f'- 低频标签（<5 次，{len(low)} 个）建议季度合并：同义归并、停用词剔除。')
L.append('- 延续"转写产物/裁判规则/经验卡片"主轴标签，保持检索可用性与分类稳定性。\n')
L.append('## 关联\n')
if link_gap:
    L.append(link_gap)
if link_log:
    L.append(link_log)

open(OUT, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print(f"扫描={total} 带标签={tagged} 覆盖率={coverage:.1f}% 唯一标签={uniq} 总使用={uses} HHI={hhi:.4f} 均匀度={uniformity:.1f}")
print("TOP5:", top5)
print(f"高频{len(high)} 中频{len(mid)} 低频{len(low)} 脏标签{len(dirty)}")
print(f"环比基准: 扫描{prev_total} 覆盖率{prev_cov}% 唯一标签{prev_uniq} 上次生成{prev_date_full}")
print(f"关联: {link_gap} / {link_log}")
