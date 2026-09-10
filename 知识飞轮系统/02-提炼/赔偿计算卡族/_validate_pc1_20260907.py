# -*- coding: utf-8 -*-
"""赔偿计算卡族（Tier1 第一批）强制字段校验器 v1.0
仅校验 2026-09-07 新建的 18 张卡：PI R-PI-259~266 / GZ R-GZ-012~021
"""
import io, os, re, yaml, glob, sys

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库"

PI_IDS = ["R-PI-259", "R-PI-260", "R-PI-261", "R-PI-262", "R-PI-263",
          "R-PI-264", "R-PI-265", "R-PI-266"]
GZ_IDS = ["R-GZ-012", "R-GZ-013", "R-GZ-014", "R-GZ-015", "R-GZ-016",
          "R-GZ-017", "R-GZ-018", "R-GZ-019", "R-GZ-020", "R-GZ-021"]

# 定位文件：rule_id + "*.md"（文件名含标题后缀）
files = []
missing = []
for rid in PI_IDS:
    cand = glob.glob(os.path.join(BASE, "人伤法", rid + "*.md"))
    if len(cand) == 1:
        files.append(cand[0])
    else:
        missing.append((rid, "人伤法", cand))
for rid in GZ_IDS:
    cand = glob.glob(os.path.join(BASE, "公众号", rid + "*.md"))
    if len(cand) == 1:
        files.append(cand[0])
    else:
        missing.append((rid, "公众号", cand))

print("应校验新卡：%d 张 (PI %d + GZ %d)" % (len(PI_IDS) + len(GZ_IDS), len(PI_IDS), len(GZ_IDS)))
print("实际定位到：%d 张" % len(files))
if missing:
    print("⚠️ 未定位到文件：")
    for rid, d, c in missing:
        print("   - %s @ %s -> %s" % (rid, d, c))
    sys.exit(1)

errs = []
seen = {}
for f in files:
    txt = io.open(f, encoding="utf-8").read()
    bn = os.path.basename(f)[:-3]
    rid = bn.split("-")[0] + "-" + bn.split("-")[1] + "-" + bn.split("-")[2]  # 还原短号
    # rule_id 应为文件名前缀
    if not (bn == rid or bn.startswith(rid + "-")):
        errs.append((bn, "文件名不以 rule_id 为前缀"))
        continue
    if not txt.startswith("---"):
        errs.append((bn, "无 frontmatter")); continue
    try:
        fm = yaml.safe_load(txt.split("---")[1]) or {}
    except Exception as e:
        errs.append((bn, "YAML解析失败:%s" % e)); continue
    frid = fm.get("rule_id")
    if frid != rid:
        errs.append((bn, "frontmatter.rule_id[%s]!=文件名短号[%s]" % (frid, rid)))
    if frid in seen:
        errs.append((bn, "rule_id重复:%s (亦见于 %s)" % (frid, seen[frid])))
    seen[frid] = bn
    if fm.get("card_type") != "赔偿计算卡":
        errs.append((bn, "card_type=%s" % fm.get("card_type")))
    if fm.get("card_subtype") not in ("交通事故赔偿计算", "工伤赔偿计算"):
        errs.append((bn, "card_subtype缺失/异常:%s" % fm.get("card_subtype")))
    if not fm.get("title"): errs.append((bn, "title缺失"))
    if not fm.get("source"): errs.append((bn, "source缺失"))
    if not isinstance(fm.get("related_links", []), list): errs.append((bn, "related_links非列表"))
    fmtext = txt.split("---")[1]
    if "[[" in fmtext or "]]" in fmtext:
        errs.append((bn, "frontmatter含[[ ]]双链(坑18)"))
    secs = re.findall(r"^##\s+[一二三四五六七八]、", txt, re.M)
    if len(secs) < 8:
        errs.append((bn, "八段不全:仅%d段" % len(secs)))

uniq = "OK" if len(seen) == len(files) else "FAIL"
print("rule_id 唯一性: %s (count=%d)" % (uniq, len(seen)))

if errs:
    print("\n❌ 校验问题 %d 项：" % len(errs))
    for b, e in errs:
        print("  - %s: %s" % (b, e))
    sys.exit(1)
print("\n✅ 强制字段校验全部通过（18/18）：rule_id唯一 / card_type=赔偿计算卡 / "
      "card_subtype完备 / 八段齐全 / frontmatter无[[ ]]双链")
sys.exit(0)
