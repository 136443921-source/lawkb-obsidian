#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LawKB 知识飞轮系统 · 法条与法理一致性巡检（一键入口）

四步流水线：
  Step1 scan_citations.py           全库扫描法条引用 → citations.json
  Step2 analyze_conflicts.py        A条号越界 / B同条异文 / C引文≠权威 → conflicts_ABC.json
  Step3 verify_and_suggest.py       反向定位，给出"疑似应改为第N条" → verified_findings.json
  Step4 detect_opposite_same_issue.py  同议题对立主张（法理逻辑冲突精筛） → issue_opposites.json

⚠️ 实现说明（2026-09-04）：
  4 个子脚本内部写死了中间产物目录 /tmp/lawkb_audit，本 runner 与之保持一致。
  `--archive DIR` 用于在巡检结束后把产物拷贝留档（月度归档用），不是中间目录。
"""

# ⚠️ 铁律（2026-09-04 血泪）：本流水线产出的是「候选疑点，不是结论」。
#   2026-09-04 首轮审计报出 12 项 P0，人工逐条核验后 7 项为误报
#   （历史法条的正确引用、明写"原《物权法》"的旧法引用、正文自述条号变迁的说明性文字）。
#   任何一条写入库文件的条号修改，必须先查权威源（provision_index / 元典 rh_ft_detail）再改，
#   严禁直接采信本脚本输出。详见运维/LawKB知识飞轮系统-法条与法理一致性审计报告-2026-09-04.md 第七节。

import os
import sys
import json
import shutil
import subprocess
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
# 与 4 个子脚本内部写死的目录保持一致（改这里不会生效，须同步改子脚本常量）
WORK = "/tmp/lawkb_audit"
DEFAULT_ARCHIVE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/运维/一致性巡检归档"

STEPS = [
    ("Step1 全库引用扫描", "scan_citations.py", "citations.json"),
    ("Step2 A/B/C 冲突检测", "analyze_conflicts.py", "conflicts_ABC.json"),
    ("Step3 反向定位·正确条号建议", "verify_and_suggest.py", "verified_findings.json"),
    ("Step4 同议题对立主张精筛", "detect_opposite_same_issue.py", "issue_opposites.json"),
]


def main():
    args = sys.argv[1:]
    quick = "--quick" in args
    archive = DEFAULT_ARCHIVE
    if "--archive" in args:
        archive = args[args.index("--archive") + 1]
    os.makedirs(WORK, exist_ok=True)

    print("=" * 68)
    print(" LawKB 法条与法理一致性巡检  %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
    print(" 中间产物：%s%s" % (WORK, "   [quick：跳过 Step4]" if quick else ""))
    print("=" * 68)

    results = {}
    for name, script, out in STEPS:
        if quick and script.startswith("detect_opposite"):
            print("\n⏭  跳过 %s（quick 模式）" % name)
            continue
        print("\n▶ %s …" % name)
        p = subprocess.run([PY, os.path.join(HERE, script)],
                           capture_output=True, text=True, cwd=HERE)
        tail = (p.stdout or "").strip().split("\n")[-8:]
        for line in tail:
            print("   " + line)
        if p.returncode != 0:
            print("   ❌ 失败（exit %s）\n%s" % (p.returncode, (p.stderr or "")[:500]))
            results[script] = {"ok": False}
            continue
        fp = os.path.join(WORK, out)
        n = None
        if os.path.exists(fp):
            try:
                d = json.load(open(fp, encoding="utf-8"))
                n = len(d) if isinstance(d, (list, dict)) else None
            except Exception:
                n = None
        results[script] = {"ok": True, "out": fp, "count": n}
        print("   ✅ 完成 → %s%s" % (out, "（%s 条记录）" % n if n is not None else ""))

    print("\n" + "=" * 68)
    print(" 巡检摘要")
    print("=" * 68)
    failed = [k for k, v in results.items() if not v.get("ok")]
    for k, v in results.items():
        if v.get("ok"):
            print("  ✅ %-38s %s" % (k, ("%s 条" % v["count"]) if v.get("count") is not None else ""))
    for k in failed:
        print("  ❌ %-38s 执行失败" % k)

    vf = os.path.join(WORK, "verified_findings.json")
    pending = 0
    if os.path.exists(vf):
        try:
            d = json.load(open(vf, encoding="utf-8"))
            pending = len(d) if isinstance(d, list) else len(d.get("findings", []))
        except Exception:
            pass
    print("\n  待人工核验疑点：%s 项" % pending)
    print("  ⚠️ 上述均为**候选疑点**，写入库文件前必须逐条查权威源复核（首轮误报率约 58%）")

    if failed:
        print("\n  🔴 存在执行失败的环节，请检查上方日志")
        return 1

    # 归档：把本轮产物拷贝到 运维/一致性巡检归档/YYYY-MM/
    if archive:
        stamp = datetime.datetime.now().strftime("%Y-%m")
        adir = os.path.join(archive, stamp)
        os.makedirs(adir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        kept = []
        for name, script, out in STEPS:
            if quick and script.startswith("detect_opposite"):
                continue
            src = os.path.join(WORK, out)
            if os.path.exists(src):
                dst = os.path.join(adir, "%s_%s" % (ts, out))
                shutil.copy2(src, dst)
                kept.append(out)
        if kept:
            summ = os.path.join(adir, "%s_巡检摘要.txt" % ts)
            with open(summ, "w", encoding="utf-8") as f:
                f.write("LawKB 一致性巡检 %s\n" % ts)
                f.write("待人工核验疑点：%s 项\n" % pending)
                f.write("产物：%s\n" % "、".join(kept))
                f.write("⚠️ 候选疑点须逐条查权威源复核后写入，首轮误报率约58%%\n")
            print("  📁 已归档 %d 份产物 → %s" % (len(kept), adir))

    print("\n  ✅ 巡检流程全部完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
