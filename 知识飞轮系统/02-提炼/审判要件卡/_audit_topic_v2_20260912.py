# -*- coding: utf-8 -*-
"""
第二卷 争点级覆盖审计（第四轮·🟡部分覆盖精细复查）
背景：第三轮（_audit_topic_20260912.py）产出 383 块，其中 0.5<=score<0.67 的
      「🟡 部分覆盖」35 块未做人工细查，且该轮 JSON 生成于 11:15，未纳入
      第十六批新拆的 3 张卡（R-JG-034/035、R-PI-371）。
本轮：
  1. 复用第三轮切块口径（章节过滤 + 级标题切块 + 特征词签名），不改动判据
  2. 卡片集更新为当前全量（450 张）
  3. 对 score < 0.67 的块输出 TOP3 命中卡 + 全文，供人工/AI 逐块判定
  4. 只写新文件 _topic_audit_v2_20260912.json，不覆盖上轮资产（安全六-B）
"""
import json, os, re, glob, subprocess, sys
from collections import Counter

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
PDF = "/Users/chenyouqiang/Desktop/贵州法院类案审判要件指南（第二卷）.pdf"
OUT = os.path.join(BASE, "02-提炼/审判要件卡/_topic_audit_v2_20260912.json")

PARTS = [(1, "建设工程合同纠纷", 36, 98), (2, "保险合同纠纷", 99, 154),
         (3, "商品房买卖合同", 155, 215), (4, "新就业形态劳动争议", 216, 253),
         (5, "婚姻家庭纠纷", 254, 307), (6, "抚养纠纷", 308, 340),
         (7, "机动车交通事故责任", 341, 412), (8, "共同饮酒者侵权", 413, 447),
         (9, "破产", 448, 514), (10, "第三人撤销之诉", 515, 545),
         (11, "案外人执行异议之诉", 546, 581)]

EXCLUDE_CH = re.compile(r"第[一二三四五六七八九十]+章\s*(概\s*述|审理难点|审判难点|审理原则|附\s*录|典型案例)")
KEEP_CH = re.compile(r"第[一二三四五六七八九十]+章\s*(审理思路|其他问题|其他需要说明的问题|要素式审查|裁判规则|审理要点)")

STOP = set("的 了 与 和 或 是 在 有 对 中 为 以 及 其 之 该 本 后 前 上 下 时 但 而 则 应 不 无 未 非 "
           "人民法院 案件 纠纷 问题 认定 审查 处理 应当 可以 一般 原则 规定 情形 认为 如果 由于 因此 但是".split())


def pages_text():
    code = r'''
import fitz, json, sys
d = fitz.open(sys.argv[1])
res = []
for i in range(d.page_count):
    res.append(d[i].get_text())
print(json.dumps(res))
'''
    r = subprocess.run([sys.executable, "-c", code, PDF], capture_output=True, text=True)
    if r.returncode != 0:
        print("fitz 提取失败:", r.stderr[:400]); sys.exit(2)
    return json.loads(r.stdout)


def load_cards():
    cards = []
    for p in glob.glob(os.path.join(BASE, "06-沉淀/裁判规则库/**/R-*.md"), recursive=True):
        t = open(p, encoding="utf-8").read()
        if not re.search(r"(?m)^card_type:\s*审判要件卡", t):
            continue
        cards.append({"path": os.path.relpath(p, BASE), "text": t})
    return cards


def is_heading(line):
    s = line.strip()
    if not s or len(s) > 40:
        return 0
    if re.match(r"^[一二三四五六七八九十]+、[^\s]", s):
        return 1
    return 0


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


