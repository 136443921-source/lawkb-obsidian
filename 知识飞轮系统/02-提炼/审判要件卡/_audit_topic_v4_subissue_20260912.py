# -*- coding: utf-8 -*-
"""
第二卷 争点级覆盖审计（第六轮·子争点切分，排查「块内多争点盲区」）
动机：一个 600 字的「一、」级块常含 3-5 个子争点，只要其中 1 个被命中，
      整块分数就被拉高，掩盖其余子争点未覆盖的事实（记为踩坑 #36）。
本轮：把 40 个低分块按「（一）/1./（1）/①/第一，」二级标记再切成子争点，
      逐个在【同域】内匹配，输出同域 score<0.34 的子争点清单。
只写新文件，不覆盖上轮资产（安全六-B）。
"""
import json, os, re, glob
from collections import Counter

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
LIB = os.path.join(BASE, "06-沉淀/裁判规则库")
SRC = os.path.join(BASE, "02-提炼/审判要件卡/_topic_audit_v3_同域重排_20260912.json")
OUT = os.path.join(BASE, "02-提炼/审判要件卡/_topic_audit_v4_子争点_20260912.json")

PART_DOMAIN = {
    1: ["建设工程", "证据规则"], 2: ["合同风险", "机动车交通事故责任纠纷"],
    3: ["合同风险"], 4: ["劳动人事"], 5: ["婚姻家庭"], 6: ["婚姻家庭"],
    7: ["机动车交通事故责任纠纷", "人伤法"], 8: ["人伤法", "生命权健康权身体权纠纷"],
    9: ["公司法", "商事纠纷", "商事"], 10: ["商事纠纷", "公司法", "案由路由"],
    11: ["案外人执行异议之诉", "案由路由"],
}
STOP = set("的 了 与 和 或 是 在 有 对 中 为 以 及 其 之 该 本 后 前 上 下 时 但 而 则 应 不 无 未 非 "
           "人民法院 案件 纠纷 问题 认定 审查 处理 应当 可以 一般 原则 规定 情形 认为 如果 由于 因此 但是".split())

# 子争点起始标记
SUB = re.compile(r"(?:^|(?<=[\s。；]))(?:（[一二三四五六七八九十]+）|\d{1,2}\.\s|[（(]\d{1,2}[)）]|"
                 r"[①②③④⑤⑥⑦⑧⑨⑩]|第[一二三四五六七八九十]+，)")


def signature(text):
    t = re.sub(r"[^\u4e00-\u9fa5]", " ", text)
    terms = Counter()
    for n in (4, 5, 3, 6):
        for i in range(len(t) - n + 1):
            w = t[i:i + n]
            if " " in w:
                continue
            if any(sw in w for sw in STOP if len(sw) >= 2):
                continue
            if w in STOP:
                continue
            terms[w] += 1
    return terms


def split_sub(text):
    ms = list(SUB.finditer(text))
    if len(ms) < 2:
        return [text]
    segs = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        seg = text[m.start():end].strip()
        if len(seg) >= 80:
            segs.append(seg)
    return segs or [text]


def load_cards():
    cards = []
    for p in glob.glob(os.path.join(LIB, "**/R-*.md"), recursive=True):
        t = open(p, encoding="utf-8").read()
        if not re.search(r"(?m)^card_type:\s*审判要件卡", t):
            continue
        cards.append({"path": os.path.relpath(p, LIB), "dom": os.path.relpath(p, LIB).split(os.sep)[0]})
    return cards


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    items = data["items"]
    cards = load_cards()
    terms = [signature(open(os.path.join(LIB, c["path"]), encoding="utf-8").read()) for c in cards]
    print(f"卡片 {len(cards)} 张；待复查低分块 {len(items)} 个")

    out, nsub = [], 0
    for it in items:
        doms = PART_DOMAIN.get(it["part"], [])
        idxs = [i for i, c in enumerate(cards) if c["dom"] in doms]
        for seg in split_sub(it["text"]):
            if len(seg) < 80:
                continue
            nsub += 1
            sig = signature(seg)
            cand = [w for w, n in sig.most_common(60) if n >= 2] or [w for w, _ in sig.most_common(40)]
            key = cand[:14]
            if not key:
                continue
            best, bi = 0.0, None
            for i in idxs:
                hit = sum(1 for w in key if w in terms[i])
                r = hit / len(key)
                if r > best:
                    best, bi = r, i
            out.append({
                "block_id": it["id"], "part": it["part"], "part_name": it["part_name"],
                "page": it["page"], "block_title": it["title"],
                "sub_score": round(best, 3),
                "sub_best": cards[bi]["path"] if bi is not None else None,
                "len": len(seg), "text": seg[:500],
            })
    out.sort(key=lambda o: o["sub_score"])
    json.dump({"generated": "2026-09-12 v4 子争点", "n_sub": nsub, "items": out},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"切出子争点 {nsub} 个")
    for lo, hi, lab in [(0, 0.34, "🔴 <0.34"), (0.34, 0.5, "🟠 0.34-0.5"), (0.5, 1.01, "🟢 >=0.5")]:
        print(f"  同域 {lab}: {len([o for o in out if lo <= o['sub_score'] < hi])}")

    print("\n=== 同域 <0.34 的子争点（真·疑似未覆盖） ===")
    for o in out:
        if o["sub_score"] < 0.34:
            print(f"\n[{o['block_id']}] 第{o['part']}部分 {o['part_name']} p{o['page']} "
                  f"score={o['sub_score']} {o['len']}字")
            print(f"   best: {o['sub_best']}")
            print(f"   {o['text'][:220]}")
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
