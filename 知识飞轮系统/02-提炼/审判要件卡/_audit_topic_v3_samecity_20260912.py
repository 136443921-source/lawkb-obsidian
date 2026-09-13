# -*- coding: utf-8 -*-
"""
第二卷 争点级覆盖审计（第五轮·同域重排复查）
发现：第四轮低分块多为「跨域误匹配」假象——例如 p125「投资型人寿保险适当性义务」
      全域 best 命中 R-HT-087（商品房），但库里其实已有 R-HT-208-投资型保险适当性义务。
      原因是全域匹配时，通用法律术语（合同/义务/认定）把分数拉到别的域去了。
本轮：对每个低分块（score<0.67）做「同域重排」——只在块所属部分的对应域目录里找 top3，
      同时保留全域 top1 作对照，输出二者分数差，用于判定：
        - 同域 top1 分显著高于全域 best（且 >=0.5）→ 假缺口（已覆盖，跨域误判）
        - 同域 top1 仍 <0.5                        → 疑似真缺口，需人工读卡核实
只写新文件，不覆盖上轮资产（安全六-B）。
"""
import json, os, re, glob
from collections import Counter

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
LIB = os.path.join(BASE, "06-沉淀/裁判规则库")
SRC = os.path.join(BASE, "02-提炼/审判要件卡/_topic_audit_v2_20260912.json")
OUT = os.path.join(BASE, "02-提炼/审判要件卡/_topic_audit_v3_同域重排_20260912.json")

# 部分 -> 主域目录（可多域）
PART_DOMAIN = {
    1: ["建设工程", "证据规则"],
    2: ["合同风险", "机动车交通事故责任纠纷"],
    3: ["合同风险"],
    4: ["劳动人事"],
    5: ["婚姻家庭"],
    6: ["婚姻家庭"],
    7: ["机动车交通事故责任纠纷", "人伤法"],
    8: ["人伤法", "生命权健康权身体权纠纷"],
    9: ["公司法", "商事纠纷", "商事"],
    10: ["商事纠纷", "公司法", "案由路由"],
    11: ["案外人执行异议之诉", "案由路由"],
}

STOP = set("的 了 与 和 或 是 在 有 对 中 为 以 及 其 之 该 本 后 前 上 下 时 但 而 则 应 不 无 未 非 "
           "人民法院 案件 纠纷 问题 认定 审查 处理 应当 可以 一般 原则 规定 情形 认为 如果 由于 因此 但是".split())


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


def load_cards():
    cards = []
    for p in glob.glob(os.path.join(LIB, "**/R-*.md"), recursive=True):
        t = open(p, encoding="utf-8").read()
        if not re.search(r"(?m)^card_type:\s*审判要件卡", t):
            continue
        rel = os.path.relpath(p, LIB)
        dom = rel.split(os.sep)[0]
        cards.append({"path": rel, "dom": dom, "text": t})
    return cards


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    blocks = data["blocks"]
    cards = load_cards()
    print(f"卡片 {len(cards)} 张；块 {len(blocks)} 个")
    card_terms = [signature(c["text"]) for c in cards]

    low = [r for r in blocks if r["score"] < 0.67]
    print(f"低分块（全域 score<0.67）共 {len(low)} 个\n")

    out = []
    for r in low:
        sig = signature(r["text"])
        cand = [w for w, n in sig.most_common(60) if n >= 2] or [w for w, _ in sig.most_common(40)]
        key = cand[:18]
        doms = PART_DOMAIN.get(r["part"], [])
        scored = []
        for i, ct in enumerate(card_terms):
            hit = sum(1 for w in key if w in ct)
            scored.append((hit / len(key), i))
        scored.sort(key=lambda x: -x[0])
        dom_hits = [(s, i) for s, i in scored if cards[i]["dom"] in doms][:3]
        dom_best = dom_hits[0] if dom_hits else (0.0, None)
        out.append({
            "id": r["id"], "part": r["part"], "part_name": r["part_name"], "page": r["page"],
            "title": r["title"], "len": r["len"],
            "global_score": r["score"], "global_best": r["best_card"],
            "dom_score": round(dom_best[0], 3),
            "dom_best": cards[dom_best[1]]["path"] if dom_best[1] is not None else None,
            "dom_top3": [{"score": round(s, 3), "card": cards[i]["path"]} for s, i in dom_hits],
            "domains": doms,
            "text": r["text"][:900],
        })

    # 判定
    for o in out:
        if o["dom_score"] >= 0.5:
            o["verdict"] = "✅ 同域已覆盖（跨域误匹配假象）"
        elif o["dom_score"] >= 0.34:
            o["verdict"] = "🟠 同域疑似薄弱·需读卡核实"
        else:
            o["verdict"] = "🔴 同域疑似真缺口·优先读卡"

    out.sort(key=lambda o: (o["dom_score"], -o["len"]))
    json.dump({"generated": "2026-09-12 v3 同域重排", "n": len(out), "items": out},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    cnt = Counter(o["verdict"] for o in out)
    for k in sorted(cnt):
        print(f"{k}: {cnt[k]} 块")
    print("\n=== 需人工读卡核实的块（同域 <0.5） ===")
    for o in out:
        if o["dom_score"] < 0.5:
            print(f"\n[{o['id']}] 第{o['part']}部分 {o['part_name']} p{o['page']} "
                  f"全域{o['global_score']}→同域{o['dom_score']} {o['len']}字")
            print(f"   标题: {o['title'][:50]}")
            print(f"   同域best: {o['dom_best']}")
            print(f"   正文: {o['text'][:230]}")
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
