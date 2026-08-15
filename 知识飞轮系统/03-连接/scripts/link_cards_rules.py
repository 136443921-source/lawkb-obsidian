# -*- coding: utf-8 -*-
"""
知识飞轮连接层 · 高价值经验卡片 ↔ 裁判规则 双向补链脚本 (v3, 自动化版)
- 用途：供「周日知识维护批处理」自动化每周调用，使新投喂的卡片/规则自动挂接领域枢纽 + 同域互链。
- 链接约定：知识图谱扫描以 `[[文件名(不含.md)]]` wiki 链接解析边（见 kg_scan.py）
- 策略：每个领域创建「连接枢纽」页(MOC)，成员卡片/规则 ↔ 枢纽 双向链接；
        同域按法律主题词做卡片↔规则语义互链(top-5 限幅)；
        跨域仅用高特异性桥接词做少量高价值桥接(每节点≤3)。
- 幂等：自动补链段以稳定前缀 `## 关联（知识飞轮连接层自动补链` 写入，重跑整体替换（按前缀切分，不受日期变化影响），不破坏既有手工链接。
- 兜底：经验卡片下出现 GROUPS 未登记的新分类时，自动建独立枢纽并做同域互链（无规则桥接）。
- 统计：运行后写 link_lastrun.json（机器可读），并打印 `LINK_STAT {...}` 单行供自动化捕获。
"""
import os, re, json, glob, datetime
from collections import defaultdict

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
CARDS = os.path.join(ROOT, "02-提炼/经验卡片")
RULES = os.path.join(ROOT, "06-沉淀/裁判规则库")
HUB_DIR = os.path.join(ROOT, "03-连接")
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
DATE = datetime.date.today().strftime("%Y-%m-%d")
MARK_BEGIN = "## 关联（知识飞轮连接层自动补链"   # 稳定前缀：幂等切分键，不含日期

# 卡片分类 -> (裁判规则子目录, 枢纽文件名, 枢纽标题)
GROUPS = {
    "慈法合规": ("慈法合规", "连接枢纽-慈法合规", "慈法合规连接枢纽"),
    "医疗纠纷": ("人伤法", "连接枢纽-人伤法", "人伤法·医疗纠纷连接枢纽"),
    "合同文书": ("合同风险", "连接枢纽-合同风险", "合同风险连接枢纽"),
    "程序知识": ("通用", "连接枢纽-通用程序", "通用程序连接枢纽"),
    "法条解读": ("通用", "连接枢纽-通用程序", "通用程序连接枢纽"),
    "学习笔记": ("学习笔记", "连接枢纽-学习笔记", "学习笔记连接枢纽"),
    "公众号":   ("公众号", "连接枢纽-公众号", "公众号连接枢纽"),
    "案例":     ("案例", "连接枢纽-案例", "案例连接枢纽"),
}

# 细分案由规则目录 -> 归并到的领域(cat)，避免碎片化枢纽（v3.1 新增）
# 说明：裁判规则库按案由细分建目录，但连接层按"法律领域"聚合，故需显式归并。
RULE_MERGE = {
    "医疗损害责任纠纷":       "医疗纠纷",   # → 连接枢纽-人伤法
    "提供劳务者受害责任纠纷": "医疗纠纷",
    "机动车交通事故责任纠纷": "医疗纠纷",
    "生命权健康权身体权纠纷": "医疗纠纷",
    "建设工程":               "合同文书",   # → 连接枢纽-合同风险
    "环境公益诉讼":           "慈法合规",   # 公益诉讼主体资格与社会组织同域
    "公司法":                 "商事纠纷",   # → 连接枢纽-商事纠纷（兜底自动新建）
    "慈善":                   "慈法合规",   # → 连接枢纽-慈法合规（2026-08-13 补：R-CF 系列自动挂载）
}

