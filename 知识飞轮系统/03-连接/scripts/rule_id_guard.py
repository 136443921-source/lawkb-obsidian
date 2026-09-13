#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rule_id_guard.py —— LawKB 裁判规则卡 **编号守卫（建卡后必跑）**

> 配套 next_rule_id.py。取号器管「不撞」，守卫管「撞了能立刻发现」。
> 设计原则：**门禁红着等于没门禁**（2026-09-10 教训），所以本脚本零依赖、快、可挂 CI。

## 检查项

| 编号 | 检查 | 级别 |
|---|---|---|
| G1 | 同域同号冲突（frontmatter `rule_id` 重复） | 🔴 ERROR |
| G2 | 文件名与 `rule_id` 不一致（仅提示，规范允许别名） | 🟡 WARN |
| G3 | 域码不在白名单（**动态解析规范第二节，当前 21 域**） | 🟠 WARN |
| G4 | `rule_id` 格式非法（非 `R-XX-NNN`）或缺失 | 🔴 ERROR |
| G5 | 序号不连续（缺号，仅提示，可能是作废号） | ⚪ INFO |
| G6 | 旧式编号（`R016-` 等）未升级为新制式 | 🟠 WARN |
| G7 | 卡型专用域被非指定卡型占用（`AY` 域必须是案由路由卡） | 🟠 WARN |

> **🔧 2026-09-11 白名单动态化**：G3 原硬编码「14 域」，与规范第二节实际 **21 域**不符，
> 误报 103 条（AY 90 / RA 6 / CL 3 / RN·XR·YS·RY 各 1）。现经 `rule_id_spec.py`
> **实时解析规范文件**，规范改版门禁自动跟随，杜绝「抄一遍就漂移」。
> 同时新增 G7，把规范里「AY 是卡型专用域」的口头约束固化为代码校验。

**豁免**：以 `_` 开头的治理/规范文档、模板、索引文件**不参与门禁**（否则误报淹没有效信号
——2026-09-11 首版实测 56 个 ERROR 中仅 25 个是真冲突，其余全是误报）。

## 用法

    python3 rule_id_guard.py                    # 全库扫描（默认）
    python3 rule_id_guard.py --since 60         # 只看最近 60 分钟新增/改动的卡
    python3 rule_id_guard.py --strict           # WARN 也判失败（CI 用）
    python3 rule_id_guard.py --json out.json    # 导出机器可读结果

