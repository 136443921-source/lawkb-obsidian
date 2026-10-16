#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fatiao_version_watch.py — 法条银行换版临期监控
============================================
扫描全库 statute 卡，找出带版本切换元数据（switch_date / version_warn /
successor_card / article_mapping）或「待生效新版」（_待生效新版 目录、
effective_date 在未来）的卡，输出换版临期清单。

设计目标（2026-10-16 收官复盘决议）：
  商标法 2027-01-01 换版已备好新版全文 + 条号映射 + switch_action 清单，
  但「到那天没人提醒就白备」。本脚本即为提醒机制——可手动跑，亦可接入
  每日 / 每周自动化，命中临期即告警。

输出：
  控制台：按临期天数升序的告警清单（≤90 天标 🔴，≤180 天标 🟠）
  可选 --report <path.md>：写一份 markdown 临期清单，便于归档 / 推送

用法：
  python3 fatiao_version_watch.py [--bank <法条银行根>] [--report <out.md>]
                                 [--horizon 180] [--today 2026-10-16]
"""
import os
import re
import sys
import argparse
from datetime import date, datetime

# 法条银行根目录（可被 --bank 覆盖）
DEFAULT_BANK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"_archive", "银行治理层"}  # 已归档不扫；治理层自身不扫
PENDING_DIR = "_待生效新版"            # 待生效新版目录名


def _parse_date(v):
    """从字符串中解析 YYYY-MM-DD；失败返回 None"""
    if not v:
        return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", v)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _load_cards(bank):
    """扫描 statute 卡，返回 [{rel, file, title, doc_no, switch_date,
    version_warn, successor_card, article_mapping, effective_date, pending}]"""
    out = []
    for dp, dn, fn in os.walk(bank):
        # 不递归进入 skip 目录（但 _待生效新版 要扫）
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for name in fn:
            if not name.endswith(".md"):
                continue
            p = os.path.join(dp, name)
            try:
                t = open(p, encoding="utf-8").read()
            except Exception:
                continue
            if not t.startswith("---"):
                continue
            ls = t.split("\n")
            close = None
            for i in range(1, len(ls)):
                if ls[i].strip() == "---":
                    close = i
                    break
            if close is None:
                continue
            fm = "\n".join(ls[1:close])
            rel = os.path.relpath(p, bank)
            if not re.search(r"^type:\s*statute\s*$", fm, re.M):
                # 「_待生效新版」目录专为暂存待生效 statute，无 type 标记也纳入
                if PENDING_DIR not in rel.split(os.sep):
                    continue
            g = lambda k: (re.search(rf"^{k}:\s*(.+)$", fm, re.M).group(1).strip()
                          if re.search(rf"^{k}:\s*(.+)$", fm, re.M) else "")
            rel = os.path.relpath(p, bank)
            is_pending = PENDING_DIR in rel.split(os.sep)
            out.append({
                "rel": rel,
                "file": name[:-3],
                "title": g("title"),
                "doc_no": g("doc_no"),
                "switch_date": g("switch_date"),
                "version_warn": g("version_warn"),
                "successor_card": g("successor_card"),
                "article_mapping": g("article_mapping"),
                "switch_action": g("switch_action"),
                "effective_date": g("effective_date"),
                "pending": is_pending,
            })
    return out


def _classify(c, today):
    """返回 (kind, event_date, days_left) —— kind ∈ {switch, pending_effective}"""
    # 1) 已设 switch_date 的现行卡：临期换版
    sd = _parse_date(c["switch_date"])
    if sd:
        return "switch", sd, (sd - today).days
    # 2) 待生效新版：effective_date 在未来
    ed = _parse_date(c["effective_date"])
    if ed and ed > today:
        return "pending_effective", ed, (ed - today).days
    return None, None, None


def main():
    ap = argparse.ArgumentParser(description="法条银行换版临期监控")
    ap.add_argument("--bank", default=DEFAULT_BANK, help="法条银行根目录")
    ap.add_argument("--report", help="输出 markdown 临期清单路径")
    ap.add_argument("--horizon", type=int, default=180, help="临期窗口天数（默认180）")
    ap.add_argument("--today", help="基准日 YYYY-MM-DD（默认今天）")
    args = ap.parse_args()

    today = _parse_date(args.today) or date.today()

    cards = _load_cards(args.bank)
    rows = []
    for c in cards:
        kind, ev, days = _classify(c, today)
        if kind is None:
            continue
        # 只报告临期窗口内，或虽无明确日期但带 version_warn 的卡
        if days is not None and days > args.horizon:
            continue
        rows.append((days, kind, c, ev))

    rows.sort(key=lambda r: r[0] if r[0] is not None else 9999)

    # 控制台输出
    print(f"═══ 法条银行换版临期监控（基准日 {today.isoformat()} · 窗口 {args.horizon} 天）═══")
    if not rows:
        print("  ✅ 无临期换版（窗口内无 switch_date / 待生效新版）")
        if args.report:
            open(args.report, "w", encoding="utf-8").write(
                f"# 法条银行换版临期清单\n\n- 基准日：{today.isoformat()}\n- 窗口：{args.horizon} 天\n- 结果：**无临期换版**\n")
        return 0

    n_red = sum(1 for r in rows if r[0] is not None and r[0] <= 90)
    n_orange = sum(1 for r in rows if r[0] is not None and 90 < r[0] <= 180)
    print(f"  命中 {len(rows)} 项（🔴≤90天 {n_red} · 🟠≤180天 {n_orange}）\n")

    md = [f"# 法条银行换版临期清单\n", f"- 基准日：{today.isoformat()}",
          f"- 临期窗口：{args.horizon} 天",
          f"- 命中：{len(rows)} 项（🔴≤90天 {n_red} · 🟠≤180天 {n_orange}）\n",
          "| 临期天数 | 类型 | 法名 | 文号 | 事件日 | 后继卡 / 说明 |",
          "|---|---|---|---|---|---|"]
    for days, kind, c, ev in rows:
        dlabel = f"{days}天" if days is not None else "无日期"
        if kind == "switch":
            klabel = "🔴 换版" if (days is not None and days <= 90) else "🟠 换版"
            note = c["successor_card"] or (c["version_warn"][:30] if c["version_warn"] else "—")
        else:
            klabel = "🟢 待生效"
            note = "新版待生效（effective_date）"
        md.append(f"| {dlabel} | {klabel} | {c['title'] or c['file']} | "
                  f"{c['doc_no'] or '—'} | {ev.isoformat() if ev else '—'} | {note} |")
        # 控制台逐条
        icon = "🔴" if (days is not None and days <= 90) else ("🟠" if days is not None else "⚪")
        print(f"  {icon} {dlabel:>6} [{klabel}] {c['title'] or c['file']}"
              f"  → {ev.isoformat() if ev else '—'}")
        if c["article_mapping"]:
            print(f"         条号映射已备：{c['article_mapping'][:60]}…")
        if c["switch_action"]:
            print(f"         换版动作：{c['switch_action'][:60]}…")

    if args.report:
        open(args.report, "w", encoding="utf-8").write("\n".join(md) + "\n")
        print(f"\n✅ 清单已写：{args.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
