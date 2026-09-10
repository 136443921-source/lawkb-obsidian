# -*- coding: utf-8 -*-
"""赔偿计算卡族（Tier2）强制字段校验器 v1.0
仅校验 2026-09-08 新建的 11 张卡：PI R-PI-267~274 / GZ R-GZ-022~024
"""
import io, os, re, yaml, glob, sys

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库"

PI_IDS = ["R-PI-267", "R-PI-268", "R-PI-269", "R-PI-270", "R-PI-271",
          "R-PI-272", "R-PI-273", "R-PI-274"]
GZ_IDS = ["R-GZ-022", "R-GZ-023", "R-GZ-024"]

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
    rid = bn.split("-")[0] + "-" + bn.split("-")[1] + "-" + bn.split("-")[2]
    if not (bn == rid or bn.startswith(rid + "-")):
        errs.append((bn, "文件名不以 rule_id 为前缀")); continue
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
print("\n✅ 强制字段校验全部通过（11/11）：rule_id唯一 / card_type=赔偿计算卡 / "
      "card_subtype完备 / 八段齐全 / frontmatter无[[ ]]双链")
sys.exit(0)
