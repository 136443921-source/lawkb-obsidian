# -*- coding: utf-8 -*-
"""
周日知识维护批处理 · 运行态管理器 (intake_sunday_driver.py)
============================================================================
镜像 intake_daily_driver.DailyRun，把「周日批 check_links（S1 盲区扫描 / S2 链接检查 /
S2_5 断链自愈 / S3 补链+图谱 / FINAL 汇总）」接入同一套标准库：
checkpoint 续跑（中断后下轮自动从断点继续，不再静默失效）+ 原子写 + 失败留痕。

与每日摄入的区别：
    - 状态文件独立：`03-连接/check_links_state.json`（空库 libs={}，不塞 IMA 5 库骨架）
    - 无 IMA 摄入语义：不提供 ingest/on_fetch_fail；失败统一经 record_fail 留痕，
      告警仍由自动化 prompt 的 QQ 推送条款负责（v1.9 cancelled 扩严）。
    - 法条体检（StatuteHealthCheck）可复用：S2/S3 关联法条引用时调用。

典型用法（写入周日批自动化 prompt 的「运行开头」）：
    import sys; sys.path.insert(0, "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/03-连接/scripts")
    from intake_sunday_driver import SundayRun
    run = SundayRun()                    # 自动 load + new_session + 打印续跑计划
    plan = run.plan                      # 仅剩未完成阶段；上轮中断自动跳过已完成
    for stage in plan:
        if stage == "S1_scan":        ...  # 阶段1 盲区扫描
        elif stage == "S2_check_links": ... # 阶段2 链接检查（cd LawKB && check_links.py）
        elif stage == "S2_5_fix_broken": ... # 阶段2.5 断链自愈（fix_source_links/resolve_broken_links）
        elif stage == "S3_relink_graph": ... # 阶段3 补链+图谱刷新（link_cards_rules/kg_scan/kg_html）
        elif stage == "FINAL":        ...  # 汇总 + 失败告警
        run.stage_done(stage)            # 每阶段原子持久化断点
    run.finalize()                       # 标记 done + 原子写回

任一处异常：
    run.record_fail(stage, "异常摘要")    # 留痕 failed_stages，随后按 prompt 条款走 QQ 告警
============================================================================
"""
import os, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from intake_runner import IntakeState, IntakeMachine, SUNDAY_CONFIG, SUNDAY_STAGES


class SundayRun:
    """周日批运行态封装（checkpoint 续跑 + 原子写 + 失败留痕）。"""

    def __init__(self, state_path=None):
        self.config = SUNDAY_CONFIG
        self.state = IntakeState(state_path or SUNDAY_CONFIG.state_path, libs={}).load()
        self.resume = self.state.new_session()
        self.machine = IntakeMachine(self.state, SUNDAY_STAGES)
        self.plan = self.machine.resume_plan()
        if self.resume:
            print("[sunday] 检测到上轮中断(in_progress)，自动续跑；跳过已完阶段：%s"
                  % self.state.data["checkpoint"].get("done"))
        else:
            print("[sunday] 全新运行；计划阶段：%s" % self.plan)

    # ---- 阶段钩子 ----
    def stage_done(self, stage):
        self.machine.complete(stage)
        self.state.save()   # 每阶段原子持久化断点

    def finalize(self):
        self.state.finish_session()
        self.state.save()
        fails = self.state.data.get("failed_stages", [])
        print("[sunday] 本轮完成；done=%s；failed_stages=%d"
              % (self.state.data["checkpoint"].get("done"), len(fails)))
        if fails:
            print("[sunday] ⚠ 失败留痕：%s" % fails)
        return fails

    # ---- 失败留痕（供 QQ 告警条款取用）----
    def record_fail(self, stage, note):
        fails = self.state.data.setdefault("failed_stages", [])
        fails.append({"stage": stage, "note": note, "date": self.state.data.get("updated")})
        self.state.save()
        return fails

    # ---- 法条体检（S2/S3 关联法条引用时复用）----
    @staticmethod
    def statute(law, article):
        from intake_runner import StatuteHealthCheck
        return StatuteHealthCheck.check(law, article)

    @staticmethod
    def statute_repealed(law, article):
        from intake_runner import StatuteHealthCheck
        return StatuteHealthCheck.is_repealed(law, article)


if __name__ == "__main__":
    # 直接运行：打印当前状态快照与续跑计划（不修改业务数据）
    r = SundayRun()
    print("state_path:", r.config.state_path)
    print("checkpoint:", r.state.data.get("checkpoint"))
    print("pending_stages:", r.plan)
    print("failed_stages:", r.state.data.get("failed_stages", []))
