#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""埋点看门狗（9655 驾驶舱 D9 / 飞轮命中率 · 死亡告警）

═══════════ 为什么要有这个 ═══════════
2026-10-22 复盘发现三处埋点全部静默断链，而**没有任何机制会告诉你它断了**：
  · card_consumption.jsonl  1773 条，其中 1769 条在 2026-09，10 月仅 4 条
  · frontdesk_events.jsonl  15 条，全部 2026-10-09（9 条是测试数据）
  · grill_events.jsonl      4 条（低频但有效）

断链不可怕，**断了自己不知道**才可怕——驾驶舱会一直显示"绿"，直到你哪天
真去查才发现三个月没数据。本脚本就是给埋点装一个「心电监护」：
连续 N 天无新增 → 直接喊出来。

═══════════ 判定 ═══════════
对每个埋点算三件事：
  1. last_ts        最后一条记录的时间
  2. silent_days    距今天数
  3. recent_count   最近 N 天（默认 3）新增条数
状态：
  ok      recent_count > 0
  stale   recent_count == 0 且 silent_days < 30（可能只是没用到，需留意）
  dead    recent_count == 0 且 silent_days >= 30（基本可断定断了）
  missing 文件不存在

═══════════ 用法 ═══════════
    python3 metrics_watchdog.py              # 人读输出
    python3 metrics_watchdog.py --json       # 机器读（供 automation / 驾驶舱）
    python3 metrics_watchdog.py --days 5     # 自定义静默窗口
退出码：0=全 ok；1=有 stale/dead/missing（便于 automation 判定是否升级告警）

