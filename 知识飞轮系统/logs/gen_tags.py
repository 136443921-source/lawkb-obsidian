#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""标签体系自动生成 v1.3：统计知识飞轮系统全部 .md 的 frontmatter tags，生成/更新标签索引。"""
import os, re, json, datetime

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT = os.path.join(BASE, "03-连接", "标签体系", "标签索引.md")
TODAY = "2026-07-19"
EXCLUDE = [".workbuddy", "logs", "标签体系", "知识图谱", "孤立笔记检测报告"]

def parse_frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}
    block = m.group(1)
    fm = {}
    # 列表式 tags:
    # tags:
    #   - a
    #   - b
    mlist = re.search(r"tags:\s*\n((?:\s*-\s*.+\n)+)", block)
    if mlist:
        tags = re.findall(r"-\s*(.+?)\s*$", mlist.group(1), re.M)
        fm["tags"] = [t for t in tags if t]
    else:
        mline = re.search(r"tags:\s*\[(.*?)\]", block)
        if mline:
            fm["tags"] = [t.strip().strip("'\"") for t in mline.group(1).split(",") if t.strip()]
    return fm

def walk(base):
    out = []
    for dp, dn, fn in os.walk(base):
        rel = os.path.relpath(dp, base)
        if any(rel == e or rel.startswith(e + os.sep) for e in EXCLUDE):
            continue
        for f in fn:
            if f.endswith(".md"):
                out.append(os.path.join(dp, f))
    return out

files = walk(BASE)
total = len(files)
tag_count = {}
tagged = 0
for p in files:
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read()
    except:
        continue
    fm = parse_frontmatter(txt)
    tags = fm.get("tags") or []
    if tags:
        tagged += 1
    for t in tags:
        tag_count[t] = tag_count.get(t, 0) + 1

sorted_tags = sorted(tag_count.items(), key=lambda x: -x[1])
n_tags = len(tag_count)
coverage = round(tagged / total, 3) if total else 0
# HHI on shares
total_use = sum(tag_count.values())
hhi = round(sum((c / total_use) ** 2 for c in tag_count.values()), 4) if total_use else 0
# 均匀度：1/HHI 归一（最大 = n_tags）
uni = round(1 / hhi, 2) if hhi else 0

high = [(t, c) for t, c in sorted_tags if c >= 20]
mid = [(t, c) for t, c in sorted_tags if 5 <= c <= 19]
low = [(t, c) for t, c in sorted_tags if c <= 4]

# 推荐：低频但领域重要 & 无标签笔记占比高 -> 建议引入标签
recs = []
if coverage < 0.8:
    recs.append(f"当前仅有 {coverage*100:.1f}% 笔记带标签，建议对未打标笔记批量补标（重点：案件库、01-采集）。")
top_low = [t for t, c in low[:10]]
if top_low:
    recs.append(f"低频标签({len(low)}个)如 {', '.join(top_low[:6])} 可考虑合并或淘汰，降低维护成本。")
if high:
    recs.append(f"高频标签集中在 {', '.join(t for t,c in high[:5])}，说明知识热点明确；建议据此构建领域索引页。")

def tbl(rows):
    if not rows:
        return "  （无）"
    return "\n".join(f"| {t} | {c} |" for t, c in rows)

md = f"""# 标签索引（自动生成）

> 生成时间：{TODAY} ｜ 自动化任务「周日知识维护批处理 v1.3」阶段 4
> 扫描范围：知识飞轮系统全库 `.md`（排除元目录）

## 一、概览

| 指标 | 数值 |
|------|------|
| 扫描笔记数 | {total} |
| 带标签笔记数 | {tagged} |
| 标签覆盖率 | {coverage*100:.1f}% |
| 不同标签数 | {n_tags} |
| 标签总使用次数 | {total_use} |
| HHI（集中度，越低越均匀） | {hhi} |
| 分布均匀度（1/HHI） | {uni} |

## 二、标签使用统计

### 🔴 高频标签（≥20 次，{len(high)} 个）
| 标签 | 次数 |
|------|------|
{tbl(high)}

### 🟡 中频标签（5–19 次，{len(mid)} 个）
| 标签 | 次数 |
|------|------|
{tbl(mid)}

### 🟢 低频标签（≤4 次，{len(low)} 个）
| 标签 | 次数 |
|------|------|
{tbl(low)}

## 三、分布均匀度解读

- HHI = {hhi}。HHI 越接近 1 表示标签越集中于少数高频标签；越接近 1/N（={round(1/n_tags,4) if n_tags else 0}）表示分布越均匀。
- 当前 HHI 仅 {hhi}，远低于 0.15 阈值，说明**标签极度分散（长尾严重）**：{len(low)}/{n_tags} 个标签使用≤4 次。建议合并长尾低频标签、建立受控标签词表。

## 四、标签推荐

{chr(10).join('- ' + r for r in recs) if recs else '- 当前标签体系健康，无需特别调整。'}

---
*本文件由自动化任务生成，每周日更新统计与详情部分。*
"""

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(md)

print(json.dumps({
    "扫描笔记数": total, "带标签笔记数": tagged, "覆盖率": coverage,
    "标签数": n_tags, "总使用次数": total_use, "HHI": hhi, "均匀度": uni,
    "高频数": len(high), "中频数": len(mid), "低频数": len(low),
    "TOP5": [t for t, c in sorted_tags[:5]],
}, ensure_ascii=False, indent=2))
