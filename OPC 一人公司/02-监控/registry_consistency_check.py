#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
registry_consistency_check.py — 数字资产登记册一致性校验器（P1）
===============================================================
类 seat_config_verify.py 的 C8 思路，但作用于「数字资产登记册」。
校验：登记册 metrics 与实测是否漂移 / location 是否断链 / last_verified 是否陈旧。
只读不写；输出控制台摘要 + 报告 md + 报告 json。

用法：
  python3 registry_consistency_check.py            # 校验并写报告
  python3 registry_consistency_check.py --quiet    # 仅返回退出码（0=无P0，1=有P0）
"""
import os
import sys
import json
import datetime
from opc_common import (REGISTRY, load_json, compute_drift, ROOT, TODAY)

OUT_DIR = os.path.join(ROOT, "OPC 一人公司/02-监控")


def main():
    quiet = "--quiet" in sys.argv
    reg = load_json(REGISTRY)
    if not reg:
        print("❌ 登记册未加载，中止")
        sys.exit(2)
    findings = compute_drift(reg)

    p0 = [f for f in findings if f["severity"] == "P0"]
    p1 = [f for f in findings if f["severity"] == "P1"]

    # 控制台
    if not quiet:
        print(f"== 登记册一致性校验（{TODAY.isoformat()}）==")
        print(f"资产条目：{len(reg.get('assets', []))} ｜ 漂移发现：{len(findings)}（P0={len(p0)} / P1={len(p1)}）")
        for f in findings:
            print(f"  [{f['severity']}] {f['id']} {f['type']}: {f['detail']}")
        if not findings:
            print("  ✅ 登记册与实测一致，无漂移")

    # 报告
    report = {
        "check_date": TODAY.isoformat(),
        "asset_count": len(reg.get("assets", [])),
        "p0": p0, "p1": p1,
        "summary": f"P0={len(p0)} P1={len(p1)}",
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "registry_consistency_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    md = [f"# 登记册一致性校验报告 · {TODAY.isoformat()}\n"]
    md.append(f"\n资产条目 **{len(reg.get('assets', []))}** ｜ 漂移发现 **{len(findings)}**（P0={len(p0)} / P1={len(p1)}）\n")
    if not findings:
        md.append("\n✅ 登记册与实测一致，无漂移。\n")
    for sev in ("P0", "P1"):
        items = [f for f in findings if f["severity"] == sev]
        if items:
            md.append(f"\n## {sev} 级（{'生产级/须立即回写' if sev=='P0' else '观察级/可排期'}）\n")
            for f in items:
                md.append(f"- `{f['id']}` **{f['type']}**：{f['detail']}")
    with open(os.path.join(OUT_DIR, "registry_consistency_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    # 退出码：有 P0 → 1，否则 0
    sys.exit(1 if p0 else 0)


if __name__ == "__main__":
    main()
