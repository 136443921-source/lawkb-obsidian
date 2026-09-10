# -*- coding: utf-8 -*-
"""破产案件批·交付校验器（2026-09-08）
ERROR=0 / WARN=0 才准交付。跑校验固定用 envs/default/bin/python（坑15）。
"""
import os, re, sys, glob, importlib.util

try:
    import yaml
except ImportError:
    print("FATAL: 缺 pyyaml。请用 /Users/chenyouqiang/.workbuddy/binaries/python/envs/default/bin/python 运行")
    sys.exit(2)

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT = f"{BASE}/06-沉淀/裁判规则库/公司法"
D = f"{BASE}/02-提炼/审判要件卡"
START, END = 5, 94

ERRORS, WARNS = [], []
def E(f, m): ERRORS.append(f"{f}: {m}")
def W(f, m): WARNS.append(f"{f}: {m}")

REQ = ["title", "rule_id", "card_type", "source", "created", "geo_scope",
       "elements", "ruling", "burden_of_proof", "negative_note", "review_step"]
SRC_MARK = re.compile(r"(北大法宝核填|华宇元典核填|权威源核填|指南引述·待回源核填)")
PLACEHOLDER = re.compile(r"(TODO|TBD|待填|XXX|xxx_|占位符|lorem)")

files = []
for n in range(START, END + 1):
    g = glob.glob(f"{OUT}/R-GS-{n:03d}-*.md")
    if not g:
        E(f"R-GS-{n:03d}", "卡片文件不存在")
    elif len(g) > 1:
        E(f"R-GS-{n:03d}", f"重复文件 {len(g)} 个")
    else:
        files.append(g[0])

print(f"候选卡片：{len(files)} 张")

ids = {}
for p in files:
    fn = os.path.basename(p)
    raw = open(p, encoding="utf-8").read()
    if not raw.startswith("---"):
        E(fn, "E1 缺 frontmatter"); continue
    m = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
    if not m:
        E(fn, "E1 frontmatter 未闭合"); continue
    fmtext = m.group(1)
    body = raw[m.end():]
    try:
        d = yaml.safe_load(fmtext)
    except Exception as ex:
        E(fn, f"E1 YAML 解析失败: {str(ex)[:80]}"); continue
    if not isinstance(d, dict):
        E(fn, "E1 frontmatter 非映射"); continue

    for k in REQ:
        if k not in d or d[k] in (None, "", []):
            E(fn, f"E2 缺必填字段 {k}")
    rid = str(d.get("rule_id", ""))
    if not re.fullmatch(r"R-GS-\d{3}", rid):
        E(fn, f"E3 rule_id 格式异常: {rid}")
    if rid in ids:
        E(fn, f"E4 rule_id 重复: {rid}")
    ids[rid] = fn
    # 文件名与 rule_id 一致
    if not fn.startswith(rid + "-"):
        E(fn, f"E5 文件名与 rule_id 不一致 ({rid})")
    if d.get("card_type") != "审判要件卡":
        E(fn, f"E6 card_type 异常: {d.get('card_type')}")
    el = d.get("elements")
    if not isinstance(el, list) or len(el) == 0:
        E(fn, "E7 elements 为空")
    else:
        for i, e in enumerate(el):
            if not all(k in e for k in ("id", "name", "desc")):
                E(fn, f"E7 elements[{i}] 缺字段")
    rul = d.get("ruling") or {}
    if not rul.get("support"): E(fn, "E7 ruling.support 为空")
    if not rul.get("reject"):  E(fn, "E7 ruling.reject 为空")

    for sec in ["## 一、裁判规则", "## 二、审查要点", "## 三、构成要件与举证",
                "## 四、法条依据", "## 五、抗辩与但书", "## 六、翻车标本",
                "## 七、来源与地域效力", "## 八、关联"]:
        if sec not in body:
            E(fn, f"E10 正文缺段落 {sec}")

    # E8 法条来源标注：按块扫描（标题行 → 下一条 **《 或下一个 ##）
    if "**《" in body:
        blocks = re.split(r"\n(?=\*\*《|## )", body)
        for blk in blocks:
            if not blk.startswith("**《"):
                continue
            if not SRC_MARK.search(blk):
                E(fn, f"E8 法条块缺来源标注: {blk.splitlines()[0][:40]}")
            if "效力状态" not in blk:
                W(fn, f"E8 法条块缺效力状态: {blk.splitlines()[0][:40]}")
    else:
        W(fn, "W1 卡内无法条块")

    # 官方核验指引标配（SKILL v1.10.0）
    if "官方核验指引" not in body:
        W(fn, "W2 缺官方核验指引子节")

    # E9 占位符 / E9b 回填库缺失标记
    for ln in body.splitlines():
        if PLACEHOLDER.search(ln):
            E(fn, f"E9 占位符残留: {ln.strip()[:50]}"); break
    if "回填库缺失" in body:
        E(fn, "E9b 存在回填库缺失引用")

    # W3 review_date / R2
    if not d.get("review_date"):
        W(fn, "W3 缺 review_date")
    if "铁律 R2" not in body:
        W(fn, "W4 缺铁律 R2 声明")

    # W5 关联链接
    rl = d.get("related_links") or []
    if not rl:
        W(fn, "W5 related_links 为空")

print(f"\nERROR：{len(ERRORS)}")
for x in ERRORS[:40]: print("  ✗", x)
print(f"WARN：{len(WARNS)}")
for x in WARNS[:40]: print("  !", x)
sys.exit(1 if (ERRORS or WARNS) else 0)
