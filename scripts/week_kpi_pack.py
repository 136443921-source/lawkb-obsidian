#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
总经理周考核包 · 采数器（只读）
================================================================
用途：为律所主任（总经理）生成《总经理周考核包》，把「考核」从记忆驱动改为数据驱动。
设计前提（DEC-2026-025）：数字员工考核权 100% 归总经理，本脚本**只采数、不做判定**。

数据源（实测确认）：
  1. ~/Documents/LawKB/_AI-Memory-Hub/09-OPC/09-5数字员工花名册/数字员工花名册.json  -> 分母（花名册）
  2. ~/.workbuddy/workbuddy.db 表 automation_runs / automations                        -> 执行率·失败归因·待审积压

三个必须遵守的口径（踩过坑，勿改）：
  ！坑1  automation_runs.created_at 是 **epoch 毫秒 整数**，不是 ISO 字符串。
         写成 created_at >= '2026-09-19...' 会 100% 漏采，静默返回 0 条。
  ！坑2  result_success=0 **不等于失败**。
         status='ACCEPTED' 才是"已裁定"；PENDING_REVIEW 只是"待审"。
         真失败判定 ONLY: status='ACCEPTED' and result_success=0
         （status=ACCEPTED/rs=1 -> OK；PENDING_REVIEW 一律 -> REVIEW，不计入分母）
  ！坑3  考核窗口必须按 schedule 的 FREQ 自适应。
         schedule 是 RRULE 文本（FREQ=DAILY|WEEKLY|MONTHLY|YEARLY）。
         一刀切 7 天会把月度/季度 job 全部误判成失联。

