# -*- coding: utf-8 -*-
"""
文书范式卡族 扩族校验器（第五批 R-LN-077~081）
校验：YAML合法 / 必填字段 / rule_id一致 / card_type=文书范式卡 / 八段齐全 / 互链零死链 / frontmatter无[[ ]]
退出码：ERROR>0 则非0；WARN 仅提示。
用 envs/default python 跑：ERROR=0/WARN=0 才准交付
"""
import os, re, sys
try:
    import yaml
except ImportError:
    print("FATAL: 缺 pyyaml，请用 /Users/chenyouqiang/.workbuddy/binaries/python/envs/default/bin/python")
    sys.exit(2)

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库/律师实务"
CARDS = [
    "R-LN-077-支付令申请书范式卡",
    "R-LN-078-执行异议之诉起诉状范式卡",
    "R-LN-079-确认之诉起诉状范式卡",
    "R-LN-080-管辖异议申请书范式卡",
    "R-LN-081-撤诉申请书范式卡",
]
SECTIONS = ["一、文书定位与适用场景", "二、要素式结构", "三、红线清单",
            "四、错误示例", "五、法条/格式依据", "六、与相邻文书的边界",
            "七、来源与地域效力", "八、关联"]
REQUIRED = ["title", "rule_id", "card_type", "subtype", "source", "related_links"]

ERROR, WARN = 0, 0
def err(m):
    global ERROR; ERROR += 1; print(f"  [ERROR] {m}")
def warn(m):
    global WARN; WARN += 1; print(f"  [WARN] {m}")

for name in CARDS:
    path = os.path.join(BASE, name + ".md")
    print(f"== 校验 {name} ==")
    if not os.path.exists(path):
        err(f"文件不存在: {path}"); continue
    txt = open(path, encoding="utf-8").read()
    # 拆分 frontmatter / body
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S)
    if not m:
        err("frontmatter 分隔符缺失"); continue
    fm_raw, body = m.group(1), m.group(2)
    try:
        meta = yaml.safe_load(fm_raw)
    except Exception as e:
        err(f"YAML 解析失败: {e}"); continue
    # 必填字段
    for k in REQUIRED:
        if k not in meta:
            err(f"缺必填字段: {k}")
    # rule_id 一致（取文件名前三段 R-LN-07X）
    rid = "-".join(name.split("-")[:3])
    if meta.get("rule_id") != rid:
        err(f"rule_id 不一致: frontmatter={meta.get('rule_id')} 文件名={rid}")
    # card_type
    if meta.get("card_type") != "文书范式卡":
        err(f"card_type 非文书范式卡: {meta.get('card_type')}")
    # frontmatter 无 [[ ]]
    if "[[" in fm_raw:
        err("frontmatter 内出现 [[ ]] 维基链接（应仅放 related_links 基名）")
    # 八段齐全
    for s in SECTIONS:
        if s not in body:
            err(f"缺段落: {s}")
    # 互链：related_links 基名 -> 文件存在 + 正文 [[基名]]
    for link in (meta.get("related_links") or []):
        base = link.split("#")[0]
        target = os.path.join(BASE, base + ".md")
        if not os.path.exists(target):
            err(f"死链（目标文件不存在）: {link}")
        if f"[[{base}]]" not in body:
            err(f"正文未出现互链 [[{base}]]")
    # 正文 [[ ]] 反向核验
    for wb in re.findall(r"\[\[([^\]]+)\]\]", body):
        b = wb.split("#")[0]
        t = os.path.join(BASE, b + ".md")
        if not os.path.exists(t):
            err(f"正文互链死链（目标不存在）: [[{wb}]]")
    # 要素式/红线/错误示例 三段强制
    if "必需要素" not in body:
        err("缺『必需要素』（要素式结构段）")
    if not re.search(r"^\d+\.", body, re.M):
        err("红线清单无编号条目")
    if "翻车标本" not in body:
        warn("缺『翻车标本』标识（非致命，建议保留）")
    print(f"  rule_id={meta.get('rule_id')} card_type={meta.get('card_type')} 段落={sum(1 for s in SECTIONS if s in body)}/8")

print(f"\nRESULT: ERROR={ERROR} WARN={WARN}")
sys.exit(1 if ERROR > 0 else 0)
