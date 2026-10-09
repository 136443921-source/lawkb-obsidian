#!/usr/bin/env python3
# 步6：注册表 vs 9 消费技能 SKILL.md 一致性校验（漂移监测）
# 重扫飞轮全量卡 + 9 消费技能，重算挂载/冲突/错挂，与 card_route_registry.yaml 比对，
# 输出漂移报告 JSON。六-B：写前 cp -n 备份。幂等：仅报告，除非 --apply。
import os, re, json, shutil, datetime

SKILLS = os.path.expanduser("~/.workbuddy/skills")
FLY = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "card_route_registry.yaml")
OUT = os.path.join(HERE, "registry_drift_report.json")
TS = datetime.datetime.now().strftime("%Y-%m-%d")

EXCLUDE_DIRS = {".git",".obsidian",".trash",".trash-dedup-20260819",".cache_20260820",
                ".backup","__pycache__",".workbuddy","CaseDrop","IMA-Inbox","_outputs",
                "logs","task-tracker","复习记录","系统迭代说明","驾驶舱_backup","_演练","_运维"}
def is_excl(d):
    b=os.path.basename(d); return b in EXCLUDE_DIRS or b.startswith(".backup_link_")

rule_re = re.compile(r'^rule_id:\s*["\']?([A-Za-z0-9_\-]+)["\']?\s*$', re.M)

# 路由行解析器：仅取「知识飞轮卡库接线」段内、首列为真实 rid 的 `| rid |` 行。
# 用于冲突/错挂检测——正文示例提及（如 '（如 R001、R-GS-001）'）不计入挂载，避免假阳性。
# 注意：meta_inflation_guard 仍用全文件提及统计（那是证明元技能被排除的牙齿），二者分离。
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

# 元技能注水阻断机制：路由统计边界只读 skill_role_registry.yaml 的 consumption_skills。
ROLE_REG = os.path.join(HERE, "skill_role_registry.yaml")
def load_consumption(path):
    if not os.path.exists(path):
        raise SystemExit(f"[check] 错误：角色注册表缺失 {path}，拒绝回退硬编码边界")
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
        if not line.startswith('  '):
            break
    if not cons:
        raise SystemExit(f"[check] 错误：角色注册表未声明 consumption_skills，拒绝空边界")
    return cons
CONS = load_consumption(ROLE_REG)
DED = {
 "06-沉淀/人伤法域库":"人损纠纷专项","02-提炼/人伤法":"人损纠纷专项",
 "06-沉淀/慈善合规域库":"非诉文书红蓝复核工作流","06-沉淀/合同风险规则库":"blue-team-contract-review-standard-v1.0",
 "06-沉淀/公司法域库":"company-due-diligence","06-沉淀/证据规则卡族":"判决书分析助手",
 "06-沉淀/裁判规则库":"判决书分析助手","06-沉淀/通用裁判规则库":"判决书分析助手",
 "02-提炼/案例摘要":"类案检索助手","06-沉淀/案例库":"类案检索助手","06-沉淀/类案检索报告卡族":"类案检索助手",
 "06-沉淀/律师实务域库":"诉讼文书红蓝复核工作流","02-提炼/经验卡片":"legal-base",
 "06-沉淀/婚姻家庭域库":"家事纠纷专项","06-沉淀/劳动人事域库":"劳动用工专项","06-沉淀/刑事域库":"刑事辩护专项","06-沉淀/案由路由卡族":"案由路由专项","06-沉淀/建设工程域库":"建设工程专项","06-沉淀/商事纠纷域库":"商事纠纷专项"}
UNI="法律检索助手"
# Plan B 逐卡覆盖（6 冲突归属 + 9 错挂归属）；R-PI-* 由前缀规则统一归人损
OVERRIDE = {
 "R-HT-101":"blue-team-contract-review-standard-v1.0",
 "R015":"legal-base","R017":"legal-base","R018":"legal-base","R020":"legal-base","R024":"判决书分析助手",
 "R-GS-001":"legal-base","R-JG-007":"法律检索助手","R-JG-008":"法律检索助手"}

