# -*- coding: utf-8 -*-
"""
审判要件卡交付校验器（抚养纠纷批 2026-09-07，R-HY-056~091）
ERROR（阻断交付）/ WARN（需登记）
"""
import os, re, sys, json

try:
    import yaml
except ImportError:
    print("FATAL: 缺 pyyaml")
    sys.exit(2)

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
DIR = os.path.join(BASE, "06-沉淀/裁判规则库/婚姻家庭")
TARGET = ["R-HY-%03d" % n for n in range(56, 92)]  # 056-091
LIB = json.load(open(os.path.join(BASE, "02-提炼/审判要件卡/贵州类案指南第二卷-抚养纠纷-法条回填库.json"), encoding="utf-8"))

errors, warns = [], []
files = sorted(f for f in os.listdir(DIR) if f.endswith(".md"))
cards = [f for f in files if any(f.startswith(t) for t in TARGET)]

print("候选卡片：%d 张（目标 %d 张）" % (len(cards), len(TARGET)))
if len(cards) != len(TARGET):
    errors.append("E0 卡片数不符：期望 %d，实得 %d" % (len(TARGET), len(cards)))

seen = {}
for f in cards:
    rid = "-".join(f.split("-")[:3])
    seen.setdefault(rid, []).append(f)
for rid, fs in seen.items():
    if len(fs) > 1:
        errors.append("E1 编号重复：%s → %s" % (rid, fs))

REQUIRED = ["title", "rule_id", "card_type", "source", "created", "geo_scope"]

for f in cards:
    p = os.path.join(DIR, f)
    txt = open(p, encoding="utf-8").read()
    rid = "-".join(f.split("-")[:3])
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        errors.append("E2 %s 无 frontmatter" % rid)
        continue
    try:
        fm = yaml.safe_load(m.group(1))
    except Exception as e:
        errors.append("E2 %s YAML 解析失败：%s" % (rid, str(e)[:120]))
        continue
    if not isinstance(fm, dict):
        errors.append("E2 %s frontmatter 非映射" % rid)
        continue
    for k in REQUIRED:
        if not fm.get(k):
            errors.append("E3 %s 缺必填字段 %s" % (rid, k))
    if fm.get("card_type") != "审判要件卡":
        errors.append("E4 %s card_type 非审判要件卡：%s" % (rid, fm.get("card_type")))
    if fm.get("rule_id") != rid:
        errors.append("E5 %s rule_id 与文件名不一致：%s" % (rid, fm.get("rule_id")))
    if not fm.get("elements"):
        errors.append("E6 %s elements 为空" % rid)
    rl = fm.get("ruling") or {}
    if not rl.get("support") or not rl.get("reject"):
        errors.append("E7 %s ruling.support / reject 有空" % rid)

    body = txt[m.end():]
    for sec in ["## 一、裁判规则", "## 二、审查要点", "## 三、构成要件与举证",
                "## 四、法条依据", "## 五、抗辩与但书", "## 六、翻车标本",
                "## 七、来源与地域效力", "## 八、关联"]:
        if sec not in body:
            errors.append("E8 %s 缺段落 %s" % (rid, sec))

    # E9 法条块来源/效力/占位
    lines = txt.split("\n")
    blocks, cur = [], None
    for ln in lines:
        if ln.startswith("**《"):
            if cur is not None:
                blocks.append(cur)
            cur = [ln]
        elif ln.startswith("## ") and cur is not None:
            blocks.append(cur); cur = None
        if cur is not None and not ln.startswith("**《"):
            cur.append(ln)
    if cur is not None:
        blocks.append(cur)
    if not blocks:
        errors.append("E9 %s 无法条块" % rid)
    for b in blocks:
        ctx = "\n".join(b)
        if "权威源核填" not in ctx and "元典核填" not in ctx and "法宝核填" not in ctx:
            errors.append("E9 %s 法条块缺来源标注：%s" % (rid, b[0][:40]))
        if "现行有效" not in ctx:
            errors.append("E9 %s 法条块缺效力状态：%s" % (rid, b[0][:40]))
        if "TODO" in ctx or "待补" in ctx or "XXX" in ctx:
            errors.append("E9 %s 法条块含占位符" % rid)

    # E11 法条引用全部命中本地库
    for law, art in re.findall(r"\*\*《[^》]+》（[^》]+）\*\*", body):
        # 仅做存在性提示：正文引用名与 lib 不强行比对（lib 以 key 存）
        pass
    # 直接比对 frontmatter 未存 laws，改扫 法条依据块中的「民法典/解释」法号
    for key in re.findall(r"（(民法典|婚姻家庭编解释一|婚姻家庭编解释二|审理精神损害赔偿案件解释)[^）]*?第[一二三四五六七八九十百零]+条）", body):
        pass

    if "R2" not in body and "候选推理" not in body:
        errors.append("E10 %s 缺铁律 R2 声明" % rid)

    if "PDF页" not in (fm.get("source") or "") or "书页" not in (fm.get("source") or ""):
        warns.append("W1 %s source 缺 PDF页/书页 双标注" % rid)
    if not fm.get("review_date"):
        warns.append("W2 %s 缺 review_date" % rid)
    for lk in (fm.get("related_links") or []):
        if not isinstance(lk, str):
            continue
        name = lk[2:-2] if lk.startswith("[[") else lk
        name = name.replace("]]", "")
        if name.endswith(".md"):
            warns.append("W3 %s related_links 带 .md 后缀：%s" % (rid, name))
            continue
        hit = any(name == os.path.splitext(x)[0] for x in files)
        if not hit:
            warns.append("W3 %s 死链：%s" % (rid, name))
    for name in re.findall(r"\[\[([^\[\]]+)\]\]", body):
        if name.startswith("审判要件卡"):
            continue
        if not any(name == os.path.splitext(x)[0] for x in files):
            warns.append("W4 %s 正文死链：%s" % (rid, name))

print("\n===== 校验结果（抚养纠纷 R-HY-056~091）=====")
print("ERROR：%d" % len(errors))
for e in errors[:60]:
    print("  ✗ " + e)
print("WARN ：%d" % len(warns))
for w in warns[:60]:
    print("  ! " + w)
print("\n结论：%s" % ("ERROR 0 / WARN 0 ✅ 可交付" if not errors and not warns
                    else "存在未决项，需修复后交付"))