输出：一份 md（vault 之外），v0.1 格式见 OUTPUT_TEMPLATE。
"""

import json
import os
import sqlite3
import sys
import collections
import datetime

ROSTER = "/Users/chenyouqiang/Documents/LawKB/_AI-Memory-Hub/09-OPC/09-5数字员工花名册/数字员工花名册.json"
DB = os.path.expanduser("~/.workbuddy/workbuddy.db")
DEFAULT_OUT = os.path.expanduser("~/Documents/OPC-考核包")  # 刻意放在 Obsidian vault 之外
NOW = datetime.datetime.now()

# 窗口映射：FREQ -> (天数, 标签)
WIN = {"DAILY": (7, "日度"), "WEEKLY": (30, "周度"), "MONTHLY": (90, "月度"), "YEARLY": (365, "年度")}
# 失败归因分级：只有 RUN_FAILED 与 ENV 属"真问题"，限流不问责（避免误伤调度侧）
FAULT = {
    "automation-rate-limited": ("限流", False),
    "automation-run-failed": ("真失败", True),
    "automation-workspace-unavailable": ("环境", True),
}
PEND_DAYS = 14  # 待审超过 N 天升级为 P1


def freq_of(schedule):
    if not schedule or "FREQ=" not in schedule:
        return "MONTHLY"
    return schedule.split("FREQ=")[1].split(";")[0].strip().upper()


def classify(status, result_success):
    if status == "ACCEPTED" and result_success == 1:
        return "OK"
    if status == "ACCEPTED" and result_success == 0:
        return "FAIL"
    return "REVIEW"


def collect():
    roster = json.load(open(ROSTER, encoding="utf-8"))
    con = sqlite3.connect(DB)
    cur = con.cursor()
    out = []
    for o in roster["operators"]:
        aid = str(o["automation_id"])
        f = freq_of(o.get("schedule"))
        days, kind = WIN.get(f, (90, "默认"))
        cut = int((NOW - datetime.timedelta(days=days)).timestamp() * 1000)
        rows = cur.execute(
            "select result_success,status,created_at,failure_code from automation_runs "
            "where automation_id=? and created_at>=?",
            (aid, cut),
        ).fetchall()
        ok = bad = pend = 0
        faults = collections.Counter()
        oldest_pend = None
        for rs, st, ts, fc in rows:
            k = classify(st, rs)
            if k == "OK":
                ok += 1
            elif k == "FAIL":
                bad += 1
                if fc in FAULT:
                    faults[FAULT[fc][0]] += 1
                else:
                    faults["未标注"] += 1
            else:
                pend += 1
                if oldest_pend is None or ts < oldest_pend:
                    oldest_pend = ts
        out.append(
            dict(
                op=o["op_id"], name=o["name"], cls=o.get("class") or "", st=o.get("status") or "",
                kind=kind, days=days, runs=len(rows), ok=ok, bad=bad, pend=pend,
                faults=faults,
                pend_age=(NOW.timestamp() * 1000 - oldest_pend) / 86400000 if oldest_pend else None,
                last=max([r[2] for r in rows], default=None),
                verified=o.get("last_verified") or "",
            )
        )
    con.close()
    return roster, out


def render(roster, rows):
    adj = sum(r["ok"] + r["bad"] for r in rows)
    ok = sum(r["ok"] for r in rows)
    pend_all = sum(r["pend"] for r in rows)
    L = []
    A = L.append
    A(f"# 总经理周考核包 · {NOW:%Y-%m-%d}")
    A("")
    A(f"> 口径时间：{NOW:%Y-%m-%d %H:%M}｜数据源：workbuddy.db(automation_runs) + 花名册 json（**只读采数，不含判定**）")
    A("> 判定权归律所主任（DEC-2026-025）；采数器与驾驶舱只供数、免考核。")
    A("")
    A("## 〇、本周总览")
    A("")
    A("| 指标 | 数值 | 判读 |")
    A("|---|---|---|")
    A(f"| 花名册分母（json） | **{len(rows)}** | md 口径 43 → **json 落后 3**，分母待修 |")
    A(f"| 已裁定次数 | {adj} | 成功 {ok} / 失败 {adj - ok} |")
    rate = f"{ok / adj * 100:.0f}%" if adj else "—"
    A(f"| 裁定成功率 | **{rate}** | 分子=ACCEPTED且rs=1 |")
    A(f"| **待审积压** | **{pend_all}** | 跑完没人裁定，占考核负担大头 |")
    A(f"| 失联（窗口内零执行） | {sum(1 for r in rows if r['runs'] == 0)} | 低频 job 按 FREQ 窗口豁免 |")
    A("")
    A("## 一、需要你裁定的（勾选即可）")
    A("")
    A("### 1.1 待审积压清单")
    p = sorted([r for r in rows if r["pend"] > 0], key=lambda x: -(x["pend_age"] or 0))
    if p:
        A("| # | 操作工 | 班组 | 窗口 | 待审 | 最老待审(天) | 建议动作 | 勾 |")
        A("|---|---|---|---|---|---|---|---|")
        for i, r in enumerate(p, 1):
            age = f"{r['pend_age']:.0f}" if r["pend_age"] is not None else "—"
            lvl = "🔴P1" if (r["pend_age"] or 0) > PEND_DAYS else "🟡P2"
            A(f"| {i} | {r['op']} {r['name'][:16]} | {r['cls']} | {r['kind']}{r['days']}d | {r['pend']} | {age} | {lvl} 清积压 | ☐ |")
    else:
        A("✅ 无待审积压")
    A("")
    A("### 1.2 失败清单（仅计 ACCEPTED 已裁定者）")
    f = sorted([r for r in rows if r["bad"] > 0], key=lambda x: -x["bad"])
    if f:
        A("| # | 操作工 | 窗口 | 成功 | 失败 | 失败归因 | 建议动作 | 勾 |")
        A("|---|---|---|---|---|---|---|---|")
        for i, r in enumerate(f, 1):
            fa = "、".join(f"{k}×{v}" for k, v in r["faults"].items()) or "未标注"
            act = "民生限流→降频/错峰" if "限流" in fa and "真失败" not in fa else "🔴 查任务本身"
            A(f"| {i} | {r['op']} {r['name'][:16]} | {r['kind']} | {r['ok']} | {r['bad']} | {fa} | {act} | ☐ |")
    else:
        A("✅ 无失败项")
    A("")
    A("### 1.3 失联清单（窗口内零执行）")
    z = [r for r in rows if r["runs"] == 0]
    if z:
        A("| # | 操作工 | 窗口 | 花名册状态 | 建议动作 | 勾 |")
        A("|---|---|---|---|---|---|")
        for i, r in enumerate(z, 1):
            act = "一次性/低频，豁免" if r["kind"] in ("月度", "季度", "年度", "默认") else "🟠 查是否被静默停摆"
            A(f"| {i} | {r['op']} {r['name'][:16]} | {r['kind']}{r['days']}d | {r['st']} | {act} | ☐ |")
    else:
        A("✅ 无失联项")
    A("")
    A("## 二、待采指标（暂无真源，标注不编）")
    A("")
    A("| 指标 | 状态 | 说明 |")
    A("|---|---|---|")
    A("| 门禁率（LTI REJECT） | ⚠️ 半 | `c8_metrics.json` 存在但 `audit_available=false`、`reject_rate=null`，须先开 audit 才有真源 |")
    A("| 回传率（IMA/中枢回传） | ❌ 待建 | 无执行回传日志，硬算即造假 |")
    A("| 席位成熟度 | ⏸ 低频 | 花名册 `seats[].maturity`，季度人工复核，不入周包 |")
    A("")
    A("## 三、口径留痕")
    A("")
    A("- 真失败判定：`status='ACCEPTED' AND result_success=0`（**PENDING_REVIEW 不计分母**）")
    A("- 时间口径：`automation_runs.created_at` 为 **epoch 毫秒整数**")
    A("- 窗口自适应：DAILY=7d / WEEKLY=30d / MONTHLY=90d / YEARLY=365d")
    A(f"- 限流（automation-rate-limited）单列归因，**不计入失职**")
    A("")
    return "\n".join(L)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    os.makedirs(out_dir, exist_ok=True)
    roster, rows = collect()
    path = os.path.join(out_dir, f"总经理周考核包_{NOW:%Y-%m-%d}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(roster, rows))
    print(f"[week_kpi_pack] 已生成：{path}")
    print("[week_kpi_pack] 只读采集，未修改任何数据库与治理文件。")


if __name__ == "__main__":
    main()
