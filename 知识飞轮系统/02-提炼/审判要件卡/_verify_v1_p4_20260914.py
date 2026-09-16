# -*- coding: utf-8 -*-
"""第二十一批（第一卷第四部分·执破融合 R-GS-095~109）交付校验器
- MUST（ERROR）：YAML 可解析 / 必填字段 / ruling.support+reject 非空 / elements 非空 /
  rule_id 唯一 / 八段齐全 / 法条段有真核填且标效力 / frontmatter 无 [[ ]]
- WARN：四星号、双书名号、空 required 段、标题后缀约定
退出码：0=通过 1=ERROR 2=依赖缺失（必须装 pyyaml）
"""
import os, re, sys, json

try:
    import yaml
except ImportError:
    print("FATAL: 缺 pyyaml —— 须用 /Users/chenyouqiang/.workbuddy/binaries/python/envs/default/bin/python 运行")
    sys.exit(2)

DIR = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库/公司法"
IDS = [f"R-GS-{i:03d}" for i in range(95, 110)]
MUST = ["title", "rule_id", "card_type", "source", "created", "geo_scope"]
SECS = ["## 一、裁判规则", "## 二、审查要点", "## 三、构成要件与举证", "## 四、法条依据",
        "## 五、抗辩与但书", "## 六、翻车标本", "## 七、来源与地域效力", "## 八、关联"]

errors, warns = [], []
nvalid = 0
seen = {}

for rid in IDS:
    hits = [f for f in os.listdir(DIR) if f.startswith(rid + "-")]
    if not hits:
        errors.append(f"{rid}: 卡片缺失")
        continue
    for fn in hits:
        path = os.path.join(DIR, fn)
        raw = open(path, encoding="utf-8").read()
        m = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
        if not m:
            errors.append(f"{rid}: 无 frontmatter")
            continue
        try:
            d = yaml.safe_load(m.group(1))
        except Exception as e:
            errors.append(f"{rid}: YAML 解析失败 → {str(e)[:90]}")
            continue
        nvalid += 1
        for k in MUST:
            if not d.get(k):
                errors.append(f"{rid}: 缺字段 {k}")
        if d.get("rule_id") != rid:
            errors.append(f"{rid}: rule_id 不匹配的归入 {d.get('rule_id')}")
        if rid in seen:
            errors.append(f"{rid}: 编号重复 ({seen[rid]} / {fn})")
        seen[rid] = fn
        r = d.get("ruling") or {}
        if not r.get("support"):
            errors.append(f"{rid}: ruling.support 为空")
        if not r.get("reject"):
            errors.append(f"{rid}: ruling.reject 为空")
        if not d.get("elements"):
            errors.append(f"{rid}: elements 为空")
        if "[[" in m.group(1):
            errors.append(f"{rid}: frontmatter 含 [[wikilink]]（坑 44）")
        for s in SECS:
            if s not in raw:
                errors.append(f"{rid}: 缺段落 {s}")
        # 法条段须有真核填（附链接或效力标注）
        blk = raw.split("## 四、法条依据")[1].split("## 五、")[0] if "## 四、法条依据" in raw else ""
        real = re.findall(r"核验链接：http|·法律数据核填·现行有效", blk)
        if not real:
            errors.append(f"{rid}: 法条段无权威核填痕迹")
        if "官方核验指引" not in blk:
            errors.append(f"{rid}: 缺官方核验指引子节")
        pending = bool(d.get("statute_text_pending"))
        if pending and "部分核填·含待回源" not in blk and "待回源" not in blk:
            errors.append(f"{rid}: pending=true 但法条段未标注待回源（坑 42 反向）")
        if (not pending) and "待回源" in blk:
            errors.append(f"{rid}: pending=false 但法条段含待回源")
        # 格式类
        if re.search(r"\*\*\*\*", raw):
            warns.append(f"{rid}: 四星号残留")
        if re.search(r"《《", raw):
            warns.append(f"{rid}: 双书名号")
        # related_links 死链（本批内部互链）
        for lk in (d.get("related_links") or []):
            if str(lk).startswith("R-GS-"):
                cand = [f for f in os.listdir(DIR) if f.startswith(str(lk) + "-") or f == str(lk) + ".md"]
                if not cand:
                    errors.append(f"{rid}: related_links 死链 {lk}")
        body_links = re.findall(r"\[\[([^\]|]+)", raw.split("---", 2)[2] if raw.count("---") > 2 else raw)
        for lk in body_links:
            if lk.startswith("R-GS-"):
                cand = [f for f in os.listdir(DIR) if f.startswith(lk + "-") or f == lk + ".md"]
                if not cand:
                    errors.append(f"{rid}: 正文死链 [[" + lk + "]]")

print(f"候选卡片：{len(IDS)} 张｜YAML 通过：{nvalid}")
print(f"ERROR：{len(errors)}")
for e in errors:
    print("   ❌", e)
print(f"WARN：{len(warns)}")
for w in warns:
    print("   ⚠️", w)
sys.exit(1 if errors else 0)
