#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
外部链接白名单生成器 v1.0.0（2026-09-08）
==========================================
背景：全库 155 个「死链」中，99 个（212 次）目标其实**真实存在**，
      只是位于 LawKB 之外（桌面办案系统 / Documents / IMA 缓存）。
      Obsidian wiki 链接跨 vault 本就无效，但这不等于链接错了 ——
      与 SKILL 坑 14 同源：**「MISS」不等于「不存在」**。

处置：建立外部白名单（指纹 → 外部真实路径），门禁命中即放行，
      同时保留路径可追溯。真·无目标的才留在死链里交人工决策。

产出：_external_links_whitelist.json
"""
import json
import os
import re
import sys

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT = os.path.join(ROOT, "02-提炼/审判要件卡/_external_links_whitelist.json")
SCAN_ROOTS = ["/Users/chenyouqiang/Desktop",
              "/Users/chenyouqiang/Documents"]
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".workbuddy", ".Trash"}

def sig(s):
    return re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", str(s)).lower()

# ── 1. 扫外部库建索引 ──────────────────────────────────────
ext = {}
for root in SCAN_ROOTS:
    for r, ds, fs in os.walk(root):
        ds[:] = [x for x in ds if x not in SKIP_DIRS and not x.startswith(".")]
        # 跳过 LawKB 自身（它属于库内，本来就该命中）
        if "知识飞轮系统" in r and r.startswith(ROOT):
            continue
        for f in fs:
            base = os.path.splitext(f)[0]
            ext.setdefault(sig(base), []).append(os.path.join(r, f))
print(f"外部文件指纹索引：{len(ext)} 条")

# ── 2. 读死链明细，分离「外部可定位」与「真无目标」──────────
data = json.load(open(os.path.join(ROOT, "02-提炼/审判要件卡/_deadlinks_20260908.json"),
                      encoding="utf-8"))
cands = data["D_真死链"] + data["B_系统引用"] + data["A2_弱匹配"] + data["A1_强匹配"]

whitelist, truly = {}, []
for r in cands:
    s = sig(r["link"])
    hit = ext.get(s)
    if hit and len(s) >= 4:
        # 优先取 LawKB 之外的路径（排除库内自指）
        lawkb = [p for p in hit if p.startswith(ROOT)]
        pick = (hit if not lawkb else [p for p in hit if not p.startswith(ROOT)] or hit)[0]
        whitelist[s] = {"link": r["link"], "path": pick, "occ": r["occ"]}
    else:
        truly.append(r)

print(f"✅ 外部可定位（入白名单）：{len(whitelist)} 个")
print(f"❌ 全盘无目标（留死链）：{len(truly)} 个")

meta = {
    "_meta": {
        "version": "1.0.0",
        "built": "2026-09-08",
        "note": "外部链接白名单：目标真实存在但位于 LawKB 之外，门禁放行。",
        "scan_roots": SCAN_ROOTS,
    },
    "entries": whitelist,
}
json.dump(meta, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"📄 已写入 → {OUT}")

json.dump(truly, open(os.path.join(ROOT, "02-提炼/审判要件卡/_deadlinks_truly_20260908.json"),
                      "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("📄 真无目标清单 → _deadlinks_truly_20260908.json")
