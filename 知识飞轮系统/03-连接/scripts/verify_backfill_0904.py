# -*- coding: utf-8 -*-
"""核验 2026-09-04 回补产出是否完整落盘（卡片 + 采集笔记），供状态回写使用。"""
import json, os

FW = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/"
pick = json.load(open(FW + "运维/_回补作业/2026-09-04/选文清单.json"))
CARD_DIR = FW + "06-沉淀/裁判规则库/"
NOTE_DIR = FW + "01-采集/IMA缓存/2026-09-04/"

LIB_KEY = {"合同文书AI助手": "合同库", "律师AI助手": "律师库",
           "人伤法律实务助手": "人伤库", "合规与政府监管AI助手": "合规库",
           "慈善组织合规AI助手": "慈善库"}

# 已建卡片索引：<folder>/<rule_id>-*.md
cards = {}
for dp, _, fns in os.walk(CARD_DIR):
    for fn in fns:
        if fn.startswith("R-") and fn.endswith(".md"):
            rid = fn.split("-")
            if len(rid) >= 3:
                cards["-".join(rid[:3])] = os.path.join(dp, fn)

rows, done = [], []
for lib, items in pick.items():
    for it in items:
        rid = it["rule_id"]
        c = cards.get(rid)
        note_ok = False
        if os.path.isdir(NOTE_DIR):
            pass
        rows.append((rid, lib, it["title"], bool(c), note_ok))

print("rule_id    库        卡片  标题")
print("-" * 92)
ok = 0
for rid, lib, title, has_card, _ in rows:
    if has_card:
        ok += 1
        done.append({"lib": lib, "rule_id": rid, "title": title, "path": cards[rid]})
    print("%-11s %-10s %s  %s" % (rid, LIB_KEY[lib], "OK " if has_card else "-- ", title[:46]))
print("-" * 92)
print("卡片完成 %d / %d" % (ok, len(rows)))

# 采集笔记清单
notes = sorted(os.listdir(NOTE_DIR)) if os.path.isdir(NOTE_DIR) else []
notes = [n for n in notes if not n.startswith("_")]
print("\n采集笔记 %d 篇：" % len(notes))
for n in notes:
    print("  ", n)

json.dump(done, open("/tmp/lawkb_done_0904.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\nSAVED /tmp/lawkb_done_0904.json")
