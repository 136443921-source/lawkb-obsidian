#!/usr/bin/env python3
# 生成全量卡库路由注册表 card_route_registry.yaml（WF-028 全量调度 SSOT）
# 覆盖知识飞轮系统全量活跃卡（WF-028 排除集），非仅已挂载 699。
# 关键：mounted 卡记真实所在技能（实测），unmounted 记意图技能（按映射）→ 暴露意图vs实际错配。
import os, re, datetime

SKILLS = os.path.expanduser("~/.workbuddy/skills")
FLY = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT = "/Users/chenyouqiang/Documents/LawKB/小强律师数字分身系统/00-系统总览与运维中心/card_route_registry.yaml"
TS = datetime.datetime.now().strftime("%Y-%m-%d")

EXCLUDE_DIRS = {".git", ".obsidian", ".trash", ".trash-dedup-20260819", ".cache_20260820",
                ".backup", "__pycache__", ".workbuddy", "CaseDrop", "IMA-Inbox",
                "_outputs", "logs", "task-tracker", "复习记录", "系统迭代说明",
                "驾驶舱_backup", "_演练", "_运维"}
def is_excl(d):
    b = os.path.basename(d)
    return b in EXCLUDE_DIRS or b.startswith(".backup_link_")

# 元技能注水阻断机制：路由统计边界只读 skill_role_registry.yaml 的 consumption_skills。
# 缺失即硬失败，绝不静默回退到硬编码（那正是 99.92% 虚高的根）。
ROLE_REG = "/Users/chenyouqiang/Documents/LawKB/小强律师数字分身系统/00-系统总览与运维中心/skill_role_registry.yaml"
def load_consumption(path):
    if not os.path.exists(path):
        raise SystemExit(f"[gen] 错误：角色注册表缺失 {path}，拒绝回退硬编码边界（元技能注水阻断）")
    t = open(path, encoding="utf-8").read()
    cons, in_block = [], False
    for line in t.splitlines():
        if re.match(r'^consumption_skills:\s*$', line):
            in_block = True; continue
        if not in_block:
            continue
        if not line.strip():
            continue
        m = re.match(r'^  - (\S+)\s*$', line)
        if m:
            cons.append(m.group(1)); continue
        if not line.startswith('  '):   # 下一顶层键 -> 块结束
            break
    if not cons:
        raise SystemExit(f"[gen] 错误：角色注册表未声明任何 consumption_skills，拒绝空边界")
    return cons

def load_old_usage(path):
    """继承旧注册表的 usage_count/last_used，避免重生成清零用量（P0 修复）。
    解析本脚本自己产出的 card_route_registry.yaml 规则块；文件缺失即返回空 dict（默认 0）。"""
    d = {}
    if not os.path.exists(path):
        return d
    cur = None
    try:
        for line in open(path, encoding="utf-8"):
            m = re.match(r'^  - rule_id:\s*(\S+)', line)
            if m:
                cur = m.group(1); d[cur] = (0, None); continue
            if cur is None:
                continue
            mu = re.match(r'^    usage_count:\s*(\d+)', line)
            if mu:
                d[cur] = (int(mu.group(1)), d[cur][1]); continue
            ml = re.match(r'^    last_used:\s*(\S+)', line)
            if ml:
                v = ml.group(1).strip()
                d[cur] = (d[cur][0], None if v == "null" else v)
    except Exception:
        return {}
    return d

rule_re = re.compile(r'^rule_id:\s*["\']?([A-Za-z0-9_\-]+)["\']?\s*$', re.M)
tok_re = re.compile(r'R-[A-Za-z0-9_\-]+')

# 路由行解析器：仅取「知识飞轮卡库接线」段内、首列为真实 rid 的 `| rid |` 行。
# 用于冲突/错挂检测——正文示例提及（如 '（如 R001、R-GS-001）'）不计入挂载，避免假阳性。
ROW_RE = re.compile(r'^\|\s*([^\s\|]+)\s*\|')
SEP_RE = re.compile(r'^\|[\s\-]+\|')
def parse_routing_rows(text, ridset):
    in_sec = False; out = set()
    for line in text.split("\n"):
        if line.startswith("## "):
            in_sec = "知识飞轮卡库接线" in line; continue
        if not in_sec:
            continue
        if SEP_RE.match(line):
            continue
        m = ROW_RE.match(line)
        if m and m.group(1) in ridset:
            out.add(m.group(1))
    return out

