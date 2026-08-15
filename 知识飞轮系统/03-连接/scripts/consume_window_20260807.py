# -*- coding: utf-8 -*-
"""消费 2026-08-07 漏窗：将 15 篇 IMA 真源 media_id 写入 ima_intake_state.json。

规则：
1. 15 条真源全部标 source=ima_true / ima_source_pending=false，occupies_new_quota=false（消费漏窗，不占新配额）。
2. 08-06 的 web_publicsource 降级条目保留（笔记为独立主题，仍是有效资产），但 ima_source_pending 由 true -> false，
   并加 resolved_note 说明已由 2026-08-07 真源补录消解。
3. 清除 pending_windows 中 2026-08-07 窗口，转入 consumed_windows 留痕。
4. schema 升 v1.13；ima_status -> runtime_healthy_consumed_2026-08-07。
"""
import io
import json
from datetime import datetime, timedelta, timezone

P = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/ima_intake_state.json"
CST = timezone(timedelta(hours=8))
PREFIX = "wechatarticle_62fe55a7567bc291dfbbee29900b27c3_"


def ts(s):
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=CST).timestamp() * 1000)


NEW = {
    # A1 合同文书AI助手（3 篇，create_time 为窗口内近似值）
    "7312048136419112": [
        ("e921fdb82b9eee4ed8770468e5a09375", "教育培训合同（范本与审查要点）", "2026-08-06 09:00", 8, True),
        ("436ab0a61d0542a9631926029ef00626", "合同风险防控的60个关键点", "2026-08-06 08:30", 9, True),
        ("79e4947cef4236217120d2d07bf630ec", "保证合同纠纷实务100问", "2026-08-05 08:30", 9, True),
    ],
    # B 律师AI助手
    "7312042960642489": [
        ("045790244569a64fbdb53aad2e8d6041", "律师办理保证担保业务操作指引（2026）（试行）", "2026-08-07 09:24", 9, False),
        ("51c5719ae3494af3b7832921c467b4dc", "律师办理债权人接受担保业务操作指引（2026）（试行）", "2026-08-06 09:19", 9, False),
        ("4371ac546302e0eafe209f38cfb01736", "律师代理竞业限制纠纷案件操作指引（试行）（2025）", "2026-08-03 09:16", 9, False),
    ],
    # B 人伤法律实务助手
    "7312035322822509": [
        ("2484434f12695819531fc337e66538ed", "医疗过错、医疗事故与医疗事故罪：三层法律逻辑", "2026-08-06 17:13", 9, False),
        ("b3a98225b891ad21ded2f98b68fb4c96", "工伤保险、雇主责任险、团体意外险和安责险分别解决什么问题", "2026-08-04 09:00", 8, False),
        ("07aefcc3f07cd5e9c62fc6c1ed257c21", "从5094件案件、82%医方败诉率看医疗纠纷", "2026-08-03 20:03", 9, False),
    ],
    # B 合规与政府监管AI助手
    "7333014572917409": [
        ("e6539073ce5e159d89de27fa2adb87b3", "医院建了一柜子制度，为什么还是被罚？", "2026-08-07 08:58", 9, False),
        ("7dd404723976f825f2856be19583d63a", "合规检查并不复杂，每季度一次就够了", "2026-08-04 07:33", 8, False),
        ("4ae189f269a5655ae33dba740a1857be", "操作指引-公司被吊销未注销执行操作指引", "2026-08-05 08:00", 9, False),
    ],
    # B 慈善组织合规AI助手
    "7311644304633438": [
        ("0926cf0384e442252e131fb4fc9bf1da", "社会组织换届要点分析", "2026-07-22 17:55", 8, False),
        ("b1f8ed18452f5f12cd5597df5362e3e5", "微小机构月捐，为了生存，也为了发展", "2026-08-03 19:52", 8, False),
        ("0aa3142242a130df4ad05207386e336b", "韩红爱心慈善基金会的高管该不该拿高薪", "2026-08-01 10:27", 8, False),
    ],
}

NOW = "2026-08-07T11:22"

d = json.load(io.open(P, encoding="utf-8"))

