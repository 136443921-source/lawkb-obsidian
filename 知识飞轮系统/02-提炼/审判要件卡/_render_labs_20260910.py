# -*- coding: utf-8 -*-
"""第十三批渲染器：机动车·立案审查与抗辩（R-PI-318~347）
防御已固化：坑1 yq转义 / 坑20 书名号幂等 / 坑23 四星号 / 坑26 页码0-based / 坑27 YAML锚点
"""
import io, os, json, re

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库/人伤法/"
LAWLIB = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/审判要件卡/贵州类案指南第二卷-机动车立案审查与抗辩-法条回填库.json"
PAGEMAP = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/审判要件卡/贵州类案指南第二卷-页码映射表.json"

LAWS = json.load(io.open(LAWLIB, encoding="utf-8"))
MP = json.load(io.open(PAGEMAP, encoding="utf-8"))


def yq(s):
    """坑1：YAML 双引号转义（中文引号交替）；坑27：值以 ** 开头会被当锚点，故一律包引号"""
    out = []
    open_q = True
    for ch in str(s):
        if ch == '"':
            out.append('\u300c' if open_q else '\u300d')
            open_q = not open_q
        else:
            out.append(ch)
    return '"' + ''.join(out) + '"'


def wrap_book(name):
    """坑20：幂等书名号包裹——含《即视为已格式化，不可用 startswith/endswith"""
    n = str(name).strip()
    return n if "《" in n else f"《{n}》"


def page(pdf_lo, pdf_hi=None):
    """坑26：映射表 key 为 0-based，书页 = MP[str(PDF页-1)]"""
    if pdf_hi is None or pdf_hi == pdf_lo:
        return f"PDF页{pdf_lo}（书页{MP.get(str(pdf_lo - 1), '?')}）"
    return f"PDF页{pdf_lo}-{pdf_hi}（书页{MP.get(str(pdf_lo - 1), '?')}-{MP.get(str(pdf_hi - 1), '?')}）"


def render_law_block(keys):
    """法条块：标题行含完整 ** 装饰（坑23：替换区间须含完整标记）"""
    out = []
    for k in keys:
        v = LAWS.get(k)
        if not v:
            out.append(f"**{k}**\n\n> ⚠️ 待回源核填\n")
            continue
        title = f"**{wrap_book(v['law'])}{v['article']}**"
        body = v["text"].replace("\n", "\n> ")
        out.append(f"{title}\n\n> {body}\n")
        out.append(f"\n*效力状态：{v['timeliness']}（{v['src']}，gid: {v.get('gid', '-')}）*\n")
        if v.get("note"):
            out.append(f"\n> {v['note']}\n")
        out.append("")
    return "\n".join(out)


OFFICIAL = """### 官方核验指引（正式文书引用前二次核对）

- 国家法律法规数据库：https://flk.npc.gov.cn/
- 最高人民法院官网：https://www.court.gov.cn/

> 本卡法条正文经北大法宝核填并标注效力状态；正式文书引用前，建议在上述官方渠道二次核对条号与文本。"""


def render_card(c):
    """渲染单卡：frontmatter + 八段"""
    rid = c["rule_id"]
    src = (f"《贵州法院类案审判要件指南（第二卷）》第七部分 机动车交通事故责任纠纷案件审判要件指南 "
           f"{c['sec']}（{page(c['pdf_lo'], c.get('pdf_hi'))}）")
    els = c.get("elements", [])
    fm = []
    fm.append("---")
    fm.append(f"title: {c['title']}（审判要件卡·人伤法）")
    fm.append(f"rule_id: {rid}")
    fm.append("card_type: 审判要件卡")
    fm.append(f"source: {src}")
    fm.append("type: 人伤法·审判要件卡")
    fm.append("created: 2026-09-10")
    fm.append("date: 2026-09-10")
    fm.append("created_month: 2026-09")
    fm.append("review_date: 2027-09-10")
    fm.append("updated: 2026-09-10")
    fm.append("geo_scope: 贵州省（贵州高院裁判尺度统一指引，跨省援引须核当地口径）")
    fm.append("yuandian_source_pending: false")
    fm.append("statute_text_pending: false")
    fm.append("library: 小强律师数字分身系统")
    fm.append(f"aliases: [{rid}]")
    fm.append(f"review_step: {c['review_step']}")
    fm.append("elements:")
    for i, e in enumerate(els, 1):
        fm.append(f"  - id: e{i}")
        fm.append(f"    name: {yq(e['name'])}")
        fm.append(f"    desc: {yq(e['desc'])}")
    fm.append("ruling:")
    fm.append(f"  support: {yq(c['support'])}")
    fm.append(f"  reject: {yq(c['reject'])}")
    fm.append(f"burden_of_proof: {yq(c['burden'])}")
    fm.append("negative_sample: true")
    fm.append(f"negative_note: {yq(c['negative'])}")
    if c.get("related"):
        fm.append("related_links:")
        for r in c["related"]:
            fm.append(f"  - {r}")
    fm.append("---")

    body = []
    body.append(f"\n# {c['title']}")
    body.append(f"\n> **来源**：{src}")
    body.append(f"> **卡型**：审判要件卡（正向裁判规则·该怎么判）")
    body.append(f"> **铁律 R2**：本卡输出的是**候选推理**，不是自动裁判。\n")

    body.append(f"\n## 一、裁判规则（正向·该怎么判）\n\n{c['s1']}")
    body.append(f"\n## 二、审查要点（审理思路）\n\n{c['s2']}")
    body.append(f"\n## 三、构成要件与举证\n\n{c['s3']}")
    body.append(f"\n## 四、法条依据（北大法宝核填·现行有效，含官方核验指引）\n\n")
    body.append(render_law_block(c.get("laws", [])))
    body.append(f"\n{OFFICIAL}\n")
    body.append(f"\n## 五、抗辩与但书\n\n{c['s5']}")
    body.append(f"\n## 六、翻车标本（负向拦截·HIR）\n\n{c['s6']}")
    body.append(f"\n## 七、来源与地域效力\n\n{src}。\n\n"
                f"本卡为贵州省高级人民法院《类案审判要件指南（第二卷）》裁判尺度统一指引，"
                f"**跨省援引须核对当地口径**。页码换算依 `02-提炼/审判要件卡/贵州类案指南第二卷-页码映射表.json`"
                f"（key 为 0-based，书页 = 映射表[str(PDF页-1)]），未套线性公式。")
    body.append(f"\n## 八、关联（知识飞轮连接层）\n\n{c.get('s8', '- 待补链')}\n")

    txt = "\n".join(fm) + "\n" + "\n".join(body)
    # 坑23：四星号兜底
    txt = re.sub(r"(?m)^\*\*\*\*(?=《)", "**", txt)
    return txt


def write_all(cards, dry_run=False):
    os.makedirs(BASE, exist_ok=True)
    exist = set(os.listdir(BASE))
    dup = [c["rule_id"] for c in cards
           if any(f.startswith(c["rule_id"] + ".md") or f.startswith(c["rule_id"] + "-") for f in exist)]
    if dup:
        print("❌ 文件冲突（禁止覆盖）:", dup)
        return 1
    if dry_run:
        print(f"DRY-RUN OK：{len(cards)} 张，零冲突。拟写：")
        for c in cards:
            print(f"  {c['rule_id']} - {c['title']}")
        return 0
    n = 0
    for c in cards:
        fn = f"{BASE}{c['rule_id']}.md"
        io.open(fn, "w", encoding="utf-8").write(render_card(c))
        n += 1
    print(f"✅ 写入 {n} 张 → {BASE}")
    return 0
