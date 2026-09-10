#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
死链专项分析器 v1.0.0（2026-09-08）
====================================
用途：全库死链盘点 + 自动归类 + 模糊匹配真实目标候选，产出可执行的修复清单。

背景：2026-09-08 全库扫描 命中 343 文件 / 死链 1189 条（历史 backlog 称 1301）。
      人工逐条看不现实，必须先机器归类，再按类施策。

四类归因（SKILL 坑 14 精神：**「MISS」不等于「不存在」，先怀疑检索/命名，再怀疑数据**）：
  A 类 改名残留   —— 目标笔记存在但基名变了（模糊匹配可命中唯一候选）→ 可自动改链
  B 类 系统引用   —— 指向非卡片文档（索引/报告/日志/SOP），本就不是卡片 → 加白名单
  C 类 编号引用   —— 形如 R-XX-NNN 的规则卡编号写法，需映射到文件名 → 可自动改链
  D 类 真死链     —— 全库无此物，需人工判定（删除 / 改指向 / 补建卡）

用法：
    python3 _analyze_deadlinks_20260908.py            # 输出分类报告
    python3 _analyze_deadlinks_20260908.py --json out.json
"""
import io
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _check_deadlinks import (ROOT, SKIP_DIRS, CONCEPT_PREFIXES,
                              build_basename_set, md_files, normalize, is_concept,
                              parse_related_links,   # v1.3.0：统一解析口径
                              is_noise,              # v1.4.0：统一噪声过滤
                              is_external)           # v1.5.0：外部白名单

import yaml

# ── 模糊匹配用：剥离一切非「中英文数字」字符 ──────────────────
NOISE = re.compile(r"[\s\-_—－·、,，.。:：;；/\\（）()【】\[\]《》〈〉「」『』\"'“”‘’?!？！#*+]")

def sig(s):
    """指纹：只留中文/字母/数字，用于跨标点差异的比对"""
    return NOISE.sub("", str(s)).lower()

# ── 系统引用白名单模式（指向非卡片文档，视为合法）─────────────
SYS_PAT = re.compile(
    r"(入库索引|可用性登记|总索引|变更记录|排期表|拆卡|提取文本|体检报告|"
    r"配置说明书|配置迭代|SOP|报告|日志|清单|汇总|统计|盘点|评估|"
    r"待确认|回源报告|学习资料|知识推送|轨迹卡|调用记录|每日|周报|月报|"
    r"计划|方案|说明|指引|规范|模板|样例|样卡|草稿|临时|tmp|test|"
    r"^\d{4}-\d{2}-\d{2}$|^\d{4}年\d{1,2}月\d{1,2}日$)"
)

# ── 规则卡编号写法：R-XX-NNN / R-XXNNN / RXXNNN ───────────────
RULE_NO = re.compile(r"^R[-_]?([A-Z]{2})[-_]?(\d{1,3})$", re.I)


def collect():
    """扫全库，返回 {死链基名: {文件: 次数}} 与 链接总数"""
    allmd = build_basename_set()
    dead_map = defaultdict(lambda: defaultdict(int))
    total_links = 0
    for p in md_files():
        txt = io.open(p, encoding="utf-8").read()
        if not txt.startswith("---"):
            continue
        try:
            fm = yaml.safe_load(txt.split("---")[1]) or {}
        except Exception:
            continue
        links = parse_related_links(fm)
        body = re.findall(r"\[\[([^\]]+)\]\]", txt)
        cand = [normalize(x) for x in links] + [normalize(x) for x in body]
        cand = [c for c in cand if c]
        total_links += len(cand)
        for c in cand:
            if c and not is_noise(c) and not is_external(c) and not is_concept(c) and c not in allmd:
                dead_map[c][os.path.basename(p)] += 1
    return allmd, dead_map, total_links


def main():
    allmd, dead_map, total_links = collect()
    print(f"全库笔记基名：{len(allmd)}")
    print(f"全库链接总数：{total_links}")
    print(f"死链去重后：{len(dead_map)} 个（累计出现 {sum(sum(v.values()) for v in dead_map.values())} 次）\n")

    # 建指纹索引：sig → [真实基名]
    sig_idx = defaultdict(list)
    for n in allmd:
        sig_idx[sig(n)].append(n)

    # 规则编号索引：("GS", 5) → [真实基名]
    rule_idx = defaultdict(list)
    for n in allmd:
        m = re.match(r"^R-([A-Za-z]{2})-(\d{3})", n)
        if m:
            rule_idx[(m.group(1).upper(), int(m.group(2)))].append(n)

    buckets = {"A1_强匹配": [], "A2_弱匹配": [], "B_系统引用": [],
               "C_编号引用": [], "D_真死链": []}

    for d, src in sorted(dead_map.items(), key=lambda x: -sum(x[1].values())):
        n_files = len(src)
        n_occ = sum(src.values())
        rec = {"link": d, "files": n_files, "occ": n_occ,
               "src_sample": list(src.items())[:3]}

        # C 类：编号写法
        m = RULE_NO.match(d)
        if m:
            cands = rule_idx.get((m.group(1).upper(), int(m.group(2))), [])
            if cands:
                rec["fix"] = cands
                buckets["C_编号引用"].append(rec)
                continue

        # A1 强匹配：指纹完全相等（差异只在标点/空格/连字符 → 零风险自动改）
        s = sig(d)
        if s and s in sig_idx:
            rec["fix"] = sig_idx[s]
            buckets["A1_强匹配"].append(rec)
            continue

        # A2 弱匹配：互为子串（需人工确认，禁止自动改 —— 可能语义不同）
        sub = []
        if len(s) >= 6:
            for n in allmd:
                ns = sig(n)
                if ns and ns != s and (s in ns or ns in s) and abs(len(ns) - len(s)) <= 6:
                    sub.append(n)
        if sub:
            rec["fix"] = sorted(sub, key=lambda x: abs(len(sig(x)) - len(s)))[:5]
            rec["ambiguous"] = len(sub) > 1
            buckets["A2_弱匹配"].append(rec)
            continue

        # B 类：系统引用
        if SYS_PAT.search(d) or len(s) < 4:
            buckets["B_系统引用"].append(rec)
            continue

        buckets["D_真死链"].append(rec)

    for k in ["A1_强匹配", "A2_弱匹配", "C_编号引用", "B_系统引用", "D_真死链"]:
        v = buckets[k]
        occ = sum(r["occ"] for r in v)
        print(f"{'='*70}\n【{k}】{len(v)} 个 / 出现 {occ} 次\n{'='*70}")
        for r in v[:40]:
            tag = "  ⚠️多候选" if r.get("ambiguous") else ""
            fx = r.get("fix")
            fx_s = ""
            if fx:
                fx_s = " → " + (fx[0] if len(fx) == 1 else f"[{len(fx)}候选] {fx[0]} | {fx[1] if len(fx)>1 else ''}")
            print(f"  {r['occ']:>4}次/{r['files']:>3}文件  {r['link']}{fx_s}{tag}")
        if len(v) > 40:
            print(f"  … 另有 {len(v)-40} 个")
        print()

    if "--json" in sys.argv:
        out = sys.argv[sys.argv.index("--json") + 1]
        with open(out, "w", encoding="utf-8") as f:
            json.dump(buckets, f, ensure_ascii=False, indent=2)
        print(f"📄 明细已导出 → {out}")


if __name__ == "__main__":
    main()
