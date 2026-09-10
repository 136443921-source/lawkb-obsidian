# -*- coding: utf-8 -*-
"""
文书范式卡族 扩族校验器（拆卡流水线范式·第七批）
校验：R-LN-090 ~ R-LN-093（4 张）
检查项：
  1. YAML 合法（frontmatter 可被 yaml 解析）
  2. 必填字段：title / rule_id / card_type / subtype / source / related_links
  3. rule_id 与文件名前三段一致（R-LN-09X）
  4. card_type == 文书范式卡
  5. 八段齐全（一、二、三、四、五、六、七、八）
  6. 互链零死链：related_links 纯基名 + 正文 [[基名]] 必须存在对应 .md
  7. frontmatter 内不得含 [[ ]] 维基链接
  8. 必备官方核验指引小节
退出码：ERROR>0 则非 0（交付门禁）
"""
import os, re, sys
import yaml

OUT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库/律师实务"
CARDS = [
    "R-LN-090-指定遗产管理人申请书范式卡",
    "R-LN-091-认定财产无主申请书范式卡",
    "R-LN-092-实现担保物权申请书范式卡",
    "R-LN-093-选民资格案件起诉状范式卡",
]
REQUIRED = ["title", "rule_id", "card_type", "subtype", "source", "related_links"]
SECTIONS = ["一、", "二、", "三、", "四、", "五、", "六、", "七、", "八、"]

errors = 0
warns = 0

def err(msg):
    global errors
    errors += 1
    print("  [ERROR] " + msg)

def warn(msg):
    global warns
    warns += 1
    print("  [WARN]  " + msg)

# 预建：目录内所有基名集合（用于死链校验）
all_basenames = set()
for fn in os.listdir(OUT):
    if fn.endswith(".md"):
        all_basenames.add(fn[:-3])

for name in CARDS:
    path = os.path.join(OUT, name + ".md")
    if not os.path.exists(path):
        err(f"文件缺失：{name}.md")
        continue
    print(f"[校验] {name}")
    with open(path, encoding="utf-8") as f:
        text = f.read()

    # 1. 拆分 frontmatter
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        err(f"{name}: 未识别到 frontmatter")
        continue
    fm_raw, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(fm_raw)
    except Exception as e:
        err(f"{name}: YAML 解析失败：{e}")
        continue

    # 2. 必填字段
    for k in REQUIRED:
        if k not in fm or fm.get(k) in (None, "", []):
            err(f"{name}: 缺必填字段 {k}")

    # 3. rule_id 与文件名一致
    rid = "-".join(name.split("-")[:3])
    if fm.get("rule_id") != rid:
        err(f"{name}: rule_id={fm.get('rule_id')} 与文件名期望 {rid} 不一致")
    if "aliases" in fm and rid not in (fm["aliases"] or []):
        warn(f"{name}: aliases 未含 rule_id {rid}")

    # 4. card_type
    if fm.get("card_type") != "文书范式卡":
        err(f"{name}: card_type={fm.get('card_type')} 非 文书范式卡")

    # 5. 八段齐全
    for s in SECTIONS:
        if s not in body:
            err(f"{name}: 缺段落 {s}")

    # 6. frontmatter 内不得含 [[ ]]
    if "[[" in fm_raw or "]]" in fm_raw:
        err(f"{name}: frontmatter 内含 [[ ]] 维基链接，应移入正文")

    # 7. 互链零死链
    rl = fm.get("related_links", []) or []
    for link in rl:
        if not isinstance(link, str):
            err(f"{name}: related_links 条目非字符串：{link}")
            continue
        if link not in all_basenames:
            err(f"{name}: related_links 死链 -> {link}.md（目录无此文件）")
    for mm in re.findall(r"\[\[([^\]]+)\]\]", body):
        if mm not in all_basenames:
            err(f"{name}: 正文死链 [[{mm}]]（目录无此文件）")

    # 8. 必备官方核验指引小节
    if "官方核验指引" not in body:
        warn(f"{name}: 正文缺『官方核验指引』小节")

print("\n========== 校验结果 ==========")
print(f"ERROR = {errors}")
print(f"WARN  = {warns}")
if errors == 0 and warns == 0:
    print("✅ 全部通过：ERROR=0 / WARN=0，可交付")
    sys.exit(0)
elif errors == 0:
    print("⚠️ 无 ERROR 但有 WARN，需人工确认")
    sys.exit(0)
else:
    print("❌ 存在 ERROR，禁止交付")
    sys.exit(1)
