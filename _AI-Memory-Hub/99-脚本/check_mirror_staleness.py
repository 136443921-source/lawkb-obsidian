#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_mirror_staleness.py —— 镜像陈旧 / 值漂移 / 双原件 巡检器  v1.1

背景（2026-11-01）：
    报告"case-state 未回写"时，实际原件已于 10-28 回写。错因不是抄错，
    是引用了桌面一份 10-13 的同名旧版 case-state.json。
    见 WF-130 §六 R12 / §七 副本腐坏处置规程。

三类检查（v1.1 收严，避免误报）：
    1. DUP    双原件：**同一案号**出现多份 case-state.json      → 🔴 P0
    2. DRIFT  值漂移：镜像里抄了已知旧值                        → 🔴 P0
    3. STALE  镜像陈旧：状态类文档 mtime 早于原件                → 🟠 P1

v1.0 → v1.1 修正（首版误报 15/17，已核）：
    - DUP 原按文件名比对，导致全系统每个案件的原件互报 → 改按 caseNo 分组
    - STALE 原按"任意文件 mtime 早于原件"判定，把历史文书全报成陈旧 → 改限定状态类文档
    - DRIFT 原逐字匹配，警告文本本身含旧值会永久误报 → 加行级豁免词

用法：python3 check_mirror_staleness.py [--json] [--quiet]
退出码：0 全清 ｜ 1 有 P1 ｜ 2 有 P0

