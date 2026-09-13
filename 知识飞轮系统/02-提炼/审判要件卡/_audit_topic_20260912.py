# -*- coding: utf-8 -*-
"""
第二卷 争点级覆盖审计（第三轮·标题块级）
页级审计会被「source 只标起始页」误导；本轮改为：
  1. 只取含裁判规则的章节（第三章 审理思路 / 第四章 其他问题 / 第五章 其他问题 等），
     排除 第一章概述、第X章审理难点/审理原则、附录/典型案例
  2. 在这些章节内部，按「一、二、三、」「（一）」「1. 」等级标题切块
  3. 每块取特征词（去掉停用词后的 3-6 字法律术语），与 447 张卡正文做语义重合度匹配
"""
import json, os, re, glob, subprocess, sys
from collections import defaultdict, Counter

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
PDF = "/Users/chenyouqiang/Desktop/贵州法院类案审判要件指南（第二卷）.pdf"
OUT = os.path.join(BASE, "02-提炼/审判要件卡/_topic_audit_20260912.json")

# 部分边界（2026-09-12 实地定位：下一页首 200 字含「主持人」反查）
PARTS = [(1, "建设工程合同纠纷", 36, 98), (2, "保险合同纠纷", 99, 154),
         (3, "商品房买卖合同", 155, 215), (4, "新就业形态劳动争议", 216, 253),
         (5, "婚姻家庭纠纷", 254, 307), (6, "抚养纠纷", 308, 340),
         (7, "机动车交通事故责任", 341, 412), (8, "共同饮酒者侵权", 413, 447),
         (9, "破产", 448, 514), (10, "第三人撤销之诉", 515, 545),
         (11, "案外人执行异议之诉", 546, 581)]

# 排除：概述 / 难点 / 原则 / 附录 / 典型案例
EXCLUDE_CH = re.compile(r"第[一二三四五六七八九十]+章\s*(概\s*述|审理难点|审判难点|审理原则|附\s*录|典型案例)")
# 含裁判规则的章节标题
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


def part_of(pno):
    for num, name, a, b in PARTS:
        if a <= pno <= b:
            return num, name
    return None, None


def load_cards():
    cards = []
    for p in glob.glob(os.path.join(BASE, "06-沉淀/裁判规则库/**/R-*.md"), recursive=True):
        t = open(p, encoding="utf-8").read()
        if not re.search(r"(?m)^card_type:\s*审判要件卡", t):
            continue
        cards.append({"path": os.path.relpath(p, BASE), "text": t})
    return cards


CN_SET = "一二三四五六七八九十"


def is_heading(line):
    s = line.strip()
    if not s or len(s) > 40:
        return 0
    # 一、xxx /（一）xxx / 1. xxx / （1）xxx
    if re.match(r"^[一二三四五六七八九十]+、[^\s]", s):
        return 1
    if re.match(r"^（[一二三四五六七八九十]+）[^\s]", s):
        return 2
    if re.match(r"^[（(]\d+[)）][^\s]", s):
        return 3
    return 0


