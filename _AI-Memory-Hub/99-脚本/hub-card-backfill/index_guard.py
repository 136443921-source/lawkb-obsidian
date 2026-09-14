#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
index_guard.py — AI 共享记忆中枢 · 索引撞号/幂等门禁（单一真源）

供两个写入器共用：
  - backfill.py   （按需补卡，手动指定/顺延 id；撞号 → ABORT 让人工看清）
  - write_back.py （任务后/自动索引器写回，自动取号；撞号 → 避让，绝不覆盖他人卡）

核心原则（见经验卡 EXP-2026-001 并发撞号事故）：
  - 幂等校验必须比对「指向实体(文件名)」，而非仅 id 字符串；
  - 异文件占同一 id = 撞号，严禁沉默覆盖他人卡片。
"""
import os
import re

# 从「已沉淀」表解析：| [[fname\|id]] | id | title | scope | updated | ✅ active |
# 文件名字符类显式排除反斜杠，避免 Obsidian wikilink 的 `\|` 转义被贪婪吞掉
_IDX_RE = re.compile(r"^\|\s*\[\[([^|\]\\]+)\\?\|([^\]]+)\]\]\s*\|\s*([^|]+?)\s*\|")


def parse_index_ids(idx_path):
    """解析索引文件 → {id: 文件名(无扩展名)}。缺失/异常返回空 dict。"""
    if not os.path.exists(idx_path):
        return {}
    out = {}
    try:
        for ln in open(idx_path, encoding="utf-8").read().splitlines():
            m = _IDX_RE.match(ln)
            if m:
                out[m.group(3).strip()] = m.group(1).strip()
    except Exception:
        return {}
    return out


def build_row(fname, new_id, title, scope, updated):
    """生成「已沉淀」表一行（wikilink 的 | 转义为 \\|）。"""
    return f"| [[{fname}\\|{new_id}]] | {new_id} | {title} | {scope} | {updated} | ✅ active |\n"


def last_table_line(lines):
    """返回表格最后一行索引（用于插入位置）。"""
    last = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("|"):
            last = i
    return last


def insert_row(idx_path, new_row, before_pending=True):
    """把 new_row 插入索引。默认插在「待沉淀」节之前（落入已沉淀表）；
    无待沉淀节则插到表格最后一行之后。返回 True。"""
    lines = open(idx_path, encoding="utf-8").read().splitlines(keepends=True)
    if before_pending:
        pend = next((i for i, ln in enumerate(lines)
                    if ln.strip().startswith("##") and "待沉淀" in ln), None)
        if pend is not None:
            at = pend
            if pend > 0 and lines[pend - 1].strip() == "":
                at = pend - 1
            lines.insert(at, new_row)
        else:
            lt = last_table_line(lines)
            if lt is not None:
                lines.insert(lt + 1, new_row)
            else:
                lines.append("\n" + new_row)
    else:
        lt = last_table_line(lines)
        if lt is not None:
            lines.insert(lt + 1, new_row)
        else:
            lines.append("\n" + new_row)
    open(idx_path, "w", encoding="utf-8").write("".join(lines))
    return True


def index_gate(idx_path, fname, new_id):
    """撞号/幂等判定。返回：
      'insert'      id 空闲，可插入
      'idempotent'  id 已被「同文件」占用，幂等跳过
      'collision'   id 被「不同文件」占用，撞号（严禁覆盖）"""
    existing = parse_index_ids(idx_path)
    if new_id not in existing:
        return "insert"
    if existing[new_id] == fname:
        return "idempotent"
    return "collision"


def next_free_id(idx_path, prefix, start=1):
    """基于索引已占用 id，取该 prefix 下空闲号（prefix-XXX，数字递增）。"""
    existing = parse_index_ids(idx_path)
    nums = []
    for rid in existing:
        if rid.startswith(prefix):
            digits = re.findall(r"\d+", rid[len(prefix):])
            if digits:
                nums.append(int(digits[-1]))
    base = max(nums) if nums else (start - 1)
    return "%s-%03d" % (prefix, base + 1)
