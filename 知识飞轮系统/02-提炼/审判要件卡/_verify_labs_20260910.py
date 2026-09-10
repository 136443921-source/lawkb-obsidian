# -*- coding: utf-8 -*-
"""第十三批交付校验器：R-PI-318~350（33 张）
校验项：YAML合法性 / 编号唯一 / 必填字段 / elements / ruling双非空 / 八段正文 / 法条来源标注 /
        页码换算(坑26) / 四星号(坑23) / 双书名号(坑20) / 死链
须用 envs/default/bin/python 运行（有 pyyaml）
"""
import sys, os, re, glob, json, io

try:
    import yaml
except ImportError:
    print("FATAL: 缺 pyyaml，请用 /Users/chenyouqiang/.workbuddy/binaries/python/envs/default/bin/python 运行")
    sys.exit(2)

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库/人伤法/"
MP = json.load(io.open("/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/审判要件卡/贵州类案指南第二卷-页码映射表.json", encoding="utf-8"))
IDS = [f"R-PI-{n}" for n in range(318, 351)]

ERRORS, WARNS = [], []
seen = set()

def E(rid, m): ERRORS.append(f"[ERROR] {rid}: {m}")
def W(rid, m): WARNS.append(f"[WARN ] {rid}: {m}")

for rid in IDS:
    fs = glob.glob(BASE + rid + ".md") + glob.glob(BASE + rid + "-*.md")
    if not fs:
        E(rid, "文件不存在"); continue
    if len(fs) > 1:
        E(rid, f"编号重复（{len(fs)} 个文件）")
    p = fs[0]
    if rid in seen: E(rid, "编号重复")
    seen.add(rid)
    raw = io.open(p, encoding="utf-8").read()

    # YAML
    m = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
    if not m:
        E(rid, "无 frontmatter"); continue
    try:
        d = yaml.safe_load(m.group(1))
    except Exception as ex:
        E(rid, f"YAML 解析失败：{str(ex)[:100]}"); continue
    if not isinstance(d, dict):
        E(rid, "frontmatter 非映射"); continue

    for k in ("title", "rule_id", "card_type", "source", "created", "geo_scope"):
        if k not in d or not d[k]: E(rid, f"缺必填字段 {k}")
    if d.get("card_type") != "审判要件卡": E(rid, f"card_type 错误：{d.get('card_type')}")
    if d.get("rule_id") != rid: E(rid, f"rule_id 与文件名不一致：{d.get('rule_id')}")
    if not d.get("elements"): E(rid, "elements 为空")
    ru = d.get("ruling") or {}
    if not ru.get("support"): E(rid, "ruling.support 为空")
    if not ru.get("reject"): E(rid, "ruling.reject 为空")
    if not d.get("burden_of_proof"): W(rid, "burden_of_proof 为空")
    if not d.get("negative_note"): W(rid, "negative_note 为空")

    body = raw[m.end():]
    for sec in ("一、裁判规则", "二、审查要点", "三、构成要件与举证",
                "四、法条依据", "五、抗辩与但书", "六、翻车标本",
                "七、来源与地域效力", "八、关联"):
        if sec not in body: E(rid, f"正文缺段：{sec}")

    # 法条来源标注：按块扫描（坑7）
    has_law = False
    for lm in re.finditer(r"^\*\*《(.+?)》(.*?)\*\*$", body, re.M):
        has_law = True
        seg = body[lm.end(): lm.end() + 1200]
        nxt = seg.find("\n**《")
        if nxt > 0: seg = seg[:nxt]
        if "效力状态" not in seg: E(rid, f"法条块无来源标注：{lm.group(1)[:20]}")
        if "北大法宝核填" not in seg: W(rid, f"法条块未标北大法宝核填：{lm.group(1)[:20]}")
    if not has_law: E(rid, "无法条块")

    # 坑23 四星号
    if re.search(r"^\*\*\*\*", body, re.M): E(rid, "存在四星号 ****")
    # 坑20 双书名号
    if "《《" in raw: E(rid, "存在双书名号 《《")

    # 坑26 页码换算：校验 书页 == MP[str(PDF页-1)]
    for pm in re.finditer(r"PDF页(\d+)(?:-(\d+))?（书页(\d+)(?:-(\d+))?）", raw):
        a = int(pm.group(1)); ya = int(pm.group(3))
        exp = MP.get(str(a - 1))
        if exp is None: W(rid, f"映射表无 PDF页{a}"); continue
        if str(exp) != str(ya):
            E(rid, f"页码偏差：PDF页{a} 标注书页{ya}，映射表为{exp}")
        if pm.group(2):
            b = int(pm.group(2)); yb = int(pm.group(4))
            expb = MP.get(str(b - 1))
            if expb and str(expb) != str(yb):
                E(rid, f"页码偏差：PDF页{b} 标注书页{yb}，映射表为{expb}")

    # 官方核验指引
    if "官方核验指引" not in body: E(rid, "缺官方核验指引子节")
    # frontmatter 禁止 [[ ]]（坑18）
    if "[[" in m.group(1): E(rid, "frontmatter 含 Obsidian 双链")

print(f"\n候选卡片：{len(IDS)} 张")
print(f"ERROR：{len(ERRORS)}")
print(f"WARN ：{len(WARNS)}")
for x in ERRORS[:40]: print("  " + x)
for x in WARNS[:40]: print("  " + x)
sys.exit(1 if ERRORS else 0)
