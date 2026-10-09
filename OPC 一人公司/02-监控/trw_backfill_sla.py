#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trw_backfill_sla.py — 回源 SLA 治理（G6 回源段）【P2-⑥】
========================================================
读各规则包 manifest 的 source_pending_ids（待核验源），定位每张 pending 卡的真实文件，
按其 frontmatter `updated` 计算"待回源龄期"，判定是否突破回源 SLA（默认 30 天）。
产出 oldest-first 回源队列（优先回源最老的卡），供元典有额度时一键回源。

设计铁律：
  - 只读真源（manifest + 规则卡 frontmatter），零改写。
  - 单轮 walk 06-沉淀 建 rule_id→(path, updated) 映射，避免逐卡慢扫（守 D7 慢盘防护）。
  - 仅落 backfill_plan.json / .md（计划文件），不改任何资产。
  - 命名冲突/缺失不编造：找不到文件的 pending id 标 missing，列入核对清单。
SLA 口径：与资产运维官"陈旧>30天"红线对齐；breach = 龄期>30 天。
"""
import os
import sys
import json
import argparse
import datetime

from opc_common import ROOT, DOMAIN_LIB, TODAY, load_json
# gen_rule_package 位于兄弟目录 01-规则包，加入搜索路径后导入（仅复用其 parse_frontmatter）
sys.path.insert(0, os.path.join(ROOT, "OPC 一人公司/01-规则包"))
import gen_rule_package as grp

OUT_DIR = os.path.join(ROOT, "OPC 一人公司/02-监控")
PKG_DIR = os.path.join(ROOT, "OPC 一人公司/01-规则包")
SLA_DAYS = 30


def build_rid_map():
    """单轮 walk 06-沉淀，建 rule_id → (path, updated) 映射。"""
    m = {}
    for dp, _, fs in os.walk(DOMAIN_LIB):
        if os.path.basename(dp).startswith('.'):
            continue
        for f in fs:
            if not (f.startswith('R-') and f.endswith('.md')):
                continue
            p = os.path.join(dp, f)
            try:
                text = open(p, encoding="utf-8").read()
            except Exception:
                continue
            fm, _ = grp.parse_frontmatter(text)
            rid = str(fm.get("rule_id", "")).strip()
            if rid:
                m[rid] = (p, str(fm.get("updated", "")).strip())
    return m


def age_of(updated):
    if not updated:
        return None
    try:
        d = datetime.date.fromisoformat(updated[:10])
        return (TODAY - d).days
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description="回源 SLA 治理 G6（oldest-first 回源队列）")
    ap.add_argument("--sla", type=int, default=SLA_DAYS, help="回源 SLA 天数（默认 30）")
    ap.add_argument("--top", type=int, default=50, help="全局回源队列 Top-N（按龄期降序）")
    ap.add_argument("--dry", action="store_true", help="仅打印不落盘")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    rid_map = build_rid_map()
    if not a.quiet:
        print(f"== 回源 SLA 治理（G6）· {TODAY.isoformat()} · SLA={a.sla}天 ==")
        print(f"[rule_id 映射] 06-沉淀 实测 {len(rid_map)} 张 R-卡（单轮 walk 建索引）")

    pkgs, global_q = [], []
    if os.path.isdir(PKG_DIR):
        for name in sorted(os.listdir(PKG_DIR)):
            mp = os.path.join(PKG_DIR, name, "manifest.json")
            if not os.path.isfile(mp):
                continue
            m = load_json(mp)
            if not m:
                continue
            qr = m.get("quality_report", {})
            pids = qr.get("source_pending_ids", []) or []
            if not pids:
                continue
            domain = m.get("domain", name)
            rows = []
            breach = 0
            missing = 0
            for rid in pids:
                path, updated = rid_map.get(rid, (None, ""))
                if path is None:
                    missing += 1
                    rows.append({"rule_id": rid, "age_days": None, "status": "missing"})
                    continue
                age = age_of(updated)
                is_breach = (age is not None and age > a.sla)
                if is_breach:
                    breach += 1
                rows.append({"rule_id": rid, "age_days": age, "status": "breach" if is_breach else "ok"})
                global_q.append({"rule_id": rid, "package": name, "domain": domain,
                                 "age_days": age, "status": "breach" if is_breach else "ok"})
            rows.sort(key=lambda r: (r["age_days"] is None, -(r["age_days"] or -1)))
            oldest = [r["rule_id"] for r in rows[:5]]
            pkgs.append({
                "package": name, "domain": domain,
                "pending_total": len(pids), "breach_count": breach, "missing_count": missing,
                "oldest_ids": oldest,
            })
    pkgs.sort(key=lambda p: p["breach_count"], reverse=True)
    global_q.sort(key=lambda r: (r["age_days"] is None, -(r["age_days"] or -1)))
    queue = global_q[:a.top]

    total_pending = sum(p["pending_total"] for p in pkgs)
    total_breach = sum(p["breach_count"] for p in pkgs)
    breached_pkgs = [p["package"] for p in pkgs if p["breach_count"] > 0]

    if not a.quiet:
        print(f"\n-- 按包（breach 降序）--")
        for p in pkgs:
            flag = "🔴" if p["breach_count"] else "·"
            print(f"   {flag} {p['package']}({p['domain']}): pending {p['pending_total']} / 破 SLA {p['breach_count']} / 缺失 {p['missing_count']}")
            if p["oldest_ids"]:
                print(f"       最老5张: {', '.join(p['oldest_ids'])}")
        print(f"\n[回源 SLA 汇总] 总 pending={total_pending} / 破 SLA={total_breach} / 破 SLA 包={len(breached_pkgs)}")
        print(f"[全局回源队列 Top-{a.top}] {len(queue)} 张（oldest-first）")
        for r in queue[:10]:
            print(f"   · {r['rule_id']} ({r['domain']}) 龄期 {r['age_days']}天 [{r['status']}]")

    if not a.dry:
        os.makedirs(OUT_DIR, exist_ok=True)
        plan = {
            "report_date": TODAY.isoformat(),
            "sla_days": a.sla,
            "summary": {
                "total_pending": total_pending,
                "total_breach": total_breach,
                "packages_breached": breached_pkgs,
                "rules_indexed": len(rid_map),
            },
            "packages": pkgs,
            "global_backfill_queue": queue,
        }
        with open(os.path.join(OUT_DIR, "backfill_plan.json"), "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        md = [
            f"# 回源 SLA 治理计划 · {TODAY.isoformat()}（SLA={a.sla}天）\n",
            f"\n总待回源 {total_pending} 张，其中突破 SLA（> {a.sla} 天）{total_breach} 张，涉及 {len(breached_pkgs)} 个包。\n",
            f"\n## 按包（breach 降序）\n",
            "| 包 | 域 | pending | 破SLA | 缺失 | 最老5张 |",
            "|---|---|---|---|---|---|",
        ]
        for p in pkgs:
            md.append(f"| {p['package']} | {p['domain']} | {p['pending_total']} | {p['breach_count']} | {p['missing_count']} | {', '.join(p['oldest_ids']) or '—'} |")
        md.append(f"\n## 全局回源队列（oldest-first · Top-{a.top}）\n")
        md.append("| 序 | rule_id | 域 | 龄期(天) | 状态 |")
        md.append("|---|---|---|---|---|")
        for i, r in enumerate(queue, 1):
            md.append(f"| {i} | {r['rule_id']} | {r['domain']} | {r['age_days']} | {r['status']} |")
        md.append("\n---\n*数据源：各包 manifest + 规则卡 frontmatter。本器只读不写；元典有额度时按队列回源，回源后跑 `gen_rule_package.py --domain <域>` 刷新包。*")
        with open(os.path.join(OUT_DIR, "backfill_plan.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(md))
        if not a.quiet:
            print(f"\n[计划已写入] {os.path.join(OUT_DIR, 'backfill_plan.json / .md')}（只读不写真源）")

    sys.exit(0)


if __name__ == "__main__":
    main()
