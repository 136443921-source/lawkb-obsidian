# -*- coding: utf-8 -*-
"""第十八批 R-PR-086~094 交付校验器"""
import os, re, sys, json, glob

try:
    import yaml
except ImportError:
    print("FATAL: 缺 pyyaml，请改用 envs/default/bin/python"); sys.exit(2)

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
DIR = f"{ROOT}/06-沉淀/裁判规则库/执行程序"
MP = json.load(open(f"{ROOT}/02-提炼/审判要件卡/贵州类案指南第一卷-页码映射表.json"))

REQ = ["title", "rule_id", "card_type", "source", "created", "geo_scope"]
SECTIONS = ["## 一、裁判规则", "## 二、审查要点", "## 三、构成要件与举证",
            "## 四、法条依据", "## 五、抗辩与但书", "## 六、翻车标本",
            "## 七、来源与地域效力", "## 八、关联"]

files = sorted(glob.glob(f"{DIR}/R-PR-0*.md"))
print(f"候选卡片：{len(files)} 张\n")

E = W = 0
for f in files:
    base = os.path.basename(f)
    raw = open(f).read()
    errs, warns = [], []

    # 1 YAML
    parts = raw.split("---", 2)
    if len(parts) < 3:
        errs.append("frontmatter 不完整")
        fm = {}
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

    # 7 法条依据段须有来源标注 + 官方核验指引
    if "企查查·法律数据核填·现行有效" not in raw:
        errs.append("法条段缺来源标注")
    if "官方核验指引" not in raw:
        warns.append("缺官方核验指引子节")

    # 8 页码校验（坑26）：source 内 PDF页X-Y（书页A-B）
    m = re.search(r"PDF页(\d+)-(\d+)·书页(\d+)-(\d+)", fm.get("source", ""))
    if not m:
        errs.append("source 页码格式不符")
    else:
        a, b, ba, bb = (int(x) for x in m.groups())
        ea, eb = MP.get(str(a - 1)), MP.get(str(b - 1))
        if ea != ba or eb != bb:
            errs.append(f"页码不符映射表: 期望书页{ea}-{eb} 实际{ba}-{bb}")

    # 9 拉丁乱码
    bad = [x for x in re.findall(r"[A-Za-z]{6,}", raw)
           if x.lower() not in ("https", "qcc", "legal", "com", "regulation",
                                "http", "www", "gov", "cn", "npc", "court",
                                "guizhoucourt", "flk", "pdf", "gl",
                                # frontmatter 字段名（合法），勿判为乱码
                                "source", "created", "review", "updated", "center",
                                "date", "title", "type", "library", "aliases",
                                "support", "reject", "sort", "false", "true",
                                "statute_text_pending", "yuandian")]
    if bad:
        warns.append(f"可疑拉丁串: {bad[:3]}")

    # 10 statute_text_pending
    if str(fm.get("statute_text_pending")).lower() == "true":
        warns.append("statute_text_pending=true")

    E += len(errs); W += len(warns)
    tag = "❌" if errs else ("⚠️" if warns else "✅")
    print(f"{tag} {base[:56]}")
    for x in errs: print(f"     ERROR: {x}")
    for x in warns: print(f"     WARN : {x}")

print(f"\n===== ERROR：{E} / WARN：{W} =====")
sys.exit(1 if E else 0)
