#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月度链接体检 Runner v1.0.0
========================================================
聚合两项检查：
  ① 断链体检    _运维/link_audit.py          （断链率门禁 0.5%）
  ② 留痕合规   05-调用/_check_call_traceability.py （合规率须 100%）

产出报告：04-巩固/知识健康度报告/月度链接体检-YYYY-MM.md
退出码：0 = 两项均健康    1 = 任一项越阈值（供自动化触发告警）

设计：纯本地计算 + 写报告，告警动作交给调用方（自动化 prompt
      经 qq-mail 技能发邮件），故本脚本不依赖任何外部连接器，
      即使邮件通道离线，报告也始终落盘可查。
"""
import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path

OPS = Path(__file__).resolve().parent
VAULT = Path("/Users/chenyouqiang/Documents/LawKB/知识飞轮系统")
CALL_CHECKER = VAULT / "05-调用" / "_check_call_traceability.py"
REPORT_DIR = VAULT / "04-巩固" / "知识健康度报告"
THRESH_LINK = 0.5      # 断链率门禁 %
THRESH_CALL = 100.0    # 留痕合规率门禁 %


def run(cmd):
    r = subprocess.run([sys.executable, str(cmd)], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def parse_link(out: str):
    m = re.search(r'断链率\s*([\d.]+)%', out)
    rate = float(m.group(1)) if m else None
    m = re.search(r'真断链:\s*(\d+)', out)
    broken = int(m.group(1)) if m else None
    m = re.search(r'有效分母:\s*(\d+)', out)
    denom = int(m.group(1)) if m else None
    m = re.search(r'alias 已索引:\s*(\d+)', out)
    alias_n = int(m.group(1)) if m else None
    return rate, broken, denom, alias_n


def parse_call(out: str):
    m = re.search(r'合规率\s*([\d.]+)%', out)
    rate = float(m.group(1)) if m else None
    m = re.search(r'不合规\s*(\d+)', out)
    bad = int(m.group(1)) if m else None
    m = re.search(r'总记录\s*(\d+)', out)
    total = int(m.group(1)) if m else None
    return rate, bad, total


def main():
    now = datetime.now()
    ym = now.strftime("%Y-%m")

    rc1, out1 = run(OPS / "link_audit.py")
    link_rate, link_broken, link_denom, alias_n = parse_link(out1)

    rc2, out2 = run(CALL_CHECKER)
    call_rate, call_bad, call_total = parse_call(out2)

    link_ok = (link_rate is not None) and (link_rate <= THRESH_LINK)
    call_ok = (call_rate is not None) and (call_rate >= THRESH_CALL)
    overall = link_ok and call_ok

    status = "✅ 健康" if overall else "🔴 异常"
    lines = []
    lines.append(f"# 月度链接体检报告 · {ym}\n")
    lines.append(f"> 生成时间：{now.strftime('%Y-%m-%d %H:%M:%S')}  |  总体状态：**{status}**\n")
    lines.append("## 一、指标汇总\n")
    lines.append("| 检查项 | 指标 | 实测 | 门禁 | 结论 |")
    lines.append("|---|---|---|---|---|")
    lines.append(f"| ① 断链体检 | 真实断链率 | {link_rate:.3f}% | ≤ {THRESH_LINK}% | {'✅' if link_ok else '🔴'} |")
    lines.append(f"| ① 断链体检 | 真断链数 | {link_broken} / {link_denom} | — | {'✅' if link_ok else '🔴'} |")
    lines.append(f"| ② 留痕合规 | 合规率 | {call_rate:.1f}% | = {THRESH_CALL:.0f}% | {'✅' if call_ok else '🔴'} |")
    lines.append(f"| ② 留痕合规 | 不合规记录 | {call_bad} / {call_total} | 0 | {'✅' if call_ok else '🔴'} |")
    lines.append(f"| 附加 | alias 已索引 | {alias_n} 个 | — | — |")
    lines.append("")
    lines.append("## 二、处置建议\n")
    if overall:
        lines.append("- 两项指标均在门禁内，无需人工介入。")
        lines.append("- 下月 28 日自动化将自动复跑；如越阈值会通过 QQ 邮箱告警。")
    else:
        lines.append("- 🔴 **存在越阈值项，需人工处置：**")
        if not link_ok:
            lines.append(f"  - 断链率 {link_rate:.3f}% 超过门禁 {THRESH_LINK}%，重点排查下列裸号/模板占位链接（详见 link_audit 输出）。")
        if not call_ok:
            lines.append(f"  - 留痕合规率 {call_rate:.1f}%，有 {call_bad} 条调用记录缺 `knowledge_called`，请补登真实命中（禁止伪造）。")
        lines.append("- 本异常应由每月 28 日自动化经 qq-mail 向 136443921@qq.com 发送告警。")
    lines.append("")
    lines.append("## 三、溯源命令\n")
    lines.append("```bash")
    lines.append(f"python3 {OPS / 'link_audit.py'}")
    lines.append(f"python3 {CALL_CHECKER} --quiet")
    lines.append("```")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = REPORT_DIR / f"月度链接体检-{ym}.md"
    report.write_text("\n".join(lines), encoding="utf-8")

    # 终端汇总（供自动化读取）
    print("=" * 56)
    print(f"  月度链接体检 · {ym}  →  {status}")
    print("=" * 56)
    print(f"  ① 断链体检 : 断链率 {link_rate:.3f}% (门禁≤{THRESH_LINK}%)  {'OK' if link_ok else 'FAIL'}")
    print(f"  ② 留痕合规 : 合规率 {call_rate:.1f}% (门禁={THRESH_CALL:.0f}%)  {'OK' if call_ok else 'FAIL'}")
    print(f"  报告已写入 : {report}")
    print("=" * 56)

    return 0 if overall else 1


if __name__ == '__main__':
    sys.exit(main())
