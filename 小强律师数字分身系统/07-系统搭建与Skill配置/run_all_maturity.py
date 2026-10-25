#!/usr/bin/env python3
"""
席位成熟度周刷新 · 调度编排器（10 席合一）
==========================================
把原来 10 条独立的「训练成熟度周刷新」自动化，收敛为一条编排入口：
按序调用各席位的专属 maturity 脚本（脚本才是逻辑，本编排器只做「顺序调度 + 结果汇总」）。

设计要点：
- 每个脚本跑 --refresh（脚本自带写前备份到 /tmp）
- 任一脚本失败不中断整体，继续跑完，最后统一汇总
- 退出码：0=全部成功；1=有 1 个及以上失败（供日报/看门狗捕捉）
- QC 双模无脚本（纯 AI 判断），本编排器只做占位提示，由上层 prompt 单独处理
"""
import subprocess
import sys
import datetime

PY = "/Users/chenyouqiang/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
SCRIPTS_DIR = "/Users/chenyouqiang/.workbuddy/skills/_common/scripts"

# 席位 -> (脚本名, 刷新参数)
SEATS = [
    ("红队出庭律师", "red_team_maturity.py", "--refresh"),
    ("蓝队出庭律师", "blue_team_maturity.py", "--refresh"),
    ("蓝队非诉律师", "blue_nonlit_maturity.py", "--refresh"),
    ("蓝队律师助理", "assistant_maturity.py", "--refresh"),
    ("模拟法庭书记员", "clerk_maturity.py", "--refresh"),
    ("律所主任(治理席)", "mp_maturity.py", "--refresh"),
    ("合规双席", "compliance_dual_seat_maturity.py", "--refresh-doc"),
    ("可视化监控运维官", "monitor_maturity.py", "--refresh"),
    ("小强律师元心智", "xiaoqiang_meta_maturity.py", "--refresh"),
]

def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print("=" * 60)
    print(f"席位成熟度周刷新 · 调度编排器  {now}")
    print(f"共 {len(SEATS)} 席（QC双模为纯AI判断，不在此编排）")
    print("=" * 60)

    results = []
    for seat, script, flag in SEATS:
        cmd = [PY, f"{SCRIPTS_DIR}/{script}", flag]
        print(f"\n▶ [{seat}] 运行 {script} {flag} ...")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            ok = (r.returncode == 0)
            results.append((seat, ok, r.returncode))
            # 输出脚本的最后几行（便于简报）
            tail = (r.stdout or "").strip().split("\n")
            for line in tail[-6:]:
                print("    " + line)
            if not ok:
                print(f"    ⚠️ 退出码 {r.returncode}")
                for line in (r.stderr or "").strip().split("\n")[-4:]:
                    print("    ERR " + line)
        except subprocess.TimeoutExpired:
            results.append((seat, False, "timeout"))
            print(f"    ⚠️ 超时(>300s)")
        except Exception as e:
            results.append((seat, False, str(e)))
            print(f"    ⚠️ 异常: {e}")

    print("\n" + "=" * 60)
    print("汇总：")
    fail_count = 0
    for seat, ok, code in results:
        mark = "✅" if ok else "❌"
        if not ok:
            fail_count += 1
        print(f"  {mark} {seat}  (code={code})")
    print("=" * 60)
    print(f"成功 {len(results) - fail_count} / {len(results)}，失败 {fail_count}")
    sys.exit(1 if fail_count > 0 else 0)

if __name__ == "__main__":
    main()