# 法律主题词词典（同域语义互链）
TERMS = [
    "公开募捐","定向募捐","互联网募捐","募捐成本","管理费用","关联交易","捐赠","受赠","赠与",
    "投资","保值增值","理财","信息公开","年度报告","志愿服务","志愿者","评比表彰","重大活动",
    "票据","免税","税前扣除","发票","基金会","理事会","监事","党建","劳务","劳动","人事",
    "专项基金","受益人","慈善信托","备案","内部治理","合规","审查","注销","清算","法定代表人",
    "负责人","承诺","互联网","直播","募捐","慈善组织","捐赠人","项目","支出","审计",
    "工伤","工伤认定","劳动能力","伤残","人身损害","赔偿","医疗损害","病历","封存","过错",
    "鉴定","护理","营养","误工","被扶养人","死亡","交通事故","机动车","交强险","提供劳务",
    "雇佣","健康权","生命权","身体权","三期","后续治疗","康复","精神损害","抚慰金","赔偿标准",
    "赔偿计算","伤残等级","护理期","营养期","误工期","后续","诊疗","诊疗过错","医疗","人身",
    "合同","违约","解除","撤销","效力","无效","条款","审查","保证","担保","抵押","质押","借款",
    "买卖","租赁","建设工程","招投标","定金","违约金","管辖","仲裁","格式条款","免责","阴阳合同",
    "股权转让","交付","验收","付款","质量","知识产权","保密","竞业限制","连带","定金罚则",
    "合同解除","合同效力","合同审查","合作协议","买卖纠纷","赠与合同","担保合同","教育培训",
    "诉讼","管辖","立案","举证","质证","证据","保全","执行","强制执行","抗辩","时效","追诉",
    "笔迹","指纹","报案","经侦","检察","监督","举报","金融监管","程序","流程","期限","送达",
    "上诉","再审","申请","代理","委托","调解","司法确认","鉴定费","诉讼费","财保","执行异议",
    "股东知情权","出资","瑕疵","诈骗","贷款","骗取","虚假","认定","监管",
    "法理学","法律检索","行政法","律师","职业","思政","成长","民商事","刑事","方法论","庭审",
    "技巧","合规","风险","案例","实务","裁判","要旨","指导案例","司法解释",
    "公益","薪酬","赞助","药企","国际贸易","出口","AI","案件管理","婚内财产","财产协议","协议",
    "行业","合理","合规管理","风险","指引",
]
STOP = {"规则","指引","基金","法律","纠纷","审查","管理","要点","合规管理","风险",
        "库","笔记","卡片","案例","知识","学习"}

# 跨域桥接：仅高特异性主题词（去掉过于宽泛的 合规/捐赠/风险/慈善 等）
BRIDGE = ["票据","免税","税前扣除","捐赠人","关联交易","公开募捐",
          "慈善信托","志愿服务","评比表彰","重大活动","投资收益","抵扣","发票","备案","信息公开"]

def get_terms(text):
    return {t for t in TERMS if t in text} - STOP

def read_note(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw, re.S)
    fm, body = (m.group(1), m.group(2)) if m else ("", raw)
    exist = {x.strip() for x in re.findall(r"\[\[([^\]\|#]+)", body)}
    return fm, body, exist

def write_note(path, fm, hub, same_links, cross_links):
    fm_lines = fm.split("\n")
    out, skip = [], False
    for ln in fm_lines:
        if ln.strip().startswith("related_links:"):
            skip = True; continue
        if skip:
            if re.match(r"^\s*-\s", ln): continue
            skip = False
        out.append(ln)
    # 读取原 body（去旧段，按稳定前缀切分，不受日期影响）
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", raw, re.S)
    body = m.group(2) if m else raw
    idx = body.find(MARK_BEGIN)
    if idx != -1:
        body = body[:idx].rstrip() + "\n"
    lines = [f"{MARK_BEGIN} · {DATE})"]
    if hub: lines.append(f"- 领域枢纽：[[{hub}]]")
    if same_links:
        lines.append("- 同域语义关联：")
        for i in range(0, len(same_links), 4):
            lines.append("  - " + " · ".join(f"[[{c}]]" for c in same_links[i:i+4]))
    if cross_links:
        lines.append("- 跨域桥接：")
        for i in range(0, len(cross_links), 4):
            lines.append("  - " + " · ".join(f"[[{c}]]" for c in cross_links[i:i+4]))
    body = body.rstrip() + "\n\n" + "\n".join(lines) + "\n"
    rl = "\nrelated_links:\n" + "\n".join(f"  - {l}" for l in ([hub]+same_links+cross_links) if l)
    new_fm = "\n".join(out).rstrip() + rl
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n" + new_fm + "\n---\n" + body)

