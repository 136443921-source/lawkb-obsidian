#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""增强双向链接 v1.3（安全版）：对本周新增知识笔记，链接化到「已存在」的概念笔记，绝不制造断链。"""
import os, re, datetime

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
TODAY = datetime.date(2026, 7, 19)
WEEK_AGO = TODAY - datetime.timedelta(days=7)
EXCLUDE_PREFIX = (".workbuddy", "logs", "系统迭代说明", "03-连接/孤立笔记检测报告",
                  "03-连接/知识图谱", "知识飞轮系统/logs")
# 概念来源目录（仅这些目录下的笔记可作为"概念"被链接）
CONCEPT_DIRS = ["02-提炼", "知识库", "03-连接", "04-巩固", "案件库", "01-采集"]
SPECIAL = "（）【】[]（）·、，。：；！？\"'"

def title_of(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        txt = f.read()
    m = re.match(r"^---\s*\n.*?title:\s*(.+?)\s*\n", txt, re.S)
    if m:
        return m.group(1).strip()
    return os.path.splitext(os.path.basename(path))[0]

def is_concept(title):
    if not title or len(title) > 14:
        return False
    if any(c in SPECIAL for c in title):
        return False
    return True

# 1) 建立 概念标题 -> 路径 映射
concept_map = {}
for dp, dn, fn in os.walk(BASE):
    rel = os.path.relpath(dp, BASE)
    if any(rel == e or rel.startswith(e + os.sep) for e in EXCLUDE_PREFIX):
        continue
    if not any(rel == d or rel.startswith(d + os.sep) for d in CONCEPT_DIRS):
        continue
    for f in fn:
        if not f.endswith(".md"):
            continue
        p = os.path.join(dp, f)
        t = title_of(p)
        if is_concept(t) and t not in concept_map:
            concept_map[t] = p

# 2) 本周新增知识笔记
weekly = []
for dp, dn, fn in os.walk(BASE):
    rel = os.path.relpath(dp, BASE)
    if any(rel == e or rel.startswith(e + os.sep) for e in EXCLUDE_PREFIX):
        continue
    for f in fn:
        if not f.endswith(".md"):
            continue
        p = os.path.join(dp, f)
        try:
            mt = datetime.date.fromtimestamp(os.path.getmtime(p))
        except:
            continue
        if WEEK_AGO <= mt <= TODAY:
            weekly.append(p)

LINK_RE = re.compile(r"\[\[[^\]]*\]\]")

def existing_targets(txt):
    out = set()
    for m in LINK_RE.finditer(txt):
        inner = m.group(0)[2:-2]
        target = inner.split("|")[0].strip()
        out.add(target)
    return out

def linkify_seg(seg, concepts, existing):
    used = set()
    for concept in sorted(concepts, key=len, reverse=True):
        if concept in used or concept in existing:
            continue
        if concept in seg:
            seg = seg.replace(concept, "[[" + concept + "]]", 1)
            used.add(concept)
    return seg

def enhance(text, concepts, existing):
    # 去掉 frontmatter
    m = re.match(r"^(---\s*\n.*?\n---\s*\n)", text, re.S)
    fm = m.group(1) if m else ""
    body = text[len(fm):]
    result = []
    last = 0
    for mm in LINK_RE.finditer(body):
        seg = body[last:mm.start()]
        result.append(linkify_seg(seg, concepts, existing))
        result.append(mm.group(0))
        last = mm.end()
    result.append(linkify_seg(body[last:], concepts, existing))
    return fm + "".join(result)

# 3) 对每周笔记，链接化未链接的概念
plan = []  # (path, [concept,...])
concepts_used = set()
for p in weekly:
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read()
    except:
        continue
    existing = existing_targets(txt)
    new_text = enhance(txt, list(concept_map.keys()), existing)
    if new_text != txt:
        added = []
        new_existing = existing_targets(new_text)
        for c in concept_map:
            if c in new_existing and c not in existing:
                added.append(c)
                concepts_used.add(c)
        plan.append((p, added))

print(f"概念候选数: {len(concept_map)}")
print(f"本周知识笔记数(待处理): {len(weekly)}")
print(f"计划建立链接的笔记数: {len(plan)}")
print(f"涉及概念数: {len(concepts_used)}")
total_links = sum(len(a) for _, a in plan)
print(f"预计新增链接数: {total_links}")
print("=== 明细（前25）===")
for p, added in plan[:25]:
    print(f"  {os.path.relpath(p, BASE)} -> {added}")

if os.environ.get("APPLY") == "1":
    print("\n=== 应用写入 ===")
    done = 0
    for p in weekly:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
        except:
            continue
        existing = existing_targets(txt)
        new_text = enhance(txt, list(concept_map.keys()), existing)
        if new_text != txt:
            with open(p, "w", encoding="utf-8") as f:
                f.write(new_text)
            done += 1
    print(f"已写入 {done} 个文件")
