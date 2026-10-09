#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trw_scheduler.py — 定向补强通用调度器（G2 编排）【P1】
======================================================
读 gap_sense 缺口清单，按域阈值/配额编排"补强计划"。
设计铁律：默认 --dry，零知识库写入（守资产运维官红线：无生产决策权，改规则库真源转主任拍板）。
- 选题：零覆盖域优先，其次按缺口率取低覆盖域 Top-N
- 每域配额：子主题≤--subtopics / 卡 --cards（沿用人伤补强经验值 3 子题 / 8 卡）
- 回源队列：从 gap_sense pending 聚合，列入计划 G6 段（P2 回源 SLA 数据源）
- --refresh-packages：补强即刷新对应包 manifest（调用 gen_rule_package.py --domain <域>）
    · 默认 dry（--refresh-packages 不带 --apply）→ 仅打印将执行的命令
    · 显式 --apply → 实际重建包子集（导出重建，不改源资产；仍须主任授权）
刷新目标取「回源队列中 pending>阈值 的包」∪「本轮选中且存在对应规则包的域」，按 gen_rule_package 域键对齐。
只读不写知识库（除非 --apply 刷新包）；仅落 trw_plan.json（计划文件）。退出码 0。
"""
import os
import sys
import json
import argparse
import subprocess as _sp

from opc_common import ROOT, TODAY
import gap_sense as gs
# gen_rule_package 位于兄弟目录 01-规则包，加入搜索路径后导入（仅复用其 DOMAIN_CONFIG 域键集合）
sys.path.insert(0, os.path.join(ROOT, "OPC 一人公司/01-规则包"))
import gen_rule_package as grp

OUT_DIR = os.path.join(ROOT, "OPC 一人公司/02-监控")
PKG_DIR = os.path.join(ROOT, "OPC 一人公司/01-规则包")


def build_plan(target, top, subtopics, cards, pending_th, apply):
    zeros = gs.sense_zero_domains()
    cov = gs.sense_coverage(target, top)
    pend = gs.sense_pending()
    # 选题：零覆盖域优先填满，再用低覆盖域补足 Top-N
    selected = list(zeros)
    for r in cov:
        if r["gap"] > 0:
            selected.append(r["domain"])
        if len(selected) >= top:
            break
    selected = list(dict.fromkeys(selected))[:top]  # 去重截断
    # 刷新候选：回源队列中 pending>阈值的包域键 ∪ 选中域中恰有对应规则包的域键
    candidates = []
    for p in pend:
        if p["pending_count"] > pending_th and p["domain"] in grp.DOMAIN_CONFIG and p["domain"] not in candidates:
            candidates.append(p["domain"])
    for d in selected:
        if d in grp.DOMAIN_CONFIG and d not in candidates:
            candidates.append(d)
    return {
        "plan_date": TODAY.isoformat(),
        "mode": "apply（已授权刷新包 manifest）" if apply else "dry（默认不写知识库，待主任拍板 --apply）",
        "target": target,
        "selected_domains": selected,
        "per_domain_quota": {"subtopics_max": subtopics, "cards": cards},
        "zero_coverage_domains": zeros,
        "coverage_gap_top": cov,
        "backfill_queue_pending": [
            {"package": p["package"], "domain": p["domain"], "pending_count": p["pending_count"]}
            for p in pend if p["pending_count"] > pending_th
        ],
        "package_refresh_candidates": candidates,
    }


def refresh_packages(domains, apply, quiet):
    """补强即刷新包 manifest：对候选域键调用 gen_rule_package.py 重建子集导出。

    - dry（apply=False）：仅打印将执行命令，零写盘。
    - apply（apply=True）：subprocess 实际重建对应包（导出重建，不改源资产）。
    返回 (ok, fail) 域名列表。
    """
    ok, fail = [], []
    gen = os.path.join(PKG_DIR, "gen_rule_package.py")
    for d in domains:
        if d not in grp.DOMAIN_CONFIG:
            if not quiet:
                print(f"  ⚠ 跳过（无对应规则包域键）：{d}")
            continue
        cmd = [sys.executable, gen, "--domain", d]
        if not apply:
            print(f"  [dry] 将执行：{' '.join(cmd)}")
            ok.append(d)
            continue
        try:
            r = _sp.run(cmd, capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                ok.append(d)
                if not quiet:
                    print(f"  ✅ 刷新包：{d}")
            else:
                fail.append(d)
                if not quiet:
                    print(f"  ❌ 刷新失败：{d}\n{r.stderr[:400]}")
        except Exception as e:
            fail.append(d)
            if not quiet:
                print(f"  ❌ 刷新异常：{d} · {e}")
    return ok, fail


def main():
    ap = argparse.ArgumentParser(description="定向补强通用调度器 G2（dry 默认）")
    ap.add_argument("--target", type=int, default=200, help="域覆盖目标线")
    ap.add_argument("--top", type=int, default=3, help="本轮补强域数")
    ap.add_argument("--subtopics", type=int, default=3, help="每域子主题上限")
    ap.add_argument("--cards", type=int, default=8, help="每域卡数")
    ap.add_argument("--pending-threshold", type=int, default=100, help="回源队列 pending 阈值")
    ap.add_argument("--dry", action="store_true", help="默认即 dry；显式标注")
    ap.add_argument("--refresh-packages", action="store_true", help="补强即刷新包：dry 打印命令 / --apply 实际重建包")
    ap.add_argument("--apply", action="store_true", help="实际执行写库动作（刷新包 manifest）；默认 dry 仅打印")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    plan = build_plan(a.target, a.top, a.subtopics, a.cards, a.pending_threshold, a.apply)

    if not a.quiet:
        print(f"== 定向补强计划（G2 编排）· {TODAY.isoformat()} · {'APPLY' if a.apply else 'DRY'} ==")
        print(f"本轮目标域（Top-{a.top}）：{', '.join(plan['selected_domains']) or '无'}")
        print(f"每域配额：子主题≤{a.subtopics} / 卡 {a.cards}")
        print(f"零覆盖域（优先补强）：{plan['zero_coverage_domains']}")
        hot = [f"{p['package']}({p['pending_count']})" for p in plan["backfill_queue_pending"]]
        print(f"回源队列(pending>{a.pending_threshold})：{hot or '无'}")
        print(f"包刷新候选（共 {len(plan['package_refresh_candidates'])}）：{plan['package_refresh_candidates'] or '无'}")
        if a.refresh_packages:
            print(f"  ↻ 刷新包 manifest（{'实际执行 --apply' if a.apply else 'dry 仅打印'}）：")
            ok, fail = refresh_packages(plan["package_refresh_candidates"], apply=a.apply, quiet=a.quiet)
            plan["package_refresh"] = {
                "attempted": plan["package_refresh_candidates"],
                "ok": ok, "failed": fail,
                "mode": "apply" if a.apply else "dry",
            }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "trw_plan.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    flag = "apply·已刷新包" if (a.refresh_packages and a.apply) else "dry·未写知识库"
    print(f"[计划已写入] {os.path.join(OUT_DIR, 'trw_plan.json')}（{flag}）")
    sys.exit(0)


if __name__ == "__main__":
    main()
