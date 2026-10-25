#!/usr/bin/env python3
"""
交付闭环校验器（delivery_closure_gate.py）
==========================================
把「埋点写回」从"靠自觉的软约束"升级为"交付前的硬关卡"。

背景（2026-10-23 复盘）：
card_consumption / grill_events / 协同效果日志 三条链路静默 10 天，根因不是发射器坏，
而是「指令写在流水线第 2.5/8 步，执行时没人真正跑」。故本校验器在交付前强制核对：
  ① card_consumption.jsonl 是否在本次交付时段内有新增
  ② 协同效果日志 是否在本次交付时段内有新增行
任一缺失 → 判定「交付未闭环」，退出码非 0，阻断交付（除非显式 --allow-skip 声明"本次无卡片消费"）。

用法：
  python3 delivery_closure_gate.py --since "YYYY-MM-DD HH:MM" [--expect-cards N] [--allow-no-card]
  --since          本次交付的起始时间（比对这个时间点之后的新增）
  --expect-cards   期望的卡片消费条数（不传则不卡条数，只卡"有没有新增"）
  --allow-no-card  显式声明本次确无卡片消费（会检查协同日志仍必须有新增行）
"""
import os
import sys
import json
import argparse
import datetime

HOME = os.path.expanduser("~")
CARD_JSONL = f"{HOME}/.workbuddy/metrics/card_consumption.jsonl"
COLLAB_LOG = f"/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/05-调用/协同效果日志.md"

def parse_time(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True, help="交付起始时间 YYYY-MM-DD HH:MM")
    ap.add_argument("--expect-cards", type=int, default=None)
    ap.add_argument("--allow-no-card", action="store_true", help="显式声明本次无卡片消费")
    args = ap.parse_args()

    since = parse_time(args.since)
    problems = []

    # ① 卡片消费埋点
    card_new = 0
    if os.path.exists(CARD_JSONL):
        with open(CARD_JSONL, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    ts = d.get("ts", "")
                    # 兼容多种时间格式
                    try:
                        t = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00")).replace(tzinfo=None)
                    except Exception:
                        continue
                    if t >= since:
                        card_new += 1
                except Exception:
                    continue

    # ② 协同日志新增行
    collab_new = 0
    if os.path.exists(COLLAB_LOG):
        with open(COLLAB_LOG, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 匹配 - [YYYY-MM-DD HH:MM] 格式
                import re
                m = re.match(r"-\s*\[(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})\]", line)
                if m:
                    try:
                        t = parse_time(f"{m.group(1)} {m.group(2)}")
                        if t >= since:
                            collab_new += 1
                    except Exception:
                        continue

    # 判定
    print("=" * 60)
    print("交付闭环校验 · since:", args.since)
    print("=" * 60)
    print(f"  ① 卡片消费埋点新增: {card_new} 条")
    print(f"  ② 协同日志新增行:   {collab_new} 条")
    print(f"  --allow-no-card:    {args.allow_no_card}")

    if args.expect_cards is not None and card_new < args.expect_cards:
        problems.append(f"卡片消费 {card_new} < 期望 {args.expect_cards}")

    if not args.allow_no_card and card_new == 0:
        problems.append("卡片消费埋点 0 新增（若本次确无卡片消费，须显式加 --allow-no-card）")

    if collab_new == 0:
        problems.append("协同日志 0 新增行（流水线第 8 步② 未执行，交付未闭环）")

    print("-" * 60)
    if problems:
        print("❌ 交付未闭环，阻断：")
        for p in problems:
            print("   -", p)
        sys.exit(1)
    else:
        print("✅ 交付闭环，埋点已写回，可交付。")
        sys.exit(0)

if __name__ == "__main__":
    main()