added, dedup_skipped, resolved = 0, 0, 0
for kb, items in NEW.items():
    lib = d["libraries"][kb]
    ing = lib.setdefault("ingested", [])
    exist = {x.get("media_id") for x in ing if isinstance(x, dict)}
    # 消解 08-06 降级标记
    for x in ing:
        if isinstance(x, dict) and x.get("ima_source_pending") is True:
            x["ima_source_pending"] = False
            x["resolved_at"] = NOW
            x["resolved_note"] = (
                "2026-08-07 已用 IMA 真源完成该库 3 篇补录；本条降级笔记主题独立、内容有效，予以保留，"
                "不再等待 IMA 原文替换。"
            )
            resolved += 1
    for rawid, title, tstr, val, approx in items:
        mid = PREFIX + rawid + kb
        if mid in exist:
            dedup_skipped += 1
            continue
        rec = {
            "media_id": mid,
            "title": title,
            "create_time": ts(tstr),
            "ingested_at": NOW,
            "value": val,
            "source": "ima_true",
            "ima_source_pending": False,
            "window": "2026-08-07",
            "occupies_new_quota": False,
        }
        if approx:
            rec["create_time_approx"] = True
        ing.append(rec)
        exist.add(mid)
        added += 1

# 清除并留痕 2026-08-07 漏窗
pw = d.get("pending_windows", [])
consumed = [w for w in pw if w.get("date") == "2026-08-07"]
d["pending_windows"] = [w for w in pw if w.get("date") != "2026-08-07"]
for w in consumed:
    w["a1_done"] = 3
    w["b_done"] = 12
    w["total_done"] = 15
    w["consumed_at"] = NOW
    w["consumed_by"] = "automation-1783920420205 v1.13 续跑会话（用户指令：补上漏掉的 A1/B 共 15 篇，不占新配额）"
    w["fault_resolution"] = (
        "配置态故障自愈后，续跑新会话中 mcp__ima-mcp__* 已挂载；"
        "并修正 media_id 构造（32 位 rawid + kb_id，前会话 8 位截断导致 220030 假失败），15 篇全部 fetch 成功。"
    )
    w["status"] = "consumed_full"
d.setdefault("consumed_windows", []).extend(consumed)

bpb = d.get("b_pending_backfill")
if isinstance(bpb, dict):
    bpb["status"] = "resolved_ima_true_source_2026-08-07"
    bpb["resolved_at"] = NOW
    bpb["resolved_note"] = (
        "2026-08-07 IMA 恢复，4 库各取 3 篇真源共 12 篇落盘（蓝红双视角笔记），"
        "08-06 降级笔记作为独立主题保留，ima_source_pending 全部消解为 false。"
    )

d["schema"] = "ima_intake_state/v1.13"
d["updated"] = NOW
d["ima_status"] = "runtime_healthy_consumed_2026-08-07"
d["note"] = (
    "2026-08-07 11:22 消费漏窗完成：A1 3 + B 12 = 15 篇 IMA 真源全部入库，"
    "occupies_new_quota=false（不占新配额）。关键修正：media_id = 前缀 + 32位rawid + kb_id。"
)

t = d.setdefault("totals", {})
t["A1_done"] = len(d["libraries"]["7312048136419112"]["ingested"])
t["B_done"] = sum(
    len(d["libraries"][k]["ingested"])
    for k in ["7312042960642489", "7312035322822509", "7333014572917409", "7311644304633438"]
)
t["all_pending"] = False
t["last_run"] = NOW
t["window_consumed"] = "2026-08-07T11:22"

d.setdefault("resolved_in_continuation", {})["window_consumed_2026-08-07"] = (
    "A1 3 篇（教育培训合同/合同风险防控60点/保证合同100问）+ B 12 篇（律师·人伤·合规·慈善 各3）"
    "全部以 IMA 真源摄入并落双视角笔记；新增规则卡 R-HT-037~039、R-HG-003；不占新配额。"
)

io.open(P, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, indent=2))
print("added=%d dedup_skipped=%d downgrade_resolved=%d" % (added, dedup_skipped, resolved))
print("A1_done=%s B_done=%s pending_windows=%d consumed_windows=%d"
      % (t["A1_done"], t["B_done"], len(d["pending_windows"]), len(d["consumed_windows"])))
for k, v in d["libraries"].items():
    print(" ", k, v.get("name"), len(v["ingested"]))
