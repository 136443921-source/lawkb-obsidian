# -*- coding: utf-8 -*-
"""08-31 运行收尾：标记已完成阶段 + finalize。A1/B 保持 pending（漏窗跟踪）。"""
import os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from intake_daily_driver import DailyRun

def main():
    run = DailyRun()
    print("resume_flag:", run.state.resume_flag)
    print("plan(before):", run.plan)
    # 仅标记本日实际完成的阶段；A1/B 不标记（漏窗待回补）
    for stage in ("A2", "A2_5", "C", "D", "FINAL"):
        if stage in run.plan:
            run.stage_done(stage)
            print("stage_done:", stage)
    run.finalize()
    # 校验
    d = run.state.data
    print("checkpoint:", d.get("checkpoint"))
    print("ingested_total:", d.get("totals", {}).get("ingested_total"))
    wins = [w["window_id"] for w in d.get("pending_windows", [])]
    print("pending_windows:", wins)
    print("OK")

if __name__ == "__main__":
    main()
