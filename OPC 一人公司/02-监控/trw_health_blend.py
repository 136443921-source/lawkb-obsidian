#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trw_health_blend.py — 资产健康月报融合（G6 月报段）【P2-⑦】
==========================================================
把「定向补强缺口报告（gap_sense）」+「回源 SLA 计划（trw_backfill_sla）」合并为
一段可直接贴入《资产健康月报》的「自学习补强与回源」小节。

设计铁律：
  - 纯只读：仅消费 gap_report.json / backfill_plan.json（二者均由 G1 / G6 脚本生成）。
  - 仅落 trw_health_monthly.md（月报片段），不改任何资产、不重算。
  - 任一源缺失则标注「未生成」，不编造数字。
"""
import os
import sys
import json
import argparse
import datetime

from opc_common import ROOT, TODAY, load_json

OUT_DIR = os.path.join(ROOT, "OPC 一人公司/02-监控")
GAP = os.path.join(OUT_DIR, "gap_report.json")
BACK = os.path.join(OUT_DIR, "backfill_plan.json")


def main():
    ap = argparse.ArgumentParser(description="资产健康月报融合（补强+回源片段）")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    gap = load_json(GAP)
    back = load_json(BACK)

    md = [
        f"# 资产健康月报 · 自学习补强与回源 · {TODAY.isoformat()}\n",
        f"\n> 本段由 `trw_health_blend.py` 融合生成，供《资产健康月报》直接引用。引擎：资产运维官第5支柱（WF-101）。\n",
    ]

    # —— 段一：定向补强缺口（G1）——
    md.append("\n## 一、定向补强缺口（G1 感知）\n")
    if gap:
        md.append(f"- 覆盖目标线：{gap.get('target')} R-卡/域")
        zd = gap.get("zero_domains", [])
        md.append(f"- 零覆盖域库（最高优先补强）：**{len(zd)}** 个 —— {', '.join(zd) or '无'}")
        cov = gap.get("coverage_gap", [])
        if cov:
            md.append(f"- 低覆盖域 Top-{len(cov)}（实测/目标/缺口）：")
            for r in cov[:5]:
                md.append(f"  · {r['domain']}: {r['actual']}/{r['target']}/缺口 {r['gap']}（覆盖 {r['coverage']*100:.0f}%）")
        p0 = gap.get("p0_alerts", [])
        if p0:
            md.append(f"- **P0 告警 {len(p0)} 项**：")
            for x in p0:
                md.append(f"  · {x}")
    else:
        md.append("- ⚠ 缺口报告未生成（先跑 `gap_sense.py`）。")

    # —— 段二：回源 SLA（G6）——
    md.append("\n## 二、回源 SLA 治理（G6 回源）\n")
    if back:
        s = back.get("summary", {})
        md.append(f"- 总待回源：**{s.get('total_pending')}** 张；突破 SLA（> {back.get('sla_days')} 天）：**{s.get('total_breach')}** 张")
        bp = s.get("packages_breached", [])
        md.append(f"- 破 SLA 包：{', '.join(bp) or '无'}")
        q = back.get("global_backfill_queue", [])
        if q:
            md.append(f"- 全局回源队列（oldest-first）首 5 张：")
            for r in q[:5]:
                md.append(f"  · {r['rule_id']}（{r['domain']}）龄期 {r['age_days']} 天 [{r['status']}]")
        md.append(f"- 回源动作：元典有额度时按 `backfill_plan.md` 队列回源，回源后跑 `gen_rule_package.py --domain <域>` 刷新包 manifest。")
    else:
        md.append("- ⚠ 回源计划未生成（先跑 `trw_backfill_sla.py`）。")

    md.append("\n---\n*自学习补强闭环：G1 缺口感知 → G2 选题排期 → G3 定向生成 → G4 去重护栏 → G5 质检门禁 → G6 回源+留痕 →（回 G1）。详见 WF-101。*")

    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "trw_health_monthly.md")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    if not a.quiet:
        print(f"== 资产健康月报融合（G6 月报段）· {TODAY.isoformat()} ==")
        print(f"[写入] {out}")
        if gap: print(f"  缺口：零覆盖域 {len(gap.get('zero_domains', []))} 个")
        if back: print(f"  回源：pending {back.get('summary', {}).get('total_pending')} / 破SLA {back.get('summary', {}).get('total_breach')}")
    sys.exit(0)


if __name__ == "__main__":
    main()
