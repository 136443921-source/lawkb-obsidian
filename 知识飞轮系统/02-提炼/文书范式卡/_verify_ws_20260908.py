# -*- coding: utf-8 -*-
"""
文书范式卡族 扩族交付校验器（第二批 067~070）
检查：YAML 合法 / 必填字段 / card_type / 八段齐全 / 互链零死链 / rule_id 与文件名一致
用 envs/default python 跑：ERROR=0/WARN=0 才准交付
"""
import os, re, sys
try:
    import yaml
except ImportError:
    print("FATAL: 缺 pyyaml，请用 /Users/chenyouqiang/.workbuddy/binaries/python/envs/default/bin/python")
    sys.exit(2)

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库/律师实务"
CARDS = ["R-LN-067-上诉状范式卡", "R-LN-068-反诉状范式卡",
         "R-LN-069-质证意见范式卡", "R-LN-070-调查取证申请书范式卡"]

REQUIRED = ["title", "rule_id", "card_type", "source", "created", "geo_scope"]
SECTIONS = ["一、文书定位", "二、要素式结构", "三、红线清单", "四、错误示例",
            "五、法条/格式依据", "六、与相邻文书", "七、来源与地域效力", "八、关联"]

errors = 0
warns = 0

def exist_link(target):
    base = target.strip()
    if base.startswith("[[") and base.endswith("]]"):
        base = base[2:-2].split("|")[0].strip()
    if not base.endswith(".md"):
        base = base + ".md"
    return os.path.exists(os.path.join(BASE, base))

for c in CARDS:
    path = os.path.join(BASE, c + ".md")
    if not os.path.exists(path):
        print(f"ERROR: 文件缺失 {c}.md"); errors += 1; continue
    txt = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        print(f"ERROR: {c} frontmatter 缺失"); errors += 1; continue
    try:
        fm = yaml.safe_load(m.group(1))
    except Exception as e:
        print(f"ERROR: {c} YAML 解析失败: {e}"); errors += 1; continue
    rid = fm.get("rule_id", "")
    if rid not in c:
        print(f"ERROR: {c} rule_id={rid} 与文件名不符"); errors += 1
    for k in REQUIRED:
        if not fm.get(k):
            print(f"ERROR: {c} 缺必填字段 {k}"); errors += 1
    if fm.get("card_type") != "文书范式卡":
        print(f"ERROR: {c} card_type={fm.get('card_type')} 非文书范式卡"); errors += 1
    for s in SECTIONS:
        if s not in txt:
            print(f"ERROR: {c} 缺八段之『{s}』"); errors += 1
    if "红线" not in txt:
        print(f"WARN: {c} 未出现『红线』"); warns += 1
    if "错误示例" not in txt and "翻车标本" not in txt:
        print(f"WARN: {c} 未出现『错误示例/翻车标本』"); warns += 1
    for link in (fm.get("related_links") or []):
        if isinstance(link, dict):
            link = link.get("name", "")
        if not exist_link(link):
            print(f"ERROR: {c} related_links 死链: {link}"); errors += 1
    for mm in re.finditer(r"\[\[([^\]]+)\]\]", txt):
        if not exist_link(mm.group(1)):
            print(f"ERROR: {c} 正文死链: {mm.group(1)}"); errors += 1
    if "[[" in m.group(1) or "]]" in m.group(1):
        print(f"ERROR: {c} frontmatter 含 [[ ]] 双链（坑18）"); errors += 1

print(f"\n候选卡片：{len(CARDS)} 张")
print(f"ERROR：{errors}")
print(f"WARN：{warns}")
sys.exit(1 if errors else 0)
