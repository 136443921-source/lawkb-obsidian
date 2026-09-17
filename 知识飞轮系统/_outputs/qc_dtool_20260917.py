# -*- coding: utf-8 -*-
"""R-CF-177/178/179 数字工具操作卡 只读 QC（venv python，含 pyyaml）。
校验：YAML 合法 / 17 字段 / card_type=数字工具操作卡 / 八段齐全 / rule_id 正则比对 /
statute_text_pending=false / 互链零死链 / frontmatter 无 [[]] / 关联段含 [[连接枢纽-慈法合规]]。
退出码 0 = 通过。
"""
import os, re, sys, glob
import yaml

KB = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
CARDDIR = os.path.join(KB, "06-沉淀/裁判规则库/慈法合规")
HUB = os.path.join(KB, "03-连接/连接枢纽-慈法合规.md")

SECTIONS = [
    r"一、操作定位与适用场景",
    r"二、按钮级步骤（操作流程）",
    r"三、关键校验点",
    r"四、常见报错与处置",
    r"五、依据（平台规则＋法定接口）",
    r"六、风险等级",
    r"七、边界",
    r"八、关联",
]
FIELDS = ["title","rule_id","card_family","card_type","subtype","source","type",
          "created","date","created_month","review_date","updated","library",
          "aliases","geo_scope","yuandian_source_pending","statute_text_pending"]

errors, warns = [], []

def check_card(path):
    txt = open(path, encoding="utf-8").read()
    # YAML 合法 + frontmatter 无 [[]]
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        errors.append(f"{path}: 无合法 frontmatter 分隔"); return
    try:
        fm = yaml.safe_load(m.group(1))
    except Exception as e:
        errors.append(f"{path}: YAML 解析失败 {e}"); return
    for f in FIELDS:
        if f not in fm:
            errors.append(f"{path}: 缺字段 {f}")
    if fm.get("card_type") != "数字工具操作卡":
        errors.append(f"{path}: card_type={fm.get('card_type')} != 数字工具操作卡")
    # rule_id 正则比对
    rid = re.match(r"^(R-CF-\d+)", os.path.basename(path)).group(1)
    if fm.get("rule_id") != rid:
        errors.append(f"{path}: rule_id {fm.get('rule_id')} != 文件名 {rid}")
    if fm.get("statute_text_pending") is not False:
        warns.append(f"{path}: statute_text_pending={fm.get('statute_text_pending')}（应 false）")
    if "[" in m.group(1) and "[" in m.group(1).replace("[[]]","") :
        # frontmatter 内不应有 Obsidian 双链
        if re.search(r"\[\[", m.group(1)):
            errors.append(f"{path}: frontmatter 含 [[]] 双链")
    # 八段齐全
    for s in SECTIONS:
        if not re.search(s, txt):
            errors.append(f"{path}: 缺八段之一 -> {s}")
    # 关联段含枢纽
    if "[[连接枢纽-慈法合规]]" not in txt:
        warns.append(f"{path}: 关联段未链 [[连接枢纽-慈法合规]]")
    # 互链死链检查
    for link in re.findall(r"\[\[([^\]]+)\]\]", txt):
        stem = link.split("|")[0].strip()
        if stem == "连接枢纽-慈法合规":
            if not os.path.exists(HUB):
                errors.append(f"{path}: 枢纽文件缺失 {HUB}")
            continue
        cand = glob.glob(os.path.join(CARDDIR, f"{stem}.md"))
        if not cand:
            errors.append(f"{path}: 死链 [[{stem}]]（慈法合规无对应文件）")
    print(f"  ✓ {rid} 八段+字段扫描完成")

for rid in ("R-CF-177","R-CF-178","R-CF-179"):
    fs = glob.glob(os.path.join(CARDDIR, f"{rid}-*.md"))
    if not fs:
        errors.append(f"{rid}: 文件不存在"); continue
    check_card(fs[0])

print("\n===== QC 结果 =====")
print(f"ERROR: {len(errors)}  WARN: {len(warns)}")
for e in errors: print("  ❌", e)
for w in warns: print("  ⚠️", w)
sys.exit(1 if errors else 0)
