# -*- coding: utf-8 -*-
"""合规审查卡 校验器（R-CF-140~149，2026-09-13 手册拆卡 P1 批）
venv python（含 pyyaml）。断言：YAML 合法 / 19必填字段 / card_type / 八段齐全 /
官方核验指引小节 / verbatim 子节 / 互链零死链 / frontmatter 无 [[ ]] /
rule_id 与文件名一致 / 内规引证 / statute_text_pending=False。
ERROR=0 且 WARN=0 才准交付（exit 0）。
"""
import os
import re
import sys
import yaml

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CARDS = [
    "R-CF-140-捐赠票据与捐赠人服务合规审查卡",
    "R-CF-141-项目发起方资质与立项合规审查卡",
    "R-CF-142-项目运营全生命周期合规审查卡",
    "R-CF-143-进展反馈与财务披露合规审查卡",
    "R-CF-144-民非会计科目设置合规审查卡",
    "R-CF-145-凭证编制与审核内控合规审查卡",
    "R-CF-146-财务会计报告披露合规审查卡",
    "R-CF-147-商户号捐赠资金核算合规审查卡",
    "R-CF-148-受益人隐私与影像授权合规审查卡",
    "R-CF-149-月捐管理合规审查卡",
]
KNOWN_HUBS = {"连接枢纽-慈法合规"}

REQUIRED_FIELDS = [
    "title", "rule_id", "card_type", "card_family", "subtype", "source", "created",
    "date", "review_date", "updated", "library", "aliases", "geo_scope",
    "yuandian_source_pending", "statute_text_pending", "manual_clauses",
    "elements", "related_links", "source_manual",
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
                files.add(f[:-3])
    return files


VAULT = vault_files()

for card in CARDS:
    path = os.path.join(BASE, "06-沉淀", "裁判规则库", "慈法合规", f"{card}.md")
    if not os.path.exists(path):
        ERRORS.append(f"[{card}] 文件不存在: {path}")
        continue
    with open(path, encoding="utf-8") as f:
        text = f.read()
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
    for field in REQUIRED_FIELDS:
        if field not in fm:
            ERRORS.append(f"[{card}] 缺必填字段: {field}")
    if fm.get("card_type") != "合规审查卡":
        ERRORS.append(f"[{card}] card_type 错误: {fm.get('card_type')}")
    if fm.get("card_family") != "慈善合规（R-CF）":
        ERRORS.append(f"[{card}] card_family 错误: {fm.get('card_family')}")
    # rule_id 正则比对（坑4）
    mm = re.match(r"^(R-CF-\d+)", card)
    expected_rid = mm.group(1) if mm else None
    if fm.get("rule_id") != expected_rid:
        ERRORS.append(f"[{card}] rule_id 与文件名不一致: {fm.get('rule_id')} != {expected_rid}")
    if fm.get("statute_text_pending") is not False:
        ERRORS.append(f"[{card}] statute_text_pending 应为 False（本批已官方核填）")
    if "[[" in fm_raw or "]]" in fm_raw:
        ERRORS.append(f"[{card}] frontmatter 含 [[ ]]")
    for sec in SECTIONS:
        if sec not in body:
            ERRORS.append(f"[{card}] 缺八段小节: {sec}")
    if "### 官方核验指引" not in body:
        ERRORS.append(f"[{card}] 缺「官方核验指引」小节")
    if "verbatim（现行有效版本·官方核填）" not in body and "verbatim（现行有效版本·本地权威源核填）" not in body:
        ERRORS.append(f"[{card}] 缺配套规章 verbatim 子节")
    if "合规管理手册" not in body:
        ERRORS.append(f"[{card}] 未引证厚德手册内规")
    if fm.get("source_manual") != "《贵州基层慈善组织数字化工具与合规操作手册》（贵州省慈善联合会编，2026年6月）":
        WARNINGS.append(f"[{card}] source_manual 未标注手册来源")
    # 死链检查
    for link in fm.get("related_links", []):
        if link in KNOWN_HUBS:
            continue
        if link not in VAULT:
            ERRORS.append(f"[{card}] related_links 死链: {link}")
    for link in re.findall(r"\[\[([^\]]+)\]\]", body):
        base = link.split("|")[0].strip()
        if base in KNOWN_HUBS:
            continue
        if base not in VAULT:
            ERRORS.append(f"[{card}] 正文互链死链: [[{base}]]")
    # 三段内容长度
    for sec, minlen in [("二、审查要件", 200), ("三、红线清单", 80), ("四、错误示例", 200)]:
        seg = body.split(sec)[-1].split("## ")[0] if sec in body else ""
        if len(seg.strip()) < minlen:
            WARNINGS.append(f"[{card}] {sec} 内容偏短({len(seg.strip())})，请复核")

print("=" * 64)
print(f"校验目标：{len(CARDS)} 张合规审查卡（R-CF-140~149）")
print(f"ERROR: {len(ERRORS)} | WARN: {len(WARNINGS)}")
print("=" * 64)
for e in ERRORS:
    print("ERROR:", e)
for w in WARNINGS:
    print("WARN :", w)
print("=" * 64)
if ERRORS or WARNINGS:
    print("RESULT: NOT PASS (ERROR>0 或 WARN>0)")
    sys.exit(1)
print("RESULT: PASS (ERROR=0 / WARN=0)")
sys.exit(0)