═══════════ 注意（不伪造）═══════════
本脚本只读埋点文件，**不补数据、不造记录**。它喊"断了"时，正确动作是去修上游
发射点，不是往 jsonl 里灌假记录。
"""
import os
import re
import sys
import json
import datetime

HOME = os.path.expanduser("~")
M = os.path.join(HOME, ".workbuddy", "metrics")

TARGETS = [
    {
        "key": "card_consumption",
        "path": os.path.join(M, "card_consumption.jsonl"),
        "label": "卡片消费（飞轮命中率真值）",
        "emitter": "emit_card_consumption.py",
        "upstream": "技能/自动化在真实消费某张卡时主动调用（被动发射器）",
        "fix_hint": "根因通常是「没人调用」而非脚本损坏：检查交付流水线是否仍含 emit 调用",
    },
    {
        "key": "frontdesk_events",
        "path": os.path.join(M, "frontdesk_events.jsonl"),
        "label": "前台唤醒/分诊遥测（D9）",
        "emitter": "frontdesk_wake_hook.py（UserPromptSubmit 钩子）",
        "upstream": "钩子 + 模式文件 frontdesk_wake_mode 须为 on",
        "fix_hint": "①查 frontdesk_wake_mode 是否 on；②查 settings.json hooks 是否挂载",
    },
    {
        "key": "grill_events",
        "path": os.path.join(M, "grill_events.jsonl"),
        "label": "Grill 门禁事件",
        "emitter": "grill_gate_hook.py（PreToolUse/PostToolUse 钩子）",
        "upstream": "钩子拦截法律域技能时写",
        "fix_hint": "低频属正常（只有被拦截才写）；>30 天无记录才需查钩子是否仍挂",
    },
    {
        "key": "协同效果日志",
        "path": os.path.join(HOME, "Documents", "LawKB", "知识飞轮系统",
                             "05-调用", "协同效果日志.md"),
        "label": "飞轮命中率统计源 · md 台账",
        "emitter": "人工/技能在交付时按流水线第 8 步②追加一行",
        "upstream": "法律文书docx交付流水线·第 8 步②（与双目录同步同批次）",
        "fix_hint": "根因是「交付时忘了写」，不是文件损坏："
                    "查流水线第 8 步是否被执行；协同效果月报（每月28日）全靠这份日志，"
                    "漏记即月报命中率失真",
    },
]


def parse_ts(line):
    """从一行里尽量捞出时间戳。

    两种来源都要吃得下：
      ① jsonl 埋点（card_consumption / frontdesk / grill）——按 JSON 键取
      ② markdown 台账（协同效果日志 `- [2026-09-29 12:38] …`）——正则兜底
    早期只认 JSON，导致 md 台账永远算不出时间戳（会拿 mtime 兜底，静默天数失真）。
    """
    try:
        obj = json.loads(line)
    except Exception:
        obj = None
    if isinstance(obj, dict):
        for k in ("ts", "timestamp", "time", "at", "recorded_at"):
            v = obj.get(k)
            if isinstance(v, str) and len(v) >= 10:
                for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S",
                            "%Y-%m-%d %H:%M", "%Y-%m-%d"):
                    try:
                        return datetime.datetime.strptime(
                            v[:len(datetime.datetime.now().strftime(fmt))], fmt)
                    except Exception:
                        continue
    # ② markdown 行首时间戳：[YYYY-MM-DD HH:MM] / [YYYY-MM-DD]
    m = re.search(r"\[(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}:\d{2}))?\]", line)
    if m:
        base = m.group(1) + (" " + m.group(2) if m.group(2) else " 00:00")
        fmt = "%Y-%m-%d %H:%M" if m.group(2) else "%Y-%m-%d %H:%M"
        try:
            return datetime.datetime.strptime(base, fmt)
        except Exception:
            return None
    return None


def scan_one(t, days):
    path = t["path"]
    if not os.path.exists(path):
        return {
            "key": t["key"], "label": t["label"], "status": "missing",
            "path": path, "last_ts": None, "silent_days": None,
            "recent_count": 0, "total": 0,
            "emitter": t["emitter"], "upstream": t["upstream"], "fix_hint": t["fix_hint"],
        }

    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    total = 0
    recent = 0
    last = None
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ts = parse_ts(line)
            if ts is None:
                # 无时间戳的行（表头/frontmatter/注释）：不计为记录
                # 早期版本在此处 total+=1，导致 md 台账的总数把标题也数进去
                continue
            total += 1
            if last is None or ts > last:
                last = ts
            if ts >= cutoff:
                recent += 1

    if last is None:
        last = datetime.datetime.fromtimestamp(os.path.getmtime(path))

    silent = (datetime.datetime.now() - last).days

    if recent > 0:
        status = "ok"
    elif silent >= 30:
        status = "dead"
    else:
        status = "stale"

    return {
        "key": t["key"], "label": t["label"], "status": status,
        "path": path,
        "last_ts": last.strftime("%Y-%m-%d %H:%M"),
        "silent_days": silent,
        "recent_count": recent,
        "total": total,
        "window_days": days,
        "emitter": t["emitter"], "upstream": t["upstream"], "fix_hint": t["fix_hint"],
    }


ICON = {"ok": "🟢", "stale": "🟡", "dead": "🔴", "missing": "⚫"}


def main():
    argv = sys.argv[1:]
    days = 3
    if "--days" in argv:
        try:
            days = int(argv[argv.index("--days") + 1])
        except Exception:
            pass

    rows = [scan_one(t, days) for t in TARGETS]
    bad = [r for r in rows if r["status"] != "ok"]

    payload = {
        "checked_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "window_days": days,
        "policy": "最近 N 天 0 新增 → stale；静默 ≥30 天 → dead。本脚本不补数据。",
        "overall": "alert" if bad else "ok",
        "alerts": len(bad),
        "items": rows,
    }

    if "--json" in argv:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
    else:
        print(f"══ 埋点看门狗 · {payload['checked_at']} · 窗口 {days} 天 ══")
        for r in rows:
            print(f"\n{ICON.get(r['status'],'·')} {r['key']}（{r['label']}）")
            print(f"   状态：{r['status']}   最后记录：{r['last_ts']}   静默：{r['silent_days']} 天")
            print(f"   近 {days} 天新增：{r['recent_count']}   累计：{r['total']} 条")
            if r["status"] != "ok":
                print(f"   发射点：{r['emitter']}")
                print(f"   上游条件：{r['upstream']}")
                print(f"   🔧 处置：{r['fix_hint']}")
        print(f"\n══ 结论：{'🔴 有 %d 项异常' % len(bad) if bad else '🟢 全部在跳'} ══")

    # 落一份快照供驾驶舱读取（覆盖写，属于缓存非事实源）
    try:
        out = os.path.join(M, "metrics_watchdog_report.json")
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
    except Exception:
        pass

    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
