#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连接层 · 断链消解器 (v1.0)
=======================
为知识飞轮系统内所有「双向链接断链」（[[target]] 无对应 .md 文件）生成概念页，
使断链转为有效解析，从而修复知识图谱连通性。

策略：
  1. 近似错写（strip "（红队）/（蓝队）" 等后缀后命中现有文件）→ 修正源文件引用（严格限定已知后缀，避免误改）。
  2. 其余断链目标 → 在 03-连接/概念页/ 下建概念枢纽页：
     - 法条引用型（匹配 《...》第X条）→ 注明条文要旨并链接母法文件；
     - 概念型 → 简明释义（内置高频词典，缺失则中性枢纽语）+ 关联现有相关笔记 + 同簇互链。
非破坏性：仅新建文件 + 修正明确错写，不动其他内容；产物均置于 概念页/ 子目录，git 可整体回滚。

用法：
  python3 resolve_broken_links.py [--apply] [--only-freq N]
  --apply   实际写入（默认 dry-run 打印计划）
  --only-freq 仅处理出现次数>=N 的断链目标（默认 1，即全部）
"""
import os, re, json, argparse
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # 知识飞轮系统/
SCRIPTS = os.path.join(ROOT, "03-连接", "scripts")
CONCEPT_DIR = os.path.join(ROOT, "03-连接", "概念页")
os.makedirs(CONCEPT_DIR, exist_ok=True)
# meta 报告目录：其内部 `[[...]]` 多为断链示例，不扫描、不建概念页
META_SKIP = {"孤立笔记检测报告", "知识库压缩去重报告"}

# ---------- 收集文件 ----------
all_md = []
for dp, dn, fn in os.walk(ROOT):
    if ".git" in dp:
        continue
    for f in fn:
        if f.endswith(".md"):
            all_md.append(os.path.join(dp, f))

# existing 包含全部 .md（含 meta 报告），使指向报告等真实文件的链接正确解析
existing = {}
for f in all_md:
    base = os.path.splitext(os.path.basename(f))[0]
    existing[base] = f

# 仅从非 meta 目录扫描「断链目标」，避免为报告内示例链接建概念页
scan_md = [f for f in all_md if not any(meta in f for meta in META_SKIP)]

# 预建 文件名->正文 索引（用于关联发现）
file_text = {}
for f in all_md:
    try:
        file_text[f] = open(f, encoding="utf-8").read()
    except Exception:
        file_text[f] = ""

link_re = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]*)?(?:\|[^\]]*)?\]\]")  # 对齐 kg_scan：剥离 #anchor 与 |别名
FILE_EXTS = (".html", ".pdf", ".docx", ".png", ".jpg", ".jpeg", ".gif", ".csv", ".xlsx", ".md")
unresolved = Counter()
broken_by_file = defaultdict(list)
for f in scan_md:
    for m in link_re.finditer(file_text[f]):
        raw = m.group(1).strip()
        if not raw:
            continue
        name = os.path.basename(raw)            # 去路径
        if any(name.endswith(ext) for ext in FILE_EXTS):
            continue                            # 文件链接，非笔记链接，跳过
        if name in existing:
            continue
        unresolved[name] += 1
        broken_by_file[f].append(name)

# ---------- 近似错写修正 ----------
def normalize(t):
    return t.replace("（红队）", "").replace("（蓝队）", "").replace("（红）", "").replace("（蓝）", "").strip()

source_fixes = defaultdict(list)
concept_targets = []
for t, c in unresolved.items():
    n = normalize(t)
    if n != t and n in existing:
        for f in broken_by_file:
            if t in broken_by_file[f]:
                source_fixes[f].append((t, n))
    else:
        concept_targets.append((t, c))

# ---------- 概念页内容生成 ----------
STATUTE_RE = re.compile(r"^《(.+?)》(.*第.+条.*)$")

# 高频法律概念释义词典（仅收录高确信项，缺失则中性枢纽语）
DEF = {
    "医疗告知义务": "医疗机构及医务人员在诊疗活动中向患者说明病情、医疗措施、风险及替代方案，并取得其明确同意的法定义务（《民法典》第1219条）。",
    "医疗损害责任": "医疗机构及其医务人员在诊疗活动中因过错致患者损害，依法应承担的侵权责任（《民法典》第1218条以下）。",
    "知情同意权": "患者对自身病情、诊疗方案、风险及替代方案享有知情并自主决定的权利。",
    "明确同意": "告知后患者以明示方式作出的同意，区别于概括授权或默示同意。",
    "医疗机构执业许可证": "医疗机构合法执业的法定许可凭证，由县级以上卫生行政部门核发。",
    "院内处理机制": "医疗机构内部对医疗纠纷、投诉、不良事件的报告、评估与处置流程。",
    "医院法律风险分类": "按业务环节对医疗机构面临的法律风险（诊疗、管理、合同、侵权等）所作的类型化划分。",
    "医疗纠纷预防和处理": "涵盖医疗质量安全管理、投诉接待、调解、鉴定与诉讼的全流程治理（《医疗纠纷预防和处理条例》）。",
    "未尽告知义务的侵权责任": "医务人员未依法履行告知义务致患者损害时，医疗机构承担的赔偿责任。",
    "医院法律风险管理": "医疗机构识别、评估、防控法律风险的体系化工作。",
    "医疗纠纷分类": "按引发原因将医疗纠纷分为医疗过错、并发症、沟通不足等类型。",
    "医疗纠纷的类型与成因分析": "对医疗纠纷的类型化梳理与成因探究。",
    "医疗纠纷的院内处理与医患沟通": "医疗机构内部纠纷处置与医患沟通实务。",
    "医保合规": "医疗机构及参保主体遵守基本医疗保险基金使用监管规范的合规要求。",
    "医疗废物管理": "医疗废物分类收集、暂存、转运与处置的法定管理要求。",
    "医院法律顾问": "为医疗机构提供法律服务的执业律师或法务岗位。",
    "医院设立双许可制度": "医疗机构设立须同时取得《设置医疗机构批准书》与《医疗机构执业许可证》的制度。",
    "公开募捐": "慈善组织面向社会公众公开募集财产的活动，须依法取得公开募捐资格并备案（《慈善法》第22条）。",
    "募捐成本核算": "慈善组织对募捐活动成本费用进行归集、核算与披露的合规管理。",
    "慈善组织合规": "慈善组织在内部治理、募捐、财产、信息公开等方面遵守法律法规与章程的合规状态。",
    "合同解除": "合同有效成立后，因法定或约定事由使合同效力消灭的制度。",
    "违约责任": "当事人不履行合同义务或履行不符合约定应承担的民事责任（《民法典》第577条）。",
    "举证责任": "当事人对其主张所依据的事实负有提供证据的责任及不利后果的分配。",
    "连带责任": "数个债务人对同一债务均负全部清偿义务，债权人可请求任一债务人清偿。",
    "股权转让协议": "股东将其股权让与他人的合同，涉及优先购买权、工商变更登记等。",
    "股东权利": "股东基于出资享有的资产收益、参与重大决策和选择管理者等权利。",
    "股东知情权": "股东查阅公司章程、股东名册、财务会计报告等资料的法定权利（《公司法》第57条）。",
    "和解协议": "当事人就争议达成的相互让步、终止纠纷的协议。",
    "人民调解": "人民调解委员会主持下，对民间纠纷进行说服疏导、促成和解的活动。",
    "民事诉讼": "人民法院在当事人参与下审理民事纠纷的程序法律制度。",
    "财产损害补偿纠纷": "因财产受损引发的补偿或赔偿争议。",
    "连带责任保证": "保证人与债务人对债务承担连带责任的保证方式。",
}

CLUSTER_KW = [
    ("医疗", ["医疗", "医患", "医院", "医保", "告知", "损害", "纠纷", "卫生", "健康"]),
    ("公司", ["公司", "股东", "股权", "出资", "董事", "监事", "章程"]),
    ("慈善", ["慈善", "募捐", "捐赠", "公益", "基金会"]),
    ("合同", ["合同", "违约", "解除", "协议", "和解", "连带", "保证", "买卖", "租赁"]),
    ("诉讼", ["诉讼", "调解", "民事", "举证", "管辖", "管辖", "仲裁", "执行"]),
    ("刑法", ["刑法", "犯罪", "刑罚", "刑事"]),
    ("劳动", ["劳动", "工伤", "雇佣", "社保"]),
    ("人伤", ["伤残", "人身损害", "误工费", "护理", "营养"]),
]

def cluster_of(term):
    for name, kws in CLUSTER_KW:
        for k in kws:
            if k in term:
                return name
    return "通用"

def find_related(term, top=8):
    """在现有笔记中按关键词匹配关联笔记（排除概念页自身与枢纽页）。"""
    cand = []
    for f, txt in file_text.items():
        base = os.path.splitext(os.path.basename(f))[0]
        if base.startswith("连接枢纽") or "/概念页/" in f.replace(ROOT, ""):
            continue
        if term in txt:
            # 简单权重：标题命中优先
            title_hit = 1 if term in os.path.basename(f) else 0
            cand.append((title_hit, base, f))
    cand.sort(key=lambda x: (-x[0], x[1]))
    return [c[1] for c in cand[:top]]

def find_statute_parent(law_name):
    """法条引用型：找母法文件（如 《公司法》第3条 -> 中华人民共和国公司法）。"""
    for base in existing:
        if law_name in base:
            return base
    return None

def build_page(target, cluster):
    lines = []
    title = target
    tags = ["概念页", f"概念-{cluster}"]
    # frontmatter
    lines.append("---")
    lines.append(f'title: "{title}"')
    lines.append("type: concept")
    lines.append(f'tags: [{" ".join(tags)}]')
    lines.append("generated_by: 断链消解器resolve_broken_links v1.0")
    lines.append("---")
    lines.append("")
    lines.append(f"# {title}")
    lines.append("")
    m = STATUTE_RE.match(target)
    if m:
        law, article = m.group(1), m.group(2)
        parent = find_statute_parent(law)
        lines.append(f"> 本法条引用型概念页。所属法律：**{law}** {article}。")
        if parent:
            lines.append(f"> 母法文件：[[{parent}]]")
        lines.append("")
        lines.append("（条文要旨待补充；本页用于消解知识图谱断链并聚合相关笔记。）")
    else:
        d = DEF.get(target)
        if d:
            lines.append(d)
        else:
            lines.append(f"本页为「{target}」概念枢纽，聚合知识飞轮系统内相关笔记，用于消解双向链接断链。")
        lines.append("")
    # 关联段（稳定前缀，幂等）
    lines.append("## 关联（知识飞轮断链消解 · 概念页自动关联）")
    lines.append("")
    related = find_related(target)
    sibs = []
    # 同簇概念页互链
    for t2, _ in concept_targets:
        if t2 != target and cluster_of(t2) == cluster:
            sibs.append(t2)
    if related:
        lines.append("**相关笔记：**")
        for r in related:
            lines.append(f"- [[{r}]]")
        lines.append("")
    if sibs:
        lines.append(f"**同簇（{cluster}）概念页：**")
        for s in sibs[:12]:
            lines.append(f"- [[{s}]]")
        lines.append("")
    return "\n".join(lines) + "\n"

# ---------- 执行 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="实际写入（默认 dry-run）")
    ap.add_argument("--only-freq", type=int, default=1, help="仅处理出现次数>=N")
    args = ap.parse_args()

    targets = [(t, c) for t, c in concept_targets if c >= args.only_freq]
    print(f"[计划] 断链唯一目标={len(unresolved)} | 近似错写源修正={len(source_fixes)}文件 | 建概念页={len(targets)} (freq>={args.only_freq})")

    if not args.apply:
        print("[dry-run] 以下为将要创建的 TOP 概念页（按出现次数）：")
        for t, c in sorted(targets, key=lambda x: -x[1])[:25]:
            print(f"   {c:3d}  [{cluster_of(t)}] {t}")
        print("[dry-run] 加 --apply 实际写入。")
        return

    # 1) 修正近似错写源引用
    for f, pairs in source_fixes.items():
        txt = file_text[f]
        for old, new in pairs:
            txt = txt.replace(f"[[{old}]]", f"[[{new}]]")
        with open(f, "w", encoding="utf-8") as fo:
            fo.write(txt)
    print(f"[写入] 近似错写源修正：{len(source_fixes)} 个文件")

    # 2) 建概念页
    created = 0
    skipped = 0
    dirty = 0
    DIRTY = re.compile(r"[\[\]#]|（红队）|（蓝队）")  # 含 [[/]]/#/红蓝队 判脏；数字前缀(案件编号)放行
    for t, c in targets:
        if DIRTY.search(t):
            dirty += 1
            continue  # 脏名（含 [[/#/数字前缀/红蓝队）不建页，避免畸形概念页
        path = os.path.join(CONCEPT_DIR, t + ".md")
        if os.path.exists(path):
            skipped += 1
            continue
        content = build_page(t, cluster_of(t))
        with open(path, "w", encoding="utf-8") as fo:
            fo.write(content)
        created += 1
    print(f"[写入] 概念页：新建 {created} | 已存在跳过 {skipped}")

    # 统计写出
    stat = {"created": created, "skipped": skipped, "source_fixed_files": len(source_fixes),
            "targets_total": len(targets), "cluster": {}}
    for t, _ in targets:
        cl = cluster_of(t)
        stat["cluster"][cl] = stat["cluster"].get(cl, 0) + 1
    with open(os.path.join(SCRIPTS, "broken_resolve_lastrun.json"), "w", encoding="utf-8") as fo:
        json.dump(stat, fo, ensure_ascii=False, indent=2)
    print("[完成] 统计已写 broken_resolve_lastrun.json")

if __name__ == "__main__":
    main()
