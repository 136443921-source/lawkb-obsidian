#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审判要件卡·全库密度审计器 v1.0（2026-09-12）
- 从 PDF 定位 11 个部分的页范围
- 从卡片 source 反查已覆盖页
- 输出每部分覆盖率 + 空白页区间（含首尾页识别）
用法：
  python _audit_density_20260912.py            # 全量审计
  python _audit_density_20260912.py --part 七   # 只列某部分空白页
"""
import os, re, sys, json, subprocess
from collections import defaultdict

PY = sys.executable
BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
LIB = os.path.join(BASE, "06-沉淀/裁判规则库")
PDF = "/Users/chenyouqiang/Desktop/贵州法院类案审判要件指南（第二卷）.pdf"
MAP = os.path.join(BASE, "02-提炼/审判要件卡/贵州类案指南第二卷-页码映射表.json")
OUT = os.path.join(BASE, "02-提炼/审判要件卡/_density_audit_20260912.json")

CN = "零一二三四五六七八九十"


def cn2num(s):
    """中文数字转阿拉伯数字，支持 十一 / 二十 / 一百零五"""
    if s is None:
        return None
    s = s.strip()
    if s.isdigit():
        return int(s)
    d = {c: i for i, c in enumerate("零一二三四五六七八九")}
    if s == "十":
        return 10
    total, section = 0, 0
    for ch in s:
        if ch in d:
            section = d[ch]
        elif ch == "十":
            section = (section or 1) * 10
        elif ch == "百":
            section = (section or 1) * 100
        elif ch == "千":
            section = (section or 1) * 1000
        else:
            return None
    total += section
    return total


def load_pagemap():
    with open(MAP, encoding="utf-8") as f:
        return json.load(f)


def locate_parts(pdf_path):
    """实地定位各部分扉页（0-based）。
    体例：部分扉页的**下一页**必为课题组成员页（首 200 字含「主持人」）。
    2026-09-12 实测返回 11 个部分扉页，1-based 分别为：
    36 / 99 / 155 / 216 / 255 / 308 / 341 / 413 / 448 / 515 / 546
    """
    """用 fitz 找每个「第X部分」标题所在 PDF 页（0-based 索引）"""
    code = r'''
import fitz, json, sys, re
d = fitz.open(sys.argv[1])
res = []
CN = "零一二三四五六七八九十"
# 部分扉页特征：**下一页**为课题组成员页（首 200 字含「主持人」）
for i in range(34, d.page_count):
    nxt = d[i + 1].get_text() if i + 1 < d.page_count else ""
    if "主持人" not in nxt[:200]:
        continue
    t = re.sub(r"\s+", "", d[i].get_text())
    m = re.match(r"^第([零一二三四五六七八九十]+)部分", t)
    if not m:
        continue
    res.append({"pdf0": i, "cn": m.group(1), "name": t[:26]})
print(json.dumps(res, ensure_ascii=False))
'''
    r = subprocess.run([PY, "-c", code, pdf_path], capture_output=True, text=True)
    if r.returncode != 0:
        print("fitz 提取失败:", r.stderr[:500])
        sys.exit(2)
    got = json.loads(r.stdout.strip().splitlines()[-1])
    # 🔴 三处扉页文本层受损，自动定位会漏（2026-09-12 实地核）：
    #   pdf0=254 第五部分 文本层为空(len=0)；pdf0=307 第六部分 页首有 "O o -- -" 噪声；
    #   pdf0=545 第十一部分 "第十一部分" 被断字为 "第 部分 … 十"。
    #   → 以「下一页为课题组成员页」法实地确认后硬编码，并运行时校验。
    FIELD = [("一", 35), ("二", 98), ("三", 154), ("四", 215), ("五", 254),
             ("六", 307), ("七", 340), ("八", 412), ("九", 447), ("十", 514),
             ("十一", 545)]
    found = {x["pdf0"] for x in got}
    out = [{"pdf0": p, "cn": cn, "name": ""} for cn, p in FIELD]
    miss = [p for cn, p in FIELD if p not in found]
    if miss:
        print(f"  [提示] 自动定位漏 {miss}（文本层受损），已按实地定位表补齐")
    return out


def scan_cards():
    """返回 [(path, part_cn, part_name, [pdf_pages...])]"""
    out = []
    for root, dirs, files in os.walk(LIB):
        dirs[:] = [x for x in dirs if not x.startswith(".") and "backup" not in x.lower()]
        for fn in files:
            if not (fn.startswith("R-") and fn.endswith(".md")):
                continue
            p = os.path.join(root, fn)
            try:
                with open(p, encoding="utf-8") as f:
                    head = f.read(4000)
            except Exception:
                continue
            if not re.search(r"^card_type:\s*审判要件卡", head, re.M):
                continue
            m = re.search(r"^source:\s*(.+)$", head, re.M)
            if not m:
                continue
            src = m.group(1)
            pm = re.search(r"第([零一二三四五六七八九十]+)部分[·・\.]?\s*([^（(]*)", src)
            part_cn = pm.group(1) if pm else None
            part_name = pm.group(2).strip() if pm else ""
            pages = set()
            # 兼容 PDF页228-228 / PDF页228 / PDF 228 等写法
            for a, b in re.findall(r"PDF\s*页?\s*(\d+)\s*[-–~至]\s*(\d+)", src):
                pages.update(range(int(a), int(b) + 1))
            # 🔴 数字后必须加 (?![\d\-–~至])，否则 "PDF页114-115" 会回溯出 "11" 这种假页号
            for a in re.findall(r"PDF\s*页?\s*(\d+)(?![\d\-–~至])", src):
                pages.add(int(a))
            out.append({"path": p, "part_cn": part_cn, "part_name": part_name,
                        "pages": sorted(pages), "source": src})
    return out


def main():
    only = None
    if "--part" in sys.argv:
        only = sys.argv[sys.argv.index("--part") + 1]
    mp = load_pagemap()
    parts = locate_parts(PDF)
    cards = scan_cards()

    # 部分边界：每个部分的起始 pdf0，结束为下一部分起始-1
    # 同一部分可能在目录页多次出现，取「正文区」首次出现（pdf0 > 20 跳过目录）
    seen = {}
    for it in parts:
        if it["pdf0"] < 15:
            continue  # 目录页
        if it["cn"] not in seen:
            seen[it["cn"]] = it
    order = sorted(seen.items(), key=lambda kv: kv[1]["pdf0"])
    # 部分名（2026-09-12 实地读页确认，扉页文本 OCR 噪声大，故以实地为准）
    NAMES = {"一": "建设工程合同纠纷案件", "二": "保险合同纠纷案件", "三": "商品房买卖合同纠纷案件",
             "四": "新就业形态劳动争议", "五": "婚姻家庭纠纷案件", "六": "抚养纠纷案件",
             "七": "机动车交通事故责任纠纷案件", "八": "共同饮酒者侵权责任纠纷案件",
             "九": "破产案件", "十": "第三人撤销之诉", "十一": "案外人执行异议之诉"}
    # 边界统一 1-based：start = 扉页0based+1，end = 下一部分扉页0based
    bounds = []
    for idx, (cn, it) in enumerate(order):
        start = it["pdf0"] + 1
        end = (order[idx + 1][1]["pdf0"]) if idx + 1 < len(order) else len(mp)
        bounds.append({"cn": cn, "num": cn2num(cn), "name": NAMES.get(cn, ""),
                       "pdf_start": start, "pdf_end": end})

    def part_of_page(p):
        for b in bounds:
            if b["pdf_start"] <= p <= b["pdf_end"]:
                return b["cn"]
        return None

    used = defaultdict(set)      # part_cn -> covered pages
    card_of = defaultdict(int)   # part_cn -> 卡数
    nocard = 0
    fallback = 0
    for c in cards:
        cn = c["part_cn"] if c["part_cn"] in seen else None
        if cn is None and c["pages"]:
            cn = part_of_page(c["pages"][0])      # 无部分名 → 按页号落区间
            if cn:
                fallback += 1
        if cn:
            used[cn].update(c["pages"])
            card_of[cn] += 1
        else:
            nocard += 1

    report = {"generated": "2026-09-12", "total_cards": len(cards),
              "cards_part_unmatched": nocard, "parts": []}
    print(f"{'部分':<6}{'类案':<22}{'PDF页范围':<16}{'卡数':>5}{'覆盖页':>7}{'总页':>6}{'覆盖率':>9}  空白页（PDF，1-based）")
    print("-" * 130)
    for b in bounds:
        cn = b["cn"]
        ps = set(range(b["pdf_start"], b["pdf_end"] + 1))
        cov = ps & used.get(cn, set())
        cards_n = card_of.get(cn, 0)
        blank = sorted(ps - cov)
        # 压缩连续区间
        segs = []
        for p in blank:
            if segs and p == segs[-1][1] + 1:
                segs[-1][1] = p
            else:
                segs.append([p, p])
        segtxt = ", ".join(f"{a}" if a == z else f"{a}-{z}" for a, z in segs)
        rate = len(cov) / len(ps) * 100 if ps else 0
        b.update({"covered": len(cov), "total": len(ps), "rate": round(rate, 1),
                  "cards": cards_n, "blank_segs": segs})
        report["parts"].append(b)
        if only and str(b["num"]) != only and cn != only:
            continue
        print(f"第{cn}部分 {b['name'][:20]:<20} {b['pdf_start']}-{b['pdf_end']:<10} "
              f"{cards_n:>5} {len(cov):>7} {len(ps):>6} {rate:>8.1f}%  {segtxt[:70]}")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n审计结果已落：{OUT}")
    print(f"审判要件卡总数：{len(cards)}｜按页号兜底归类 {fallback} 张｜完全未匹配 {nocard} 张")


if __name__ == "__main__":
    main()
