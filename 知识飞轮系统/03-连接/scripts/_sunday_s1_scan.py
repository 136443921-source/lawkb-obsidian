# -*- coding: utf-8 -*-
"""阶段1：知识盲区扫描（S1_scan）— 周日批处理 v1.11"""
import os, re, sys, json, datetime

VAULT = "/Users/chenyouqiang/Documents/LawKB"
CASE_DIR = os.path.join(VAULT, "知识飞轮系统/05-调用/案件管理")
OUT_DIR = os.path.join(VAULT, "知识飞轮系统/06-沉淀/知识盲区扫描日志")
TODAY = datetime.date(2026, 9, 6)
WIN_START = TODAY - datetime.timedelta(days=90)
os.makedirs(OUT_DIR, exist_ok=True)

# 排除：备份/临时
EXCL = (".bak", ".bak-", "_bak")

def recent_mtime(path):
    try:
        mt = datetime.datetime.fromtimestamp(os.path.getmtime(path)).date()
        return mt >= WIN_START
    except Exception:
        return False

def has_frontmatter(text):
    return text.startswith("---")

def count_links(text):
    return len(re.findall(r"\[\[[^\]]+\]\]", text))

def has_tags(text):
    fm = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not fm:
        return False
    return bool(re.search(r"^tags:", fm.group(1), re.M))

def fm_updated_recent(text):
    fm = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not fm:
        return False
    m = re.search(r"^updated:\s*(\d{4}-\d{2}-\d{2})", fm.group(1), re.M)
    if m:
        try:
            d = datetime.datetime.strptime(m.group(1), "%Y-%m-%d").date()
            return d >= WIN_START
        except Exception:
            return False
    return False

# ---------- 案件分布 ----------
case_files = []
for fn in os.listdir(CASE_DIR):
    if not fn.endswith(".md") or fn.endswith(EXCL) or ".bak-" in fn:
        continue
    fp = os.path.join(CASE_DIR, fn)
    if not recent_mtime(fp):
        continue
    case_files.append(fp)

cases = []
for fp in case_files:
    try:
        txt = open(fp, encoding="utf-8", errors="ignore").read()
    except Exception:
        continue
    fm = re.match(r"^---\n(.*?)\n---", txt, re.S)
    ctype = cstatus = "未知"
    if fm:
        m = re.search(r"^case_type:\s*(.+)$", fm.group(1), re.M)
        if m: ctype = m.group(1).strip()
        m = re.search(r"^case_status:\s*(.+)$", fm.group(1), re.M)
        if m: cstatus = m.group(1).strip()
    name = os.path.splitext(os.path.basename(fp))[0]
    if "知识调用映射" in name:
        name = name.replace("-知识调用映射", "")
    cases.append((name, ctype, cstatus))

# ---------- 覆盖度扫描 ----------
# 遍历全 vault 的 .md（排除备份），按领域关键词匹配
DOMAINS = {
    "合同纠纷": ["合同", "买卖", "租赁", "借款", "承揽", "赠与"],
    "股东知情权/公司法": ["股东知情权", "公司决议", "公司法", "股东代表诉讼"],
    "婚姻家庭": ["婚姻", "离婚", "抚养", "继承", "赡养"],
    "担保/商事": ["担保", "抵押", "质押", "保证合同"],
    "人伤/劳务": ["人伤", "工伤", "劳务", "医疗损害", "交通事故", "提供劳务"],
    "慈法合规": ["慈善", "基金会", "公益", "社会组织", "慈善法"],
}

all_md = []
for root, dirs, fns in os.walk(VAULT):
    # 跳过无关大目录
    dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules",)]
    for fn in fns:
        if not fn.endswith(".md"):
            continue
        if any(x in fn for x in EXCL):
            continue
        all_md.append(os.path.join(root, fn))

total_files = len(all_md)

# 预聚合：每个文件计算一次质量指标（用于所有领域，避免重复读）
file_cache = {}
def file_metrics(fp):
    if fp in file_cache:
        return file_cache[fp]
    try:
        txt = open(fp, encoding="utf-8", errors="ignore").read()
    except Exception:
        return None
    n = len(txt)
    fm = has_frontmatter(txt)
    links = count_links(txt)
    tags = has_tags(txt)
    upd = fm_updated_recent(txt) or recent_mtime(fp)
    # 长度归一：2000字≈1.0，上限1.3
    len_norm = min(max(n / 2000.0, 0.0), 1.3)
    file_cache[fp] = dict(fm=fm, links=links, tags=tags, upd=upd, n=n, len_norm=len_norm)
    return file_cache[fp]

