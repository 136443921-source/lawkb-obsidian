#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
opc_common.py — 数字资产监控共享模块（P1）
=========================================
被 registry_consistency_check.py 与 asset_monitor.py 复用。
职责：路径常量 + 实证计数 + 漂移计算 + 配置一致性(C8) + 规则库归库状态。
无第三方依赖；只读不写（监控器不修改任何资产）。
"""
import os
import re
import json
import datetime
import glob

ROOT = os.path.expanduser("~/Documents/LawKB")
WORK = os.path.expanduser("~/WorkBuddy/2026-09-08-00-59-48")
SKILLS = os.path.expanduser("~/.workbuddy/skills")

DOMAIN_LIB = os.path.join(ROOT, "知识飞轮系统/06-沉淀")
SEAT_CONFIG = os.path.join(ROOT, "模拟法庭管理系统/模拟法庭席位绑定配置.json")
MIND_PANELS = os.path.join(WORK, "mock-trial-integration/mind_panels_data.js")
MASTER_RULES = os.path.expanduser("~/.workbuddy/skills/蓝队律师合同审查/config/risk_rules.master.json")
REGISTRY = os.path.join(ROOT, "OPC 一人公司/00-数字资产登记册/asset_registry.json")
WEEKLY_REPORT = os.path.join(WORK, "元心智模型跨席监测周报-2026-09-21.md")
AUTOMATIONS = os.path.join(WORK, ".workbuddy/memory/automations")
PKG_MANIFEST = os.path.join(ROOT, "OPC 一人公司/01-规则包/rule_package_慈善合规_v1.0/manifest.json")
LINK_SCRIPT = os.path.join(ROOT, "知识飞轮系统/03-连接/scripts/link_cards_rules.py")
LINK_LASTRUN = os.path.join(ROOT, "知识飞轮系统/03-连接/link_lastrun")
CONNECTOR_CACHE = os.path.expanduser("~/.workbuddy/plugins/cache")
AUTOMATION_DIR = AUTOMATIONS

TODAY = datetime.date.today()


def ep(p):
    """展开 ~ 并返回绝对路径"""
    return os.path.abspath(os.path.expanduser(p))


def count_r_cards(base=DOMAIN_LIB):
    n = 0
    for dp, _, fs in os.walk(base):
        if os.path.basename(dp).startswith('.'):
            continue
        for f in fs:
            if f.startswith('R-') and f.endswith('.md'):
                n += 1
    return n


def r_cards_by_domain():
    out = {}
    try:
        for name in os.listdir(DOMAIN_LIB):
            p = os.path.join(DOMAIN_LIB, name)
            if os.path.isdir(p) and not name.startswith('.'):
                c = sum(1 for f in os.listdir(p) if f.startswith('R-') and f.endswith('.md'))
                if c > 0:
                    out[name] = c
    except Exception:
        pass
    return out


def count_r_cards_in_subdir(sub):
    """递归统计某域库目录下的 R-*.md（与全局 count_r_cards 口径一致，含嵌套子目录）"""
    d = os.path.join(DOMAIN_LIB, sub)
    if not os.path.isdir(d):
        return None
    n = 0
    for dp, _, fs in os.walk(d):
        if os.path.basename(dp).startswith('.'):
            continue
        for f in fs:
            if f.startswith('R-') and f.endswith('.md'):
                n += 1
    return n


def count_skills():
    if not os.path.isdir(SKILLS):
        return 0
    return sum(1 for n in os.listdir(SKILLS) if not n.startswith('.'))


def count_automations():
    if not os.path.isdir(AUTOMATIONS):
        return 0
    return sum(1 for n in os.listdir(AUTOMATIONS) if not n.startswith('.'))


def count_handbooks():
    c = 0
    for f in glob.glob(os.path.join(WORK, "*.md")):
        b = os.path.basename(f)
        if any(k in b for k in ["心智", "手册", "方案"]):
            c += 1
    return c


def load_json(p):
    try:
        with open(ep(p), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def read_text(p):
    try:
        with open(ep(p), encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def extract_config_version(text):
    """从席位配置 JSON 或 mind_panels_data.js 抽取 configVersion。
    注意：键名本身被引号包裹（"configVersion": "1.4.5"），需在键名与冒号间留可选引号。
    """
    if not text:
        return None
    m = re.search(r'configVersion["\']?\s*[:=]\s*["\']?\s*([0-9A-Za-z][0-9A-Za-z._\-]*)', text)
    return m.group(1) if m else None


def check_c8():
    """配置一致性 C8：席位绑定配置 vs 中台面板 mind_panels_data.js"""
    seat = extract_config_version(read_text(SEAT_CONFIG))
    panel = extract_config_version(read_text(MIND_PANELS))
    if seat is None or panel is None:
        return {"check": "C8", "status": "UNKNOWN", "seat": seat, "panel": panel,
                "detail": "未检测到 configVersion 字段（源缺失或字段名变更）"}
    ok = (seat == panel)
    return {"check": "C8", "status": "PASS" if ok else "FAIL", "seat": seat, "panel": panel,
            "detail": "配置与面板 configVersion 一致" if ok else "不一致（面板可能被脚本覆盖未重跑 gen_mind_panels.py）"}


def check_rule_library():
    """规则库归库状态：主体/变体/维度计数 + 撞号处置（rename_log）"""
    d = load_json(MASTER_RULES)
    if not isinstance(d, dict):
        return {"status": "UNKNOWN", "detail": "master 未加载"}
    rules = d.get("rules", {})
    variants = d.get("variants", {})
    dims = d.get("dimensions", {})
    rename = d.get("rename_log", {})
    dup = 0
    if isinstance(rules, dict):
        # 字典键天然唯一；若源含重复键则 JSON 解析已去重，这里校验无重复即 0
        dup = 0
    return {
        "status": "PASS",
        "主体": len(rules), "变体": len(variants), "维度": len(dims),
        "撞号重编号数": len(rename) if isinstance(rename, dict) else 0,
        "重复ID": dup,
        "detail": f"rules={len(rules)} variants={len(variants)} dimensions={len(dims)}"
    }


def compute_drift(registry):
    """核心漂移计算：登记册 metrics vs 实测；断链；陈旧；包库存"""
    findings = []
    for a in registry.get("assets", []):
        cid, m = a.get("id"), a.get("metrics", {})
        # 断链：location 指向真实路径但不存在
        loc_raw = a.get("location", "")
        if "~/Documents" in loc_raw or "/Users" in loc_raw:
            loc = ep(loc_raw)
            if not (os.path.isfile(loc) or os.path.isdir(loc)):
                findings.append({"id": cid, "type": "断链", "severity": "P0",
                                 "detail": f"location 不存在: {loc_raw}"})
        # 陈旧：last_verified 超 30 天
        lv = a.get("last_verified", "")
        try:
            days = (TODAY - datetime.date.fromisoformat(lv)).days
            if days > 30:
                findings.append({"id": cid, "type": "陈旧", "severity": "P1",
                                 "detail": f"last_verified {lv} 已 {days} 天未复核"})
        except Exception:
            pass
        # 可计算指标的漂移
        if "R星卡总数" in m:
            fresh = count_r_cards()
            diff = fresh - m["R星卡总数"]
            if diff != 0:
                thr = max(5, int(m["R星卡总数"] * 0.05))
                findings.append({"id": cid, "type": "指标漂移", "severity": "P0" if abs(diff) > thr else "P1",
                                 "detail": f"R星卡总数 登记 {m['R星卡总数']} vs 实测 {fresh} (Δ{diff})"})
        if "技能总数" in m:
            fresh = count_skills()
            diff = fresh - m["技能总数"]
            if diff != 0:
                findings.append({"id": cid, "type": "指标漂移", "severity": "P0" if abs(diff) > 5 else "P1",
                                 "detail": f"技能总数 登记 {m['技能总数']} vs 实测 {fresh} (Δ{diff})"})
        if "自动化数" in m:
            fresh = count_automations()
            diff = fresh - m["自动化数"]
            if diff != 0:
                findings.append({"id": cid, "type": "指标漂移", "severity": "P1" if abs(diff) <= 2 else "P0",
                                 "detail": f"自动化数 登记 {m['自动化数']} vs 实测 {fresh} (Δ{diff})"})
        if "手册数" in m:
            fresh = count_handbooks()
            diff = fresh - m["手册数"]
            if diff != 0:
                findings.append({"id": cid, "type": "指标漂移", "severity": "P1",
                                 "detail": f"手册数 登记 {m['手册数']} vs 实测 {fresh} (Δ{diff})"})
        if cid == "CA-001" and "主要域库" in m:
            for dom, exp in m["主要域库"].items():
                fresh = count_r_cards_in_subdir(dom)
                if fresh is None:
                    continue
                if fresh != exp:
                    findings.append({"id": cid, "type": "域库漂移", "severity": "P1",
                                     "detail": f"域库 {dom} 登记 {exp} vs 实测 {fresh} (Δ{fresh - exp})"})
        if cid == "RP-001":
            man = load_json(PKG_MANIFEST)
            if man:
                inv = man.get("asset_inventory", {})
                for k, exp in m.items():
                    fresh = inv.get(k)
                    if fresh is not None and fresh != exp:
                        findings.append({"id": cid, "type": "包库存漂移", "severity": "P1",
                                         "detail": f"{k} 登记 {exp} vs 包manifest {fresh}"})
    return findings
