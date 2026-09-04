# -*- coding: utf-8 -*-
"""
09-02/03/04 三窗合并回补 · 状态回写（幂等，支持 dry-run）

铁律：
  ✅ 只回写「已取到全文并产出采集笔记+规则卡」的 15 篇
  ⛔ 30 篇因 IMA 通道掉线未取全文，绝不写 ingested（摄入中断铁律）
"""
import json, os, sys, time, shutil

FW = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/"
STATE = FW + "ima_intake_state.json"
PICK = FW + "运维/_回补作业/2026-09-04/选文清单.json"
CANDS = FW + "03-连接/scripts/_backfill_cands_0904.json"
DONE = "/tmp/lawkb_done_0904.json"

APPLY = "--apply" in sys.argv
NOW = time.strftime("%Y-%m-%dT%H:%M")

d = json.load(open(STATE, encoding="utf-8"))
pick = json.load(open(PICK, encoding="utf-8"))
cands = json.load(open(CANDS, encoding="utf-8"))
done = json.load(open(DONE, encoding="utf-8"))

# media_id -> create_time
ct_map = {}
for lib, items in cands["candidates"].items():
    for it in items:
        ct_map[it["media_id"]] = it.get("create_time", "")

done_rids = {x["rule_id"] for x in done}

# 已入库集合（防重复）
existing = set()
for lid, info in d["libraries"].items():
    for x in info.get("ingested", []):
        existing.add(x.get("media_id") if isinstance(x, dict) else str(x))

LIBID = {"合同文书AI助手": "7312048136419112", "律师AI助手": "7312042960642489",
         "人伤法律实务助手": "7312035322822509", "合规与政府监管AI助手": "7333014572917409",
         "慈善组织合规AI助手": "7311644304633438"}

added_by_lib = {}
skipped = []
for lib, items in pick.items():
    for it in items:
        if it["rule_id"] not in done_rids:
            continue
        mid = it["media_id"]
        if mid in existing:
            skipped.append("已存在 " + it["rule_id"])
            continue
        entry = {
            "media_id": mid,
            "title": it["title"],
            "create_time": ct_map.get(mid, ""),
            "ingested_at": NOW,
            "value": 8,
            "rule_id": it["rule_id"],
            "batch": "backfill-2026-09-04",
        }
        d["libraries"][LIBID[lib]]["ingested"].append(entry)
        existing.add(mid)
        added_by_lib[lib] = added_by_lib.get(lib, 0) + 1

# totals 重算
total = sum(len(v.get("ingested", [])) for v in d["libraries"].values())
old_total = d["totals"].get("ingested_total")
d["totals"]["ingested_total"] = total

# ---- 漏窗更新 ----
log_entry = {
    "at": NOW,
    "added": len(done),
    "note": ("三窗合并回补第 1 批：IMA 通道 13:00-13:47 可用期间实补 15 篇（合同库 9 + 律师库 6），"
             "均已完成『取全文→采集笔记→规则卡』全链路。13:47 后 IMA MCP 从工具索引与连接器注册表"
             "（connector-states.json 8 条目已无 ima-mcp）双双消失，属配置态故障，须 UI 重新授权，"
             "手改无效 → 剩余 30 篇（律师3/人伤9/合规9/慈善9）本轮无法取全文，按铁律**不写 ingested**。"
             "选文清单已持久化至 运维/_回补作业/2026-09-04/选文清单.json，通道恢复后可一键续跑。"),
    "cards": sorted(done_rids),
}
for w in d["pending_windows"]:
    wid = w.get("window_id", "")
    if wid == "w_2026-09-02_A1B_channel_down":
        w["total_done"] = 15
        w["status"] = "backfilled"
        w.setdefault("backfill_log", []).append(log_entry)
        w["attribution_note"] = ("按总量口径先行关闭：实补 15 篇，但分库分布为 合同9/律师6，"
                                 "与名义的 3+3+3+3+3 不同（人伤/合规/慈善本轮 0 篇，顺延至 09-03/09-04 窗）。")
    elif wid in ("w_2026-09-03_A1B_channel_down", "w_2026-09-04_A1B_channel_down"):
        w["status"] = "open"
        w["done"] = 0
        w.setdefault("backfill_log", []).append({
            "at": NOW, "added": 0,
            "note": "本轮通道中断未补（见 09-02 窗 backfill_log）；窗口保持 open，待 IMA UI 重新授权后续跑。",
        })

# ---- 断点（供下轮续跑） ----
d["checkpoint"] = {
    "session_id": "backfill-2026-09-04-batch1",
    "stage": "B",
    "status": "paused_channel_down",
    "started_at": "2026-09-04T13:00",
    "finished_at": NOW,
    "done": ["合同文书AI助手(9/9)", "律师AI助手(6/9)"],
    "remaining": {
        "律师AI助手": ["R-LN-052", "R-LN-053", "R-LN-054"],
        "人伤法律实务助手": ["R-PI-243 ~ R-PI-251 (9)"],
        "合规与政府监管AI助手": ["R-HG-062 ~ R-HG-070 (9)"],
        "慈善组织合规AI助手": ["R-CF-101 ~ R-CF-109 (9)"],
    },
    "resume_assets": {
        "选文清单": "知识飞轮系统/运维/_回补作业/2026-09-04/选文清单.json",
        "作业规范": "知识飞轮系统/运维/_回补作业/2026-09-04/作业规范.md",
        "候选池": "知识飞轮系统/03-连接/scripts/_backfill_cands_0904.json",
        "raw兜底目录": "知识飞轮系统/01-采集/IMA缓存/2026-09-04/_raw/",
    },
    "blocking": "ima-mcp 配置态故障：connector-states.json 无 ima-mcp 条目，须 UI 重新授权/重新添加",
}
d["updated"] = NOW

print("=" * 70)
print("DRY-RUN" if not APPLY else "APPLY")
print("新增 ingested：")
for k, v in added_by_lib.items():
    print("   %-22s %d 篇" % (k, v))
print("   ingested_total: %s -> %s" % (old_total, total))
print("跳过：", skipped or "无")
print("09-02 窗 -> backfilled(15) ; 09-03/09-04 -> open(0)")
print("=" * 70)

if APPLY:
    ts = time.strftime("%Y%m%d-%H%M%S")
    bak = STATE + ".bak-" + ts
    shutil.copy2(STATE, bak)
    json.dump(d, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("已写入:", STATE)
    print("备份:", bak)
else:
    print("（未写入，加 --apply 执行）")
