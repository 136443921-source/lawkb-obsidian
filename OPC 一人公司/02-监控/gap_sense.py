#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gap_sense.py — 定向补强缺口感知器（G1）【P0-③】
================================================
嵌资产运维官第5支柱「🟪 自学习补强」的缺口感知臂。
读数字资产登记册 SSOT + 各规则包 manifest，算出三类缺口：
  1) 域覆盖缺口：06-沉淀 各域库 R-卡实测 vs 目标线(target)，列零覆盖/低覆盖域 Top-N
  2) 待回源缺口(pending)：聚合各包 manifest quality_report.source_pending_*
     → 直接喂 G6 回源 SLA（P2）
  3) 登记册漂移（--drift 复用 opc_common.compute_drift）

只读不写（与监控器同铁律）；输出 md+json 到 02-监控/；--dry 仅打印不落盘。
退出码：有 P0 级（零覆盖域 / pending 超阈包）→ 1，否则 0（--quiet 仅返回码）。
"""
import os
import sys
import json
import argparse
import datetime

from opc_common import (
    ROOT, DOMAIN_LIB, REGISTRY, TODAY,
    load_json, count_r_cards_in_subdir, compute_drift,
)

OUT_DIR = os.path.join(ROOT, "OPC 一人公司/02-监控")
PKG_DIR = os.path.join(ROOT, "OPC 一人公司/01-规则包")
# 非域库目录（采集缓存/公开渠道/案由路由/学习笔记/回收站）不计为补强域
EXCLUDE_DIRS = {'.trash_a', '.backup', '__pycache__',
                '01-采集', '公众号', '案例', '案由路由', '学习笔记'}
# 子串排除：日志/备份/设计稿/总结/_dryrun/_治理 等非域库目录
SKIP_SUBSTR = ('日志', '备份', '设计', '总结', '_dryrun', '_治理')


def _skip(name):
    if name.startswith('.') or name in EXCLUDE_DIRS:
        return True
    return any(s in name for s in SKIP_SUBSTR)


def sense_zero_domains():
    """零覆盖域库（有目录但 0 张 R-卡）——最高优先级补强目标"""
    zeros = []
    if not os.path.isdir(DOMAIN_LIB):
        return zeros
    for name in sorted(os.listdir(DOMAIN_LIB)):
        dp = os.path.join(DOMAIN_LIB, name)
        if not os.path.isdir(dp):
            continue
        if _skip(name):
            continue
        n = count_r_cards_in_subdir(name)
        if n == 0:
            zeros.append(name)
    return zeros


def sense_coverage(target, top):
    """扫描 06-沉淀 各域库 R-卡实测，计算覆盖缺口（actual<target 即缺口）"""
    rows = []
    if not os.path.isdir(DOMAIN_LIB):
        return rows
    for name in sorted(os.listdir(DOMAIN_LIB)):
        dp = os.path.join(DOMAIN_LIB, name)
        if not os.path.isdir(dp):
            continue
        if _skip(name):
            continue
        n = count_r_cards_in_subdir(name)
        if n is None or n == 0:
            continue
        rows.append({
            "domain": name,
            "actual": n,
            "target": target,
            "gap": max(0, target - n),
            "coverage": round(min(1.0, n / target), 3),
        })
    rows.sort(key=lambda r: r["actual"])
    return rows[:top]


def sense_pending():
    """聚合各规则包 manifest 的待回源(pending)缺口 → 回源 SLA 队列"""
    out = []
    if not os.path.isdir(PKG_DIR):
        return out
    for name in sorted(os.listdir(PKG_DIR)):
        mp = os.path.join(PKG_DIR, name, "manifest.json")
        if not os.path.isfile(mp):
            continue
        m = load_json(mp)
        if not m:
            continue
        qr = m.get("quality_report", {})
        pc = qr.get("source_pending_count", 0) or 0
        pids = qr.get("source_pending_ids", []) or []
        if pc:
            out.append({
                "package": name,
                "domain": m.get("domain", name),
                "pending_count": pc,
                "pending_ids_sample": pids[:20],
                "pending_total_ids": len(pids),
            })
    out.sort(key=lambda r: r["pending_count"], reverse=True)
    return out


def main():
    ap = argparse.ArgumentParser(description="定向补强缺口感知器 G1")
    ap.add_argument("--target", type=int, default=200, help="域覆盖目标线（R-卡数/域）")
    ap.add_argument("--top", type=int, default=8, help="低覆盖域输出 Top-N")
    ap.add_argument("--pending-threshold", type=int, default=100, help="pending 超限告警线")
    ap.add_argument("--drift", action="store_true", help="一并跑登记册漂移核查")
    ap.add_argument("--dry", action="store_true", help="仅打印不写报告文件")
    ap.add_argument("--quiet", action="store_true", help="仅返回退出码")
    a = ap.parse_args()

    zeros = sense_zero_domains()
    cov = sense_coverage(a.target, a.top)
    pend = sense_pending()
    drift = compute_drift(load_json(REGISTRY)) if a.drift else []

    p0 = []
    if zeros:
        p0.append(f"零覆盖域库 {len(zeros)} 个：{', '.join(zeros)}（最高优先级补强目标）")
    big_pending = [p for p in pend if p["pending_count"] > a.pending_threshold]
    for p in big_pending:
        p0.append(f"包 {p['package']} 待回源 {p['pending_count']} 条 > 阈值 {a.pending_threshold}（回源 SLA 触发）")

    if not a.quiet:
        print(f"== 定向补强缺口感知（G1）· {TODAY.isoformat()} ==")
        print(f"[覆盖目标线] {a.target} R-卡/域 ｜ [Top-N] {a.top}")
        print(f"\n-- 零覆盖域库（P0 补强目标）: {len(zeros)} --")
        for z in zeros:
            print(f"   · {z}")
        print(f"\n-- 低覆盖域 Top-{a.top}（actual<target）--")
        for r in cov:
            flag = "⚠" if r["gap"] > 0 else "✓"
            print(f"   {flag} {r['domain']}: 实测 {r['actual']} / 目标 {r['target']} / 缺口 {r['gap']} / 覆盖 {r['coverage']*100:.0f}%")
        print(f"\n-- 待回源缺口(pending) 按包 --")
        for p in pend:
            tag = "🔴" if p["pending_count"] > a.pending_threshold else "·"
            print(f"   {tag} {p['package']}({p['domain']}): pending {p['pending_count']}")
        if a.drift:
            print(f"\n-- 登记册漂移: {len(drift)} 项 --")
            for f in drift[:10]:
                print(f"   [{f.get('severity')}] {f.get('detail')}")
        print(f"\n[缺口汇总] 零覆盖域={len(zeros)} / 待回源超阈包={len(big_pending)} / P0告警={len(p0)}")

    if not a.dry:
        os.makedirs(OUT_DIR, exist_ok=True)
        report = {
            "report_date": TODAY.isoformat(),
            "target": a.target,
            "zero_domains": zeros,
            "coverage_gap": cov,
            "pending_backlog": pend,
            "drift": drift if a.drift else "skipped(--drift off)",
            "p0_alerts": p0,
        }
        with open(os.path.join(OUT_DIR, "gap_report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        md = [
            f"# 定向补强缺口感知报告 · {TODAY.isoformat()}\n",
            f"\n覆盖目标线 {a.target} R-卡/域。本报告由 `gap_sense.py` 生成（G1 缺口感知器，嵌资产运维官第5支柱）。\n",
            f"\n## 零覆盖域库（最高优先级补强目标）\n",
        ]
        md += [f"- {z}" for z in zeros] or ["- 无"]
        md.append(f"\n## 低覆盖域 Top-{a.top}\n")
        md.append("| 域 | 实测 | 目标 | 缺口 | 覆盖 |")
        md.append("|---|---|---|---|---|")
        for r in cov:
            md.append(f"| {r['domain']} | {r['actual']} | {r['target']} | {r['gap']} | {r['coverage']*100:.0f}% |")
        md.append("\n## 待回源缺口(pending) · 回源 SLA 队列\n")
        md.append("| 包 | 域 | pending |")
        md.append("|---|---|---|")
        for p in pend:
            md.append(f"| {p['package']} | {p['domain']} | {p['pending_count']} |")
        md.append("\n---\n*数据源：登记册 SSOT + 各规则包 manifest。本器只读不写，冲突以最新实测为准。*")
        with open(os.path.join(OUT_DIR, "gap_report.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(md))

    sys.exit(1 if p0 else 0)


if __name__ == "__main__":
    main()
