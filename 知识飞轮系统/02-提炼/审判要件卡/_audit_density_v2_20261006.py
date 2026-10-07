#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审判要件卡·第二卷密度审计器（修正版 2026-10-06）
——修复第一版 _audit_density_20260912.py 的 LIB 盲区：
   第一版 LIB = 06-沉淀/裁判规则库，但第二卷审判要件卡实际落在
   公司法域库 / 婚姻家庭域库 / 合同风险规则库 / 劳动人事域库 /
   建设工程域库 / 人伤法域库 / 证据规则卡族 等主题域库，
   裁判规则库/ 下无第二卷卡。若直接跑第一版会得到「0 张卡」假阴性。

本版：
- LIBS 扫描上述全部主题域库（+ 裁判规则库 / 刑事域库 兜底）；
- 仅统计 source 含「第二卷」的审判要件卡；
- 沿用第一版硬编码的 11 部分 pdf0 边界与 NAMES；
- 页抽取正则兼容「PDF页N（书页M）」「PDF页N-N（书页M-M）」；
- 附：fitz 自动定位部分扉页做交叉校验（非致命，仅告警）；
- 附：越界卡（页号落在其标注部分区间外）清单，用于发现边界/页码漂移。
"""
import os, re, sys, json, subprocess
from collections import defaultdict

PY = sys.executable
BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
ROOT = os.path.join(BASE, "06-沉淀")
LIBS = [
    os.path.join(ROOT, "公司法域库"),
    os.path.join(ROOT, "婚姻家庭域库"),
    os.path.join(ROOT, "合同风险规则库"),
    os.path.join(ROOT, "劳动人事域库"),
    os.path.join(ROOT, "建设工程域库"),
    os.path.join(ROOT, "人伤法域库"),
    os.path.join(ROOT, "证据规则卡族"),
    os.path.join(ROOT, "裁判规则库"),
    os.path.join(ROOT, "刑事域库"),
]
PDF = "/Users/chenyouqiang/Desktop/贵州法院类案审判要件指南（第二卷）.pdf"
MAP = os.path.join(BASE, "02-提炼/审判要件卡/贵州类案指南第二卷-页码映射表.json")
OUT = os.path.join(BASE, "02-提炼/审判要件卡/_density_audit_v2_20261006.json")

# 第二卷 11 部分：pdf0 扉页索引（2026-09-12 实地核，3 处文本层受损已硬编码补齐）
FIELD = [("一", 35), ("二", 98), ("三", 154), ("四", 215), ("五", 254),
         ("六", 307), ("七", 340), ("八", 412), ("九", 447), ("十", 514),
         ("十一", 545)]
NAMES = {"一": "建设工程合同纠纷案件", "二": "保险合同纠纷案件", "三": "商品房买卖合同纠纷案件",
         "四": "新就业形态劳动争议", "五": "婚姻家庭纠纷案件", "六": "抚养纠纷案件",
         "七": "机动车交通事故责任纠纷案件", "八": "共同饮酒者侵权责任纠纷案件",
         "九": "破产案件", "十": "第三人撤销之诉", "十一": "案外人执行异议之诉"}


def load_pagemap():
    with open(MAP, encoding="utf-8") as f:
        return json.load(f)


def locate_parts_fitz(pdf_path):
    """非致命：自动定位各部分扉页（下一页含「主持人」），仅用于交叉校验。"""
    code = r'''
import fitz, json, sys, re
d = fitz.open(sys.argv[1])
res = []
for i in range(34, d.page_count):
    nxt = d[i + 1].get_text() if i + 1 < d.page_count else ""
    if "主持人" not in nxt[:200]:
        continue
    t = re.sub(r"\s+", "", d[i].get_text())
    m = re.match(r"^第([零一二三四五六七八九十]+)部分", t)
    if not m:
        continue
    res.append({"pdf0": i, "cn": m.group(1)})
print(json.dumps({"pages": d.page_count, "parts": res}, ensure_ascii=False))
'''
    try:
        r = subprocess.run([PY, "-c", code, pdf_path], capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            return None
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return None


def scan_cards():
    out = []
    for LIB in LIBS:
        if not os.path.isdir(LIB):
            continue
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
                if "第二卷" not in src:
                    continue  # 仅统计第二卷卡
                pm = re.search(r"第([零一二三四五六七八九十]+)部分", src)
                part_cn = pm.group(1) if pm else None
                pages = set()
                for a, b in re.findall(r"PDF\s*页?\s*(\d+)\s*[-–~至]\s*(\d+)", src):
                    pages.update(range(int(a), int(b) + 1))
                for a in re.findall(r"PDF\s*页?\s*(\d+)(?![\d\-–~至])", src):
                    pages.add(int(a))
                out.append({"path": p, "part_cn": part_cn, "pages": sorted(pages),
                            "source": src.strip()})
    return out


def main():
    only = None
    if "--part" in sys.argv:
        only = sys.argv[sys.argv.index("--part") + 1]
    mp = load_pagemap()
    total_pdf_pages = len(mp)  # 映射表键 0..N-1 ⇒ 共 N 页
    cards = scan_cards()

    # 部分边界（基于硬编码 FIELD）
    seen = {cn: {"pdf0": p} for cn, p in FIELD}
    order = sorted(seen.items(), key=lambda kv: kv[1]["pdf0"])
    bounds = []
    for idx, (cn, it) in enumerate(order):
        start = it["pdf0"] + 1
        end = (order[idx + 1][1]["pdf0"]) if idx + 1 < len(order) else total_pdf_pages
        bounds.append({"cn": cn, "num": cn2num(cn), "name": NAMES.get(cn, ""),
                       "pdf_start": start, "pdf_end": end})

    def part_of_page(p):
        for b in bounds:
            if b["pdf_start"] <= p <= b["pdf_end"]:
                return b["cn"]
        return None

    used = defaultdict(set)
    card_of = defaultdict(int)
    nocard = 0
    outliers = []  # 页号落在标注部分区间外的卡
    for c in cards:
        cn = c["part_cn"]
        if cn is None:
            nocard += 1
            continue
        # 越界检测
        b = next((x for x in bounds if x["cn"] == cn), None)
        if b:
            oob = [p for p in c["pages"] if not (b["pdf_start"] <= p <= b["pdf_end"])]
            if oob:
                outliers.append({"file": os.path.basename(c["path"]), "part": cn,
                                 "oob_pages": oob, "all_pages": c["pages"]})
        used[cn].update(c["pages"])
        card_of[cn] += 1

    # fitz 交叉校验（非致命）
    fitz_res = locate_parts_fitz(PDF)
    fitz_note = ""
    if fitz_res:
        fitz_pages = {x["pdf0"] for x in fitz_res["parts"]}
        miss = [p for cn, p in FIELD if p not in fitz_pages]
        fitz_note = (f"fitz自动定位：PDF共{fitz_res['pages']}页，"
                     f"命中部分扉页{fitz_pages}；硬编码FIELD漏定位={miss or '无'}")
    else:
        fitz_note = "fitz 自动校验未执行（跳过）"

    report = {"generated": "2026-10-06", "total_pdf_pages": total_pdf_pages,
              "v2_card_total": len(cards), "cards_part_unmatched": nocard,
              "fitz_note": fitz_note, "outliers": outliers, "parts": []}
    print(f"PDF 总页数: {total_pdf_pages}｜第二卷审判要件卡总数: {len(cards)}｜"
          f"未标部分: {nocard}｜越界卡: {len(outliers)}")
    print(fitz_note)
    print()
    print(f"{'部分':<6}{'类案':<22}{'PDF页范围':<16}{'卡数':>5}{'覆盖页':>7}{'总页':>6}{'覆盖率':>9}  空白页（PDF，1-based）")
    print("-" * 132)
    for b in bounds:
        cn = b["cn"]
        ps = set(range(b["pdf_start"], b["pdf_end"] + 1))
        cov = ps & used.get(cn, set())
        cards_n = card_of.get(cn, 0)
        blank = sorted(ps - cov)
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
    print()
    if outliers:
        print("=== 越界卡（页号落在其标注部分区间外，需人工复核页码/边界）===")
        for o in outliers:
            print(f"  {o['file']} 标注部分={o['part']} 越界页={o['oob_pages']} 全部页={o['all_pages']}")
    else:
        print("越界检测：无（全部卡页号均落在其标注部分区间内）")

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n审计结果已落：{OUT}")


def cn2num(s):
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


if __name__ == "__main__":
    main()
