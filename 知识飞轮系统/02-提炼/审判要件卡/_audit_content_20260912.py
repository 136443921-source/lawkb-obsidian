#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
审判要件卡·内容级覆盖审计器 v2.0（2026-09-12）
——页级密度审计的补丁：解决「source 只标起始页、未含续页」造成的假空白（坑 32）

原理：
  ① 从 PDF 提取每个部分的**骨架项**（一/二/三/四级标题，带 PDF 页）
  ② 汇总该部分全部已有卡的「source + 全文」为语料
  ③ 骨架项取核心词（去序号/去标点）在语料中做子串匹配 → 命中即视为已覆盖
  ④ 输出**内容级未覆盖骨架项**清单

用法：python _audit_content_20260912.py [--part 七]
"""
import os, re, sys, json, subprocess
from collections import defaultdict

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
LIB = f"{BASE}/06-沉淀/裁判规则库"
PDF = "/Users/chenyouqiang/Desktop/贵州法院类案审判要件指南（第二卷）.pdf"
OUT = f"{BASE}/02-提炼/审判要件卡/_content_audit_20260912.json"

# 2026-09-12 实地定位（扉页 0-based，见 _audit_density_20260912.py）
FIELD = [("一", "建设工程合同纠纷案件", 35), ("二", "保险合同纠纷案件", 98),
         ("三", "商品房买卖合同纠纷案件", 154), ("四", "新就业形态劳动争议", 215),
         ("五", "婚姻家庭纠纷案件", 254), ("六", "抚养纠纷案件", 307),
         ("七", "机动车交通事故责任纠纷案件", 340), ("八", "共同饮酒者侵权责任纠纷案件", 412),
         ("九", "破产案件", 447), ("十", "第三人撤销之诉", 514),
         ("十一", "案外人执行异议之诉", 545)]

SKIP_KW = ("概述", "审理难点", "审理原则", "附 录", "附录", "案例", "编撰", "主持人", "执笔人",
           "指导原则", "基本原则", "工作思路", "总体要求")


def skeleton(a, b):
    """提取 [a,b) 页（0-based）内的骨架标题项"""
    code = r'''
import fitz, json, sys, re
d = fitz.open(sys.argv[1]); a=int(sys.argv[2]); b=int(sys.argv[3])
PAT = re.compile(r'^(第[一二三四五六七八九十]+[章节]\s*[^\n]{0,28}|[一二三四五六七八九十]+[、．]\s*[^\n]{0,34}|（[一二三四五六七八九十]+）\s*[^\n]{0,30}|\([一二三四五六七八九十]+\)\s*[^\n]{0,30})')
res=[]
for i in range(a,min(b,d.page_count)):
    for ln in d[i].get_text().split("\n"):
        s=ln.strip()
        if not s or len(s)>44: continue
        m=PAT.match(s)
        if m:
            t=re.sub(r'\s+','',m.group(1)).strip('、．')
            if len(t)>=2: res.append({"p":i+1,"t":t})
print(json.dumps(res,ensure_ascii=False))
'''
    r = subprocess.run([sys.executable, "-c", code, PDF, str(a), str(b)],
                       capture_output=True, text=True)
    return json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else []


def cards_of(cn):
    """该部分已有卡的 source + 全文"""
    out = []
    for root, dirs, files in os.walk(LIB):
        dirs[:] = [x for x in dirs if not x.startswith(".") and "backup" not in x.lower()]
        for fn in files:
            if not (fn.startswith("R-") and fn.endswith(".md")):
                continue
            p = os.path.join(root, fn)
            try:
                t = open(p, encoding="utf-8").read()
            except Exception:
                continue
            if not re.search(r"^card_type:\s*审判要件卡", t, re.M):
                continue
            m = re.search(r"^source:\s*(.+)$", t, re.M)
            if not m:
                continue
            if f"第{cn}部分" in m.group(1):
                out.append(t)
            else:
                # 无部分名但有页号 → 按页区间兜底
                pm = re.search(r"PDF\s*页?\s*(\d+)", m.group(1))
                if pm:
                    out.append(t) if False else None
    return out


def cards_by_page(lo, hi):
    out = []
    for root, dirs, files in os.walk(LIB):
        dirs[:] = [x for x in dirs if not x.startswith(".") and "backup" not in x.lower()]
        for fn in files:
            if not (fn.startswith("R-") and fn.endswith(".md")):
                continue
            p = os.path.join(root, fn)
            try:
                head = open(p, encoding="utf-8").read(3000)
            except Exception:
                continue
            if not re.search(r"^card_type:\s*审判要件卡", head, re.M):
                continue
            m = re.search(r"^source:\s*(.+)$", head, re.M)
            if not m:
                continue
            pages = set()
            for x, y in re.findall(r"PDF\s*页?\s*(\d+)\s*[-–~至]\s*(\d+)", m.group(1)):
                pages.update(range(int(x), int(y) + 1))
            for x in re.findall(r"PDF\s*页?\s*(\d+)(?![\d\-–~至])", m.group(1)):
                pages.add(int(x))
            # 起始页 ±1 容差（应对只标起始页的情形）
            if any(lo - 2 <= pg <= hi + 2 for pg in pages):
                out.append(open(p, encoding="utf-8").read())
    return out


def main():
    only = sys.argv[sys.argv.index("--part") + 1] if "--part" in sys.argv else None
    report = {"generated": "2026-09-12", "parts": []}
    for idx, (cn, name, start) in enumerate(FIELD):
        end = FIELD[idx + 1][2] if idx + 1 < len(FIELD) else 581
        if only and cn != only:
            continue
        sk = skeleton(start, end)
        corpus = "\n".join(cards_by_page(start + 1, end))
        # 骨架项去重
        seen, items = set(), []
        for it in sk:
            if it["t"] in seen:
                continue
            seen.add(it["t"])
            items.append(it)
        # 🔴 章级归属：第一章「概述」/第二章「审理难点」/「附录」整章不含裁判规则，
        #    其子项（一)(二)等）密度 0 属正常，必须整章排除，否则全额虚报为空白。
        cur_chap, chap_ok = "", True
        covered, gaps = [], []
        for it in items:
            t = it["t"]
            if re.match(r"^第[一二三四五六七八九十]+章", t):
                cur_chap = t
                chap_ok = not any(k in t for k in SKIP_KW)
                continue
            if not chap_ok:
                continue
            if any(k in t for k in SKIP_KW):
                continue
            core = re.sub(r'^[第（(][^）)\s]*[）)]\s*', '', t)
            core = re.sub(r'[（(].*?[）)]', '', core).strip()
            core = core[:12]
            if len(core) < 3:
                continue
            if core in corpus:
                covered.append(it)
            else:
                gaps.append(it)
        rate = len(covered) / (len(covered) + len(gaps)) * 100 if (covered or gaps) else 0
        report["parts"].append({"cn": cn, "name": name, "items": len(items),
                                "covered": len(covered), "gap": len(gaps),
                                "rate": round(rate, 1), "gaps": gaps})
        print(f"第{cn}部分 {name}：骨架项 {len(items)}｜有效 {len(covered)+len(gaps)}｜"
              f"已覆盖 {len(covered)}｜未覆盖 {len(gaps)}｜覆盖率 {rate:.1f}%")
        for g in gaps[:14]:
            print(f"     · p{g['p']}  {g['t']}")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n结果已落：{OUT}")


if __name__ == "__main__":
    main()
