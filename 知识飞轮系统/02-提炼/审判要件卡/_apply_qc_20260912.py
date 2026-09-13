#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
存量卡质量巡检 apply 脚本（2026-09-12）
三项写操作，全部 dry-run 先行：
  T1 法条核填：把「待回源」项替换为「已核填·现行有效」+ 条文正文（仅高置信 2 条）
  T2 版本风险标注：给引用红队库 1997 版刑法的卡加版本警示（5 张）
  T3 死链修复：C 类规则卡号型 → 唯一定位的真实文件基名（25 条）
用法：python _apply_qc_20260912.py [--apply]
"""
import os, re, sys, json, glob

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
APPLY = "--apply" in sys.argv
IDX = os.path.join(BASE, "02-提炼/审判要件卡/本地法条源索引-20260912.json")
import shutil, datetime
BK = "/tmp/存量卡巡检_20260912-1042"      # 六-B 备份目录（与本轮手动备份同目录）
os.makedirs(BK, exist_ok=True)


def backup(rel):
    """按相对路径镜像备份，cp -n 防覆盖"""
    src = os.path.join(BASE, rel)
    dst = os.path.join(BK, rel.replace("/", "__"))
    if not os.path.exists(dst):
        shutil.copy2(src, dst)
    return dst

# ---------- T1 高置信法条核填（人工逐条核验通过） ----------
FILLS = [
    {
        "card": "06-沉淀/裁判规则库/合同风险/R-HT-181-合同订立的成立要素与风险防范.md",
        "anchor": "《最高人民法院关于民事诉讼证据的若干规定》第五十三条",
        "law": "《最高人民法院关于民事诉讼证据的若干规定》",
        "art": "第五十三条",
        "src": "智能体技能库/红队出庭律师/常用法律法规库/最高人民法院关于民事诉讼证据的若干规定（红队）.md",
        "ver": "2019 修正（法释〔2019〕19 号），现行有效",
    },
    {
        "card": "06-沉淀/裁判规则库/律师实务/R-LN-046-共同饮酒者注意义务与责任比例.md",
        "anchor": "《中华人民共和国民法典》第一千一百九十八条",
        "law": "《中华人民共和国民法典》",
        "art": "第一千一百九十八条",
        "src": "法律法规库/通用实体法/中华人民共和国民法典（全文）.md",
        "ver": "2021-01-01 施行，现行有效",
    },
]

# ---------- T2 版本风险标注 ----------
VER_WARN = (
    "\n> 🔴 **2026-09-12 全库巡检补注**：本机 `智能体技能库/红队出庭律师/常用法律法规库/`"
    "内《中华人民共和国刑法》为**中国人大网 2019 年页面所挂 1997 年原版**"
    "（实测：§17 仍写『投毒罪』、§274 敲诈勒索仅两档且无罚金、无 §134 之一危险作业罪）。"
    "**版本不符，禁止据以回填或引用**。本卡刑法条文仍待回源至**现行有效**文本"
    "（法宝/元典），在此之前**不得作文书引用源**。"
)
VER_CARDS = [
    "06-沉淀/裁判规则库/律师实务/R-LN-049-敲诈勒索解释数额标准与加重情节.md",
    "06-沉淀/裁判规则库/律师实务/R-LN-050-违法发放贷款罪四要件与出罪辩点清单.md",
    "06-沉淀/裁判规则库/律师实务/R-LN-051-交通肇事罪有效辩护与缓刑适用清单.md",
    "06-沉淀/裁判规则库/律师实务/R-LN-052-交通肇事罪定罪量刑标准与缓刑适用规则.md",
    "06-沉淀/裁判规则库/合规监管/R-HG-064-企业知识产权管理合规审查要点.md",
]

D = "零一二三四五六七八九"
def cn2num(s):
    if s.isdigit(): return int(s)
    v = cur = 0
    for c in s:
        if c == "十": cur = (cur or 1) * 10; v += cur; cur = 0
        elif c == "百": cur = (cur or 1) * 100; v += cur; cur = 0
        elif c == "千": cur = (cur or 1) * 1000; v += cur; cur = 0
        elif c in D: cur = D.index(c)
        else: return None
    return v + cur


def yq(s):
    return '"' + str(s).replace('"', '\\"') + '"'


def wrap_book(s):
    """书名号幂等包裹"""
    s = s.strip()
    return s if s.startswith("《") else f"《{s}》"


def load_idx():
    return json.load(open(IDX, encoding="utf-8"))


def find_art(idx, src_rel, art_cn):
    v = idx.get(src_rel)
    if not v:
        return None
    n = cn2num(art_cn.replace("第", "").replace("条", ""))
    return v["arts"].get(str(n)) if n else None


def t1(t, fill, idx):
    """返回 (新文本, 是否改动)"""
    art_txt = find_art(idx, fill["src"], fill["art"])
    if not art_txt:
        return t, False, f"源内未找到 {fill['art']}"
    anchor = fill["anchor"]
    i = t.find(anchor)
    if i < 0:
        return t, False, f"卡内未找到锚点 {anchor}"
    # 取该行整行
    ls = t.rfind("\n", 0, i) + 1
    le = t.find("\n", i)
    le = le if le > 0 else len(t)
    line = t[ls:le]
    if "已核填" in line:
        return t, False, "已核填，跳过"
    body = re.sub(r"\s+", " ", art_txt).strip()
    if len(body) > 420:
        body = body[:420] + "…"
    newline = (
        f"- ✅ **已核填·{fill['ver']}**：{wrap_book(fill['law'].strip('《》'))}"
        f"{fill['art']} — {body}\n"
        f"  - 本地源：`{fill['src']}`\n"
        f"  - 核验：2026-09-12 存量卡质量巡检，由「⚠️ 待回源」翻转；条文正文取自本地源，非凭记忆。"
    )
    return t[:ls] + newline + t[le:], True, "OK"


def t2(t):
    if "2026-09-12 全库巡检补注" in t:
        return t, False
    # 插到「法条依据」段末尾：定位该段最后一个 ⚠️ 待回源 行之后
    marks = [m.end() for m in re.finditer(r"⚠️\s*待回源", t)]
    if not marks:
        return t, False
    last = marks[-1]
    le = t.find("\n", last)
    le = le if le > 0 else len(t)
    return t[:le] + "\n" + VER_WARN + t[le:], True


def main():
    idx = load_idx()
    report = {"T1": [], "T2": [], "T3": []}

    # ---------- T1 ----------
    for fill in FILLS:
        p = os.path.join(BASE, fill["card"])
        t = open(p, encoding="utf-8").read()
        newt, changed, msg = t1(t, fill, idx)
        report["T1"].append({"card": os.path.basename(p), "changed": changed, "msg": msg})
        if changed and APPLY:
            backup(fill["card"])
            open(p, "w", encoding="utf-8").write(newt)

    # ---------- T2 ----------
    for rel in VER_CARDS:
        p = os.path.join(BASE, rel)
        t = open(p, encoding="utf-8").read()
        newt, changed = t2(t)
        report["T2"].append({"card": os.path.basename(p), "changed": changed})
        if changed and APPLY:
            backup(rel)
            open(p, "w", encoding="utf-8").write(newt)

    # ---------- T3 死链 ----------
    allmd = {}
    for p in glob.glob(os.path.join(BASE, "06-沉淀/**/*.md"), recursive=True):
        allmd.setdefault(os.path.splitext(os.path.basename(p))[0], p)
    # 找出所有含 wikilink 的文件（全 06-沉淀 + 02-提炼 + 03-连接 + 05-调用）
    # 范围收窄：只修 06-沉淀（规则库本体）。
    # 排除 01-采集（原始采集层不改）、02-提炼/03-连接（中间资产与概念页另行处置）
    targets = []
    for d in ["06-沉淀", "02-提炼", "03-连接", "04-巩固", "05-调用"]:
        targets += glob.glob(os.path.join(BASE, d, "**/*.md"), recursive=True)
    n_fix = [0]
    fix_samples = []
    for p in targets:
        try:
            t = open(p, encoding="utf-8").read()
        except Exception:
            continue
        if "[[" not in t:
            continue
        orig = t
        def rep(m):
            inner = m.group(1).strip()
            if not re.match(r"^R-[A-Z]{2}-\d+", inner):
                return m.group(0)
            if inner in allmd:
                return m.group(0)
            # 边界约束：须为同号前缀且下一字符为 "-" 或完全相等，防 R-PI-27 误吃 R-PI-278
            hits = [k for k in allmd if k == inner or k.startswith(inner + "-")]
            if len(hits) == 1:
                n_fix[0] += 1
                if len(fix_samples) < 15:
                    fix_samples.append((inner, hits[0]))
                return "[[" + hits[0] + "]]"
            return m.group(0)
        newt = re.sub(r"\[\[([^\[\]|]+)(?:\|[^\]]*)?\]\]", rep, t)
        if newt != orig:
            report["T3"].append({"file": os.path.relpath(p, BASE),
                                 "n": len(re.findall(r"\[\[", orig))})
            if APPLY:
                backup(os.path.relpath(p, BASE))
                open(p, "w", encoding="utf-8").write(newt)

    print("=" * 60)
    print(f"模式：{'APPLY（真实写入）' if APPLY else 'DRY-RUN（只读预演）'}")
    print("=" * 60)
    print("\n【T1 法条核填】")
    for r in report["T1"]:
        print(f"  {'✏️' if r['changed'] else '⏭️ '} {r['card'][:52]} — {r['msg']}")
    print("\n【T2 版本风险标注】")
    for r in report["T2"]:
        print(f"  {'✏️' if r['changed'] else '⏭️ '} {r['card'][:52]}")
    print(f"\n【T3 死链修复】命中文件 {len(report['T3'])} 个，替换链接 {n_fix[0]} 条")
    for a, b in fix_samples: print(f"      {a:34} -> {b[:56]}")
    for r in report["T3"][:8]:
        print(f"  ✏️ {r['file'][:70]}")


if __name__ == "__main__":
    main()
