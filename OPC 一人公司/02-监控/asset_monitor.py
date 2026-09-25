#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
asset_monitor.py — 数字资产八维监控矩阵（P1）
============================================
把「漂移追杀」从手册变成可跑的器：每维独立体检，汇总 P0/P1/P2 告警，
产出《资产健康月报》模板（md）+ 机器可读 json。

八维：
  D1 编目完整性   D2 数据漂移      D3 配置一致性   D4 自动化健康
  D5 规则库归库   D6 连接器状态    D7 连接层完整性 D8 心智成熟度

复用 opc_common：路径常量 + 实证计数 + compute_drift + check_c8 + check_rule_library
只读不写（监控器不修改任何资产）。
退出码：有 P0→1，否则 0（--quiet 时仅返回退出码）。
"""
import os
import sys
import json
import re
import datetime
import concurrent.futures as cf

from opc_common import (
    ROOT, WORK, REGISTRY, TODAY,
    load_json, read_text, ep,
    count_r_cards, count_skills, count_automations, count_handbooks,
    compute_drift, check_c8, check_rule_library,
    LINK_SCRIPT, LINK_LASTRUN, CONNECTOR_CACHE, AUTOMATION_DIR,
)

OUT_DIR = os.path.join(ROOT, "OPC 一人公司/02-监控")
AUTOMATION_STALE_DAYS = 30
CONNECTOR_STALE_DAYS = 7


# ───────────────────────── 维度体检函数 ─────────────────────────

def dim_catalog(reg):
    """D1 编目完整性：9 大类是否全部入册、每类资产数、是否存在未入册孤儿根目录"""
    cats = reg.get("categories", [])
    assets = reg.get("assets", [])
    by_cat = {}
    for a in assets:
        by_cat[a.get("category", "未分类")] = by_cat.get(a.get("category", "未分类"), 0) + 1
    findings = []
    for c in cats:
        if by_cat.get(c, 0) == 0:
            findings.append({"severity": "P1", "detail": f"大类「{c}」在登记册中 0 条目，疑似漏编目"})
    # 孤儿检测（轻量）：skills 与 06-沉淀 必然应入册
    known = {a.get("location", "") for a in assets}
    checks = [
        ("~/.workbuddy/skills", "技能库根"),
        (os.path.join(ROOT, "知识飞轮系统/06-沉淀"), "卡库根"),
    ]
    for loc, label in checks:
        if loc not in known and ep(loc) not in {ep(k) for k in known}:
            findings.append({"severity": "P2", "detail": f"{label} 未在登记册 location 命中（建议核对 SSOT 覆盖）"})
    status = "PASS" if not any(f["severity"] in ("P0", "P1") for f in findings) else ("WARN" if any(f["severity"] == "P1" for f in findings) else "PASS")
    return {"dim": "D1", "name": "编目完整性", "status": status,
            "summary": f"大类 {len(cats)} / 已入册资产 {len(assets)} / 分布 {by_cat}",
            "findings": findings}


def dim_drift(reg):
    """D2 数据漂移：复用 compute_drift"""
    findings = compute_drift(reg)
    status = "PASS" if not findings else ("FAIL" if any(f["severity"] == "P0" for f in findings) else "WARN")
    return {"dim": "D2", "name": "数据漂移", "status": status,
            "summary": f"发现 {len(findings)} 项（P0={sum(1 for f in findings if f['severity']=='P0')} / P1={sum(1 for f in findings if f['severity']=='P1')}）",
            "findings": findings}


def dim_config():
    """D3 配置一致性：C8 席位配置 vs 中台面板"""
    r = check_c8()
    sev = {"PASS": None, "FAIL": "P0", "UNKNOWN": "P1"}.get(r.get("status"))
    findings = []
    if sev:
        findings.append({"severity": sev, "detail": f"C8 {r.get('detail')}（seat={r.get('seat')} panel={r.get('panel')}）"})
    status = "PASS" if r.get("status") == "PASS" else ("FAIL" if r.get("status") == "FAIL" else "WARN")
    return {"dim": "D3", "name": "配置一致性", "status": status,
            "summary": f"seat={r.get('seat')} panel={r.get('panel')} → {r.get('status')}",
            "findings": findings}


def dim_automation(reg):
    """D4 自动化健康：实测数 vs 登记 + 陈旧复核"""
    reg_count = next((a.get("metrics", {}).get("自动化数") for a in reg.get("assets", []) if a.get("id") == "AU-001"), None)
    fresh = count_automations()
    findings = []
    if reg_count is not None and fresh != reg_count:
        findings.append({"severity": "P1", "detail": f"自动化数 登记 {reg_count} vs 实测 {fresh}（Δ{fresh-reg_count}），须回写登记册"})
    # 陈旧复核
    lv = next((a.get("last_verified") for a in reg.get("assets", []) if a.get("id") == "AU-001"), "")
    try:
        if lv and (TODAY - datetime.date.fromisoformat(lv)).days > AUTOMATION_STALE_DAYS:
            findings.append({"severity": "P2", "detail": f"AU-001 last_verified {lv} 超 {AUTOMATION_STALE_DAYS} 天，建议重测"})
    except Exception:
        pass
    status = "PASS" if not findings else "WARN"
    return {"dim": "D4", "name": "自动化健康", "status": status,
            "summary": f"实测自动化 {fresh} / 登记 {reg_count}",
            "findings": findings}


def dim_rule_lib():
    """D5 规则库归库状态"""
    r = check_rule_library()
    sev = "PASS" if r.get("status") == "PASS" else "WARN"
    findings = []
    if r.get("重复ID", 0) != 0:
        findings.append({"severity": "P0", "detail": f"规则库存在重复ID {r.get('重复ID')}（归库不幂等）"})
    return {"dim": "D5", "name": "规则库归库", "status": sev,
            "summary": r.get("detail", str(r)),
            "findings": findings}


def dim_connector(reg):
    """D6 连接器状态：登记口径 + 缓存目录实证 + 陈旧标记"""
    cn = next((a for a in reg.get("assets", []) if a.get("id") == "CN-001"), None)
    findings = []
    cache_dirs = 0
    if os.path.isdir(CONNECTOR_CACHE):
        cache_dirs = sum(1 for n in os.listdir(CONNECTOR_CACHE) if not n.startswith('.'))
    # 实证：连接器缓存目录存在即证明连接器体系在
    if cache_dirs == 0:
        findings.append({"severity": "P1", "detail": "未检测到连接器缓存目录，连接器可能未初始化"})
    lv = cn.get("last_verified", "") if cn else ""
    try:
        if lv and (TODAY - datetime.date.fromisoformat(lv)).days > CONNECTOR_STALE_DAYS:
            findings.append({"severity": "P2", "detail": f"CN-001 last_verified {lv} 超 {CONNECTOR_STALE_DAYS} 天，活连接状态须 UI 复核（本器无法读取实时连接态）"})
    except Exception:
        pass
    status = "PASS" if not findings else "WARN"
    return {"dim": "D6", "name": "连接器状态", "status": status,
            "summary": f"缓存连接器目录 {cache_dirs}（实时连接态以 WorkBuddy UI 为准）",
            "findings": findings}


# ───────────────────────── D7 增量扫描缓存 ─────────────────────────
D7_CACHE_PATH = os.path.join(OUT_DIR, ".d7_link_cache.json")
D7_CACHE_VERSION = 1

def _d7_covered_incremental():
    """增量统计「含自动补链段」的成员卡数（D7 连接层完整性）。

    成员卡目录（与 link_cards_rules.py 一致）：02-提炼/经验卡片 + 06-沉淀。
    缓存每个文件的 mtime 与命中状态，仅重扫 mtime 变更的文件，避开慢盘逐文件
    全量读（实测全量 ~50s，LawKB 位于慢盘）导致自动化超时。首次运行或缓存
    失效则回退全量。缓存损坏/版本不符均安全回退。
    """
    member_roots = [
        os.path.join(ROOT, "知识飞轮系统/02-提炼/经验卡片"),
        os.path.join(ROOT, "知识飞轮系统/06-沉淀"),
    ]
    marker = "关联（知识飞轮连接层自动补链"
    try:
        with open(D7_CACHE_PATH, encoding='utf-8') as f:
            cache = json.load(f)
    except Exception:
        cache = {}
    if not isinstance(cache, dict) or cache.get("version") != D7_CACHE_VERSION:
        cache = {"version": D7_CACHE_VERSION, "files": {}}
    files = cache.get("files", {})
    now_paths = set()
    changed = []  # (path, mtime) 需重扫
    for base in member_roots:
        if not os.path.isdir(base):
            continue
        for dp, _, fs in os.walk(base):
            bn = os.path.basename(dp)
            # 跳过隐藏目录、巨型备份目录（.backup_link_*）与缓存，仅统计活卡片
            if bn.startswith('.') or 'backup' in bn.lower() or '__pycache__' in bn:
                continue
            for fn in fs:
                if not fn.endswith('.md'):
                    continue
                p = os.path.join(dp, fn)
                now_paths.add(p)
                try:
                    mt = os.path.getmtime(p)
                except Exception:
                    continue
                rec = files.get(p)
                if isinstance(rec, dict) and rec.get("mtime") == mt and "hit" in rec:
                    continue  # 缓存命中，跳过读取
                changed.append((p, mt))
    # 重扫变更文件（线程池并行，缓解慢盘 I/O）
    if changed:
        paths = [c[0] for c in changed]
        mtimes = [c[1] for c in changed]
        def _has_marker(p):
            try:
                with open(p, encoding='utf-8', errors='ignore') as fh:
                    return marker in fh.read(16000)
            except Exception:
                return False
        with cf.ThreadPoolExecutor(max_workers=8) as ex:
            for p, mt, ok in zip(paths, mtimes, ex.map(_has_marker, paths)):
                files[p] = {"mtime": mt, "hit": ok}
    # 清理已删文件
    for p in [k for k in files if k not in now_paths]:
        del files[p]
    covered = sum(1 for v in files.values() if isinstance(v, dict) and v.get("hit"))
    try:
        with open(D7_CACHE_PATH, "w", encoding='utf-8') as f:
            json.dump({"version": D7_CACHE_VERSION, "files": files,
                       "last_scan": TODAY.isoformat(),
                       "changed_this_run": len(changed)}, f, ensure_ascii=False)
    except Exception:
        pass
    return covered


def dim_link_layer():
    """D7 连接层完整性：补链脚本存在 + 自动补链段覆盖广度 + lastrun 标记"""
    findings = []
    script_ok = os.path.isfile(LINK_SCRIPT)
    if not script_ok:
        findings.append({"severity": "P1", "detail": "连接层补链脚本 link_cards_rules.py 未找到"})
    # 实证：统计含自动补链段的成员卡数（证明补链器跑过）
    # 范围收窄到补链器实际处理的成员卡目录（与 link_cards_rules.py 一致）：
    #   02-提炼/经验卡片（经验卡片分类目录） + 06-沉淀（裁判规则库 + 17 个域库规则卡）
    # 不再 walk 整个「知识飞轮系统」，避开 01-中枢/03-连接/04-Workflows/07-输出
    # 等非卡片大目录，根治 D7 超时（D7 超时运维 2026-09-24）
    # 增量扫描成员卡（02-提炼/经验卡片 + 06-沉淀），仅重扫变更文件，避开慢盘全量读超时
    covered = _d7_covered_incremental()
    if covered == 0:
        findings.append({"severity": "P0", "detail": "未检测到任何自动补链段，连接层可能从未运行"})
    else:
        findings.append({"severity": "P2", "detail": f"自动补链段覆盖 {covered} 个文件（补链器已运行）"})
    if not os.path.isdir(LINK_LASTRUN):
        findings.append({"severity": "P2", "detail": "未找到 link_lastrun 标记目录，无法确认最近一次补链时间，建议落 lastrun 时间戳"})
    status = "PASS" if not any(f["severity"] in ("P0", "P1") for f in findings) else ("FAIL" if any(f["severity"] == "P0" for f in findings) else "WARN")
    return {"dim": "D7", "name": "连接层完整性", "status": status,
            "summary": f"补链脚本={'在' if script_ok else '缺'} / 覆盖 {covered} 文件",
            "findings": findings}


def dim_maturity(reg):
    """D8 心智成熟度：手册数实测 vs 登记 + 成熟度追踪文件存在性"""
    reg_count = next((a.get("metrics", {}).get("手册数") for a in reg.get("assets", []) if a.get("id") == "MM-001"), None)
    fresh = count_handbooks()
    findings = []
    if reg_count is not None and fresh != reg_count:
        findings.append({"severity": "P1", "detail": f"手册数 登记 {reg_count} vs 实测 {fresh}（Δ{fresh-reg_count}），须回写登记册"})
    # 成熟度追踪文件（*成熟度* / *复盘报告*）
    mt = 0
    for f in os.listdir(WORK):
        if os.path.isfile(os.path.join(WORK, f)) and ('成熟度' in f or '复盘' in f):
            mt += 1
    if mt == 0:
        findings.append({"severity": "P2", "detail": "未检测到心智成熟度周报/复盘文件，建议建立常态化成熟度追踪"})
    status = "PASS" if not findings else "WARN"
    return {"dim": "D8", "name": "心智成熟度", "status": status,
            "summary": f"实测手册 {fresh} / 登记 {reg_count} / 成熟度追踪文件 {mt}",
            "findings": findings}


# ───────────────────────── 主流程 ─────────────────────────

def main():
    quiet = "--quiet" in sys.argv
    reg = load_json(REGISTRY)
    if not reg:
        print("❌ 登记册未加载，中止")
        sys.exit(2)

    dims = [
        dim_catalog(reg),
        dim_drift(reg),
        dim_config(),
        dim_automation(reg),
        dim_rule_lib(),
        dim_connector(reg),
        dim_link_layer(),
        dim_maturity(reg),
    ]

    # 汇总告警
    all_f = [f for d in dims for f in d["findings"]]
    p0 = [f for f in all_f if f["severity"] == "P0"]
    p1 = [f for f in all_f if f["severity"] == "P1"]
    p2 = [f for f in all_f if f["severity"] == "P2"]

    if not quiet:
        print(f"== 数字资产八维监控矩阵（{TODAY.isoformat()}）==")
        print(f"维度 8 ｜ 告警 P0={len(p0)} / P1={len(p1)} / P2={len(p2)}")
        for d in dims:
            print(f"  [{d['status']:4}] {d['dim']} {d['name']}: {d['summary']}")
            for f in d["findings"]:
                if f["severity"] in ("P0", "P1"):
                    print(f"        · [{f['severity']}] {f['detail']}")
        if not all_f:
            print("  ✅ 八维全部健康，无告警")

    # 报告
    os.makedirs(OUT_DIR, exist_ok=True)
    report = {
        "report_date": TODAY.isoformat(),
        "report_type": "资产健康月报",
        "dimensions": dims,
        "p0": p0, "p1": p1, "p2": p2,
        "summary": f"P0={len(p0)} P1={len(p1)} P2={len(p2)}",
    }
    with open(os.path.join(OUT_DIR, "asset_health_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    md = [f"# 数字资产健康月报 · {TODAY.isoformat()}\n"]
    md.append(f"\n本报告由 `asset_monitor.py` 自动生成，覆盖八维监控矩阵。\n")
    md.append(f"**告警汇总**：P0={len(p0)}（生产级/须立即处置）｜ P1={len(p1)}（观察级/可排期）｜ P2={len(p2)}（建议项）\n")
    md.append("\n## 八维矩阵\n")
    md.append("| 维度 | 名称 | 状态 | 概要 |")
    md.append("|---|---|---|---|")
    for d in dims:
        md.append(f"| {d['dim']} | {d['name']} | {d['status']} | {d['summary']} |")
    for sev, title in (("P0", "## P0 级（生产级 · 须立即处置）"),
                       ("P1", "## P1 级（观察级 · 可排期回写）"),
                       ("P2", "## P2 级（建议项 · 优化）")):
        items = [f for f in all_f if f["severity"] == sev]
        if items:
            md.append(f"\n{title}\n")
            for f in items:
                md.append(f"- {f['detail']}")
    md.append("\n---\n*登记册 SSOT：`00-数字资产登记册/asset_registry.json`｜ 一致性与本矩阵互为印证，冲突以最新实测为准。*")
    with open(os.path.join(OUT_DIR, "asset_health_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    sys.exit(1 if p0 else 0)


if __name__ == "__main__":
    main()
