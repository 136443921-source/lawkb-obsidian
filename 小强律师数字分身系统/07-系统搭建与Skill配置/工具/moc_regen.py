#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOC 重生成器（持久固化版 v1.0 · 2026-10-22）

来源：由 `/tmp/moc_regen_dry.py` + `/tmp/moc_build.py`（易被系统清理）固化而来，
遵老强 P0-3「/tmp 脚本固化迁移至数字分身系统工具目录，长期复用」。

用途：扫描 `06-沉淀/裁判规则库/` 物理卡 → 与 MOC 现有 rule_id 比对 → 输出差异清单。

用法：
  python3 moc_regen.py --scan                 # 仅扫描，缓存到 <tool>/cards_cache.json
  python3 moc_regen.py --diff                 # 出「新增/多余」清单（先核多余=0 防丢卡）
  python3 moc_regen.py --diff --json out.json # 导出差异

设计铁律（沿用卡族MOC重生成 SKILL.md 的实测坑）：
  ① 全库 os.walk 慢 → 本脚本限定 SCAN_ROOT，且外部用 run_in_background；
  ② 并发写：扫描后可能有新卡落盘 → 交付前复扫确认时点；
  ③ 中文路径 bash grep 有假阴性坑 → 本脚本用 Python，不用 shell grep；
  ④ parse_fm 键正则必须含数字（`^([A-Za-z_][A-Za-z0-9_]*):`）；
  ⑤ 必须读全文件（不可 read(4000) 截断）；
  ⑥ 覆盖率比对必须 wikilink 感知：`(?:\\[\\[)?(R-[A-Z]{2}-\\d{{3}})(?:\\]\\])?`。
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KB = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
SCAN_ROOT = os.path.join(KB, "06-沉淀")  # 2026-10-22 扩面：覆盖全部域库（17 个）
MOC_PATH = os.path.join(KB, "06-沉淀", "裁判规则库", "裁判规则库.md")
CACHE = os.path.join(HERE, "cards_cache.json")

# 排除目录（2026-10-22 实测：.trash_a 回收站会被误扫入，污染「新增」清单）
EXCLUDE_DIRS = {".trash_a", ".trash", ".obsidian", "__pycache__", "_backup", "_ARCHIVED"}

# ⑥ wikilink 感知正则（防假阴性夸大缺失）
RULE_ID_RE = re.compile(r"(?:\[\[)?(R-[A-Z]{2}-\d{3})(?:\]\])?")
# ④ 键正则必须含数字
FM_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")


def parse_fm(text: str):
    """解析首页 frontmatter。⑤ 必须传入全文（调用方 read() 全文件）。"""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    block = text[3:end]
    fm = {}
    cur_key = None
    for line in block.split("\n"):
        m = FM_KEY_RE.match(line)
        if m:
            cur_key = m.group(1)
            fm[cur_key] = m.group(2).strip().strip('"').strip("'")
        elif cur_key and line.strip().startswith("- "):
            # 列表项：拼接到当前键
            item = line.strip()[2:].strip().strip('"').strip("'")
            fm[cur_key] = (fm.get(cur_key) or "") + ("|" if fm.get(cur_key) else "") + item
    return fm


def scan():
    """扫描物理卡，返回 {rule_id: {file, title, card_type, domain, path}}。"""
    cards = {}
    dups = {}
    for dp, dn, fn in os.walk(SCAN_ROOT):
        # 排除回收站/备份目录（否则污染「新增」清单）
        dn[:] = [d for d in dn if d not in EXCLUDE_DIRS]
        for f in fn:
            if not f.endswith(".md"):
                continue
            if not f.startswith("R-"):
                continue
            fp = os.path.join(dp, f)
            try:
                text = open(fp, encoding="utf-8").read()  # ⑤ 读全文件
            except Exception:
                continue
            fm = parse_fm(text)
            if fm is None:
                # frontmatter 缺失，退回文件名取号
                m = RULE_ID_RE.search(f)
                if not m:
                    continue
                rid = m.group(1)
                fm = {}
            else:
                rid = fm.get("rule_id") or fm.get("card_id") or ""
                if not rid:
                    m = RULE_ID_RE.search(f)
                    rid = m.group(1) if m else ""
            if not rid or not RULE_ID_RE.fullmatch(rid):
                continue
            rel = os.path.relpath(fp, SCAN_ROOT)
            rec = {
                "file": f,
                "title": (fm.get("title") or os.path.splitext(f)[0])[:80],
                "card_type": fm.get("card_type") or "",
                "card_family": fm.get("card_family") or "",
                "domain": fm.get("domain") or "",
                "path": rel,
            }
            if rid in cards:
                dups.setdefault(rid, [cards[rid]["path"]]).append(rel)
            else:
                cards[rid] = rec
    return cards, dups


