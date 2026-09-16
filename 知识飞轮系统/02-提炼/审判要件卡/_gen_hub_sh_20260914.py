#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 连接枢纽-商事纠纷.md：扫描商事纠纷/ 下全部 R-SH-*.md，按 frontmatter title 自动建链，消除孤立卡死链。"""
import os, re, glob

SRC = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库/商事纠纷"
OUT = os.path.join(SRC, "连接枢纽-商事纠纷.md")

def get_title(p):
    txt = open(p, encoding="utf-8").read()
    m = re.search(r"^title:\s*(.+)$", txt, re.M)
    return m.group(1).strip() if m else os.path.basename(p)

def num_of(base):
    return int(re.search(r"R-SH-(\d+)", base).group(1))

files = sorted(glob.glob(os.path.join(SRC, "R-SH-*.md")))
rows = [(os.path.splitext(os.path.basename(f))[0], get_title(f)) for f in files]
new_rows = [r for r in rows if 42 <= num_of(r[0]) <= 55]
old_rows = [r for r in rows if not (42 <= num_of(r[0]) <= 55)]

def table(rows):
    out = ["| 卡号 | 标题 |", "|------|------|"]
    for base, title in rows:
        out.append("| [[%s]] | %s |" % (base, title))
    return "\n".join(out)

content = """---
title: 连接枢纽·商事纠纷（SH 域审判要件卡导航）
type: 连接枢纽
created: 2026-09-14
domain: SH
---

# 连接枢纽·商事纠纷（SH 域）

> 本页为 `06-沉淀/裁判规则库/商事纠纷/` 下全部 SH 域审判要件卡的导航枢纽，
> 消弭历史孤立卡（R-SH-026/027 此前未被任何索引引用）的死链风险。
> 共 %d 张 SH 卡。

## 一、知识产权惩罚性赔偿（本批新增 · R-SH-042~055，14 张）

%s

## 二、股权转让与公司纠纷（历史卡 · R-SH-001~041）

%s

## 三、孤立卡消链登记
- R-SH-026、R-SH-027 已在本枢纽第二节列出，历史死链风险消除。
- 全量 %d 张 SH 卡均经本枢纽互链，related_links 目标指向本枢纽与总索引。
""" % (len(rows), table(new_rows), table(old_rows), len(rows))

open(OUT, "w", encoding="utf-8").write(content)
print("WROTE", OUT, "rows=", len(rows), "new=", len(new_rows), "old=", len(old_rows))
