# -*- coding: utf-8 -*-
"""
合规审查卡 校验器（R-CF-118~121，2026-09-08）
venv python（含 pyyaml）。断言：YAML 合法 / 必填字段 / card_type / 八段齐全 /
官方核验指引小节 / 互链零死链 / frontmatter 无 [[ ]] / rule_id 与文件名一致。
ERROR=0 且 WARN=0 才准交付（exit 0）。
"""
import os
import re
import sys
import yaml

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CARDS = [
    "R-CF-118-关联交易合规审查卡",
    "R-CF-119-公开募捐资格与备案合规审查卡",
    "R-CF-120-慈善信息公开义务合规审查卡",
    "R-CF-121-慈善信托合规审查卡",
]
# 已知枢纽/非文件链接（允许在 related_links / 正文 [[ ]] 中）
KNOWN_HUBS = {"连接枢纽-慈法合规"}

REQUIRED_FIELDS = [
    "title", "rule_id", "card_type", "subtype", "source", "created",
    "date", "review_date", "updated", "library", "aliases", "geo_scope",
    "yuandian_source_pending", "statute_text_pending", "manual_clauses",
    "elements", "related_links",
]
SECTIONS = [
    "一、审查定位与适用场景", "二、审查要件（要素式结构）", "三、红线清单",
    "四、错误示例（翻车标本）", "五、援引法条与内规", "六、风险等级与偏离处置",
    "七、与相邻制度边界", "八、关联（知识飞轮连接层）",
]

ERRORS = []
WARNINGS = []

def vault_files():
    files = set()
    for root, _, fs in os.walk(BASE):
        for f in fs:
            if f.endswith(".md"):
                files.add(f[:-3])  # basename without .md
    return files

VAULT = vault_files()

for card in CARDS:
    path = os.path.join(BASE, "06-沉淀", "裁判规则库", "慈法合规", f"{card}.md")
    if not os.path.exists(path):
        ERRORS.append(f"[{card}] 文件不存在: {path}")
        continue
    with open(path, encoding="utf-8") as f:
        text = f.read()
    # 拆分 frontmatter / body
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        ERRORS.append(f"[{card}] frontmatter 分隔符缺失")
        continue
    fm_raw, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(fm_raw)
    except Exception as e:
        ERRORS.append(f"[{card}] YAML 解析失败: {e}")
        continue
    # 必填字段
    for field in REQUIRED_FIELDS:
        if field not in fm:
            ERRORS.append(f"[{card}] 缺必填字段: {field}")
    # card_type
    if fm.get("card_type") != "合规审查卡":
        ERRORS.append(f"[{card}] card_type 错误: {fm.get('card_type')}")
    # rule_id 与文件名一致（文件名形如 R-CF-118-xxxx.md，rule_id=R-CF-118）
    expected_rid = re.match(r"^(R-CF-\d+)", card)
    expected_rid = expected_rid.group(1) if expected_rid else None
    if fm.get("rule_id") != expected_rid:
        ERRORS.append(f"[{card}] rule_id 与文件名不一致: {fm.get('rule_id')} != {expected_rid}")
    # frontmatter 禁 [[ ]]
    if "[[" in fm_raw or "]]" in fm_raw:
        ERRORS.append(f"[{card}] frontmatter 含 [[ ]]（坑18）")
    # 八段齐全
    for sec in SECTIONS:
        if sec not in body:
            ERRORS.append(f"[{card}] 缺八段小节: {sec}")
    # 官方核验指引
    if "### 官方核验指引" not in body:
        ERRORS.append(f"[{card}] 缺「官方核验指引」小节")
    # 内规引证
    if "合规管理手册" not in body:
        ERRORS.append(f"[{card}] 未引证厚德手册内规")
    # related_links 须真实文件或已知枢纽
    for link in fm.get("related_links", []):
        if link in KNOWN_HUBS:
            continue
        if link not in VAULT:
            ERRORS.append(f"[{card}] related_links 死链: {link}")
    # 正文 [[ ]] 互链零死链
    for link in re.findall(r"\[\[([^\]]+)\]\]", body):
        base = link.split("|")[0].strip()
        if base in KNOWN_HUBS:
            continue
        if base not in VAULT:
            ERRORS.append(f"[{card}] 正文互链死链: [[{base}]]")
    # 要素式/红线/错误示例 三段内容非空（简单长度检查）
    for sec, minlen in [("二、审查要件", 30), ("三、红线清单", 20), ("四、错误示例", 20)]:
        seg = body.split(sec)[-1].split("##")[0] if sec in body else ""
        if len(seg.strip()) < minlen:
            WARNINGS.append(f"[{card}] {sec} 内容偏短，请复核")

print("=" * 60)
print(f"校验目标：{len(CARDS)} 张合规审查卡")
print(f"ERROR: {len(ERRORS)} | WARN: {len(WARNINGS)}")
print("=" * 60)
for e in ERRORS:
    print("ERROR:", e)
for w in WARNINGS:
    print("WARN :", w)
print("=" * 60)
if ERRORS or WARNINGS:
    print("RESULT: NOT PASS (ERROR>0 或 WARN>0)")
    sys.exit(1)
print("RESULT: PASS (ERROR=0 / WARN=0)")
sys.exit(0)
