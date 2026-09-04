# -*- coding: utf-8 -*-
"""生成 09-02/03/04 三窗合并回补的最终选文清单（每库 9 篇，共 45 篇）。

v2（2026-09-04）：产出改落 LawKB 实体路径（子代理沙箱看不到主控 /tmp）。
"""
import json, sys
sys.path.insert(0, "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/03-连接/scripts")
from _backfill_crawl_0904 import raw32  # noqa

FW = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/"
d = json.load(open(FW + "03-连接/scripts/_backfill_cands_0904.json"))
st = json.load(open(FW + "ima_intake_state.json"))
broken = {raw32(x.get("media_id") if isinstance(x, dict) else x) for x in st["failed_220030"]}
ing = set()
for lib in st["libraries"].values():
    for x in lib.get("ingested", []):
        ing.add(raw32(x.get("media_id") if isinstance(x, dict) else str(x)))

# 人工选文：库名 -> [候选下标]
PICKS = {
    "合同文书AI助手":       [9, 10, 44, 22, 23, 18, 26, 15, 35],
    "律师AI助手":           [1, 8, 12, 19, 21, 24, 30, 40, 41],
    "人伤法律实务助手":     [0, 1, 2, 4, 5, 6, 22, 24, 40],
    "合规与政府监管AI助手": [44, 43, 38, 3, 11, 20, 22, 26, 28],
    "慈善组织合规AI助手":   [4, 16, 19, 17, 22, 9, 15, 33, 38],
}
RANGES = {
    "合同文书AI助手":       ("HT", 179, "合同风险"),
    "律师AI助手":           ("LN", 46,  "律师实务"),
    "人伤法律实务助手":     ("PI", 243, "人伤法"),
    "合规与政府监管AI助手": ("HG", 62,  "合规监管"),
    "慈善组织合规AI助手":   ("CF", 101, "慈善"),
}

out, problems = {}, []
for lib, idxs in PICKS.items():
    dom, start, folder = RANGES[lib]
    items = d["candidates"][lib]
    picked = []
    for n, i in enumerate(idxs):
        it = items[i]
        r = raw32(it["media_id"])
        if r in broken:
            problems.append("[X] %s 命中220030: %s" % (lib, it["title"])); continue
        if r in ing:
            problems.append("[X] %s 已摄入: %s" % (lib, it["title"])); continue
        picked.append({
            "rule_id": "R-%s-%03d" % (dom, start + n),
            "folder": folder,
            "media_id": it["media_id"],
            "title": it["title"],
            "lib": lib,
            "lib_id": it["lib_id"],
            "file_size": it.get("file_size", ""),
        })
    out[lib] = picked
    print("%-22s 选 %d 篇  %s-%03d ~ %s-%03d"
          % (lib, len(picked), dom, start, dom, start + len(picked) - 1))

if problems:
    print("\n[!] 问题：")
    for p in problems:
        print("  ", p)
else:
    print("\n[OK] 45 篇全部通过 220030 / 已摄入 双重校验")

dst = FW + "运维/_回补作业/2026-09-04/选文清单.json"
json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("SAVED:", dst)
print("TOTAL:", sum(len(v) for v in out.values()))
