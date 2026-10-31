# -*- coding: utf-8 -*-
"""
月度回灌 · 运行态管理器 (intake_monthly_driver.py)
============================================================================
镜像 intake_daily_driver.DailyRun，把「月度回灌（M0 备份 / M1 扫描 / M2 追加 /
M3 日志 / FINAL 汇总）」接入同一套标准库：checkpoint 续跑 + 原子写 + 失败留痕。

与每日摄入的区别：
    - 状态文件独立：`03-连接/monthly_backfill_state.json`（空库 libs={}）
    - 无 IMA 摄入语义：不提供 ingest/on_fetch_fail；失败统一经 record_fail 留痕
    - M0 备份是安全铁律前置：记录备份路径于状态文件 `last_backup`，供 M2 异常秒级回滚

典型用法（写入月度回灌自动化 prompt 的「运行开头」）：
    import sys; sys.path.insert(0, "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/03-连接/scripts")
    from intake_monthly_driver import MonthlyRun
    run = MonthlyRun()                   # 自动 load + new_session + 打印续跑计划
    plan = run.plan                      # 仅剩未完成阶段；上轮中断自动跳过已完成
    for stage in plan:
        if stage == "M0_backup":   ... run.record_backup(path)  # 备份 self.md（六-B 前置）
        elif stage == "M1_scan":   ...  # 只读扫描 经验卡片/裁判规则 本月新增
        elif stage == "M2_append": ...  # 追加 self.md 经验索引区（仅追加，>400 行中止）
        elif stage == "M3_log":    ...  # 写 月度回灌日志.md
        elif stage == "FINAL":     ...  # 响应摘要
        run.stage_done(stage)           # 每阶段原子持久化断点
    run.finalize()                      # 标记 done + 原子写回

任一处异常：
    run.record_fail(stage, "异常摘要")   # 留痕 failed_stages
============================================================================
"""
import os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from intake_runner import IntakeState, IntakeMachine, MONTHLY_CONFIG, MONTHLY_STAGES


class MonthlyRun:
    """月度回灌运行态封装（checkpoint 续跑 + 原子写 + 失败留痕 + 备份记录）。"""

    def __init__(self, state_path=None):
        self.config = MONTHLY_CONFIG
        self.state = IntakeState(state_path or MONTHLY_CONFIG.state_path, libs={}).load()
        self.resume = self.state.new_session()
        self.machine = IntakeMachine(self.state, MONTHLY_STAGES)
        self.plan = self.machine.resume_plan()
        if self.resume:
            print("[monthly] 检测到上轮中断(in_progress)，自动续跑；跳过已完阶段：%s"
                  % self.state.data["checkpoint"].get("done"))
        else:
            print("[monthly] 全新运行；计划阶段：%s" % self.plan)

    # ---- 阶段钩子 ----
    def stage_done(self, stage):
        self.machine.complete(stage)
        self.state.save()

    def finalize(self):
        self.state.finish_session()
        self.state.save()
        fails = self.state.data.get("failed_stages", [])
        print("[monthly] 本轮完成；done=%s；failed_stages=%d"
              % (self.state.data["checkpoint"].get("done"), len(fails)))
        return fails

    # ---- 失败留痕 ----
    def record_fail(self, stage, note):
        fails = self.state.data.setdefault("failed_stages", [])
        fails.append({"stage": stage, "note": note, "date": self.state.data.get("updated")})
        self.state.save()
        return fails

    # ---- 备份记录（M0 安全铁律前置，异常时秒级回滚依据）----
    def record_backup(self, backup_path):
        self.state.data["last_backup"] = {
            "path": backup_path, "date": self.state.data.get("updated"),
        }
        self.state.save()
        return backup_path


if __name__ == "__main__":
    # 直接运行：打印当前状态快照与续跑计划（不修改业务数据）
    r = MonthlyRun()
    print("state_path:", r.config.state_path)
    print("checkpoint:", r.state.data.get("checkpoint"))
    print("pending_stages:", r.plan)
    print("last_backup:", r.state.data.get("last_backup"))
    print("failed_stages:", r.state.data.get("failed_stages", []))
