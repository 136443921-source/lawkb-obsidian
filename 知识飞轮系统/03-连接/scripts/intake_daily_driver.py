# -*- coding: utf-8 -*-
"""
每日摄入 · 运行态管理器 (intake_daily_driver.py)
============================================================================
封装 intake_runner 四大模块，作为自动化「每轮开头」的统一入口，把"请继续"变成
自动续跑。本文件不含 MCP 取文/蒸馏逻辑（那些由 Agent 经工具调用完成），只负责
**状态机与去重真源**，Agent 在每个阶段之间调用本模块的钩子即可。

典型用法（写入自动化 prompt 的「运行开头」）：
    from intake_daily_driver import DailyRun
    run = DailyRun()                 # 自动 load + new_session + 打印续跑计划
    plan = run.plan                  # ['B','A2',...] 仅剩未完成阶段
    for stage in plan:
        ... Agent 调 ima-mcp / yuandian / WebSearch 完成该阶段 ...
        run.stage_done(stage)        # 持久化断点
    run.finalize()                   # 标记 done + 原子写回

重试单篇 220030 时：
    dec = run.on_fetch_fail(media_id, "220030", channel_ok=True)
    # dec['action']=='register_failed_220030' → 已登记，绝不写 ingested（铁律）
============================================================================
"""
import os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from intake_runner import (IntakeState, IntakeMachine, DegradationLayer,
                           StatuteHealthCheck, DAILY_CONFIG, SUNDAY_CONFIG,
                           MONTHLY_CONFIG, make_media_id)


class DailyRun:
    """每日摄入运行态封装。"""

    def __init__(self, state_path=DAILY_CONFIG.state_path):
        self.state = IntakeState(state_path).load()
        self.resume = self.state.new_session()
        self.machine = IntakeMachine(self.state, DAILY_CONFIG.stages)
        self.plan = self.machine.resume_plan()
        self.config = DAILY_CONFIG
        if self.resume:
            print("[intake] 检测到上轮中断(in_progress)，自动续跑；跳过已完阶段：%s"
                  % self.state.data["checkpoint"].get("done"))
        else:
            print("[intake] 全新运行；计划阶段：%s" % self.plan)

    # ---- 阶段钩子 ----
    def stage_done(self, stage):
        self.machine.complete(stage)
        self.state.save()   # 每阶段原子持久化断点

    def finalize(self):
        self.state.finish_session()
        self.state.save()
        print("[intake] 本轮完成；ingested_total=%s；failed_220030=%d"
              % (self.state.data["totals"]["ingested_total"],
                 len(self.state.data.get("failed_220030", []))))

    # ---- 摄入写回（幂等 + 兼容 dict/str）----
    def ingest(self, lib_id, media_id, title, create_time, value=0):
        ok = self.state.mark_ingested(lib_id, media_id, title, create_time, value)
        if ok:
            self.state.save()
        return ok

    # ---- 失败处理（摄入中断铁律在此落地）----
    def on_fetch_fail(self, media_id, code, channel_ok=True, websearch_mirror=None):
        dec = DegradationLayer.on_fetch_fail(self.state, media_id, code,
                                             channel_ok, websearch_mirror)
        self.state.save()
        return dec

    # ---- 漏窗升级阶梯 ----
    def escalation(self):
        return DegradationLayer.escalation(self.state)

    # ---- 法条体检（B/D 阶段调用）----
    @staticmethod
    def statute(law, article):
        return StatuteHealthCheck.check(law, article)

    @staticmethod
    def statute_repealed(law, article):
        return StatuteHealthCheck.is_repealed(law, article)

    @staticmethod
    def statute_needs_exact(law, article):
        return StatuteHealthCheck.needs_exact_verify(law, article)


# =============================================================================
# 三场景复用示例（周日批 / 月度回灌 仅换 config 与 stages，库完全一致）
# =============================================================================
def sunday_batch_run():
    """周日 check_links 批处理：复用 RunState 续跑 + StatuteHealthCheck，独立状态文件。"""
    st = IntakeState(SUNDAY_CONFIG.state_path).load()
    st.new_session()
    m = IntakeMachine(st, SUNDAY_CONFIG.stages)
    return st, m, m.resume_plan()


def monthly_backfill_run():
    """月度回灌：复用 IntakeState + DegradationLayer + StatuteHealthCheck。"""
    st = IntakeState(MONTHLY_CONFIG.state_path).load()
    st.new_session()
    m = IntakeMachine(st, MONTHLY_CONFIG.stages)
    return st, m, m.resume_plan()


if __name__ == "__main__":
    # 直接运行：打印当前状态快照与续跑计划（不修改业务数据）
    r = DailyRun()
    print("checkpoint:", r.state.data.get("checkpoint"))
    print("totals:", r.state.data.get("totals"))
    print("pending_stages:", r.plan)
    print("escalation:", r.escalation())