作者：小强（WorkBuddy）  2026-11-01
"""
import os
import re
import json
import time
import argparse

# ─────────────────────────── 配置区 ───────────────────────────

WATCHERS = [
    {
        "name": "6658 丁戊祥诉刘九零吊顶案",
        "origin": "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/"
                  "丁戊祥诉刘九零吊顶买卖合同纠纷案/case-state.json",
        "case_no": "(2026)黔0330民初6658号",

        # 镜像：只列"声称当前状态"的文档所在位置（不含案卷文书）
        "mirror_dirs": [
            "/Users/chenyouqiang/.workbuddy/rules",
            "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/"
            "丁戊祥诉刘九零吊顶买卖合同纠纷案/作战室/00_总纲",
            "/Users/chenyouqiang/Documents/LawKB/_AI-Memory-Hub/00-全局规则",
            "/Users/chenyouqiang/Documents/LawKB/_AI-Memory-Hub/02-当前项目",
        ],
        # 镜像中还必须是"本案件状态声明"文档才算：文件名须命中案件标识
        "mirror_name_pat": r"6658|吊顶|case-warroom",
        # 双原件检测范围
        "dup_roots": [
            "/Users/chenyouqiang/Desktop/小强律师办案系统",
            "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统",
        ],
        "dup_name": "case-state.json",
        # 已知旧值
        "stale_values": [
            r"一审已判·待生效",
            r"updated[\"']?\s*[:：]\s*2026-10-15",
            r"回写待老强拍板",
            r"原告\+黄茂姣/欧派店已上诉",
        ],
        "exempt": [r"05-归档", r"_backups", r"接线方案_v1", r"\.workbuddy/memory/"],
        "must_contain": ["6658", "丁戊祥"],
    },
]

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".obsidian", "_backups", "05-归档"}
SCAN_EXT = (".md", ".json", ".yaml", ".yml")
MAX_SIZE = 2 * 1024 * 1024

# 警告/禁止语境豁免：同一行出现这些词，说明是在"举反例"，不算漂移
EXEMPT_LINE = re.compile(r"不得引用|勿引|旧版|警告|读错|禁止|已废弃|DEPRECATED|❌")


# ─────────────────────────── 检查逻辑 ───────────────────────────

def load_origin(path):
    mt = os.path.getmtime(path)
    d = {}
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        d = {"_error": str(e)}
    return mt, d


def find_duplicate_originals(roots, name, origin_path, case_no):
    """同案号出现多份原件才算双原件"""
    paths = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dp, dns, fns in os.walk(root):
            dns[:] = [x for x in dns if x not in SKIP_DIRS]
            if name in fns:
                paths.append(os.path.join(dp, name))

    same_case = []
    for p in paths:
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if (d.get("caseNo") or "").strip() == case_no:
            same_case.append((p, d))

    if len(same_case) <= 1:
        return []
    # 只剩权威源之外的那些
    auth = os.path.abspath(origin_path)
    out = []
    for p, d in same_case:
        if os.path.abspath(p) == auth:
            continue
        out.append({
            "level": "P0", "kind": "DUP", "path": p,
            "detail": "同案号另一份原件：status=%s / updatedAt=%s"
                      % (d.get("status", "?"), d.get("updatedAt", "?")),
            "mtime": os.path.getmtime(p),
        })
    return out


def scan_mirrors(w, origin_mtime):
    issues = []
    stale_res = [re.compile(p) for p in w["stale_values"]]
    exempt_res = [re.compile(p) for p in w["exempt"]]
    path_pat = re.compile(w["mirror_name_pat"]) if w["mirror_name_pat"] else None
    seen = set()

    for root in w["mirror_dirs"]:
        if not os.path.isdir(root):
            continue
        for dp, dns, fns in os.walk(root):
            dns[:] = [x for x in dns if x not in SKIP_DIRS]
            for fn in fns:
                if not fn.lower().endswith(SCAN_EXT):
                    continue
                fp = os.path.join(dp, fn)
                if fp == w["origin"] or fp in seen:
                    continue
                seen.add(fp)
                if any(r.search(fp) for r in exempt_res):
                    continue
                if path_pat and not path_pat.search(fn):
                    continue
                try:
                    if os.path.getsize(fp) > MAX_SIZE:
                        continue
                    txt = open(fp, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                if not all(k in txt for k in w["must_contain"]):
                    continue

                # DRIFT：逐行查旧值，跳过"警告语境"行
                hits = []
                for i, line in enumerate(txt.splitlines(), 1):
                    if EXEMPT_LINE.search(line):
                        continue
                    for r in stale_res:
                        if r.search(line):
                            hits.append("L%d %s" % (i, r.pattern))
                if hits:
                    issues.append({
                        "level": "P0", "kind": "DRIFT", "path": fp,
                        "detail": "抄了旧值 → %s" % "；".join(hits[:3]),
                        "mtime": os.path.getmtime(fp),
                    })
                    continue

                # STALE：仅状态声明类文档，且按"日"比较（同日不算陈旧）
                mt = os.path.getmtime(fp)
                d_mirror = time.strftime("%Y-%m-%d", time.localtime(mt))
                d_origin = time.strftime("%Y-%m-%d", time.localtime(origin_mtime))
                if d_mirror < d_origin:
                    issues.append({
                        "level": "P1", "kind": "STALE", "path": fp,
                        "detail": "mtime %s 早于原件 %s"
                                  % (time.strftime("%Y-%m-%d", time.localtime(mt)),
                                     time.strftime("%Y-%m-%d", time.localtime(origin_mtime))),
                        "mtime": mt,
                    })
    return issues


def run(w):
    if not os.path.exists(w["origin"]):
        return [{"level": "P0", "kind": "MISSING", "path": w["origin"],
                 "detail": "原件不存在", "mtime": 0}]
    omt, od = load_origin(w["origin"])
    issues = []
    issues.extend(find_duplicate_originals(
        w["dup_roots"], w["dup_name"], w["origin"], w["case_no"]))
    issues.extend(scan_mirrors(w, omt))
    for it in issues:
        it["case"] = w["name"]
        it["origin_status"] = od.get("status", "?")
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    all_issues = []
    for w in WATCHERS:
        all_issues.extend(run(w))

    if a.json:
        print(json.dumps(all_issues, ensure_ascii=False, indent=2))
    elif not all_issues:
        if not a.quiet:
            print("✅ 无双原件、无值漂移、无陈旧镜像。")
    else:
        p0 = [i for i in all_issues if i["level"] == "P0"]
        p1 = [i for i in all_issues if i["level"] == "P1"]
        print("巡检：🔴 P0 %d ｜ 🟠 P1 %d\n" % (len(p0), len(p1)))
        for it in p0 + p1:
            mark = "🔴" if it["level"] == "P0" else "🟠"
            print("%s [%s] %s" % (mark, it["kind"], it["path"]))
            print("      %s" % it["detail"])
        print("")

    if any(i["level"] == "P0" for i in all_issues):
        raise SystemExit(2)
    if any(i["level"] == "P1" for i in all_issues):
        raise SystemExit(1)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
