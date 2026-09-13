# -*- coding: utf-8 -*-
"""
第二十批交付校验器：R-PI-373~377（人伤法/）＋ R-PR-171~177（刑事程序/）
覆盖：YAML / 必填 / elements / ruling / 八段 / 四星号 / 双书名号 /
      法条来源标注 / 页码映射（坑26 0-based） / 拉丁乱码 / pending 标记
"""
import os, re, sys, json, glob

try:
    import yaml
except ImportError:
    print("FATAL: 缺 pyyaml，请改用 envs/default/bin/python"); sys.exit(2)

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
MP = json.load(open(f"{ROOT}/02-提炼/审判要件卡/贵州类案指南第一卷-页码映射表.json"))

DIRS = [f"{ROOT}/06-沉淀/裁判规则库/人伤法",
        f"{ROOT}/06-沉淀/裁判规则库/刑事程序"]

REQ = ["title", "rule_id", "card_type", "source", "created", "geo_scope"]
SECTIONS = ["## 一、裁判规则", "## 二、审查要点", "## 三、构成要件与举证",
            "## 四、法条依据", "## 五、抗辩与但书", "## 六、翻车标本",
            "## 七、来源与地域效力", "## 八、关联"]

BATCH = {"R-PI-373", "R-PI-374", "R-PI-375", "R-PI-376", "R-PI-377",
         "R-PR-171", "R-PR-172", "R-PR-173", "R-PR-174", "R-PR-175",
         "R-PR-176", "R-PR-177"}

files = []
for d in DIRS:
    files += glob.glob(f"{d}/R-PI-37*.md") + glob.glob(f"{d}/R-PR-17*.md")
def _rid(path):
    m = re.match(r"(R-(?:PI|PR)-\d{3})", os.path.basename(path))
    return m.group(1) if m else ""


files = sorted(f for f in files if _rid(f) in BATCH)
print(f"候选卡片：{len(files)} 张\n")

E = W = 0
for f in files:
    base = os.path.basename(f)
    raw = open(f).read()
    errs, warns = [], []

    # 1 YAML
    parts = raw.split("---", 2)
    if len(parts) < 3:
        errs.append("frontmatter 不完整"); fm = {}
    else:
        try:
            fm = yaml.safe_load(parts[1])
            if not isinstance(fm, dict):
                errs.append("frontmatter 非 dict"); fm = {}
        except Exception as ex:
            errs.append(f"YAML 解析失败: {str(ex)[:80]}"); fm = {}

    # 2 必填
    for k in REQ:
        if not fm.get(k):
            errs.append(f"缺必填字段 {k}")
    if fm.get("card_type") != "审判要件卡":
        errs.append("card_type 非审判要件卡")
    rid = fm.get("rule_id", "")
    if not base.startswith(rid):
        errs.append(f"文件名与 rule_id 不符（{rid} vs {base[:9]}）")

    # 3 elements / ruling
    if not fm.get("elements"):
        errs.append("elements 为空")
    r = fm.get("ruling") or {}
    if not (isinstance(r, dict) and r.get("support") and r.get("reject")):
        errs.append("ruling.support/reject 未双双非空")
    if not fm.get("burden_of_proof"):
        errs.append("burden_of_proof 为空")
    if not fm.get("negative_note"):
        warns.append("negative_note 为空")

    # 4 八段
    for s in SECTIONS:
        if s not in raw:
            errs.append(f"缺段落 {s}")

    # 5 四星号（坑23）
    if re.search(r"(?m)^\*\*\*\*", raw):
        errs.append("存在四星号 ****")

    # 6 双书名号（坑20）
    for m in re.finditer(r"《《(.+?)》([^》]*)》", raw):
        errs.append(f"双书名号嵌套: {m.group(0)[:30]}")

    # 7 法条依据段须有权威来源标注 + 官方核验指引
    if "企查查·法律数据核填·现行有效" not in raw:
        errs.append("法条段缺权威来源标注")
    if "官方核验指引" not in raw:
        warns.append("缺官方核验指引子节")

    # 8 页码校验（坑26 0-based）
    m = re.search(r"PDF页(\d+)-(\d+)·书页(\d+)-(\d+)", fm.get("source", ""))
    if not m:
        errs.append("source 页码格式不符")
    else:
        a, b, ba, bb = (int(x) for x in m.groups())
        ea, eb = MP.get(str(a - 1)), MP.get(str(b - 1))
        if ea != ba or eb != bb:
            errs.append(f"页码不符映射表: 期望书页{ea}-{eb} 实际{ba}-{bb}")

    # 9 拉丁乱码（白名单含 frontmatter 字段名与合法域名/标识）
    WHITE = {"https", "qcc", "legal", "com", "regulation", "http", "www", "gov",
             "cn", "npc", "court", "guizhoucourt", "flk", "pdf", "gl",
             "source", "created", "review", "updated", "center", "date", "title",
             "type", "library", "pending", "statute", "text", "yuandian",
             "false", "true", "aliases", "widgets", "sort", "elements", "ruling",
             "support", "reject", "burden", "negative", "sample", "note", "step",
             "links", "related", "desc", "frontmatter", "href", "target", "blank",
             "markdown", "utf", "json", "html",
             # 法条通道与状态术语（合法，非乱码）
             "pkulaw", "pointbalance", "yuandian", "qcc", "mcp"}
    bad = [x for x in re.findall(r"[A-Za-z]{6,}", raw) if x.lower() not in WHITE]
    if bad:
        warns.append(f"可疑拉丁串: {bad[:3]}")

    # 10 pending 标记（如实提示，非缺陷 → 单独列出，不计 WARN）
    notes = []
    if str(fm.get("statute_text_pending")).lower() == "true":
        notes.append("📋 statute_text_pending=true（卡内已如实标注待回源条号，非缺陷）")

    E += len(errs); W += len(warns)
    tag = "❌" if errs else ("⚠️" if warns else "✅")
    print(f"{tag} {base[:60]}")
    for x in errs: print(f"     ERROR: {x}")
    for x in warns: print(f"     WARN : {x}")
    for x in notes: print(f"     {x}")

print(f"\n===== ERROR：{E} / WARN：{W} =====")
sys.exit(1 if E else 0)
