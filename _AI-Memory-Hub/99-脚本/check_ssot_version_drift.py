#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_ssot_version_drift.py —— 中枢 SSOT 版本口径漂移巡检器  v1.1

v1.0 → v1.1（2026-11-06 首跑实测 6 条全为历史沿革误报，已核）：
    - 加结构性豁免 is_history_line()：版本演进表行 / 变更日志标题不算当前状态声明
    - 扩充豁免词（修复/升级/演进/沿革/回放…）；历史事故回放卡加 SSOT-DISCLAIMER 标记整份归档

立卡依据：RULE-060（2026-11-06 老强裁决「中枢为唯一事实源，中枢一变其它才能变」）
背景：2026-10-09 / 2026-11-06 两次「WF-002 带偏·五维」事故，根因是下游各自
      保留旧版本号、没有单向派发纪律。本脚本把 RULE-060 §三步骤⑤「回读验证」机械化。

两类检查：
  1. VALUE  登记值一致性：从 RULE-060 frontmatter 读 runtime_version / qc_spec_version
            （**不硬编码期望值**，否则脚本自己又变成漂移源），
            逐一核验下游各制品的自报版本。
  2. STALE  写死旧口径：下游文档残留 v4.8.x / 五维 QC / v4.10.3 / 三模块 等硬编码；
            带行级豁免词（历史/已废弃/禁止/事故/快照…）的行不计，避免误报
            （承 check_mirror_staleness.py v1.1 的行级豁免设计）。

ARCHIVE 类：含 `SSOT-DISCLAIMER` 标记的归档史料单列提示，计为「已声明失效」，不计漂移。

用法：python3 check_ssot_version_drift.py [--json] [--quiet]
退出码：0 全清 ｜ 1 有漂移（须按 RULE-060 §三单向派发顺序修复，禁止就地硬改）

