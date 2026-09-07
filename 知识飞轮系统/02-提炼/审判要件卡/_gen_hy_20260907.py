# -*- coding: utf-8 -*-
"""
第五部分 婚姻家庭纠纷 · 审判要件卡生成器
起始号：R-HY-004（HY 域物理 max=003，2026-09-07 实地取号）
"""
import json, os, re, sys, datetime, importlib.util

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUTDIR = os.path.join(BASE, "06-沉淀/裁判规则库/婚姻家庭")
LIB = json.load(open(os.path.join(BASE, "02-提炼/审判要件卡/贵州类案指南第二卷-婚姻家庭-法条回填库.json"),
                     encoding="utf-8"))
PM = json.load(open(os.path.join(BASE, "02-提炼/审判要件卡/贵州类案指南第二卷-页码映射表.json"),
                    encoding="utf-8"))

def load(mod_name, path):
    spec = importlib.util.spec_from_file_location(mod_name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

D = os.path.join(BASE, "02-提炼/审判要件卡")
CARDS = load("c1", os.path.join(D, "_hy_cards1_20260907.py")).CARDS1 + \
        load("c2", os.path.join(D, "_hy_cards2_20260907.py")).CARDS2

START = 4  # R-HY-004
TODAY = "2026-09-07"
NOW = TODAY + "T09:30"
REVIEW = "2027-03-07"


def yq(s):
    """frontmatter 双引号值转义：英文双引号 → 中文直角引号（坑 1）"""
    out, open_q = [], True
    for ch in str(s):
        if ch == '"':
            out.append('\u300c' if open_q else '\u300d')
            open_q = not open_q
        else:
            out.append(ch)
    return '"' + ''.join(out) + '"'


def bookpage(pdf):
    return PM.get(str(pdf), "?")


def rid(i):
    return "R-HY-%03d" % (START + i - 1)


def fname(c):
    return "%s-%s" % (rid(c["i"]), c["short"])


LAWNAME_MAP = {
    "民法典": "《中华人民共和国民法典》",
    "民事诉讼法": "《中华人民共和国民事诉讼法》",
    "民诉法解释": "《最高人民法院关于适用〈中华人民共和国民事诉讼法〉的解释》",
    "婚姻家庭编解释一": "《最高人民法院关于适用〈中华人民共和国民法典〉婚姻家庭编的解释（一）》",
    "婚姻家庭编解释二": "《最高人民法院关于适用〈中华人民共和国民法典〉婚姻家庭编的解释（二）》",
    "涉彩礼案件规定": "《最高人民法院关于审理涉彩礼纠纷案件适用法律若干问题的规定》",
    "老年人权益保障法": "《中华人民共和国老年人权益保障法》",
    "反家庭暴力法": "《中华人民共和国反家庭暴力法》",
    "诉讼费用交纳办法": "《诉讼费用交纳办法》",
}


def render_laws(laws):
    """渲染法条块：标题行 → 引用块 → 效力/来源标注（校验器按块向下扫描，坑 7）"""
    if not laws:
        return []
    out = ["## 四、法条依据（权威源回填，非凭记忆）", ""]
    seen, missing = set(), []
    for law, art in laws:
        key = "%s|%s" % (law, art)
        if key in seen:
            continue
        seen.add(key)
        v = LIB.get(key)
        if not v:
            missing.append(key)
            continue
        out.append("**%s%s**" % (LAWNAME_MAP.get(law, law), art))
        out.append("")
        out.append("> %s" % v["text"].replace("\n", " ").strip())
        out.append("")
        out.append("*效力状态：%s。%s*" % (v["timeliness"], v["source"]))
        out.append("")
    if missing:
        print("  !! 法条缺失:", missing)
    return out


def build(c, cardmap):
    r = rid(c["i"])
    pdf = c["pdf"]
    bp = bookpage(pdf)
    if '案例' in c["short"]:
        section = "第四章 附录·%s" % c["short"].replace("案例", "案例")
    else:
        section = "第三章 审理思路"
    src = "《贵州法院类案审判要件指南（第二卷）》第五部分 婚姻家庭纠纷案件审判要件指南 %s（PDF页%s（书页%s））" % (
        section, pdf, bp)
    related = [cardmap[j] for j in c.get("related", []) if j in cardmap]

    L = []
    L.append("---")
    L.append("title: %s" % yq(c["title"] + "（审判要件卡·婚姻家庭）"))
    L.append("rule_id: %s" % r)
    L.append("card_type: 审判要件卡")
    L.append("source: %s" % yq(src))
    L.append("type: 婚姻家庭·审判要件卡")
    L.append("created: %s" % NOW)
    L.append("date: %s" % TODAY)
    L.append("created_month: %s" % TODAY[:7])
    L.append("updated: %s" % NOW)
    L.append("review_date: %s" % REVIEW)
    L.append("review_step: %s" % c["review_step"])
    L.append("geo_scope: 贵州省（贵州高院裁判尺度统一指引，跨省援引须核当地口径）")
    L.append("yuandian_source_pending: false")
    L.append("library: 小强律师数字分身系统")
    L.append("aliases: [%s]" % r)
    L.append("elements:")
    for eid, name, desc in c["elements"]:
        L.append("  - id: %s" % eid)
        L.append("    name: %s" % yq(name))
        L.append("    desc: %s" % yq(desc))
    L.append("ruling:")
    L.append("  support: %s" % yq(c["support"]))
    L.append("  reject: %s" % yq(c["reject"]))
    L.append("burden_of_proof: %s" % yq(c["burden"]))
    L.append("negative_sample: true")
    L.append("negative_note: %s" % yq(c["negative"]))
    if related:
        L.append("related_links:")
        for x in related:
            L.append("  - %s" % x)
    else:
        L.append("related_links: []")
    L.append("tags:")
    L.append("  - 审判要件卡")
    L.append("  - 婚姻家庭")
    L.append("  - 贵州类案指南第二卷")
    L.append("---")
    L.append("")
    L.append("# %s" % c["title"])
    L.append("")
    L.append("> **铁律 R2**：本卡输出的是**候选推理**，不是自动裁判。法官智能体须给出【候选·待人工确认】结论。")
    L.append("> **地域效力**：%s" % "贵州省（贵州高院裁判尺度统一指引，跨省援引须核当地口径）")
    L.append("")
    L.append("## 一、裁判规则（正向·该怎么判）")
    L.append("")
    L.append(c["title"].split("：")[-1] if "：" in c["title"] else c["title"])
    L.append("")
    L.append("## 二、审查要点（审理思路）")
    L.append("")
    for eid, name, desc in c["elements"]:
        L.append("- **%s（%s）**：%s" % (name, eid, desc))
    L.append("")
    L.append("## 三、构成要件与举证")
    L.append("")
    L.append("- **支持（予以认定/准许）**：%s" % c["support"])
    L.append("- **不支持（驳回/不予受理）**：%s" % c["reject"])
    L.append("- **举证责任**：%s" % c["burden"])
    L.append("")
    L.extend(render_laws(c["laws"]))
    L.append("## 五、抗辩与但书")
    L.append("")
    L.append("- %s" % c["reject"])
    L.append("- 主张适用本规则须先行满足审查要点全部要件，缺一则落入不予支持口径。")
    L.append("")
    L.append("## 六、翻车标本（负向拦截·HIR）")
    L.append("")
    L.append("%s" % c["negative"])
    L.append("")
    L.append("## 七、来源与地域效力")
    L.append("")
    L.append("- 来源：%s" % src)
    L.append("- 效力：贵州高院类案审判要件指南，属省级裁判尺度统一指引，非司法解释；援引时须并列引用上位法。")
    L.append("- 卡内法条正文均经权威源核填（本地法律法规库 + 最高法院公报/中国政府网），标注现行有效。")
    L.append("")
    L.append("## 八、关联（知识飞轮连接层）")
    L.append("")
    if related:
        for x in related:
            L.append("- [[%s]]" % x)
    else:
        L.append("- 待补（本批首轮未登记互链）")
    L.append("")
    L.append("- 总索引：[[审判要件卡-卡型定义与总索引]]")
    L.append("")
    return "\n".join(L)


def main():
    apply = "--apply" in sys.argv
    cardmap = {c["i"]: fname(c) for c in CARDS}
    # dry-run 查重（六-B：批量写入先 dry-run）
    exist = set(os.listdir(OUTDIR))
    conflict = [fname(c) + ".md" for c in CARDS if fname(c) + ".md" in exist]
    print("计划建卡：%d 张（%s ~ %s）" % (len(CARDS), rid(1), rid(len(CARDS))))
    print("目标目录：%s" % OUTDIR)
    print("文件名冲突数：%d %s" % (len(conflict), conflict[:5]))
    if not apply:
        print("\n[dry-run] 未写入。加 --apply 落盘。")
        return
    if conflict:
        print("存在冲突，已中止写入（安全铁律）。")
        return
    n = 0
    for c in CARDS:
        p = os.path.join(OUTDIR, fname(c) + ".md")
        open(p, "w", encoding="utf-8").write(build(c, cardmap))
        n += 1
    print("已写入 %d 张。" % n)


if __name__ == "__main__":
    main()