# 有效分组：GROUPS + 未知卡片分类自动建独立枢纽
EG = {c: GROUPS[c] for c in GROUPS}
if os.path.isdir(CARDS):
    for cat in sorted(os.listdir(CARDS)):
        d = os.path.join(CARDS, cat)
        if os.path.isdir(d) and cat not in EG:
            EG[cat] = (None, f"连接枢纽-{cat}", f"{cat}连接枢纽")

# 兜底(v3.1)：裁判规则库出现既未被 GROUPS 映射、也未被 RULE_MERGE 归并的新子目录时，
# 自动建独立枢纽——防止新增案由目录静默游离在连接层之外（2026-08-04 修复 R-SH/R-GS 等 39 条规则失联）。
_covered = {v[0] for v in EG.values() if v[0]} | set(RULE_MERGE.keys())
if os.path.isdir(RULES):
    for rd in sorted(os.listdir(RULES)):
        if not os.path.isdir(os.path.join(RULES, rd)) or rd.startswith(("__", ".")):
            continue
        if rd in _covered:
            continue
        if rd in EG:      # 卡片同名分类已存在 → 升级为带规则域
            EG[rd] = (rd, EG[rd][1], EG[rd][2])
        else:
            EG[rd] = (rd, f"连接枢纽-{rd}", f"{rd}连接枢纽")

# 枚举成员
members = defaultdict(list)
node_hub = {}
for cat, (rdomain, hubfile, hubtitle) in EG.items():
    cdir = os.path.join(CARDS, cat)
    if os.path.isdir(cdir):
        for p in sorted(glob.glob(os.path.join(cdir, "*.md"))):
            base = os.path.splitext(os.path.basename(p))[0]
            fm, body, _ = read_note(p)
            members[cat].append((base, p, get_terms(fm+"\n"+body)))
            node_hub[base] = hubfile

# 规则枚举(v3.1)：以 cat 为驱动，聚合「主规则目录 + RULE_MERGE 归并目录」
cat_rdirs = defaultdict(list)
for cat, (rd, _, _) in EG.items():
    if rd: cat_rdirs[cat].append(rd)
for rdir_name, target_cat in RULE_MERGE.items():
    if target_cat in EG:
        cat_rdirs[target_cat].append(rdir_name)
    else:
        print(f"[WARN] RULE_MERGE 目标领域不存在，规则目录未挂载: {rdir_name} -> {target_cat}")

for cat, rdirs in cat_rdirs.items():
    hubfile = EG[cat][1]
    for rdomain in dict.fromkeys(rdirs):          # 去重且保序
        rdir = os.path.join(RULES, rdomain)
        if not os.path.isdir(rdir): continue
        for p in sorted(glob.glob(os.path.join(rdir, "*.md"))):
            base = os.path.splitext(os.path.basename(p))[0]
            fm, body, _ = read_note(p)
            members[cat].append((base, p, get_terms(fm+"\n"+body)))
            node_hub[base] = hubfile

# 计算边
neighbors = defaultdict(set)
hub_members = defaultdict(list)
for cat, (rdomain, hubfile, hubtitle) in EG.items():
    items = members[cat]; fns = [it[0] for it in items]
    hub_members[cat] = fns
    for fn in fns:
        neighbors[fn].add(hubfile); neighbors[hubfile].add(fn)
    n = len(items)
    for i in range(n):
        fi, pi, ti = items[i]
        scored = []
        for j in range(n):
            if i == j: continue
            fj, pj, tj = items[j]
            sh = ti & tj
            if sh: scored.append((len(sh), fj))
        scored.sort(key=lambda x: -x[0])
        for _, fj in scored[:5]:
            neighbors[fi].add(fj); neighbors[fj].add(fi)

# 跨域桥接（高特异性词，每节点严格限 3 条）
allterms = {base: ts for cat, items in members.items() for base, p, ts in items}
node_cross_cnt = defaultdict(int)
for bterm in BRIDGE:
    grp = [fn for fn, ts in allterms.items() if bterm in ts]
    for a in grp:
        if node_cross_cnt[a] >= 3:
            continue
        ha = node_hub.get(a)
        for b in grp:
            if a == b: continue
            if node_cross_cnt[a] >= 3:
                break
            hb = node_hub.get(b)
            if ha and hb and ha != hb and b not in neighbors[a]:
                neighbors[a].add(b); neighbors[b].add(a)
                node_cross_cnt[a] += 1
        if node_cross_cnt[a] >= 3:
            break

