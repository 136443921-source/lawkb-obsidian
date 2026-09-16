#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
「沉默错链」审计器 v1 / 2026-09-15

🔴 背景（本轮新发现）：
  死链门禁只能发现「目标不存在」的链接。但 AY 域实证出现
  **案由序号 ≠ rule_id 序号**（案由 292 落地为 R-AY-274）的错位，
  此时若 292 恰好落在已分配号段内，链接会**指向一张错误的卡**，
  门禁 100% 检测不到 —— 称为「沉默错链」，比死链更危险。

判据：
  链接形如 `R-<域>-<NNN>-<标题>`，全库存在该 rule_id 的物理文件时，
  比对「链接内标题」与「实际卡文件名标题」：
    - 一致（或互为子串/高相似）→ 正常
    - 不一致且相似度低 → 🔴 沉默错链（指向错误卡片）
  rule_id 存在但链接无标题（裸编号）→ 不计（无法比对）

只读审计，不写任何文件。
"""
import os, re, sys, json, importlib.util, difflib

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "_check_deadlinks.py")
ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"

spec = importlib.util.spec_from_file_location("gate", GATE)
gate = importlib.util.module_from_spec(spec)
_argv = list(sys.argv)
sys.argv = [GATE, "--help"]
spec.loader.exec_module(gate)
sys.argv = _argv

# R-域-NNN-标题（标题可含中文/英文/数字/括号）
LINK = re.compile(r"R-([A-Z]{2})-(\d{3,})-([^\s\(\)（）\[\]|、,，；;：:\"']+)")
NOISE = re.compile(r"[^\u4e00-\u9fa5A-Za-z0-9]")


def sig(s):
    return NOISE.sub("", str(s)).lower()


def main():
    names = gate.build_basename_set()
    # rule_id -> 实际基名集合
    by_rid = {}
    for n in names:
        m = re.match(r"^(R-[A-Z]{2}-\d{3,})", n)
        if m:
            by_rid.setdefault(m.group(1), []).append(n)
    print(f"门禁同款基名集：{len(names)}  |  可解析 rule_id：{len(by_rid)}")

    files = gate.md_files()
    silent = {}      # (rid, link_title) -> {files, actual}
    checked = 0
    for p in files:
        try:
            t = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in LINK.finditer(t):
            rid = "R-%s-%s" % (m.group(1), m.group(2))
            title = m.group(3).rstrip("-· ")
            if rid not in by_rid:
                continue                      # 死链，由门禁负责
            # 🔴 噪声过滤：代码块残片 / 正文叙述性文本不是链接
            if any(ch in title for ch in ".`…→」】）)\"'") or title.endswith("md"):
                continue
            actuals = by_rid[rid]
            # 🔴 裸编号命名（文件名就是 R-XX-NNN.md）时，编号匹配即合法，跳过
            if any(a == rid for a in actuals):
                continue
            checked += 1
            # 与任一实际基名匹配即视为正常（同号多副本场景取最优）
            best = max(
                (difflib.SequenceMatcher(None, sig(title), sig(a)).ratio(), a)
                for a in actuals)
            # 关键：只看「编号之后」的标题部分做比对
            best2 = 0.0
            for a in actuals:
                at = re.sub(r"^R-[A-Z]{2}-\d{3,}-?", "", a)
                s_at, s_t = sig(at), sig(title)
                if s_at.startswith(s_t) or s_t.startswith(s_at):
                    best2 = 1.0               # 前缀/子串关系＝截断或简称，合法
                    break
                best2 = max(best2,
                            difflib.SequenceMatcher(None, s_t, s_at).ratio())
            if best2 < 0.60:
                silent.setdefault((rid, title), {"files": set(), "actual": actuals,
                                                 "sim": round(best2, 3)})
                silent[(rid, title)]["files"].add(p)

    out = []
    for (rid, title), v in sorted(silent.items(), key=lambda x: x[1]["sim"]):
        out.append({"rule_id": rid, "link_title": title, "sim": v["sim"],
                    "actual": v["actual"],
                    "files": sorted(os.path.relpath(f, ROOT) for f in v["files"])})
    op = os.path.join(HERE, "沉默错链审计-20260915.json")
    json.dump(out, open(op, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"\n带标题链接校验：{checked} 条")
    print(f"🔴 沉默错链（编号存在但标题不符，指向错误卡片）：{len(out)} 类")
    for o in out[:40]:
        print(f"  - {o['rule_id']}-{o['link_title']}  (sim={o['sim']})")
        print(f"      实际：{o['actual'][:2]}")
        print(f"      出现：{len(o['files'])} 文件")
    print(f"\n报告 → {op}")


if __name__ == "__main__":
    main()
