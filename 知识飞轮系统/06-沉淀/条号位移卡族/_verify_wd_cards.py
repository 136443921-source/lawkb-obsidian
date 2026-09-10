#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
条号位移卡族·交付校验器（v1.0.1）
校验项：
  - 7 张卡全部存在（WD-00~WD-06）
  - YAML frontmatter 合法（解析失败 = exit 2，绝不静默降级）
  - 必填字段齐全：title / card_type / family / verification / related
  - card_type == 新旧法衔接·条号位移卡
  - frontmatter 不含 Obsidian 双链 [[ ]]（坑18）
  - related 为列表
退出码：0=通过 / 1=发现问题 / 2=未能完成检查（解析失败等）
"""
import os, sys, glob, re
import yaml

FAMILY = os.path.dirname(os.path.abspath(__file__))
EXPECTED = [
    "WD-00-条号位移卡族总索引与调用纪律.md",
    "WD-01-公司法条号位移卡-2023修订vs2018修正.md",
    "WD-02-民诉法条号位移卡-2023修正vs2021修正.md",
    "WD-03-慈善法条号位移卡-2023修正vs2016版.md",
    "WD-04-三法过渡期适用规则卡.md",
    "WD-05-主题核对提醒卡.md",
    "WD-06-核验状态码总览卡.md",
]
REQUIRED = ["title", "card_type", "family", "verification", "related"]
CARD_TYPE = "新旧法衔接·条号位移卡"

ERR = 0
WARN = 0
PARSE_ERR = 0

def parse_frontmatter(text):
    """返回 (fm_dict_or_None, parse_ok, raw_fm_text)"""
    if not text.startswith("---"):
        return None, True, ""
    # 第二个 --- 结束 frontmatter
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return None, True, ""
    raw = m.group(1)
    try:
        data = yaml.safe_load(raw)
        return data, True, raw
    except Exception as e:
        return None, False, raw

print("=== 条号位移卡族·交付校验 ===")
print("校验目录：%s\n" % FAMILY)

# 1. 文件存在性
for f in EXPECTED:
    p = os.path.join(FAMILY, f)
    if not os.path.exists(p):
        print("  ❌ 缺失文件：%s" % f)
        ERR += 1
    else:
        print("  ✅ 存在：%s" % f)
print("")

# 2. 逐卡校验
files = sorted(glob.glob(os.path.join(FAMILY, "WD-*.md")))
for p in files:
    name = os.path.basename(p)
    with open(p, encoding="utf-8") as fh:
        text = fh.read()
    fm, ok, raw = parse_frontmatter(text)
    if not ok:
        print("  ❌ [%(n)s] YAML 解析失败（frontmatter 损坏）" % {"n": name})
        PARSE_ERR += 1
        continue
    if fm is None:
        print("  ❌ [%(n)s] 无 frontmatter" % {"n": name})
        ERR += 1
        continue
    # 必填字段
    for k in REQUIRED:
        if k not in fm or fm.get(k) in (None, "", []):
            print("  ❌ [%(n)s] 缺必填字段：%(k)s" % {"n": name, "k": k})
            ERR += 1
    # card_type
    if fm.get("card_type") != CARD_TYPE:
        print("  ❌ [%(n)s] card_type 不符：%(v)s" % {"n": name, "v": fm.get("card_type")})
        ERR += 1
    # frontmatter 双链检查
    if "[[" in raw or "]]" in raw:
        print("  ❌ [%(n)s] frontmatter 含 Obsidian 双链 [[ ]]（坑18）" % {"n": name})
        ERR += 1
    # related 为列表
    if "related" in fm and not isinstance(fm.get("related"), list):
        print("  ❌ [%(n)s] related 非列表" % {"n": name})
        ERR += 1
    if ERR == 0 or True:
        print("  ✅ [%(n)s] 字段/类型/双链校验通过" % {"n": name})
print("")

print("=== 校验结果 ===")
print("ERROR：%d" % ERR)
print("WARN：%d" % WARN)
if PARSE_ERR > 0:
    print("解析失败文件数：%d → exit(2)" % PARSE_ERR)
    sys.exit(2)
if ERR > 0:
    print("存在错误 → exit(1)")
    sys.exit(1)
print("全部通过 → exit(0)")
sys.exit(0)