def signature(text):
    """取特征词：3-6 字中文片段，去停用词"""
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
    print("[1/5] 提取 PDF 全文 ...")
    pages = pages_text()
    print(f"      共 {len(pages)} 页")

    print("[2/5] 判定各页所属章节属性 ...")
    # 逐页判定：扫描每页是否出现「第X章 <标题>」
    page_ch = {}   # pno(1-based) -> (chapter_title_line, keep?)
    for i, t in enumerate(pages):
        pno = i + 1
        flat = re.sub(r"\s+", "", t)
        for m in re.finditer(r"第[一二三四五六七八九十]+章[\u4e00-\u9fa5]{0,14}", flat):
            raw = m.group(0)
            if EXCLUDE_CH.match(raw):
                page_ch.setdefault(pno, []).append((raw, False))
            elif KEEP_CH.match(raw):
                page_ch.setdefault(pno, []).append((raw, True))

    # 生成「当前生效章节」游标
    cur = (None, False)
    page_flag = {}
    for i in range(len(pages)):
        pno = i + 1
        if pno in page_ch:
            keeps = [k for _, k in page_ch[pno]]
            titles = [t for t, _ in page_ch[pno]]
            cur = (titles[0], True if True in keeps else False)
        page_flag[pno] = cur

    print("[3/5] 切分争点块（仅含裁判规则章节） ...")
    blocks = []
    for num, name, a, b in PARTS:
        for pno in range(a, min(b, len(pages)) + 1):
            ch, keep = page_flag.get(pno, (None, False))
            if not keep:
                continue
            lines = pages[pno - 1].split("\n")
            # 去掉页眉页脚
            body = []
            for ln in lines:
                s = ln.strip()
                if re.match(r"^[\|\u007c]?\s*\d{3}\s*[\|\u007c]?$", s):
                    continue
                if "审判要件指南" in s and len(s) < 30:
                    continue
                if "贵州法院类案审判要件指南" in s and len(s) < 40:
                    continue
                body.append(s)
            # 切块
            cur_block = {"title": "(章起始)", "lines": [], "part": num, "part_name": name,
                         "page": pno, "ch": ch}
            for s in body:
                lv = is_heading(s)
                if lv == 1:
                    if len("".join(cur_block["lines"])) > 120:
                        blocks.append(cur_block)
                    cur_block = {"title": s, "lines": [], "part": num, "part_name": name,
                                 "page": pno, "ch": ch}
                else:
                    cur_block["lines"].append(s)
            if len("".join(cur_block["lines"])) > 120:
                blocks.append(cur_block)

    print(f"      争点块 {len(blocks)} 个")

    print("[4/5] 载入卡片并做语义覆盖匹配 ...")
    cards = load_cards()
    print(f"      审判要件卡 {len(cards)} 张")
    card_terms = []
    for c in cards:
        card_terms.append(signature(c["text"]))

    results = []
    for idx, blk in enumerate(blocks):
        text = "".join(blk["lines"])
        if len(text) < 150:
            continue
        sig = signature(text)
        # 取最具代表性的 18 个词（频次>=2 优先，否则取长词）
        cand = [w for w, n in sig.most_common(60) if n >= 2] or [w for w, _ in sig.most_common(40)]
        key = cand[:18]
        if not key:
            continue
        best, best_card = 0.0, None
        for i, ct in enumerate(card_terms):
            hit = sum(1 for w in key if w in ct)
            r = hit / len(key)
            if r > best:
                best, best_card = r, cards[i]["path"]
        results.append({
            "id": idx, "part": blk["part"], "part_name": blk["part_name"],
            "page": blk["page"], "ch": blk["ch"], "title": blk["title"],
            "len": len(text), "score": round(best, 3), "best_card": best_card,
            "key": key[:8], "text": text[:600],
        })

    results.sort(key=lambda r: (r["score"], -r["len"]))
    json.dump({"generated": "2026-09-12", "n_blocks": len(results),
               "n_cards": len(cards), "blocks": results},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"[5/5] 审计完成 → {OUT}\n")
    bands = [(0.0, 0.34), (0.34, 0.5), (0.5, 0.67), (0.67, 1.01)]
    labels = ["🔴 疑似未覆盖(<0.34)", "🟠 覆盖薄弱(0.34-0.5)", "🟡 部分覆盖(0.5-0.67)", "🟢 已覆盖(>0.67)"]
    for (lo, hi), lab in zip(bands, labels):
        sub = [r for r in results if lo <= r["score"] < hi]
        print(f"{lab}: {len(sub)} 块")

    print("\n=== 🔴 疑似未覆盖 TOP 30（按字数降序） ===")
    red = sorted([r for r in results if r["score"] < 0.34], key=lambda r: -r["len"])
    for r in red[:30]:
        print(f"  第{r['part']}部分 {r['part_name'][:8]:8} p{r['page']:>3} {r['score']:.2f} "
              f"{r['len']:>4}字 | {r['title'][:32]}")


if __name__ == "__main__":
    main()