作者：小强（WorkBuddy）  2026-11-06
"""
import os
import re
import json
import argparse

LAWKB = "/Users/chenyouqiang/Documents/LawKB"
HUB = os.path.join(LAWKB, "_AI-Memory-Hub")
SKILLS = "/Users/chenyouqiang/.workbuddy/skills/LTI文本监控器"
COCKPIT = os.path.join(LAWKB, "小强律师数字分身系统/07-系统搭建与Skill配置/9655-cockpit-v2/subapps/lti")

SSOT_CARD = os.path.join(HUB, "00-全局规则/RULE-060-中枢唯一事实源SSOT与单向派发铁律-版本规则口径以中枢为准.md")

P_JSON = os.path.join(COCKPIT, "lti_dimensions_v9.json")
P_QC9 = os.path.join(COCKPIT, "lti_qc9.py")
P_WF002 = os.path.join(HUB, "04-Workflows/WF-002-法条LTI五维QC门禁.md")
P_SKILL = os.path.join(SKILLS, "SKILL.md")
P_MAIN = os.path.join(SKILLS, "references/main.py")

# (取哪个登记值, 说明, 路径, 提取正则)
VALUE_SOURCES = [
    ("qc_spec_version", "QC spec · lti_dimensions_v9.json", P_JSON, r'"version"\s*:\s*"([^"]+)"'),
    ("qc_spec_version", "QC spec · lti_qc9.py 自报", P_QC9, r"lti_qc9\.py\)\s*v(\d+\.\d+\.\d+)"),
    ("qc_spec_version", "QC spec · WF-002 frontmatter", P_WF002, r"^version:\s*(\d+\.\d+\.\d+)\s*$"),
    ("runtime_version", "Runtime · SKILL.md frontmatter", P_SKILL, r"^version:\s*(\d+\.\d+\.\d+)\s*$"),
    ("runtime_version", "Runtime · main.py docstring 首行", P_MAIN, r"多维法律文本监控器（v(\d+\.\d+\.\d+)"),
]

# 下游「声明当前状态」的文档；中枢自身卡（RULE-060 / WF-002）不扫，避免把禁令文字误报成漂移
STALE_FILES = [
    os.path.join(LAWKB, "小强律师数字分身系统/00-系统总览与运维中心/小强律师数字分身系统-用户使用手册-v4.0.0.md"),
    os.path.join(SKILLS, "运维/LTI文本监控系统运维手册.md"),
    P_SKILL,
    P_MAIN,
    os.path.join(HUB, "04-Workflows/_索引.md"),
    os.path.join(HUB, "00-全局规则/_索引.md"),
    os.path.join(LAWKB, "知识飞轮系统/02-提炼/经验卡片/飞轮运维/经验卡-LTI九维被旧文档WF-002带偏-凭记忆占位误写五维-20261009.md"),
    os.path.join(LAWKB, "知识飞轮系统/02-提炼/经验卡片/经验卡片-引对方自认反噬铁律-辩论前须先确认对方真立场-2026-10-21.md"),
]

STALE_PATTERNS = [
    (r"v4\.8\.x", "v4.8.x 旧版本硬编码"),
    (r"五维\s*QC|五维\s*门禁|R/L/C/T/P\s*五维", "五维 QC 旧口径"),
    (r"v4\.10\.3", "v4.10.3 旧当前版本"),
    (r"v4\.0[，,]\s*三模块|三模块法律文本监控器", "v4.0 三模块旧口径"),
    (r"v4\.9\.0，九维|（\*\*v4\.9\.2", "旧真源标注"),
]

# 行级豁免词：出现即视为「历史陈述 / 禁令 / 事故回放」，不是当前状态声明
EXEMPT_WORDS = [
    "历史", "已废弃", "已删除", "已失效", "禁止", "不得", "事故", "快照", "漂移",
    "stale", "superseded", "archive", "归档", "豁免", "旧版本", "旧口径", "旧文档",
    "误写", "带偏", "遗留", "作废", "不再维护", "曾", "已升", "已改", "已修",
    # v1.1 增：变更日志/版本演进/事故回放的合法历史陈述
    "修复", "升级", "演进", "沿革", "变更记录", "纠正", "回放", "新增", "上线",
    "当时", "首修", "收口", "实测", "回归", "已闭环", "早期", "此前", "初版",
]

DISCLAIMER_MARK = "SSOT-DISCLAIMER"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def load_ssot():
    text = read(SSOT_CARD)
    fm = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if not fm:
        raise SystemExit(f"[ERR] RULE-060 缺 frontmatter: {SSOT_CARD}")
    out = {}
    for key in ("runtime_version", "qc_spec_version"):
        m = re.search(rf'^{key}:\s*"?([\d.]+)"?', fm.group(1), re.M)
        if not m:
            raise SystemExit(f"[ERR] RULE-060 缺登记字段 {key}，禁止凭记忆填值")
        out[key] = m.group(1)
    return out


def check_values(ssot):
    rows, bad = [], 0
    for key, label, path, pat in VALUE_SOURCES:
        if not os.path.exists(path):
            rows.append((label, "MISSING", ssot[key], "文件不存在"))
            bad += 1
            continue
        m = re.search(pat, read(path), re.M)
        got = m.group(1) if m else "UNPARSED"
        ok = (got == ssot[key])
        rows.append((label, got, ssot[key], "✅" if ok else "🔴 漂移"))
        if not ok:
            bad += 1
    return rows, bad


def is_history_line(line):
    """结构性豁免：版本演进表行 / 变更日志标题 / 带历史豁免词的行，均非当前状态声明。"""
    s = line.strip()
    if re.match(r"^#{2,4}\s*(?:v?\d+\.\d+|\d{4}-\d{2}-\d{2})", s):
        return True
    if re.match(r"^\|?\s*\*{0,2}v?\d+\.\d+\.\d+\*{0,2}\s*\|", s):
        return True
    return any(w.lower() in s.lower() for w in EXEMPT_WORDS)


def check_stale():
    hits, exempted, archives = [], 0, []
    for path in STALE_FILES:
        if not os.path.exists(path):
            continue
        text = read(path)
        if DISCLAIMER_MARK in text:
            archives.append(os.path.basename(path))
            continue  # 已加口径失效横幅的归档史料，整份不计漂移
        for lineno, line in enumerate(text.splitlines(), 1):
            for pat, label in STALE_PATTERNS:
                if not re.search(pat, line):
                    continue
                if is_history_line(line):
                    exempted += 1
                else:
                    hits.append((os.path.basename(path), lineno, label, line.strip()[:100]))
                break
    return hits, exempted, archives


def main():
    ap = argparse.ArgumentParser(description="中枢 SSOT 版本口径漂移巡检")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--quiet", action="store_true", help="只输出结论")
    args = ap.parse_args()

    ssot = load_ssot()
    values, v_bad = check_values(ssot)
    hits, exempted, archives = check_stale()
    drift = v_bad + len(hits)

    if args.json:
        print(json.dumps({
            "ssot": ssot,
            "value_checks": [{"name": a, "got": b, "expected": c, "verdict": d} for a, b, c, d in values],
            "stale_hits": [{"file": a, "line": b, "label": c, "text": d} for a, b, c, d in hits],
            "exempted_lines": exempted,
            "archives": archives,
            "drift": drift,
        }, ensure_ascii=False, indent=2))
        return 1 if drift else 0

    if not args.quiet:
        print("=== 中枢 SSOT 版本口径漂移巡检 · RULE-060 ===")
        print(f"登记值: runtime_version={ssot['runtime_version']}  qc_spec_version={ssot['qc_spec_version']}\n")
        print("[VALUE] 登记值一致性")
        for label, got, exp, verdict in values:
            print(f"  {verdict:8s} {label}: 实读 {got} / 中枢 {exp}")
        print(f"\n[STALE] 写死旧口径：命中 {len(hits)} 行（行级豁免 {exempted} 行）")
        for f, ln, label, txt in hits:
            print(f"  🔴 {f}:{ln} [{label}] {txt}")
        print(f"\n[ARCHIVE] 已声明失效 / 历史快照，不计漂移：{len(archives)} 份")
        for a in archives:
            print(f"  🗄 {a}")
    print(("🔴 结论：存在漂移，须按 RULE-060 §三单向派发顺序修复（禁止就地硬改）" if drift
           else "✅ 结论：无漂移，中枢登记值与下游自报值一致"))
    return 1 if drift else 0


if __name__ == "__main__":
    raise SystemExit(main())
