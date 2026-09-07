# -*- coding: utf-8 -*-
"""渲染器：把 CARDS 渲染为 36 张审判要件卡（R-LD-010~045）"""
import os, sys, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _gen_ld_20260906 as G
import _ld_cards_p2_20260906 as P2

P2.extend(G.add)
CARDS = G.C
DATE = G.DATE
REVIEW = G.REVIEW
OUTDIR = G.OUTDIR
print("卡片总数", len(CARDS))

START = 10
SLUG2F = {}
for i, c in enumerate(CARDS):
    SLUG2F[c["slug"]] = f"R-LD-{START+i:03d}-{c['slug']}"

# 校验 related 引用
missing = []
for c in CARDS:
    for r in c.get("related", []):
        if r not in SLUG2F:
            missing.append((c["slug"], r))
if missing:
    print("!! related 未解析：", missing); sys.exit(1)


def norm_elements(raw):
    flat = []
    for it in raw:
        if isinstance(it, (tuple, list)):
            flat.extend(list(it))
        else:
            flat.append(it)
    out = []
    i = 0
    while i < len(flat):
        if isinstance(flat[i], str) and len(flat[i]) <= 3 and flat[i].startswith("C") and i + 2 <= len(flat) - 1:
            out.append((flat[i], flat[i + 1], flat[i + 2])); i += 3
        elif isinstance(flat[i], str) and len(flat[i]) <= 3 and flat[i].startswith("C") and i + 1 < len(flat):
            out.append((flat[i], flat[i + 1], "")); i += 2
        else:
            i += 1
    # 生成 id
    res = []
    for k, (_, name, desc) in enumerate(out, 1):
        res.append((f"C{k}", name, desc))
    return res


def render(i, c):
    rid = f"R-LD-{START+i:03d}"
    fn = SLUG2F[c["slug"]]
    p1, p2 = c["srcp"]
    s = G.src(p1, p2)
    els = norm_elements(c["elements"])
    body = c["body"]
    tags = ["LD", "新就业形态", "劳动争议", "审判要件卡", "劳动关系认定" if "从属性" in c["title"] or "劳动关系" in c["title"] else "裁判规则"]

    fm = []
    fm.append(f"title: {G.yq('审判要件卡·新就业形态劳动争议：'+c['title'])}")
    fm.append(f"rule_id: {rid}")
    fm.append("card_type: 审判要件卡")
    fm.append(f"source: {G.yq(s)}")
    fm.append("type: 劳动人事·审判要件卡")
    fm.append(f"created: {DATE}")
    fm.append(f"date: {DATE}")
    fm.append("created_month: 2026-09")
    fm.append(f"review_date: {REVIEW}")
    fm.append(f"updated: {DATE}")
    fm.append("geo_scope: 贵州省（贵州高院裁判尺度统一指引，跨省援引须核当地口径）")
    fm.append("yuandian_source_pending: false")
    fm.append("library: 小强律师数字分身系统")
    fm.append(f"aliases: [{rid}]")
    fm.append(f"review_step: {G.yq(c['step'])}")
    fm.append("elements:")
    for eid, name, desc in els:
        fm.append(f"  - id: {eid}")
        fm.append(f"    name: {G.yq(name)}")
        fm.append(f"    desc: {G.yq(desc)}")
    fm.append("ruling:")
    fm.append(f"  support: {G.yq(c['support'])}")
    fm.append(f"  reject: {G.yq(c['reject'])}")
    fm.append(f"burden_of_proof: {G.yq(c['burden'])}")
    fm.append("negative_sample: true")
    fm.append(f"negative_note: {G.yq(c['neg'])}")
    fm.append("related_links:")
    for r in c.get("related", []):
        fm.append(f"  - {G.yq(SLUG2F[r])}")
    fm.append(f"  - {G.yq('审判要件卡-卡型定义与总索引')}")
    fm.append("tags:")
    for t in tags:
        fm.append(f"  - {t}")
    fm_txt = "---\n" + "\n".join(fm) + "\n---\n"

    L = []
    L.append(fmt := f"# 审判要件卡·新就业形态劳动争议：{c['title']}\n")
    L.append(f"> **rule_id**：{rid}　**card_type**：审判要件卡　**领域**：劳动人事（新就业形态）")
    L.append(f"> **来源**：{s}")
    L.append(f"> **审理环节**：{c['step']}　**geo_scope**：贵州省（贵州高院裁判尺度统一指引，跨省援引须核当地口径）")
    L.append("> ⚠️ 本卡输出**候选推理（【候选·待人工确认】）**，非自动裁判。（铁律 R2：审判要件卡输出候选推理，非自动裁判）\n")
    L.append("## 一、裁判规则（正向·该怎么判）")
    L.append(body["rule"].strip() + "\n")
    L.append("## 二、审查要点（审理思路）")
    for eid, name, desc in els:
        L.append(f"- **{eid}　{name}**：{desc}")
    L.append("")
    L.append(body["point"].strip() + "\n")
    L.append("## 三、构成要件与举证")
    L.append(body["burden2"].strip() + "\n")
    L.append("## 四、法条依据（权威源回填，非凭记忆）")
    L.append(G.lawblock(c["laws"]) + "\n")
    L.append("## 五、抗辩与但书")
    L.append(body["defense"].strip() + "\n")
    L.append("## 六、翻车标本（负向拦截·HIR）")
    L.append(body["neg2"].strip() + "\n")
    L.append("## 七、来源与地域效力")
    L.append(f"- **来源**：{s}")
    L.append(f"- **上位依据**：《劳动法》《劳动合同法》《劳动争议调解仲裁法》《工伤保险条例》、劳社部发〔2005〕12号、人社部发〔2021〕56号、法释〔2020〕26号、《新就业形态人员职业伤害保障办法（试行）》（人社部发〔2025〕24号附件）、法〔2025〕226号。")
    L.append("- **地域效力**：贵州省（贵州高院裁判尺度统一指引，跨省援引须核当地口径）。")
    L.append(f"- **复核日期**：{REVIEW}　**建卡日期**：{DATE}\n")
    L.append("## 八、关联（知识飞轮连接层）")
    for r in c.get("related", []):
        L.append(f"- [[{SLUG2F[r]}]]")
    L.append(f"- [[审判要件卡-卡型定义与总索引]]")
    L.append("")
    return fn, fm_txt + "\n".join(L)


os.makedirs(OUTDIR, exist_ok=True)
# dry-run：检查文件名冲突
conf = []
for i, c in enumerate(CARDS):
    fn = SLUG2F[c["slug"]]
    fp = os.path.join(OUTDIR, fn + ".md")
    if os.path.exists(fp):
        conf.append(fp)
if conf:
    print("!! dry-run 冲突（拒绝写入）：")
    for f in conf: print("   ", f)
    sys.exit(1)
print("dry-run 冲突数 = 0，开始写入")

n_el = 0
n_law = 0
for i, c in enumerate(CARDS):
    fn, txt = render(i, c)
    fp = os.path.join(OUTDIR, fn + ".md")
    open(fp, "w", encoding="utf-8").write(txt)
    n_el += len(norm_elements(c["elements"]))
    n_law += len(c["laws"])

print(f"写入完成：{len(CARDS)} 张 → {OUTDIR}")
print(f"号段：R-LD-{START:03d} ~ R-LD-{START+len(CARDS)-1:03d}")
print(f"要件总数：{n_el}　法条引用条次：{n_law}")
