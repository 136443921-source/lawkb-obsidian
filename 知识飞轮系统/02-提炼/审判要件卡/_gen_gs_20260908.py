# -*- coding: utf-8 -*-
"""破产案件批·卡片渲染器（2026-09-08）
八段正文 + frontmatter；法条正文一律从回填库取，绝不凭记忆。
"""
import json, os, sys, datetime, importlib.util

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT = f"{BASE}/06-沉淀/裁判规则库/公司法"
LAWJSON = f"{BASE}/02-提炼/审判要件卡/贵州类案指南第二卷-破产案件-法条回填库.json"
D = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/审判要件卡"

LAWS = json.load(open(LAWJSON, encoding="utf-8"))

def load(mod_file, var="CARDS"):
    spec = importlib.util.spec_from_file_location("m_" + mod_file[:-3], f"{D}/{mod_file}")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return getattr(m, var)

ALL = []
for f in ["_gs_cards1_20260908.py", "_gs_cards2_20260908.py",
          "_gs_cards3_20260908.py", "_gs_cards4_20260908.py"]:
    ALL += load(f)

# 建号→标题映射，供 related_links 用真实文件名基名（坑 9）
NAMEMAP = {}
for c in ALL:
    NAMEMAP[c["no"]] = f"R-GS-{c['no']}-{c['title']}"

def yq(s):
    """坑1: frontmatter 双引号转中文引号，避免破坏 YAML"""
    out = []; open_q = True
    for ch in str(s):
        if ch == '"':
            out.append('\u300c' if open_q else '\u300d'); open_q = not open_q
        else:
            out.append(ch)
    return '"' + ''.join(out) + '"'

TODAY = "2026-09-08"
def plus6m(d):
    y, m, dd = map(int, d.split("-"))
    m += 6
    if m > 12: m -= 12; y += 1
    return f"{y}-{m:02d}-{dd:02d}"

BOOK = "《贵州法院类案审判要件指南（第二卷）》第九部分 破产案件审判要件指南"

def wrap_book(name):
    """书名号包裹（幂等）—— 2026-09-08 修复双书名号《《X》》
    病根：回填库 law 字段本身可能已带书名号（如「《中华人民共和国环境保护法》」），
          硬编码 f"《{law}》" 会渲染成「《《…》》」。全库 12 处受害（5 张 GS + 5 张 CF）。
    修法：先判首尾是否已是书名号，是则原样返回。
    """
    # 注意：不能用 startswith/endswith 判断 —— R-GS-020 的 law 字段是
    # 「《…非法集资…意见》第九条第四款」，书名号包裹的是法律名而非整个字段，
    # endswith("》") 为假 → 又被套一层。改为「含『《』即视为已格式化」。
    n = str(name).strip()
    return n if "《" in n else f"《{n}》"


def render_laws(laws):
    """第四段：法条依据（元典核填·现行有效，含官方核验指引）"""
    if not laws:
        return "（本卡为程序性裁判规则，无对应法条正文）\n"
    lines = []
    miss = []
    for k in laws:
        v = LAWS.get(k)
        if not v:
            miss.append(k); continue
        lines.append(f"**{wrap_book(v['law'])}{v['article']}**")
        lines.append("")
        for ln in v["text"].split("\n"):
            lines.append(f"> {ln}")
        note = f"，{v['note']}" if v.get("note") else ""
        lines.append("")
        lines.append(f"*效力状态：{v['timeliness']}（{v['source']}）{note}*")
        lines.append("")
    if miss:
        lines.append(f"<!-- 回填库缺失（E9 校验项）：{'; '.join(miss)} -->")
        lines.append("")
    lines.append("### 官方核验指引（正式文书引用前二次核对）")
    lines.append("")
    lines.append("- 国家法律法规数据库：https://flk.npc.gov.cn/")
    lines.append("- 最高人民法院官网：https://www.court.gov.cn/")
    lines.append("- 核验要点：法规全称与文号、条号、现行有效性、施行日期；本卡法条正文据权威源核填，引用前请以上述官方渠道二次核对。")
    lines.append("")
    return "\n".join(lines)

