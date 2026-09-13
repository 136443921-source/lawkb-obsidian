#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
页码偏差修复器（2026-09-12）｜坑 26 补丁
——修 02-提炼 下索引/踩坑文档中按 1-based 取值遗留的书页偏差（Δ 恒 -1）
铁律：书页 = mp[str(PDF页 - 1)]，范围两端都重算，严禁只 ±1。
用法：python _fix_pagemap_drift_20260912.py [--apply]
"""
import re, json, os, sys, shutil

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
MP = json.load(open(f"{BASE}/02-提炼/审判要件卡/贵州类案指南第二卷-页码映射表.json", encoding="utf-8"))
TARGETS = [
    f"{BASE}/02-提炼/审判要件卡/审判要件卡-入库索引-执行异议之诉补拆-2026-09-11.md",
    f"{BASE}/02-提炼/经验卡片/程序知识/批量拆卡流水线-开工前须实操读PDF核实章节标题踩坑-2026-09-09.md",
]
APPLY = "--apply" in sys.argv
PAT = re.compile(r"PDF页(\d+)(?:-(\d+))?（书页(\d+)(?:-(\d+))?）")

total = 0
for p in TARGETS:
    t = open(p, encoding="utf-8").read()
    out, n = [], 0

    def rep(m):
        global n
        a = int(m.group(1)); b = m.group(2)
        ea = MP.get(str(a - 1))
        if ea is None:
            return m.group(0)
        if b:
            eb = MP.get(str(int(b) - 1))
            if eb is None:
                return m.group(0)
            s = f"PDF页{a}-{b}（书页{ea}-{eb}）"
        else:
            s = f"PDF页{a}（书页{ea}）"
        if s != m.group(0):
            n += 1
        return s

    new = PAT.sub(rep, t)
    print(f"{'APPLY' if APPLY else 'DRY-RUN'} {os.path.basename(p)}：将修正 {n} 处")
    total += n
    if APPLY and n:
        open(p, "w", encoding="utf-8").write(new)
print(f"合计 {total} 处")