退出码：0 = 通过（无 ERROR）；1 = 有 ERROR；2 = --strict 下有 WARN。
"""

import os
import re
import sys
import json
import time
import argparse
from collections import defaultdict
from datetime import datetime

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库"

# 白名单**动态解析**规范第二节（2026-09-11 起），不再硬编码。
# 解析失败自动回退内置兜底清单，门禁绝不因规范改版而失效。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from rule_id_spec import load_spec
    SPEC = load_spec()
except Exception as _e:                                    # pragma: no cover
    SPEC = None
    print(f"⚠️ rule_id_spec 加载失败（{_e}），G3/G7 检查将跳过", file=sys.stderr)
WHITELIST = set(SPEC.domains) if SPEC else set()
CARD_TYPE_DOMAIN = SPEC.card_type_domain if SPEC else {}

RULE_ID_RE = re.compile(r'^rule_id:\s*"?\s*(R-([A-Z]{2})-(\d{3}))', re.M)
FNAME_RE = re.compile(r'^(R-([A-Z]{2})-(\d{3}))')
CARD_TYPE_RE = re.compile(r'^card_type:\s*(.+)$', re.M)
# 旧式编号（2026-07 之前批次，如 R016- / R030-），单独归类，不判 ERROR
FNAME_LEGACY_RE = re.compile(r'^R(\d{2,3})-')
# 非规则卡文档：以下划线开头的治理/规范文件，或明确的管理型文档
DOC_PAT = re.compile(r'^_|规范\.md$|方案表\.md$|规则库\.md$|模板|索引|README|说明', re.I)


def classify_card(fname):
    """判定文件属于哪一类卡片。返回 'rule'(新制式规则卡) / 'legacy'(旧式编号) / 'doc'(非规则卡文档)。"""
    if FNAME_RE.match(fname):
        return "rule"
    if FNAME_LEGACY_RE.match(fname):
        return "legacy"
    if DOC_PAT.search(fname):
        return "doc"
    # 文件名不含卡号且不像治理文档 —— 视为普通文档，不强行判错
    return "doc"


def scan(since_min=None):
    files = []
    cutoff = time.time() - since_min * 60 if since_min else 0
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if not d.startswith(".") and d != "_备份"]
        for f in fn:
            if not f.endswith(".md"):
                continue
            p = os.path.join(dp, f)
            if cutoff and os.path.getmtime(p) < cutoff:
                continue
            files.append(p)
    return files


def check(paths):
    by_id = defaultdict(list)
    issues = []
    scanned = 0
    skipped = 0
    for p in paths:
        try:
            s = open(p, encoding="utf-8", errors="ignore").read(15000)
        except Exception:
            continue
        rel = os.path.relpath(p, ROOT)
        fname = os.path.basename(p)
        kind = classify_card(fname)
        # 非规则卡文档（治理表、规范、模板等）不参与编号门禁
        if kind == "doc":
            skipped += 1
            continue
        scanned += 1
        m = RULE_ID_RE.search(s)
        fm = FNAME_RE.match(fname)
        # 旧式编号卡：单列 G6，不判 ERROR（遗留批次，待编号治理）
        if kind == "legacy":
            lg = FNAME_LEGACY_RE.match(fname)
            legacy_no = lg.group(1) if lg else "?"
            if not m:
                issues.append(("G6", "WARN", rel,
                               f"旧式编号 R{legacy_no}- 未升级为 R-XX-NNN（缺 rule_id）"))
            else:
                issues.append(("G6", "WARN", rel,
                               f"旧式编号 R{legacy_no}- 未升级为 R-XX-NNN（rule_id={m.group(1)}）"))
            continue
        if not m:
            issues.append(("G4", "ERROR", rel, "缺 rule_id 或格式非法（应为 R-XX-NNN）"))
            continue
        rid, dom, num = m.group(1), m.group(2), int(m.group(3))
        by_id[rid].append(rel)
        # G3 白名单（规范解析失败时跳过，避免空集导致全库误报）
        if WHITELIST and dom not in WHITELIST:
            issues.append(("G3", "WARN", rel,
                           f"域码 {dom} 不在 {len(WHITELIST)} 域白名单（{rid}）"))
        # G7 卡型专用域约束（AY 域必须是案由路由卡）
        if dom in CARD_TYPE_DOMAIN:
            want = CARD_TYPE_DOMAIN[dom]
            ct = CARD_TYPE_RE.search(s)
            got = ct.group(1).strip().strip('"').strip("'") if ct else "(无 card_type)"
            if got != want:
                issues.append(("G7", "WARN", rel,
                               f"{dom} 为卡型专用域，card_type 应为「{want}」，实为「{got}」（{rid}）"))
        if fm:
            if fm.group(2) != dom or int(fm.group(3)) != num:
                issues.append(("G2", "WARN", rel,
                               f"文件名 {fm.group(1)} ≠ rule_id {rid}（规范允许别名，但应登记 aliases）"))
        else:
            issues.append(("G2", "WARN", rel, f"文件名不含卡号，rule_id={rid}"))
    # G1 同号冲突
    conflicts = {k: v for k, v in by_id.items() if len(v) > 1}
    for rid, paths_ in sorted(conflicts.items()):
        issues.append(("G1", "ERROR", rid, "同号冲突：" + " ｜ ".join(paths_)))
    # G5 缺号
    dom_nums = defaultdict(set)
    for rid in by_id:
        m = re.match(r'^R-([A-Z]{2})-(\d{3})$', rid)
        if m:
            dom_nums[m.group(1)].add(int(m.group(2)))
    gaps = {}
    for dom, ns in dom_nums.items():
        if not ns:
            continue
        miss = sorted(set(range(1, max(ns) + 1)) - ns)
        if miss and len(miss) <= 30:
            gaps[dom] = miss
        elif miss:
            gaps[dom] = f"{len(miss)} 个（{miss[0]}…{miss[-1]}）"
    return scanned, issues, conflicts, gaps, skipped


def main():
    ap = argparse.ArgumentParser(description="LawKB 规则卡编号守卫")
    ap.add_argument("--since", type=int, help="只检查最近 N 分钟内改动的卡")
    ap.add_argument("--strict", action="store_true", help="WARN 也判失败")
    ap.add_argument("--json", dest="json_out", help="导出 JSON 结果")
    args = ap.parse_args()

    paths = scan(args.since)
    scanned, issues, conflicts, gaps, skipped = check(paths)

    errs = [i for i in issues if i[1] == "ERROR"]
    warns = [i for i in issues if i[1] == "WARN"]

    print(f"=== 规则卡编号守卫 · {datetime.now():%Y-%m-%d %H:%M:%S} ===")
    print(f"扫描 {scanned} 张规则卡" + (f"（近 {args.since} 分钟）" if args.since else "（全库）")
          + f" ｜ 已跳过非规则卡文档 {skipped} 个（治理表/规范/模板等）")
    print(f"🔴 ERROR {len(errs)} ｜ 🟠 WARN {len(warns)} ｜ 同号冲突 {len(conflicts)} 组")
    print("-" * 74)

    if errs:
        print("\n【🔴 ERROR】")
        for code, lv, who, msg in errs:
            print(f"  [{code}] {who}\n        {msg}")
    if warns:
        print(f"\n【🟠 WARN】共 {len(warns)} 条，按类型归并：")
        agg = defaultdict(list)
        for code, lv, who, msg in warns:
            key = re.sub(r'R-[A-Z]{2}-\d{3}', 'R-XX-NNN', msg)
            agg[(code, key)].append(who)
        for (code, key), whos in sorted(agg.items(), key=lambda x: -len(x[1])):
            print(f"  [{code}] {key}  → {len(whos)} 张")
            for w in whos[:3]:
                print(f"        {w}")
            if len(whos) > 3:
                print(f"        …另 {len(whos)-3} 张")
    if gaps:
        print("\n【⚪ INFO 缺号（可能为作废号，规范第四节登记后不复用）】")
        for dom, g in sorted(gaps.items()):
            print(f"  {dom}: {g}")

    print("\n" + "-" * 74)
    if args.json_out:
        json.dump({"scanned": scanned, "errors": len(errs), "warns": len(warns),
                   "conflicts": conflicts, "gaps": {k: str(v) for k, v in gaps.items()},
                   "issues": issues}, open(args.json_out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"📄 已导出：{args.json_out}")

    if errs:
        print("❌ 门禁未通过：存在 ERROR，须修复后归档")
        sys.exit(1)
    if args.strict and warns:
        print("❌ strict 模式：存在 WARN")
        sys.exit(2)
    print("✅ 编号门禁通过")


if __name__ == "__main__":
    main()
