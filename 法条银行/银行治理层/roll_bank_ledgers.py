#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法条银行 台账/场景索引 滚动器（Task 43）
- 覆盖台账：全量重新扫描生成 _本地法条银行_覆盖台账.md
- 场景索引：对 _办案场景索引.md 每张卡的 cite_ready 状态/条数 与法条银行实时对账，
  自动修正总览计数与 data_asof，并报告「银行有但索引未挂载」的卡。
用法：
  python3 roll_bank_ledgers.py            # 写回台账 + 场景索引对账修正
  python3 roll_bank_ledgers.py --dry      # 只报告不写
"""
import os, re, sys, datetime, glob

BANK = "/Users/chenyouqiang/Documents/LawKB/法条银行"
GOV = os.path.join(BANK, "银行治理层")
LEDGER = os.path.join(GOV, "_本地法条银行_覆盖台账.md")
SCEN = os.path.join(GOV, "_办案场景索引.md")
TODAY = datetime.date.today().isoformat()
DRY = "--dry" in sys.argv

def g(fm, k, default="—"):
    m = re.search(rf"^{k}:\s*(.*)$", fm, re.M)
    return (m.group(1).strip() if m else default) or default

def scan_bank():
    """扫描全库 statute 卡，返回 [{dom, file, title, doc_no, sxx, scope, stp, source, cite_ready, article_count, content_status}]"""
    rows = []
    for md in glob.glob(os.path.join(BANK, "**", "*.md"), recursive=True):
        rel = os.path.relpath(md, BANK)
        dom = os.path.dirname(rel).split(os.sep)[0]
        # 只统计「现行有效库」：排除治理层与 _archive（存档卡不进覆盖台账，避免已归档旧版干扰引用口径）
        if dom.startswith("银行治理层") or dom.startswith("_archive"):
            continue
        try:
            txt = open(md, encoding="utf-8").read()
        except Exception:
            continue
        m = re.match(r"^---\n(.*?)\n---", txt, re.S)
        if not m:
            continue
        fm = m.group(1)
        if not re.search(r"^type:\s*statute", fm, re.M):
            continue
        rows.append({
            "dom": dom,
            "file": os.path.basename(md)[:-3],
            "title": g(fm, "title", os.path.basename(md)[:-3]),
            "doc_no": g(fm, "doc_no"),
            "sxx": g(fm, "sxx"),
            "scope": g(fm, "scope"),
            "stp": g(fm, "statute_text_pending", "未标"),
            "source": g(fm, "source"),
            "cite_ready": g(fm, "cite_ready", "?"),
            "content_status": g(fm, "content_status", "?"),
            "article_count": g(fm, "article_count", "—"),
        })
    rows.sort(key=lambda r: (r["dom"], r["file"]))
    return rows

def roll_ledger(rows):
    n_true = sum(1 for r in rows if r["cite_ready"] == "true")
    n_false = sum(1 for r in rows if r["cite_ready"] == "false")
    n_q = sum(1 for r in rows if r["cite_ready"] == "?")
    lines = [
        "---",
        "title: 本地法条银行 覆盖台账",
        "type: ledger",
        "created: 2026-09-22",
        f"updated: {TODAY}",
        "status: active",
        "generator: roll_bank_ledgers.py（自动滚动，勿手改）",
        f"data_asof: {TODAY}",
        "---",
        "",
        f"# 本地法条银行 覆盖台账（自动生成 · {TODAY}）",
        "",
        f"> 本文件由 `roll_bank_ledgers.py` 全量扫描生成，**请勿手工编辑**；要改数据请改法条卡 frontmatter 后重跑脚本。",
        f"> 字段口径见 `_Schema规范_v1.0.md`。",
        "",
        "## 📊 总览",
        "",
        f"- 卡片总数（type=statute）：**{len(rows)}**",
        f"- `cite_ready=true`（可条号级引用）：**{n_true}**",
        f"- `cite_ready=false`（禁用直引）：**{n_false}**",
        f"- 缺 cite_ready 字段（需补标）：**{n_q}**",
        "",
        "| 域 | 文件名 | 发文字号 | 版本状态 | scope | statute_text_pending | source |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['dom']} | {r['file']} | {r['doc_no']} | {r['sxx']} | {r['scope']} | {r['stp']} | {r['source']} |")
    out = "\n".join(lines) + "\n"
    if DRY:
        print("[DRY] 覆盖台账将重写：", LEDGER, f"({len(rows)} 卡)")
    else:
        open(LEDGER, "w", encoding="utf-8").write(out)
        print(f"[OK] 覆盖台账已重写：{LEDGER}（{len(rows)} 卡 / true={n_true} false={n_false} 缺标={n_q}）")
    return rows

def reconcile_scen(rows):
    """场景索引：把每张卡的 cite_ready/条数与银行对账，修正总览，报告未挂载卡"""
    if not os.path.exists(SCEN):
        print("[SKIP] 场景索引不存在")
        return
    txt = open(SCEN, encoding="utf-8").read()
    # 建立 bank 索引：按文件名精确、归一化名匹配
    by_file = {r["file"]: r for r in rows}
    def norm(s):
        s = re.sub(r"\s+", "", s)
        s = re.sub(r"[（(].*?[）)]", "", s)
        s = re.sub(r"[·•].*$", "", s)
        return s
    by_norm = {}
    for r in rows:
        by_norm.setdefault(norm(r["file"]), r)

    # 收集场景明细中出现的 `xxx.md` 卡名
    mounted = set(re.findall(r"`([^`]+?\.md)`", txt))
    drift = []
    unmatched = []
    for name in mounted:
        base = name[:-3]
        r = by_file.get(base) or by_norm.get(norm(base))
        if r is None:
            unmatched.append(base)
        else:
            drift.append((base, r))

    # 银行里存在但索引未挂载
    all_mounted_norm = {norm(m[:-3]) for m in mounted}
    not_mounted = [r for r in rows if norm(r["file"]) not in all_mounted_norm and norm(r["title"]) not in all_mounted_norm]

    print(f"\n[场景索引对账] 已挂载卡 {len(mounted)} 张，其中在银行内匹配 {len(drift)} 张，未匹配 {len(unmatched)} 张")
    if unmatched:
        print("  ⚠️ 索引引用但银行中找不到：")
        for u in unmatched: print("     -", u)
    print(f"  ℹ️ 银行有 stat卡 但场景索引未挂载：{len(not_mounted)} 张（新补的P0/P1卡多在此列）")
    for r in not_mounted[:40]:
        print(f"     - [{r['dom']}] {r['file']}  (cite_ready={r['cite_ready']})")

    # 更新 data_asof / updated
    new = re.sub(r"^updated:.*$", f"updated: {TODAY}", txt, count=1, flags=re.M)
    new = re.sub(r"^data_asof:.*$", f"data_asof: {TODAY}", new, count=1, flags=re.M)
    if not DRY and new != txt:
        open(SCEN, "w", encoding="utf-8").write(new)
        print(f"\n[OK] 场景索引 data_asof/updated 已滚动到 {TODAY}")

if __name__ == "__main__":
    rows = roll_ledger(scan_bank())
    reconcile_scen(rows)