def load_moc_ids():
    """从 MOC 提取已收录 rule_id（⑥ wikilink 感知）。"""
    if not os.path.exists(MOC_PATH):
        return set()
    text = open(MOC_PATH, encoding="utf-8").read()
    return set(RULE_ID_RE.findall(text))


def emit_full_index(cards: dict, dups: dict, out_path: str, moc_ids: set):
    """生成全量索引快照（按域分组的 4 列表格）。

    为什么独立成文件而不写进 MOC：
      `裁判规则库.md` 是月度快照 + 分散索引表体例，且已 96KB；
      把 300 张全量表格塞进去会让文件失去可读性。独立快照反而便于检索与比对。
    """
    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    # 按域分组
    by_domain = {}
    for rid, rec in cards.items():
        dom = rec.get("domain") or "(未标域)"
        by_domain.setdefault(dom, []).append(rid)
    for dom in by_domain:
        by_domain[dom].sort(key=lambda x: (x.split("-")[1], int(x.split("-")[2])))

    lines = [
        "---",
        "title: 裁判规则库 · 全量物理索引快照",
        f"created: {now}",
        "source_ai: workbuddy",
        "type: 索引快照",
        "tags:",
        "  - 裁判规则库",
        "  - 全量索引",
        "---",
        "",
        "# 裁判规则库 · 全量物理索引快照",
        "",
        f"> **生成时间**：{now}｜**扫描根**：`06-沉淀/裁判规则库/`（已排除 `.trash_a` 等回收站目录）",
        f"> **物理卡总数**：{len(cards)} 张｜**分域**：{len(by_domain)} 个",
        "> **性质**：物理重扫快照，与 MOC（`裁判规则库.md`）互为校验，**不替代 MOC**。",
        "",
        "## 📊 分域统计",
        "",
        "| 域 | 卡数 | rule_id 号段 |",
        "|---|---|---|",
    ]
    for dom in sorted(by_domain, key=lambda d: -len(by_domain[d])):
        ids = by_domain[dom]
        nums = sorted(int(r.split("-")[2]) for r in ids)
        lines.append(f"| {dom} | {len(ids)} | {ids[0].split('-')[1]}-{nums[0]:03d}~{nums[-1]:03d} |")

    if dups:
        lines += ["", "## ⚠️ 同号冲突", "",
                  "> 同一 rule_id 存在多张物理卡，检索会产生歧义，须人工裁定保留哪张。", "",
                  "| rule_id | 冲突文件 |", "|---|---|"]
        for rid in sorted(dups):
            for p in dups[rid]:
                lines.append(f"| {rid} | `{p}` |")

    lines += ["", "## 📇 全量卡清单", ""]
    for dom in sorted(by_domain, key=lambda d: -len(by_domain[d])):
        lines += [f"### {dom}（{len(by_domain[dom])} 张）", "",
                  "| rule_id | 标题 | 路径 | MOC 收录 |", "|---|---|---|---|"]
        for rid in by_domain[dom]:
            rec = cards[rid]
            title = (rec["title"] or "").replace("|", "丨")[:60]
            in_moc = "✅" if rid in moc_ids else "—"
            lines.append(f"| {rid} | {title} | `{rec['path']}` | {in_moc} |")
        lines.append("")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return len(cards), len(by_domain)