# 写回
written = 0
for cat, (rdomain, hubfile, hubtitle) in EG.items():
    for base, p, ts in members[cat]:
        my_hub = node_hub.get(base)
        same, cross = [], []
        for l in neighbors[base]:
            if l == base or l == my_hub: continue
            if node_hub.get(l) == my_hub:
                same.append(l)
            else:
                cross.append(l)
        seen=set(); same=[x for x in same if not (x in seen or seen.add(x))]
        seen=set(); cross=[x for x in cross if not (x in seen or seen.add(x))]
        fm, _, exist = read_note(p)
        write_note(p, fm, my_hub, same, cross)
        written += 1

# 生成枢纽页（每次整体重建，自动纳入新成员）
os.makedirs(HUB_DIR, exist_ok=True)
for cat, (rdomain, hubfile, hubtitle) in EG.items():
    fns = hub_members[cat]
    cards = [fn for fn, p, ts in members[cat] if "/经验卡片/" in p]
    rules = [fn for fn, p, ts in members[cat] if "/裁判规则库/" in p]
    L = ["---", f"title: {hubtitle}", "type: 连接枢纽", f"domain: {cat}",
         f"generated_by: 连接层自动补链({DATE})", f"created: {DATE}T22:00",
         "tags:", "  - 连接枢纽", f"  - {cat}", "---", "", f"# {hubtitle}", "",
         f"> 本页为「{cat}」领域连接枢纽（MOC），由知识飞轮连接层于 {DATE} 自动生成。",
         f"> 共挂载 {len(cards)} 张经验卡片 + {len(rules)} 条裁判规则，双向链接已自动建立。",
         "", "## 经验卡片"]
    for fn in cards: L.append(f"- [[{fn}]]")
    L += ["", "## 裁判规则"]
    for fn in rules: L.append(f"- [[{fn}]]")
    L.append("")
    with open(os.path.join(HUB_DIR, hubfile + ".md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))

# 规则覆盖自检(v3.1)：确认裁判规则库无游离子目录
rule_total = rule_linked = 0
uncovered = []
if os.path.isdir(RULES):
    linked_rdirs = {rd for rds in cat_rdirs.values() for rd in rds}
    for rd in sorted(os.listdir(RULES)):
        d = os.path.join(RULES, rd)
        if not os.path.isdir(d) or rd.startswith(("__", ".")): continue
        n = len(glob.glob(os.path.join(d, "*.md")))
        rule_total += n
        if rd in linked_rdirs: rule_linked += n
        else: uncovered.append(rd)

total_edges = sum(len(v) for v in neighbors.values()) // 2
stat = {"date": DATE, "script": "link_cards_rules.py", "version": "3.1",
        "processed": written, "hubs": len(EG),
        "members_per_cat": {c: len(members[c]) for c in EG},
        "rules_total": rule_total, "rules_linked": rule_linked,
        "uncovered_rule_dirs": uncovered,
        "estimated_edges": total_edges}
with open(os.path.join(SCRIPTS, "link_lastrun.json"), "w", encoding="utf-8") as f:
    json.dump(stat, f, ensure_ascii=False, indent=1)
with open(os.path.join(SCRIPTS, "link_neighbors.json"), "w", encoding="utf-8") as f:
    json.dump({k: sorted(v) for k, v in neighbors.items()}, f, ensure_ascii=False, indent=1)

print("=== 连接层补链 v3.1 完成 ===")
print(f"裁判规则覆盖: {rule_linked}/{rule_total}" + (f"  ⚠️游离目录: {uncovered}" if uncovered else "  ✅ 无游离目录"))
print(f"处理笔记文件数: {written}（含幂等覆盖）")
print(f"生成枢纽页: {len(EG)}")
for cat in EG:
    fns = hub_members[cat]
    e = sum(1 for a in fns for b in neighbors[a] if b in fns) // 2
    print(f"  {cat}: 成员{len(fns)} 同域互链~{e}")
print("LINK_STAT " + json.dumps(stat, ensure_ascii=False))