cards={}
for root,dirs,files in os.walk(FLY):
    dirs[:]=[d for d in dirs if not is_excl(d)]
    for f in files:
        if not f.endswith(".md"): continue
        try: t=open(os.path.join(root,f),encoding="utf-8",errors="ignore").read()
        except: continue
        m=rule_re.search(t[:4000]); 
        if not m: continue
        rid=m.group(1); rel=os.path.relpath(os.path.join(root,f),FLY)
        if rid not in cards: cards[rid]=("/".join(rel.split("/")[:2]),os.path.basename(rel))

all_rids=set(cards)
skill_rids={}      # 全文件提及（供 meta_inflation_guard 证明元技能被排除）
routing_rids={}    # 仅卡库接线段内真实 `| rid |` 行（供冲突/错挂检测）
for root,dirs,files in os.walk(SKILLS):
    if "node_modules" in root or "_backup" in root: continue
    for f in files:
        if f=="SKILL.md":
            d=os.path.basename(root)
            try: t=open(os.path.join(root,f),encoding="utf-8",errors="ignore").read()
            except: continue
            found={r for r in all_rids if r in t}
            if found: skill_rids.setdefault(d,set()).update(found)
            routed=parse_routing_rows(t, all_rids)
            if routed: routing_rids.setdefault(d,set()).update(routed)

# 元技能注水自检：扫描「全部」技能，统计非 consumption 技能引用了哪些卡 rid。
# 这些技能被强制排除出路由统计（边界生效证明），同时暴露未来新增注水风险。
meta_inflation={}
for sk,rset in skill_rids.items():
    if sk in CONS:
        continue
    if rset:
        meta_inflation[sk]=sorted(rset)

cur={"total":len(cards),"mounted":0,"unmounted":0,"conflict":0,"misroute":0}
conflicts=[]; misroutes=[]
for rid,(dom,fn) in sorted(cards.items()):
    intended=DED.get(dom,UNI)
    if rid.startswith("R-AY-"): intended="案由路由专项"   # P1(A) 升格：全量 R-AY-* 归案由路由专项（覆盖目录去重歧义）
    elif rid.startswith("R-PI-"): intended="人损纠纷专项"
    elif rid in OVERRIDE: intended=OVERRIDE[rid]
    mounted=rid in routing_rids.get(intended,set())
    cons_hits=[sk for sk in CONS if rid in routing_rids.get(sk,set())]
    if not mounted:
        cur["unmounted"]+=1
        if cons_hits:
            cur["misroute"]+=1; misroutes.append({"rule_id":rid,"domain":dom,"intended":intended,"actual":cons_hits})
    elif len(cons_hits)>1:
        cur["conflict"]+=1; cur["mounted"]+=1; conflicts.append({"rule_id":rid,"domain":dom,"skills":cons_hits})
    else:
        cur["mounted"]+=1

# 读旧注册表汇总
reg_summary={}
if os.path.exists(REG):
    rt=open(REG,encoding="utf-8").read()
    for k in ["total_cards","mounted","unmounted"]:
        m=re.search(rf'^{k}: (\S+)',rt,re.M); reg_summary[k]=int(m.group(1)) if m else None
    reg_conf=sorted(set(re.findall(r'status: conflict',rt)))

drift={
 "generated":TS,
 "current":cur,
 "registry_summary":reg_summary,
 "delta_mounted":(cur["mounted"]-reg_summary.get("mounted")) if reg_summary.get("mounted") is not None else None,
 "delta_unmounted":(cur["unmounted"]-reg_summary.get("unmounted")) if reg_summary.get("unmounted") is not None else None,
 "conflicts":conflicts,
 "misroutes":misroutes,
 "meta_inflation_guard":meta_inflation,
}
json.dump(drift, open(OUT,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"[check] 当前: 挂载 {cur['mounted']}/{cur['total']} 缺口 {cur['unmounted']} 冲突 {cur['conflict']} 错挂 {cur['misroute']}")
print(f"[check] 注册表记录: 挂载 {reg_summary.get('mounted')} 缺口 {reg_summary.get('unmounted')}")
print(f"[check] 漂移报告已写 {OUT}（冲突 {len(conflicts)} / 错挂 {len(misroutes)}）")
print(f"[check] 元技能注水自检：{len(meta_inflation)} 个非消费技能引用了卡 rid（已强制排除，不入统计）")
for sk in sorted(meta_inflation):
    print(f"        - {sk}: {len(meta_inflation[sk])} 张卡引用（meta，已排除）")