def render(c):
    no, t = c["no"], c["title"]
    rid = f"R-GS-{no}"
    fname = f"{rid}-{t}.md"
    sup, rej, bp, neg = c["sup"], c["rej"], c["bp"], c["neg"]
    step = c["step"]
    src = c["src"]

    fm = []
    fm.append("---")
    fm.append(f"title: {t}（审判要件卡·破产）")
    fm.append(f"rule_id: {rid}")
    fm.append("card_type: 审判要件卡")
    fm.append(f"source: {BOOK}（{src}）")
    fm.append("type: 公司治理·审判要件卡")
    fm.append(f"created: {TODAY}")
    fm.append(f"date: {TODAY}")
    fm.append("created_month: 2026-09")
    fm.append(f"review_date: {plus6m(TODAY)}")
    fm.append(f"updated: {TODAY}T00:00")
    fm.append("geo_scope: 贵州省（贵州高院裁判尺度统一指引，跨省援引须核当地口径）")
    fm.append("yuandian_source_pending: false")
    fm.append("library: 小强律师数字分身系统")
    fm.append(f"aliases: [{rid}]")
    fm.append(f"review_step: {yq(step)}")
    fm.append("elements:")
    for eid, en, ed in c["el"]:
        fm.append(f"  - id: {eid}")
        fm.append(f"    name: {yq(en)}")
        fm.append(f"    desc: {yq(ed)}")
    fm.append("ruling:")
    fm.append(f"  support: {yq(sup)}")
    fm.append(f"  reject: {yq(rej)}")
    fm.append(f"burden_of_proof: {yq(bp)}")
    fm.append("negative_sample: true")
    fm.append(f"negative_note: {yq(neg)}")
    fm.append("related_links:")
    for r in c["rel"]:
        fm.append(f"  - {yq(r)}")
    fm.append("---")
    fm.append("")

    b = []
    b.append(f"# {rid} · {t}")
    b.append("")
    b.append("## 一、裁判规则（正向·该怎么判）")
    b.append("")
    b.append(c["rule"])
    b.append("")
    b.append("## 二、审查要点（审理思路）")
    b.append("")
    for p in c["pts"]:
        b.append(f"- {p}")
    b.append("")
    b.append("## 三、构成要件与举证")
    b.append("")
    b.append("| 要件编号 | 要件名称 | 要件内容 |")
    b.append("|---|---|---|")
    for eid, en, ed in c["el"]:
        b.append(f"| {eid} | {en} | {ed} |")
    b.append("")
    b.append(f"**举证责任分配**：{bp}")
    b.append("")
    b.append("## 四、法条依据（权威源核填·现行有效，含官方核验指引）")
    b.append("")
    b.append(render_laws(c["laws"]))
    b.append("## 五、抗辩与但书")
    b.append("")
    b.append(f"**支持的条件与结论**：{sup}")
    b.append("")
    b.append(f"**不予支持／驳回的条件与结论**：{rej}")
    b.append("")
    b.append("## 六、翻车标本（负向拦截·HIR）")
    b.append("")
    b.append(neg)
    b.append("")
    b.append("## 七、来源与地域效力")
    b.append("")
    b.append(f"- 母本：{BOOK}（{src}）")
    b.append("- 地域效力：贵州省。本卡为贵州高院裁判尺度统一指引，跨省援引须核对当地口径。")
    b.append("- 铁律 R2：本卡输出的是**候选推理**，不是自动裁判，结论须经人工确认。")
    b.append("")
    b.append("## 八、关联（知识飞轮连接层）")
    b.append("")
    if c["rel"]:
        for r in c["rel"]:
            b.append(f"- [[{r}]]")
    else:
        b.append("- [[审判要件卡-卡型定义与总索引]]")
    b.append("")

    return fname, "\n".join(fm) + "\n".join(b)

if __name__ == "__main__":
    dry = "--dry" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    exist = set(os.listdir(OUT))
    conflict = []
    for c in ALL:
        fn, _ = render(c)
        if fn in exist:
            conflict.append(fn)
    print(f"卡片总数: {len(ALL)}")
    print(f"号段: R-GS-{ALL[0]['no']} ~ R-GS-{ALL[-1]['no']}")
    print(f"文件名冲突: {len(conflict)}")
    for x in conflict[:10]:
        print("   冲突:", x)
    # 号段连续性
    nums = sorted(int(c["no"]) for c in ALL)
    gaps = [n for n in range(nums[0], nums[-1] + 1) if n not in nums]
    dup = [n for n in set(nums) if nums.count(n) > 1]
    print(f"号段空洞: {gaps if gaps else '无'}")
    print(f"重复号: {dup if dup else '无'}")
    # 法条缺失检查（E9）
    missall = []
    for c in ALL:
        for k in c["laws"]:
            if k not in LAWS:
                missall.append((c["no"], k))
    print(f"法条库缺失引用: {len(missall)}")
    for n, k in missall[:15]:
        print(f"   R-GS-{n}: {k}")
    # 关联链接死链自查（坑 9）
    valid = set(NAMEMAP.values())
    dead = []
    for c in ALL:
        for r in c["rel"]:
            if r not in valid:
                dead.append((c["no"], r))
    print(f"关联链接疑似死链: {len(dead)}")
    for n, r in dead[:15]:
        print(f"   R-GS-{n} -> {r}")
    if dry:
        print("\n[dry-run] 未写入。")
        sys.exit(0)
    n = 0
    for c in ALL:
        fn, body = render(c)
        with open(f"{OUT}/{fn}", "w", encoding="utf-8") as f:
            f.write(body)
        n += 1
    print(f"\n已写入 {n} 张卡 -> {OUT}")