DEDICATED = {
    "06-沉淀/人伤法域库": "人损纠纷专项",
    "02-提炼/人伤法": "人损纠纷专项",
    "06-沉淀/慈善合规域库": "非诉文书红蓝复核工作流",
    "06-沉淀/合同风险规则库": "blue-team-contract-review-standard-v1.0",
    "06-沉淀/公司法域库": "company-due-diligence",
    "06-沉淀/证据规则卡族": "判决书分析助手",
    "06-沉淀/裁判规则库": "判决书分析助手",
    "06-沉淀/通用裁判规则库": "判决书分析助手",
    "02-提炼/案例摘要": "类案检索助手",
    "06-沉淀/案例库": "类案检索助手",
    "06-沉淀/类案检索报告卡族": "类案检索助手",
    "06-沉淀/律师实务域库": "诉讼文书红蓝复核工作流",
    "02-提炼/经验卡片": "legal-base",
    "06-沉淀/婚姻家庭域库": "家事纠纷专项",
    "06-沉淀/劳动人事域库": "劳动用工专项",
    "06-沉淀/刑事域库": "刑事辩护专项",
    "06-沉淀/案由路由卡族": "案由路由专项",
}
# Plan B 逐卡覆盖（6 冲突归属 + 9 错挂归属）；R-PI-* 由前缀规则统一归人损
OVERRIDE = {
    "R-HT-101": "blue-team-contract-review-standard-v1.0",
    "R015": "legal-base", "R017": "legal-base", "R018": "legal-base",
    "R020": "legal-base", "R024": "判决书分析助手",
    "R-GS-001": "legal-base", "R-JG-007": "法律检索助手", "R-JG-008": "法律检索助手",
}
UNIVERSAL = "法律检索助手"

# 1. 收集全量活跃卡
cards = {}  # rid -> (domain, card_file)
for root, dirs, files in os.walk(FLY):
    dirs[:] = [d for d in dirs if not is_excl(d)]
    for f in files:
        if not f.endswith(".md"):
            continue
        p = os.path.join(root, f)
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        m = rule_re.search(txt[:4000])
        if not m:
            continue
        rid = m.group(1)
        rel = os.path.relpath(p, FLY)
        if rid not in cards:
            cards[rid] = ("/".join(rel.split("/")[:2]), os.path.basename(rel))

# 2. 每个技能含哪些 rid（实测，精确匹配卡片 rid 全集，避免前缀误判）
#    【铁律修正①】原 tok_re=R-[A-Za-z0-9_\-]+ 只认 R- 前缀，漏判 LC-/PI-/HG- 等非 R 前缀卡，
#                造成假阴性 pending。改为用全部卡片 rid 在 SKILL.md 做精确子串匹配。
#    【铁律修正②】原 d=os.path.basename(os.path.dirname(root)) 取的是 ~/.workbuddy/skills 自身，
#                导致全部卡的 skill 字段错标为 "skills"。改为 basename(root)=真实技能目录名。
all_rids = set(cards.keys())
skill_rids = {}  # skill_dir -> set(rid)
for root, dirs, files in os.walk(SKILLS):
    if "node_modules" in root or "_backup" in root:
        continue
    for f in files:
        if f == "SKILL.md":
            d = os.path.basename(root)
            try:
                t = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
            except Exception:
                continue
            found = parse_routing_rows(t, all_rids)
            if found:
                skill_rids.setdefault(d, set()).update(found)

# 3. 构造注册表条目
#    【铁律修正③】路由归属只针对消费技能（consumption_skills，来自角色注册表 SSOT），
#    元技能（模拟法庭主控协调器/拆卡流水线/编排器等）引用全量卡属系统级行为，不计入路由冲突。
#    mounted = 是否在其指派的消费技能中；conflict = 同时出现在 ≥2 个消费技能；其余 pending。
CONS = load_consumption(ROLE_REG)
# P0 修复：重生成前继承旧注册表用量，避免每次重生成清零（如未跑 usage_aggregate 立即归零）
OLD_USAGE = load_old_usage(OUT)
entries = []
domain_stat = {}  # domain -> {total,intended,mounted,conflict,unmounted,misrouted}
for rid, (dom, fname) in sorted(cards.items()):
    intended = DEDICATED.get(dom, UNIVERSAL)
    if rid.startswith("R-AY-"):
        intended = "案由路由专项"   # P1(A) 升格：全量 R-AY-* 路由卡归属案由路由专项（覆盖目录去重歧义，如 R-AY-007 双文件）
    elif rid.startswith("R-PI-"):
        intended = "人损纠纷专项"
    elif rid in OVERRIDE:
        intended = OVERRIDE[rid]
    mounted = rid in skill_rids.get(intended, set())
    cons_hits = [sk for sk in CONS if rid in skill_rids.get(sk, set())]
    if not mounted:
        # pending 中若其实挂在别的消费技能 -> 错挂(misrouted)，需改接线
        status = "pending"; owner = intended
    elif len(cons_hits) > 1:
        status = "conflict"; owner = cons_hits[0]
    else:
        status = "active"; owner = intended
    entries.append({
        "rule_id": rid, "domain": dom, "skill": owner,
        "card_file": fname, "mounted": mounted,
        "mounted_at": TS if mounted else None,
        "intended_skill": intended, "status": status,
        "usage_count": OLD_USAGE.get(rid, (0, None))[0],
        "last_used": OLD_USAGE.get(rid, (0, None))[1],
    })
    ds = domain_stat.setdefault(dom, {"total":0,"intended":intended,"mounted":0,"conflict":0,"unmounted":0,"misrouted":0})
    ds["total"] += 1
    if mounted: ds["mounted"] += 1
    else: ds["unmounted"] += 1
    if status == "conflict": ds["conflict"] += 1
    if status == "pending" and cons_hits: ds["misrouted"] += 1

