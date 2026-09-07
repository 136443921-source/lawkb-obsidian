#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批次2 AY 卡（008-021）交付校验器。覆盖此前 glob 漏检的 008/009。
本机无 yaml 模块，用正则解析 frontmatter。"""

import os, re, glob, sys

DIR = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库/案由路由"
os.chdir(DIR)

# 覆盖 000-029 全段，实际只应有 001-021；用集合过滤
files = sorted(glob.glob("R-AY-00*.md") + glob.glob("R-AY-01*.md") + glob.glob("R-AY-02*.md"))

# 只取 008-021
def num(f):
    m = re.search(r"R-AY-(\d+)-", f)
    return int(m.group(1)) if m else -1

target = [f for f in files if 8 <= num(f) <= 21]
target = sorted(target, key=num)

errors = []
warns = []

def fm(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None, text
    return m.group(1), text

def get_field(block, key):
    # 取 key: <value> 单行值；若存在多行块（后续 - 行）返回标记 'LIST'
    pat = re.compile(r"^%s:\s*(.*)$" % re.escape(key), re.M)
    mm = pat.search(block)
    if not mm:
        return None
    val = mm.group(1).strip()
    return val

def has_list(block, key):
    # 检查 key: 后是否有以 - 开头的条目
    pat = re.compile(r"^%s:\s*\n((?:\s*-\s+.*\n?)+)" % re.escape(key), re.M)
    return bool(pat.search(block))

expected = list(range(8, 22))
present = [num(f) for f in target]
missing = [n for n in expected if n not in present]
if missing:
    errors.append("缺失卡号: %s" % missing)

for f in target:
    n = num(f)
    base = f[:-3]  # 去 .md
    block, _ = fm(f)
    if block is None:
        errors.append("[%s] 无 frontmatter" % f)
        continue
    # rule_id 应为文件名基名的前缀（基名 = rule_id + 描述段）
    rid = get_field(block, "rule_id")
    if not (base == rid or base.startswith(rid + "-")):
        errors.append("[%s] rule_id(%s) 与文件名基名(%s) 不匹配" % (f, rid, base))
    # card_type
    ct = get_field(block, "card_type")
    if ct != "案由路由卡":
        errors.append("[%s] card_type 应为 案由路由卡，实为 %s" % (f, ct))
    # 子类型
    cst = get_field(block, "card_subtype") or ""
    is_l2 = "定性分野" in cst
    is_l1 = "单案由" in cst
    if not (is_l2 or is_l1):
        errors.append("[%s] card_subtype 无法识别卡型: %s" % (f, cst))
    # 版本四件套
    for kf in ["code_2020", "code_2025", "version_status", "version_delta"]:
        v = get_field(block, kf)
        if v is None or v.strip() == "":
            errors.append("[%s] 缺版本字段 %s" % (f, kf))
    # version_delta 含 漂移机理
    vd = get_field(block, "version_delta") or ""
    if "漂移机理" not in vd:
        errors.append("[%s] version_delta 未含『漂移机理』四字" % f)
    # L2 三强制字段
    if is_l2:
        for kf in ["discriminator", "discriminator_source", "counter_case"]:
            v = get_field(block, kf)
            if v is None or v.strip() == "":
                errors.append("[%s] L2 缺强制字段 %s" % (f, kf))
    # L1 不应挂定性分野三字段实质内容（discriminator 应为空串/空）
    if is_l1:
        d = get_field(block, "discriminator")
        if d and d.strip() not in ("", '""'):
            warns.append("[%s] L1 却挂了非空 discriminator（%s），疑为错标" % (f, d))
    # 必备列表字段
    for lf in ["request_base", "confusable", "linked_cards"]:
        if not (has_list(block, lf) or (get_field(block, lf) not in (None, ""))):
            warns.append("[%s] 列表字段 %s 似乎为空" % (f, lf))

print("=" * 60)
print("批次2 AY 卡校验（008-021）")
print("扫描文件数: %d" % len(target))
print("覆盖卡号: %s" % present)
print("=" * 60)
if errors:
    print("ERROR (%d):" % len(errors))
    for e in errors:
        print("  ✗", e)
else:
    print("ERROR: 0")
if warns:
    print("WARN (%d):" % len(warns))
    for w in warns:
        print("  ⚠", w)
else:
    print("WARN: 0")
print("=" * 60)
sys.exit(1 if errors else 0)
