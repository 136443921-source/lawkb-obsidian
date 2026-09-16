#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
count_rules.py —— 小强律师数字分身系统·知识飞轮卡库规模季度复核脚本
================================================================================
目的：
    把「卡库规模数字」从「人工记忆填数」彻底改为「脚本自动产生」，消除
    P0-2 类系统性隐患（数字声明与实测脱节 3–5 倍）。

统计维度（与主控协调器 SKILL / MEMORY.md 基线 / 系统评估报告对齐）：
    - 裁判规则库：子库数、R-* 规则卡总数、negative_note 覆盖数
    - 案由路由卡 R-AY-* 数量
    - 经验卡（02-提炼/经验卡片）总数
    - 审判要件卡物理数（注意：审判长 persona 声明的 215 为「内联+矩阵」口径，
      物理文件 70 为「实体卡」口径，二者不冲突，脚本分别记录）
    - 反面案例库行数（已迁飞轮 canonical：02-提炼/案例摘要/反面案例库/；skill 镜像保留为运行时工作镜像）
    - 审判长 JUDGE_CARDS 声明张数（从 judge_persona_v1.md 解析）
    - 07-卡族总索引指针数
    - 知识飞轮六层 .md 数

输出：
    - card_scale_baseline.json（结构化，供脚本/报告引用，幂等覆盖）
    - 人类可读摘要（stdout）
    - 写前对 baseline 做 .bak 备份

用法：
    python3 count_rules.py            # 统计 + 写 baseline + 打印
    python3 count_rules.py --quiet    # 仅写 baseline，不打印

