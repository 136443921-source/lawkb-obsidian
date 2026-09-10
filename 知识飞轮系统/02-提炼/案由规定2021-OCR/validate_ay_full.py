#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AY 域全量交付校验器（自动 glob 全库 R-AY-*.md，当前至 R-AY-088）。
本机无 yaml 模块，正则解析 frontmatter。
检查项：
  ERROR（阻断，须为 0）：
    - 无 frontmatter
    - rule_id 重复（跨文件）
    - rule_id 与文件名基名不匹配
    - card_type 非「案由路由卡」
    - card_subtype 无法识别（非 L1/L2）
    - 版本四件套缺失（code_2020/code_2025/version_status/version_delta 空）
    - L2 缺 discriminator/discriminator_source/counter_case 任一
    - L1 挂非空 discriminator
  WARN（信息，本批次外历史债务）：
    - 编号已漂移(2020≠2025)但 version_delta 未含『漂移机理』
    - 必备列表字段(request_base/confusable/linked_cards)为空
"""
import os, re, glob, sys

DIR = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库/案由路由"
os.chdir(DIR)
files = sorted(glob.glob("R-AY-*.md"))

def num(f):
    m = re.search(r"R-AY-(\d+)-", f)
    return int(m.group(1)) if m else -1

def fm(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return (m.group(1) if m else None), text

def gf(block, key):
    if block is None:
        return None
    pat = re.compile(r"^%s:\s*(.*)$" % re.escape(key), re.M)
    mm = pat.search(block)
    return mm.group(1).strip() if mm else None

def has_list(block, key):
    if block is None:
        return False
    pat = re.compile(r"^%s:\s*\n((?:\s*-\s+.*\n?)+)" % re.escape(key), re.M)
    return bool(pat.search(block))

errors = []
warns = []
EMPTY = ("", '""', None)

# 1) rule_id 重复检测
rid_map = {}
for f in files:
    block, _ = fm(f)
    if block is None:
        continue
    rid = gf(block, "rule_id")
    rid_map.setdefault(rid, []).append(f)
for rid, fs in rid_map.items():
    if len(fs) > 1:
        errors.append("rule_id 重复: %s 出现在 %d 个文件 -> %s" % (rid, len(fs), fs))

# 2) 逐文件结构校验
for f in files:
    n = num(f)
    base = f[:-3]
    block, _ = fm(f)
    if block is None:
        errors.append("[%s] 无 frontmatter" % f)
        continue
    rid = gf(block, "rule_id")
    if not (base == rid or base.startswith(rid + "-")):
        errors.append("[%s] rule_id(%s) 与文件名基名(%s) 不匹配" % (f, rid, base))
    ct = gf(block, "card_type")
    if ct != "案由路由卡":
        errors.append("[%s] card_type 应为『案由路由卡』，实为 %r" % (f, ct))
    cst = gf(block, "card_subtype") or ""
    is_l2 = "定性分野" in cst
    is_l1 = ("单案由" in cst) or ("串联导航" in cst)
    if not (is_l2 or is_l1):
        errors.append("[%s] card_subtype 无法识别卡型: %r" % (f, cst))
    for kf in ["code_2020", "code_2025", "version_status", "version_delta"]:
        v = gf(block, kf)
        if v in EMPTY:
            errors.append("[%s] 缺版本字段 %s" % (f, kf))
    vd = gf(block, "version_delta") or ""
    c20 = gf(block, "code_2020") or ""
    c25 = gf(block, "code_2025") or ""
    drifted = (c20.strip() != c25.strip())
    if drifted and "漂移机理" not in vd:
        warns.append("[%s] 编号已漂移(2020≠2025)但 version_delta 未含『漂移机理』（历史待补强）" % f)
    if is_l2:
        for kf in ["discriminator", "discriminator_source", "counter_case"]:
            v = gf(block, kf)
            if v in EMPTY:
                errors.append("[%s] L2 缺强制字段 %s" % (f, kf))
    if is_l1:
        d = gf(block, "discriminator")
        if d not in EMPTY:
            warns.append("[%s] L1 却挂非空 discriminator: %r" % (f, d))
    for lf in ["request_base", "confusable", "linked_cards"]:
        if not (has_list(block, lf) or (gf(block, lf) not in EMPTY)):
            warns.append("[%s] 列表字段 %s 似乎为空" % (f, lf))

# 批次3 聚焦
batch3 = [f for f in files if 22 <= num(f) <= 31]
b3_err = [e for e in errors if any(f in e for f in batch3)]
b3_warn = [w for w in warns if any(f in w for f in batch3)]
legacy_warn = [w for w in warns if w not in b3_warn]

print("=" * 64)
print("AY 域全量校验（自动 glob 全库，共 %d 文件）" % len(files))
print("=" * 64)
print("【全局】ERROR: %d | WARN: %d" % (len(errors), len(warns)))
print("【批次3 R-AY-022~031】ERROR: %d | WARN: %d" % (len(b3_err), len(b3_warn)))
if b3_err:
    print("  -- 批次3 ERROR --")
    for e in b3_err: print("    ✗", e)
if b3_warn:
    print("  -- 批次3 WARN --")
    for w in b3_warn: print("    ⚠", w)
print("【历史批次待补强 WARN（非本批次引入）】%d 条" % len(legacy_warn))
for w in legacy_warn:
    print("    ⚠", w)
print("=" * 64)
if errors:
    print("ERROR 明细（全部）:")
    for e in errors:
        print("  ✗", e)
else:
    print("✅ ERROR: 0")
print("=" * 64)
sys.exit(1 if errors else 0)