# 4. 写 yaml
lines = []
lines.append(f"# 卡库路由注册表 · 全量调度 SSOT（卡库 DNS）")
lines.append(f"# 生成: {TS} | 覆盖: 知识飞轮系统全量活跃卡 {len(entries)} 张 | WF-028")
lines.append(f"version: 1")
lines.append(f"generated: {TS}")
lines.append(f"total_cards: {len(entries)}")
lines.append(f"mounted: {sum(1 for e in entries if e['mounted'])}")
lines.append(f"unmounted: {sum(1 for e in entries if not e['mounted'])}")
lines.append("policy:")
lines.append("  sleep_threshold_days: 30      # 沉睡卡阈值")
lines.append("  sleep_action: demote          # 处置策略：降级(status->deprecated)")
lines.append("  conflict_action: alert        # 同 rule_id 多技能 -> 告警待人工裁决")
lines.append("  aggregation_source: 05-调用   # usage_count/last_used 由步5从调用记录聚合")
lines.append("rules:")
for e in entries:
    lines.append(f"  - rule_id: {e['rule_id']}")
    lines.append(f"    domain: {e['domain']}")
    lines.append(f"    skill: {e['skill']}")
    lines.append(f"    intended_skill: {e['intended_skill']}")
    lines.append(f"    card_file: {e['card_file']}")
    lines.append(f"    mounted: {str(e['mounted']).lower()}")
    lines.append(f"    mounted_at: {e['mounted_at']}")
    lines.append(f"    status: {e['status']}")
    lines.append(f"    usage_count: {e['usage_count']}")
    lines.append(f"    last_used: {('null' if e['last_used'] is None else e['last_used'])}")
yaml_text = "\n".join(lines) + "\n"

os.makedirs(os.path.dirname(OUT), exist_ok=True)
if os.path.exists(OUT):
    # 备份名带时分秒，唯一化、绝不覆盖既有备份（守 cp -n 防覆盖铁律，避开宿主策略 prompt）
    bak = OUT + f".bak-{datetime.datetime.now():%Y%m%d-%H%M%S}"
    import shutil
    shutil.copy2(OUT, bak)
open(OUT, "w", encoding="utf-8").write(yaml_text)

# 5. 域覆盖分析表（复盘用）
n_mounted=sum(1 for e in entries if e['mounted'])
n_unmounted=sum(1 for e in entries if not e['mounted'])
n_conflict=sum(1 for e in entries if e['status']=='conflict')
n_mis=sum(ds['misrouted'] for ds in domain_stat.values())
print(f"[gen] 注册表已写 {OUT}（{len(entries)} 条）")
print(f"[gen] 已在其指派消费技能挂载 {n_mounted} / 未挂载(pending) {n_unmounted} / 冲突(≥2消费技能共存) {n_conflict} / 其中错挂(挂在别消费技能) {n_mis}")
print("\n=== 域覆盖分析（按卡片数降序，供复盘）===")
print(f"{'域':40s} {'总数':>5s} {'意图技能':32s} {'已挂':>5s} {'未挂':>5s} {'冲突':>4s} {'错挂':>4s}")
for dom, ds in sorted(domain_stat.items(), key=lambda x:-x[1]['total']):
    print(f"{dom:40s} {ds['total']:5d} {ds['intended']:32s} {ds['mounted']:5d} {ds['unmounted']:5d} {ds['conflict']:4d} {ds['misrouted']:4d}")