依赖：仅标准库（os / json / re / datetime / pathlib）。
作者：小强律师AI助手（2026-09-15）
"""

import os
import re
import json
import shutil
import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# 路径常量（绝对路径，硬编码，避免 cd 错目录导致静默失败）
# ---------------------------------------------------------------------------
LAWKB = "/Users/chenyouqiang/Documents/LawKB"
FLY = os.path.join(LAWKB, "知识飞轮系统")
RULE_LIB = os.path.join(FLY, "06-沉淀", "裁判规则库")
EXP_CARDS = os.path.join(FLY, "02-提炼", "经验卡片")
HUB = os.path.join(LAWKB, "_AI-Memory-Hub")
IDX07 = os.path.join(HUB, "07-卡族总索引", "_索引.md")
BLUE_LIB = "/Users/chenyouqiang/.workbuddy/skills/蓝队出庭律师/反面案例库.md"
JUDGE_PERSONA = "/Users/chenyouqiang/.workbuddy/skills/ai-mock-court-judge/judge_persona_v1.md"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))  # 00-系统总览与运维中心
BASELINE = os.path.join(OUT_DIR, "card_scale_baseline.json")

SIX_LAYERS = ["01-采集", "02-提炼", "03-连接", "04-巩固", "05-调用", "06-沉淀"]


# ---------------------------------------------------------------------------
# 统计工具函数
# ---------------------------------------------------------------------------
def count_md_files(root: str) -> int:
    """统计目录下所有 .md 文件数（递归）。排除 .bak / .bak_ 备份脏数据。"""
    if not os.path.isdir(root):
        return 0
    n = 0
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(".md") and not fn.endswith(".bak") and ".bak_" not in fn:
                n += 1
    return n


def count_subdirs(root: str) -> int:
    """统计直接子目录数"""
    if not os.path.isdir(root):
        return 0
    return sum(1 for e in os.listdir(root)
               if os.path.isdir(os.path.join(root, e)))


def count_rule_cards(root: str) -> int:
    """统计 R-*.md 规则卡数（递归）"""
    if not os.path.isdir(root):
        return 0
    n = 0
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.startswith("R-") and fn.endswith(".md"):
                n += 1
    return n


def count_negative_note(root: str) -> int:
    """统计含 negative_note 字段的 .md 文件数（递归）"""
    if not os.path.isdir(root):
        return 0
    n = 0
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    if "negative_note" in fh.read():
                        n += 1
            except OSError:
                continue
    return n


def count_by_glob(root: str, pattern: str) -> int:
    """统计文件名匹配 pattern（不区分大小写）的 .md 数（递归）"""
    import fnmatch
    pat = pattern.lower()
    n = 0
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(".md") and fnmatch.fnmatch(fn.lower(), pat):
                n += 1
    return n


def count_ay_routing(root: str) -> int:
    """统计 R-AY-*.md 案由路由卡（全盘）"""
    return count_by_glob(root, "R-AY-*.md")


def count_trial_elements_physical(root: str) -> int:
    """审判要件卡物理文件数（路径或文件名含『审判要件』且非『总索引』，
    宽口径，含调用记录/登记卡；与审判长 persona 215 矩阵口径对照）"""
    n = 0
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if (not fn.endswith(".md")) or fn.endswith(".bak") or ".bak_" in fn:
                continue
            if "总索引" in fn:
                continue
            if "审判要件" in dirpath or "审判要件" in fn:
                n += 1
    return n


def parse_judge_cards_declared(path: str) -> int:
    """从审判长 persona 解析 JUDGE_CARDS 声明张数（如『215 张审判要件卡』）"""
    if not os.path.isfile(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
    except OSError:
        return 0
    m = re.search(r"(\d+)\s*张审判要件卡", text)
    return int(m.group(1)) if m else 0


def count_index_pointers(path: str) -> int:
    """统计 07 索引里的知识飞轮 wikilink 指针数"""
    if not os.path.isfile(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
    except OSError:
        return 0
    return text.count("[[知识飞轮系统")


def count_file_lines(path: str) -> int:
    """统计文件行数"""
    if not os.path.isfile(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


# ---------------------------------------------------------------------------
# 漂移比对（锁死数字：季度自动化识别异常漂移 / 路径断裂 / 误删）
# ---------------------------------------------------------------------------
DRIFT_METRICS = [
    ("rule_library.rule_cards_R", "裁判规则库R卡"),
    ("rule_library.sub_libs", "子库数"),
    ("rule_library.negative_note_coverage", "negative_note覆盖"),
    ("ay_routing_cards", "案由路由卡R-AY"),
    ("experience_cards", "经验卡"),
    ("trial_elements.physical_cards", "审判要件卡物理"),
    ("trial_elements.judge_persona_declared", "审判长声明张数"),
    ("counter_case_lib.lines", "反面案例库行数"),
    ("cardfamily_index_pointers", "卡族索引指针"),
    ("six_layers_total", "六层.md总数"),
]
REVIEW_PCT = 20.0  # 核心指标变动超过该比例触发 REVIEW


def _get(d, path):
    cur = d
    for k in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
        if cur is None:
            return None
    return cur


def compute_drift(new_d: dict, old_d: dict) -> dict:
    items = []
    overall = "LOCKED"
    for path, label in DRIFT_METRICS:
        nv = _get(new_d, path)
        if nv is None:
            continue
        ov = _get(old_d, path) if isinstance(old_d, dict) else None
        if ov is None:
            status = "NEW_BASELINE"
        elif ov > 0 and nv == 0:
            status = "BREAKAGE"
            overall = "BREAKAGE"
        else:
            pct = (abs(nv - ov) / ov * 100) if ov else 0.0
            if pct > REVIEW_PCT:
                status = "REVIEW"
                if overall == "LOCKED":
                    overall = "REVIEW"
            else:
                status = "OK"
        items.append({
            "metric": label, "path": path,
            "prev": ov, "curr": nv,
            "delta": (nv - ov) if ov is not None else None,
            "pct": round(pct, 1) if (ov not in (None, 0)) else None,
            "status": status,
        })
    return {"generated_at": new_d.get("generated_at"),
            "drift_status": overall, "items": items}


def _print_drift(d: dict):
    print("\n--- 季度漂移比对（vs 上季 baseline）---")
    print(f"  drift_status: {d['drift_status']}")
    for it in d["items"]:
        if it["status"] in ("OK", "NEW_BASELINE"):
            continue
        print(f"  ⚠️ {it['metric']}: {it['prev']} → {it['curr']} "
              f"(Δ{it['delta']}, {it['pct']}%) [{it['status']}]")
    if d["drift_status"] == "LOCKED":
        print("  ✅ 本季规模数字稳定，无异常漂移")


# ---------------------------------------------------------------------------
# 主统计
# ---------------------------------------------------------------------------
def main(quiet: bool = False) -> dict:
    six_layer = {}
    for layer in SIX_LAYERS:
        six_layer[layer] = count_md_files(os.path.join(FLY, layer))

    data = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "count_rules.py (自动统计，非人工记忆)",
        "rule_library": {
            "sub_libs": count_subdirs(RULE_LIB),
            "rule_cards_R": count_rule_cards(RULE_LIB),
            "negative_note_coverage": count_negative_note(RULE_LIB),
        },
        "ay_routing_cards": count_ay_routing(FLY),
        "experience_cards": count_md_files(EXP_CARDS),
        "trial_elements": {
            "physical_cards": count_trial_elements_physical(FLY),
            "judge_persona_declared": parse_judge_cards_declared(JUDGE_PERSONA),
            "note": "physical=实体卡文件数；declared=审判长persona声明的『内联+矩阵』口径(215含3张裁量尺度卡)，二者不冲突",
        },
        "counter_case_lib": {
            "lines": count_file_lines(BLUE_LIB),
            "location": "已迁飞轮canonical(02-提炼/案例摘要/反面案例库/)，skill镜像保留为运行时工作镜像",
        },
        "cardfamily_index_pointers": count_index_pointers(IDX07),
        "six_layers_md": six_layer,
        "six_layers_total": sum(six_layer.values()),
    }

    # 写 baseline（写前备份）
    if os.path.isfile(BASELINE):
        bak = BASELINE + ".bak"
        shutil.copy2(BASELINE, bak)
    with open(BASELINE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)

    # 漂移比对（锁死数字：季度自动化可识别异常漂移 / 路径断裂）
    drift_path = os.path.join(OUT_DIR, "card_scale_drift_report.json")
    old_d = None
    if os.path.isfile(BASELINE + ".bak"):
        try:
            with open(BASELINE + ".bak", "r", encoding="utf-8") as _fb:
                old_d = json.load(_fb)
        except Exception:
            old_d = None
    drift = compute_drift(data, old_d)
    with open(drift_path, "w", encoding="utf-8") as fh:
        json.dump(drift, fh, ensure_ascii=False, indent=2)

    if not quiet:
        _print_human(data)
        print(f"\n✅ baseline 已写入: {BASELINE}")
    return data


def _print_human(d: dict):
    print("=" * 64)
    print("  知识飞轮卡库规模 · 季度复核（自动统计）")
    print("=" * 64)
    rl = d["rule_library"]
    print(f"  裁判规则库      子库 {rl['sub_libs']:>4} | R-*卡 {rl['rule_cards_R']:>5} | negative_note覆盖 {rl['negative_note_coverage']:>4}")
    print(f"  案由路由卡 R-AY       {d['ay_routing_cards']:>5}")
    print(f"  经验卡               {d['experience_cards']:>5}")
    te = d["trial_elements"]
    print(f"  审判要件卡  物理 {te['physical_cards']:>4} | 审判长声明 {te['judge_persona_declared']:>4} (口径见note)")
    print(f"  反面案例库行数       {d['counter_case_lib']['lines']:>5}  ({d['counter_case_lib']['location']})")
    print(f"  07卡族总索引指针     {d['cardfamily_index_pointers']:>5}")
    print(f"  六层 .md 总数        {d['six_layers_total']:>5}")
    for k, v in d["six_layers_md"].items():
        print(f"    └ {k}: {v}")
    print("=" * 64)


if __name__ == "__main__":
    import sys
    quiet = "--quiet" in sys.argv
    main(quiet=quiet)
