#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all_maturity.py —— 席位成熟度周刷新统一编排器 v1.0

把 9 个席位成熟度脚本收敛为一条统一编排：按序调用各席 --refresh，
捕获 stdout / stderr / 退出码，逐席打印，末尾出汇总表。

席位脚本实体位于 ~/.workbuddy/skills/_common/scripts/（席位脚本自带写前 cp 备份）。
本编排器只做「按序驱动 + 汇总」，不改任何席位脚本、不碰各备忘录 MATURITY/TRAINLOG 以外的内容。

用法：
  python3 run_all_maturity.py            # 逐席刷新 + 汇总
  python3 run_all_maturity.py --dry-run  # 只打印席位映射，不实际调用

退出码：
  0 = 全部席位成功
  1 = 存在失败席位（末尾附「失败席位清单」）
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime

# 席位脚本目录（席位脚本彼此 import 依赖同目录，须在脚本目录下运行）
SCRIPTS_DIR = os.path.expanduser("~/.workbuddy/skills/_common/scripts")

# 席位清单：按任务指定顺序。合规双席用 --refresh-doc（其 CLI 无 --refresh），其余 8 席用 --refresh。
SEATS = [
    ("红队出庭",   "red_team_maturity.py",          ["--refresh"]),
    ("蓝队出庭",   "blue_team_maturity.py",         ["--refresh"]),
    ("蓝队非诉",   "blue_nonlit_maturity.py",       ["--refresh"]),
    ("蓝队助理",   "assistant_maturity.py",         ["--refresh"]),
    ("书记员",     "clerk_maturity.py",             ["--refresh"]),
    ("律所主任",   "mp_maturity.py",                ["--refresh"]),
    ("合规双席",   "compliance_dual_seat_maturity.py", ["--refresh-doc"]),
    ("可视化运维官", "monitor_maturity.py",          ["--refresh"]),
    ("元心智",     "xiaoqiang_meta_maturity.py",    ["--refresh"]),
]

PY = "/Users/chenyouqiang/.workbuddy/binaries/python/versions/3.13.12/bin/python3"


def run_seat(label, script, args):
    """运行单个席位脚本，返回 (退出码, stdout, stderr)。"""
    script_path = os.path.join(SCRIPTS_DIR, script)
    if not os.path.isfile(script_path):
        return 2, "", f"[编排器] 席位脚本不存在：{script_path}"

    # 在脚本目录下运行，保证 seat_event_bus 等同目录 import 可用
    try:
        proc = subprocess.run(
            [PY, script_path] + args,
            cwd=SCRIPTS_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 3, "", "[编排器] 席位脚本运行超时（>300s）"
    except Exception as e:  # noqa: BLE001
        return 4, "", f"[编排器] 调用异常：{e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="只打印席位映射，不实际调用")
    a = ap.parse_args()

    print("=" * 70)
    print(f"席位成熟度周刷新 · 统一编排器 · {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    if a.dry_run:
        print("\n席位映射（dry-run，未实际调用）：\n")
        for i, (label, script, args) in enumerate(SEATS, 1):
            print(f"  {i}. {label:<8} -> {script} {' '.join(args)}")
        print("\n如需真实刷新，去掉 --dry-run。")
        return

    results = []  # (label, returncode, stdout, stderr)
    for label, script, args in SEATS:
        print("\n" + "#" * 70)
        print(f"# 席位：{label}（{script} {' '.join(args)}）")
        print("#" * 70)
        rc, out, err = run_seat(label, script, args)
        results.append((label, rc, out, err))
        if out.strip():
            print(out.strip())
        if err.strip():
            print(f"[stderr]\n{err.strip()}")
        if rc == 0:
            print(f"\n✅ {label}：刷新完成（退出码 0）")
        else:
            print(f"\n❌ {label}：失败（退出码 {rc}）")

    # ---- 汇总表 ----
    print("\n\n" + "=" * 70)
    print("席位成熟度周刷新 · 汇总表")
    print("=" * 70)
    print(f"{'席位':<10} {'状态':<6} {'退出码':<6}")
    print("-" * 70)
    failed = []
    for label, rc, _, _ in results:
        status = "✅" if rc == 0 else "❌"
        print(f"{label:<10} {status:<6} {rc}")
        if rc != 0:
            failed.append((label, rc))
    print("-" * 70)
    ok = len(SEATS) - len(failed)
    print(f"合计：{ok}/{len(SEATS)} 席成功，{len(failed)} 席失败")

    if failed:
        print("\n" + "⚠️ 失败席位清单".center(70, "="))
        for label, rc in failed:
            # 取该席 stderr 末尾几行作失败原因
            for l, r, o, e in results:
                if l == label:
                    reason = (e or o).strip().splitlines()
                    reason = "；".join(reason[-4:]) if reason else "无输出"
                    print(f"\n· 席位：{label}（退出码 {rc}）")
                    print(f"  失败原因：{reason}")
                    break
        print("\n（编排器退出码 1：存在失败席位，未为汇总变绿而跳过报告）")
        sys.exit(1)
    else:
        print("\n✅ 全部 9 席刷新完成。")
        sys.exit(0)


if __name__ == "__main__":
    main()