def main():
    print("[1/4] 提取 PDF 全文 ...")
    pages = pages_text()
    print(f"      共 {len(pages)} 页")

    print("[2/4] 切争点块 ...")
    page_ch = {}
    for i, t in enumerate(pages):
        pno = i + 1
        flat = re.sub(r"\s+", "", t)
        for m in re.finditer(r"第[一二三四五六七八九十]+章[\u4e00-\u9fa5]{0,14}", flat):
            raw = m.group(0)
            if EXCLUDE_CH.match(raw):
                page_ch.setdefault(pno, []).append((raw, False))
            elif KEEP_CH.match(raw):
                page_ch.setdefault(pno, []).append((raw, True))
    cur = (None, False)
    page_flag = {}
    for i in range(len(pages)):
        pno = i + 1
        for raw, keep in page_ch.get(pno, []):
            cur = (raw, keep)
        page_flag[pno] = cur

    blocks = []
    for i, t in enumerate(pages):
        pno = i + 1
        ch, keep = page_flag.get(pno, (None, False))
        if not keep:
            continue
        num, name = None, None
        for pn, pname, a, b in PARTS:
            if a <= pno <= b:
                num, name = pn, pname
                break
        if num is None:
            continue
        body = []
        for ln in t.split("\n"):
            s = ln.strip()
            if re.match(r"^[\|\u007c]?\s*\d{3}\s*[\|\u007c]?$", s):
                continue
            if "审判要件指南" in s and len(s) < 30:
                continue
            if "贵州法院类案审判要件指南" in s and len(s) < 40:
                continue
            body.append(s)
        cur_block = {"title": "(章起始)", "lines": [], "part": num, "part_name": name,
                     "page": pno, "ch": ch}
        for s in body:
            if is_heading(s) == 1:
                if len("".join(cur_block["lines"])) > 120:
                    blocks.append(cur_block)
                cur_block = {"title": s, "lines": [], "part": num, "part_name": name,
                             "page": pno, "ch": ch}
            else:
                cur_block["lines"].append(s)
        if len("".join(cur_block["lines"])) > 120:
            blocks.append(cur_block)
    print(f"      争点块 {len(blocks)} 个")

    print("[3/4] 载入卡片并匹配（全量） ...")
    cards = load_cards()
    print(f"      审判要件卡 {len(cards)} 张")
    card_terms = [signature(c["text"]) for c in cards]

    results = []
    for idx, blk in enumerate(blocks):
        text = "".join(blk["lines"])
        if len(text) < 150:
            continue
        sig = signature(text)
        cand = [w for w, n in sig.most_common(60) if n >= 2] or [w for w, _ in sig.most_common(40)]
        key = cand[:18]
        if not key:
            continue
        scored = []
        for i, ct in enumerate(card_terms):
            hit = sum(1 for w in key if w in ct)
            scored.append((hit / len(key), cards[i]["path"]))
        scored.sort(key=lambda x: -x[0])
        top3 = scored[:3]
        results.append({
            "id": idx, "part": blk["part"], "part_name": blk["part_name"],
            "page": blk["page"], "ch": blk["ch"], "title": blk["title"],
            "len": len(text), "score": round(top3[0][0], 3), "best_card": top3[0][1],
            "top3": [{"score": round(s, 3), "card": p} for s, p in top3],
            "key": key[:10], "text": text[:1800],
        })
    results.sort(key=lambda r: (r["score"], -r["len"]))
    json.dump({"generated": "2026-09-12 v2", "n_blocks": len(results),
               "n_cards": len(cards), "blocks": results},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"[4/4] → {OUT}\n")

    bands = [(0.0, 0.34), (0.34, 0.5), (0.5, 0.67), (0.67, 1.01)]
    labels = ["🔴 疑似未覆盖(<0.34)", "🟠 覆盖薄弱(0.34-0.5)", "🟡 部分覆盖(0.5-0.67)", "🟢 已覆盖(>0.67)"]
    for (lo, hi), lab in zip(bands, labels):
        print(f"{lab}: {len([r for r in results if lo <= r['score'] < hi])} 块")

    print("\n=== 🟡 部分覆盖 逐块清单（按分数升序） ===")
    yellow = [r for r in results if 0.5 <= r["score"] < 0.67]
    for r in yellow:
        print(f"\n[{r['id']}] 第{r['part']}部分 {r['part_name']} p{r['page']} score={r['score']} {r['len']}字")
        print(f"   标题: {r['title'][:50]}")
        print(f"   best: {r['best_card'].split('/')[-1][:60]}")
        print(f"   正文: {r['text'][:260]}")


if __name__ == "__main__":
    main()