def emit_family_index(cards: dict, dups: dict, out_path: str):
    """按 frontmatter `card_type` 分族生成索引（2026-10-22 老强定口径）。

    背景：`卡族MOC重生成` SKILL.md 铁律——**成员 = frontmatter 卡型字段，
    不是目录名、不是 rule_id 前缀**（R-XX 是域码不是卡型，同一前缀下混多种卡型）。
    本函数即按该口径分族。

    未填 card_type 的卡单列「未标卡型（待补）」组，**不猜测归族**——
    强行推断会把治理问题掩盖成"看起来整齐"。
    """
    import datetime
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    by_type = {}
    for rid, rec in cards.items():
        ct = (rec.get("card_type") or "").strip() or "未标卡型（待补）"
        by_type.setdefault(ct, []).append(rid)

    ORDER = ["通用裁判规则卡", "裁判规则卡", "实务规则卡", "赔偿计算卡", "裁量尺度卡",
             "合规审查卡", "经验卡", "操作指引卡", "文书范式卡", "规范要点卡",
             "审判要件卡", "证据规则卡", "案由路由卡", "请求权基础卡",
             "案例规则卡", "要件映射卡", "要件映射指针卡", "庭审主持卡", "工具事故卡",
             "未标卡型（待补）"]
    def _key(t):
        return (ORDER.index(t) if t in ORDER else len(ORDER), t)
    fams = sorted(by_type, key=_key)

    lines = [
        "---",
        "title: 裁判规则库 · 分族索引（按 card_type）",
        f"created: {now}",
        "source_ai: workbuddy",
        "type: 索引快照",
        "member_criterion: frontmatter card_type（非目录名、非 rule_id 前缀）",
        "tags:",
        "  - 裁判规则库",
        "  - 分族索引",
        "  - card_type",
        "---",
        "",
        "# 裁判规则库 · 分族索引（按 card_type）",
        "",
        f"> **生成**：{now}｜**成员口径**：frontmatter `card_type`（老强 2026-10-22 拍板）",
        f"> **物理卡总数**：{len(cards)} 张｜**卡型族**：{len(by_type)} 个",
        "> **铁律**：`R-XX` 前缀是**域码不是卡型**，同一前缀下混有多种卡型——故按卡型字段分族，不按前缀。",
        "",
        "## 📊 分族统计",
        "",
        "| 卡型 | 张数 | 占比 |",
        "|---|---|---|",
    ]
    for t in fams:
        n = len(by_type[t])
        lines.append(f"| {t} | {n} | {n/len(cards):.1%} |")

    if "未标卡型（待补）" in by_type:
        lines += ["", "> ⚠️ 「未标卡型（待补）」组须补填 frontmatter `card_type` 后方可归族。",
                  "> **不做推测性归族**——猜测会把治理问题掩盖成整齐。"]

    for t in fams:
        ids = by_type[t]
        ids.sort(key=lambda x: (x.split("-")[1], int(x.split("-")[2]) if x.split("-")[2].isdigit() else 0))
        lines += ["", f"## {t}（{len(ids)} 张）", "",
                  "| rule_id | 标题 | 路径 |", "|---|---|---|"]
        for rid in ids:
            rec = cards[rid]
            title = (rec.get("title") or "").replace("|", "丨")[:60]
            lines.append(f"| {rid} | {title} | `{rec['path']}` |")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return len(cards), len(by_type), {t: len(by_type[t]) for t in fams}


def main():
    ap = argparse.ArgumentParser(description="MOC 重生成器（扫描/差异）")
    ap.add_argument("--scan", action="store_true", help="扫描物理卡并缓存")
    ap.add_argument("--diff", action="store_true", help="输出新增/多余清单")
    ap.add_argument("--json", help="差异导出路径")
    ap.add_argument("--emit-full-index", metavar="PATH",
                    help="生成全量物理索引快照（按域分组 4 列表）")
    ap.add_argument("--emit-family-index", metavar="PATH",
                    help="生成分族索引（按 card_type 分组，老强 2026-10-22 定口径）")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not (args.scan or args.diff):
        ap.print_help()
        sys.exit(2)

    print(f"扫描根：{SCAN_ROOT}")
    cards, dups = scan()
    print(f"物理卡：{len(cards)} 张" + (f"（同号冲突 {len(dups)} 组）" if dups else ""))

    if args.scan:
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump({"scanned_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
                       "count": len(cards), "cards": cards, "dups": dups},
                      f, ensure_ascii=False, indent=1)
        print(f"✅ 缓存 → {CACHE}")

    if args.diff:
        moc_ids = load_moc_ids()
        print(f"MOC 已收录（全文出现的 rule_id）：{len(moc_ids)} 张")
        new = sorted(set(cards) - moc_ids)
        extra = sorted(moc_ids - set(cards))
        print(f"\n【新增】物理有 · MOC 无：{len(new)} 张")
        for r in new[:60]:
            print(f"  + {r}  {cards[r]['path']}")
        if len(new) > 60:
            print(f"  … 其余 {len(new)-60} 张略")
        print(f"\n【多余】MOC 有 · 物理无：{len(extra)} 张")
        for r in extra[:40]:
            print(f"  - {r}")
        if len(extra) > 40:
            print(f"  … 其余 {len(extra)-40} 张略")
        if extra:
            print("\n⚠️ 多余≠0，先核是否物理卡被移动/改名，**不得直接删除 MOC 条目**（防丢卡）")
        if args.json:
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump({"physical": len(cards), "moc_ids": len(moc_ids),
                           "new": new, "extra": extra, "dups": dups},
                          f, ensure_ascii=False, indent=1)
            print(f"\n✅ 差异导出 → {args.json}")

    if args.emit_full_index:
        moc_ids = load_moc_ids() if not args.diff else moc_ids
        n, nd = emit_full_index(cards, dups, args.emit_full_index, moc_ids)
        print(f"\n✅ 全量索引快照 → {args.emit_full_index}（{n} 张 / {nd} 域）")

    if args.emit_family_index:
        n, nf, stats = emit_family_index(cards, dups, args.emit_family_index)
        print(f"\n✅ 分族索引 → {args.emit_family_index}（{n} 张 / {nf} 族）")
        for t, c in stats.items():
            if c >= 20:
                print(f"     {t}: {c}")


if __name__ == "__main__":
    main()
