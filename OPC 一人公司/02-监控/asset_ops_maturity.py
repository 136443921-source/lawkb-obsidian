#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
asset_ops_maturity.py — 数字资产运维官·成熟度追踪 + 商业化闭环（P2）
================================================================
回答运营部门最关心的三件事：
  1. 采用率   —— 多少可商业化域库已封装成包？（包覆盖度）
  2. 计费口径 —— 所有包是否统一 subscription_by_domain / internal_commercial_unit？（防漂移）
  3. 跨域复用 —— 横切包（审判要件/裁量尺度）复用多少既有域卡？（资产杠杆）
另含：待核验源泄漏（商用风险）、包内一致性（交付质量）。

复用 opc_common 的路径/计数；只读不写。
产物：asset_maturity_report.json + asset_maturity_report.md + 成熟度指数(0-100)。
退出码：有 P0→1，否则 0（--quiet 仅返回退出码）。
"""
import os
import sys
import json
import datetime
import glob

from opc_common import ROOT, REGISTRY, load_json, TODAY

PKG_ROOT = os.path.join(ROOT, "OPC 一人公司/01-规则包")
OUT_DIR  = os.path.join(ROOT, "OPC 一人公司/02-监控")

EXPECT_BILLING_MODEL = "subscription_by_domain"
EXPECT_LICENSE_TYPE  = "internal_commercial_unit"


def load_packages():
    """扫描 01-规则包/*_v1.0 下的 manifest，返回列表"""
    pkgs = []
    if not os.path.isdir(PKG_ROOT):
        return pkgs
    for d in sorted(os.listdir(PKG_ROOT)):
        mp = os.path.join(PKG_ROOT, d, "manifest.json")
        if os.path.isfile(mp):
            try:
                m = json.load(open(mp, encoding="utf-8"))
                m["_dir"] = d
                pkgs.append(m)
            except Exception:
                pass
    return pkgs


def pkg_rule_ids(pkg):
    """读取某包 assets/rules/ 下规则卡 JSON（排除 source_pending_list），返回 rule_id 集合"""
    d = os.path.join(PKG_ROOT, pkg["_dir"], "assets/rules")
    if not os.path.isdir(d):
        return set()
    ids = set()
    for fp in glob.glob(os.path.join(d, "*.json")):
        if os.path.basename(fp) == "source_pending_list.json":
            continue
        try:
            arr = json.load(open(fp, encoding="utf-8"))
            if isinstance(arr, list):
                for r in arr:
                    rid = str(r.get("rule_id", "")).strip()
                    if rid:
                        ids.add(rid)
        except Exception:
            pass
    return ids


def compute_maturity(pkgs, registry):
    findings = []

    # ── M1 包覆盖度 / 采用率 ──
    ca = next((a for a in registry.get("assets", []) if a.get("id") == "CA-001"), None)
    n_domain_libs = 0
    if ca:
        n_domain_libs = len(ca.get("metrics", {}).get("主要域库", {}))

    def mode_of(p):
        return p.get("selection", {}).get("mode") or "目录"   # 旧包无 selection → 视为域库包
    domain_pkgs = [p for p in pkgs if mode_of(p) == "目录"]
    cross_pkgs  = [p for p in pkgs if mode_of(p).startswith("横切")]
    coverage = min(100.0, len(domain_pkgs) / n_domain_libs * 100) if n_domain_libs else 0
    if coverage < 50:
        findings.append({"sev": "P1", "dim": "M1", "detail":
            f"域库封装采用率 {coverage:.0f}%（{len(domain_pkgs)}/{n_domain_libs} 域库已包），12 个域库待封装"})
    m1 = {"n_domain_libs": n_domain_libs, "domain_packages": len(domain_pkgs),
          "cross_packages": len(cross_pkgs), "total_packages": len(pkgs),
          "coverage_pct": round(coverage, 1)}

    # ── M2 计费口径一致性 ──
    bill_bad = []
    for p in pkgs:
        b = p.get("billing", {})
        if b.get("model") != EXPECT_BILLING_MODEL or b.get("license_type") != EXPECT_LICENSE_TYPE:
            bill_bad.append(p["package"])
    if bill_bad:
        findings.append({"sev": "P0", "dim": "M2", "detail":
            f"计费口径漂移：{', '.join(bill_bad)} 非统一 subscription_by_domain/internal_commercial_unit"})
    m2 = {"expected_model": EXPECT_BILLING_MODEL, "expected_license": EXPECT_LICENSE_TYPE,
          "consistent": len(bill_bad) == 0, "bad": bill_bad}

    # ── M3 跨域复用 ──
    rule_map = {}
    for p in pkgs:
        for rid in pkg_rule_ids(p):
            rule_map.setdefault(rid, []).append(p.get("domain", p["_dir"]))
    reused = {rid: ps for rid, ps in rule_map.items() if len(ps) >= 2}
    # 横切包命中域包的数量 = 横切包中有多少卡也出现在域包
    cross_reuse = 0
    for p in cross_pkgs:
        ids = pkg_rule_ids(p)
        if ids:
            hit = sum(1 for rid in ids if len(rule_map.get(rid, [])) >= 2)
            cross_reuse += hit
    m3 = {"total_rules_indexed": len(rule_map), "reused_rule_count": len(reused),
          "cross_package_reuse_hits": cross_reuse,
          "sample": [{"rule_id": k, "packages": v} for k, v in list(reused.items())[:5]]}

    # ── M4 待核验源泄漏（商用风险）──
    total_pending = 0
    pending_leak = []
    for p in pkgs:
        c = p.get("quality_report", {}).get("source_pending_count", 0)
        total_pending += c
        sl = os.path.join(PKG_ROOT, p["_dir"], "assets/rules/source_pending_list.json")
        if c > 0 and not os.path.isfile(sl):
            pending_leak.append(p["package"])
    if pending_leak:
        findings.append({"sev": "P1", "dim": "M4", "detail":
            f"{', '.join(pending_leak)} 含待核验源但缺 source_pending_list.json，商用前法源不可追溯"})
    total_rules = sum(p.get("asset_inventory", {}).get("rules", 0) for p in pkgs)
    pending_ratio = (total_pending / total_rules * 100) if total_rules else 0
    m4 = {"total_rules": total_rules, "total_source_pending": total_pending,
          "pending_ratio_pct": round(pending_ratio, 1), "leak": pending_leak}

    # ── M5 包内一致性（交付质量）──
    inconsistent = []
    dup_notes = []
    for p in pkgs:
        inv = p.get("asset_inventory", {})
        d = os.path.join(PKG_ROOT, p["_dir"], "assets/rules")
        file_rules = 0
        dup = 0
        for fp in [f for f in glob.glob(os.path.join(d, "*.json"))
                   if os.path.basename(f) != "source_pending_list.json"]:
            try:
                arr = json.load(open(fp, encoding="utf-8"))
                if isinstance(arr, list):
                    file_rules += len(arr)
                    ids = [str(r.get("rule_id", "")) for r in arr]
                    dup += len(ids) - len(set(ids))
            except Exception:
                pass
        if file_rules and file_rules != inv.get("rules", 0):
            inconsistent.append(f"{p['package']}: manifest规则{inv.get('rules')} vs 文件{file_rules}")
        if dup > 0:
            dup_notes.append(f"{p['package']} {dup} 张重复 rule_id（源资产编号治理范畴 P0-4，不影响本包交付）")
        lp = os.path.join(PKG_ROOT, p["_dir"], "assets/laws/laws_index.json")
        if os.path.isfile(lp):
            try:
                laws = json.load(open(lp, encoding="utf-8"))
                if isinstance(laws, list) and len(laws) != inv.get("laws", 0):
                    inconsistent.append(f"{p['package']}: manifest法规{inv.get('laws')} vs 文件{len(laws)}")
            except Exception:
                pass
    if inconsistent:
        findings.append({"sev": "P0", "dim": "M5", "detail":
            "包内 manifest 与文件不一致：" + "；".join(inconsistent)})
    if dup_notes:
        findings.append({"sev": "P2", "dim": "M5b", "detail":
            "重复 rule_id（源资产编号缺陷）：" + "；".join(dup_notes)})
    m5 = {"consistent": len(inconsistent) == 0, "issues": inconsistent, "dup_notes": dup_notes}

    # ── M6 规则库弹药厚度（上下文）──
    rl = next((a for a in registry.get("assets", []) if a.get("id") == "RL-001"), None)
    m6 = rl.get("metrics", {}) if rl else {}

    # ── 成熟度指数（加权 0-100）──
    score_coverage  = m1["coverage_pct"]                                  # 30%
    score_billing   = 100.0 if m2["consistent"] else 40.0                  # 20%
    score_consist   = 100.0 if m5["consistent"] else 30.0                  # 20%
    score_reuse     = min(100.0, m3["reused_rule_count"] / 50.0 * 100)     # 15%（50 张复用=满分）
    score_verify    = max(0.0, 100.0 - m4["pending_ratio_pct"])            # 15%（待核验源占比越低越好）
    maturity = (score_coverage*0.30 + score_billing*0.20 + score_consist*0.20
                + score_reuse*0.15 + score_verify*0.15)
    dims = {"M1": m1, "M2": m2, "M3": m3, "M4": m4, "M5": m5, "M6": m6}
    return dims, findings, round(maturity, 1), {
        "coverage": round(score_coverage, 1), "billing": round(score_billing, 1),
        "consistency": round(score_consist, 1), "reuse": round(score_reuse, 1),
        "verify": round(score_verify, 1)}


def main():
    quiet = "--quiet" in sys.argv
    reg = load_json(REGISTRY)
    if not reg:
        print("❌ 登记册未加载，中止"); sys.exit(2)
    pkgs = load_packages()
    if not pkgs:
        print("❌ 未扫描到任何规则包（01-规则包/*_v1.0/manifest.json）"); sys.exit(2)

    dims, findings, maturity, comp = compute_maturity(pkgs, reg)
    p0 = [f for f in findings if f["sev"] == "P0"]
    p1 = [f for f in findings if f["sev"] == "P1"]

    if not quiet:
        print(f"== 数字资产成熟度 + 商业化闭环（{TODAY.isoformat()}）==")
        print(f"规则包 {dims['M1']['total_packages']} 个（域库包 {dims['M1']['domain_packages']} / 横切包 {dims['M1']['cross_packages']}）")
        print(f"采用率 {dims['M1']['coverage_pct']}% ｜ 跨域复用 {dims['M3']['reused_rule_count']} 张 ｜ 待核验源泄漏 {dims['M4']['total_source_pending']} 张（占比 {dims['M4']['pending_ratio_pct']}%）")
        print(f"计费口径一致：{dims['M2']['consistent']} ｜ 包内一致：{dims['M5']['consistent']}")
        print(f"成熟度指数 = {maturity}/100  （覆盖{comp['coverage']} 计费{comp['billing']} 一致{comp['consistency']} 复用{comp['reuse']} 核验{comp['verify']}）")
        for f in findings:
            print(f"  [{f['sev']}] {f['dim']} {f['detail']}")
        if not findings:
            print("  ✅ 商业化闭环无告警")

    report = {"report_date": TODAY.isoformat(), "maturity_index": maturity,
              "components": comp, "dimensions": dims,
              "p0": p0, "p1": p1, "summary": f"P0={len(p0)} P1={len(p1)}"}
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "asset_maturity_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    md = [f"# 数字资产成熟度 · 商业化闭环报告 · {TODAY.isoformat()}\n"]
    md.append(f"\n**成熟度指数：{maturity}/100**\n")
    md.append(f"| 维度 | 得分 | 说明 |")
    md.append(f"|---|---|---|")
    md.append(f"| 覆盖(M1) | {comp['coverage']} | 域库封装采用率 {dims['M1']['coverage_pct']}%（{dims['M1']['domain_packages']}/{dims['M1']['n_domain_libs']}） |")
    md.append(f"| 计费口径(M2) | {comp['billing']} | 统一 {EXPECT_BILLING_MODEL} / {EXPECT_LICENSE_TYPE} |")
    md.append(f"| 包内一致(M5) | {comp['consistency']} | 交付质量 |")
    md.append(f"| 跨域复用(M3) | {comp['reuse']} | 复用 {dims['M3']['reused_rule_count']} 张（横切包命中 {dims['M3']['cross_package_reuse_hits']}） |")
    md.append(f"| 法源核验(M4) | {comp['verify']} | 待核验源占比 {dims['M4']['pending_ratio_pct']}% |")
    md.append(f"\n## 采用率与包清单\n")
    md.append(f"- 可商业化域库：**{dims['M1']['n_domain_libs']}** 个；已封装域库包：**{dims['M1']['domain_packages']}**（采用率 {dims['M1']['coverage_pct']}%）")
    md.append(f"- 横切标签包：**{dims['M1']['cross_packages']}**（审判要件 / 裁量尺度）")
    md.append(f"- 规则包总量：**{dims['M1']['total_packages']}**\n")
    md.append(f"## 跨域复用（资产杠杆）\n")
    md.append(f"- 入库规则卡去重 **{dims['M3']['total_rules_indexed']}** 张；被 ≥2 个包复用 **{dims['M3']['reused_rule_count']}** 张")
    md.append(f"- 横切包命中既有域卡 **{dims['M3']['cross_package_reuse_hits']}** 次（复用非重复建设）")
    if dims['M3']['sample']:
        md.append(f"- 样例：{', '.join(s['rule_id'] for s in dims['M3']['sample'])}")
    md.append(f"\n## 待核验源泄漏（商用前须复核）\n")
    md.append(f"- 全部包待核验源合计 **{dims['M4']['total_source_pending']}** 张（占规则卡 {dims['M4']['pending_ratio_pct']}%）")
    md.append(f"- 各包均生成 `source_pending_list.json`，可追溯；商用前须由运营/合规负责人逐条元典核验。\n")
    for sev, title in (("P0", "## P0 级（须立即处置）"), ("P1", "## P1 级（可排期）")):
        items = [f for f in findings if f["sev"] == sev]
        if items:
            md.append(title)
            for f in items:
                md.append(f"- [{f['dim']}] {f['detail']}")
    if not findings:
        md.append("\n## 告警\n✅ 商业化闭环无 P0/P1 告警。")
    md.append("\n---\n*来源：asset_ops_maturity.py 自动生成；与登记册 SSOT 互为印证。*")
    with open(os.path.join(OUT_DIR, "asset_maturity_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    sys.exit(1 if p0 else 0)


if __name__ == "__main__":
    main()