# 对每个领域匹配
results = {}
for dom, kws in DOMAINS.items():
    matched = []
    for fp in all_md:
        try:
            txt = open(fp, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        if any(kw in txt for kw in kws):
            matched.append(fp)
    # 计算加权质量分
    if not matched:
        results[dom] = (0, 0.0)
        continue
    s_fm = s_links = s_tags = s_upd = s_len = 0
    for fp in matched:
        m = file_metrics(fp)
        if m is None:
            continue
        s_fm += 1 if m["fm"] else 0
        s_links += min(m["links"] / 5.0, 1.3)  # 5个链接≈满
        s_tags += 1 if m["tags"] else 0
        s_upd += 1 if m["upd"] else 0
        s_len += m["len_norm"]
    cnt = len(matched)
    q = (s_fm/cnt)*0.2 + (s_links/cnt)*0.2 + (s_tags/cnt)*0.1 + (s_upd/cnt)*0.2 + (s_len/cnt)*0.3
    results[dom] = (cnt, round(q, 3))

# 判定
def judge(q):
    if q < 0.5: return "🔴 严重"
    if q < 1.0: return "🟡 中度"
    return "🟢 良好"

# ---------- 输出 ----------
lines = []
lines.append("---")
lines.append("created: %sT21:00" % TODAY.isoformat())
lines.append("updated: %sT22:55" % TODAY.isoformat())
lines.append("tags:")
lines.append("  - 知识盲区")
lines.append("  - 周日批处理")
lines.append("  - 覆盖度扫描")
lines.append("  - 2026")
lines.append("---")
lines.append("")
lines.append("# 知识盲区扫描报告（%s / W36）" % TODAY.isoformat())
lines.append("")
lines.append("> **方法**：按 W31 量化口径测算各领域覆盖度。")
lines.append("> 笔记质量分 = frontmatter×0.2 + 双向链接×0.2 + 标签×0.1 + 90天更新×0.2 + 长度×0.3")
lines.append("> 覆盖度 = 匹配笔记该加权分均值。")
lines.append("> 判定：<0.5 严重 / 0.5–1.0 中度 / >1.0 良好。")
lines.append("> 扫描基准日：%s；近90天窗口：%s 至 %s；扫描文件总数 %d。" % (
    TODAY.isoformat(), WIN_START.isoformat(), TODAY.isoformat(), total_files))
lines.append("")
lines.append("## 一、最近90天案件类型分布（05-调用/案件管理/）")
lines.append("")
lines.append("| 案件 | 类型 | 状态 |")
lines.append("|------|------|------|")
for name, ctype, cstatus in cases:
    lines.append("| %s | %s | %s |" % (name, ctype, cstatus))
lines.append("")
# 分布摘要
from collections import Counter
type_counter = Counter()
for _, ctype, _ in cases:
    main = ctype.split("/")[0].split("（")[0].strip()
    type_counter[main] += 1
dist_str = "、".join("%s %d 件" % (k, v) for k, v in type_counter.items())
lines.append("**分布**：%s。" % dist_str)
lines.append("")
lines.append("## 二、六大领域覆盖度量化结果")
lines.append("")
lines.append("| 领域 | 匹配数 | 量化覆盖度 | 判定 |")
lines.append("|------|------:|------:|------|")
sev = mod = good = 0
for dom in DOMAINS:
    cnt, q = results[dom]
    j = judge(q)
    if "严重" in j: sev += 1
    elif "中度" in j: mod += 1
    else: good += 1
    lines.append("| %s | %d | %.3f | %s |" % (dom, cnt, q, j))
lines.append("")
lines.append("**盲区判定**：严重 %d 件 / 中度 %d 件 / 良好 %d 件。" % (sev, mod, good))
lines.append("")
lines.append("## 三、本周学习建议（优先序）")
lines.append("")
if sev + mod == 0:
    lines.append("- **全域保级**：本周六大领域覆盖度持续处于「良好」区间，无严重/中度盲区，知识维护重心继续由'广度补缺'转向'深度提质 + 交叉规则强化'。")
    lines.append("- **交叉规则强化**：合同纠纷（%d 匹配）与慈法合规（%d 匹配）量最大，建议析出'基金会合同纠纷'独立子主题并强化'先刑后民'驳回起诉类交叉规则卡。" % (results["合同纠纷"][0], results["慈法合规"][0]))
    lines.append("- **裁判规则终核**：优先做 pending_exact 标注法条的 exact wording 终核（最高法医疗损害解释/医师法/医疗纠纷条例等），并推进跨案模式提炼。")
    lines.append("- **结构治理**：匹配数虚高含泛匹配，建议结合标签体系治理（概念页脏标签规整）提升匹配精度，避免覆盖度被泛匹配抬升而掩盖真实薄点。")
else:
    lines.append("- **优先补盲**：%s。" % ("、".join("%s(%.3f)" % (d, results[d][1]) for d in DOMAINS if judge(results[d][1]) != "🟢 良好")))
    lines.append("- 建议本周定向投喂对应领域经验卡与裁判规则，并挂接领域枢纽。")
lines.append("")
lines.append("## 四、结论")
lines.append("")
if sev + mod == 0:
    lines.append("本周知识库六大领域覆盖度持续全部处于「良好」区间，无严重/中度盲区，知识维护重点由'广度补缺'正式转入'深度提质 + 交叉规则强化'阶段。")
else:
    lines.append("本周仍存在 %d 个需关注领域（严重 %d / 中度 %d），建议按上条建议定向补强。" % (sev+mod, sev, mod))
lines.append("")
lines.append("---")
lines.append("*生成：周日知识维护批处理 v1.11 阶段1（S1_scan）｜ 扫描基准 %s ｜ 数据源 知识飞轮系统（%d 文件）*" % (TODAY.isoformat(), total_files))
lines.append("")

out_path = os.path.join(OUT_DIR, "知识盲区扫描-%s.md" % TODAY.isoformat())
with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

# 输出关键指标供响应正文
print("TOTAL_FILES=%d" % total_files)
print("CASE_COUNT=%d" % len(cases))
for dom in DOMAINS:
    print("DOMAIN %s | matched=%d | coverage=%.3f | %s" % (dom, results[dom][0], results[dom][1], judge(results[dom][1])))
print("BLIND sev=%d mod=%d good=%d" % (sev, mod, good))
print("OUT=%s" % out_path)
