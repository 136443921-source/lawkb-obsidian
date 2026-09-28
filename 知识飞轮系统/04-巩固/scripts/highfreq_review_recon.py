#!/usr/bin/env python3
"""
高频引用卡复习对账批（highfreq_review_recon.py）
功能：
  1. 扫描知识飞轮系统六层（01-采集~06-沉淀）全部 md 的 wiki 链接 [[...]]，统计每张
     经验卡片（02-提炼/经验卡片/）被引用次数（backlink 频次）。
  2. 与 SM-2 复习字段（review_date / importance / repetition）交叉对账，分三类：
     🔴 存过未熟 —— 高频引用但 repetition=0（从未复习过），最优先补入复习队列
     🟠 逾期对账 —— 有 review_date 但已逾期（review_date < today）
     🟢 已熟在册 —— repetition>0（复习机制已生效）
  3. 产出对账批报告 md 落 04-巩固/Spaced-Repetition/，与既有复习队列衔接。

安全铁律（六-B）：
  - 默认 dry-run，只打印统计不写盘；--apply 才写报告文件（新建文件，不改动任何既有卡）。
  - 全路径写死在飞轮目录内；跳过隐藏目录。

用法：
  python3 highfreq_review_recon.py --top 30            # dry-run 预览
  python3 highfreq_review_recon.py --top 30 --apply    # 写对账批报告
"""

import os
import re
import argparse
import datetime
from collections import Counter
from pathlib import Path

BASE = Path("/Users/chenyouqiang/Documents/LawKB/知识飞轮系统")
CARDS_DIR = BASE / "02-提炼" / "经验卡片"
LAYERS = ["01-采集", "02-提炼", "03-连接", "04-巩固", "05-调用", "06-沉淀"]
OUT_DIR = BASE / "04-巩固" / "Spaced-Repetition"

FM_PATTERN = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
RD_PATTERN = re.compile(r"review_date:\s*[\"']?(\d{4}-\d{2}-\d{2})")
IMP_PATTERN = re.compile(r"importance:\s*(\d+)")
REP_PATTERN = re.compile(r"(?<!last_)repetition:\s*(\d+)")
WIKI_PATTERN = re.compile(r"\[\[([^\]\|#]+)")

# 汇编导航页（非复习对象）：文件名级排除
NAV_NAMES = {"README"}
NAV_KEYWORDS = ("总索引-MOC", "总索引-MOC")


def is_nav(name: str) -> bool:
    if name in NAV_NAMES:
        return True
    return any(k in name for k in NAV_KEYWORDS)


def scan_cards():
    """返回 {卡名(不含.md): (path, review_date, importance, repetition)}"""
    cards = {}
    for root, dirs, files in os.walk(CARDS_DIR):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in files:
            if not f.endswith(".md"):
                continue
            name = f[:-3]
            if is_nav(name):
                continue
            fp = Path(root) / f
            try:
                head = fp.read_text(encoding="utf-8")[:4096]
            except Exception:
                continue
            m = FM_PATTERN.match(head)
            rd = imp = rep = None
            if m:
                fm = m.group(1)
                rd_m = RD_PATTERN.search(fm)
                rd = rd_m.group(1) if rd_m else None
                imp_m = IMP_PATTERN.search(fm)
                imp = int(imp_m.group(1)) if imp_m else None
                rep_m = REP_PATTERN.search(fm)
                rep = int(rep_m.group(1)) if rep_m else 0
            cards[name] = {"path": fp, "review_date": rd, "importance": imp, "repetition": rep}
    return cards


def count_backlinks(cards):
    """扫六层全部 md 的 wiki 链接，统计每张卡被引用次数。返回 Counter。"""
    counter = Counter()
    for layer in LAYERS:
        layer_dir = BASE / layer
        if not layer_dir.exists():
            continue
        for root, dirs, files in os.walk(layer_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                if not f.endswith(".md"):
                    continue
                fp = Path(root) / f
                try:
                    content = fp.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                for m in WIKI_PATTERN.finditer(content):
                    target = m.group(1).strip()
                    if target in cards:
                        counter[target] += 1
    return counter


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--apply", action="store_true", help="写对账批报告（默认 dry-run）")
    args = ap.parse_args()

    today = datetime.date.today()
    cards = scan_cards()
    counter = count_backlinks(cards)

    total_links = sum(counter.values())
    zero_link = len(cards) - len(counter)

    # 分类（口径：review_date 三分——未排期🔴 / 逾期🟠 / 在册🟢）
    red, orange, green = [], [], []
    for name, cnt in counter.most_common():
        c = cards[name]
        row = (name, cnt, c["review_date"], c["importance"], c["repetition"])
        rd = c["review_date"]
        if rd is None:
            red.append(row)  # 从未入复习队列
        elif rd < today.isoformat():
            orange.append(row)  # 已排期但逾期
        else:
            green.append(row)  # 在册待复习

    print(f"== 高频引用卡复习对账（{today}）==")
    print(f"经验卡总数: {len(cards)} ｜ 被引用卡: {len(counter)} ｜ 零引用卡: {zero_link} ｜ 总引用边: {total_links}")
    print(f"🔴 未排期(review_date未设): {len(red)} ｜ 🟠 逾期(review_date已过): {len(orange)} ｜ 🟢 在册待复习: {len(green)}")
    print(f"\nTop {args.top} 高频卡（含状态）:")
    for name, cnt in counter.most_common(args.top):
        c = cards[name]
        rd = c["review_date"]
        state = "🔴未排期" if rd is None else ("🟠逾期" if rd < today.isoformat() else "🟢在册")
        print(f"  [{state}] {cnt:>3}次  {name}  (imp={c['importance']}, rep={c['repetition']}, rd={c['review_date']})")

    if not args.apply:
        print("\n[dry-run] 未写盘。加 --apply 生成对账批报告。")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"高频引用卡对账批-{today.isoformat()}.md"
    lines = [
        "---",
        f"created: {datetime.datetime.now().strftime('%Y-%m-%dT%H:%M')}",
        f"title: 高频引用卡对账批-{today.isoformat()}",
        "tags:",
        "  - Spaced-Repetition",
        "  - 高频引用对账",
        "type: 巩固层机写批",
        "---",
        "",
        f"# 高频引用卡复习对账批（{today.isoformat()}）",
        "",
        f"> 机制：`04-巩固/scripts/highfreq_review_recon.py` 机写。对账口径：**backlink 频次 × SM-2 复习状态**。",
        f"> 数据：经验卡 {len(cards)} 张，被引用 {len(counter)} 张，总引用边 {total_links}；🔴存过未熟 {len(red)} ｜ 🟠逾期 {len(orange)} ｜ 🟢已熟 {len(green)}。",
        "",
        f"## 🔴 未排期 · Top {args.top}（高频引用但从未入复习队列，最优先入队）",
        "",
        "| 引用次数 | 卡片 | importance | 复习日期 |",
        "|---|---|---|---|",
    ]
    for name, cnt, rd, imp, rep in red[: args.top]:
        lines.append(f"| {cnt} | [[{name}]] | {imp or '-'} | {rd or '未设'} |")
    lines += [
        "",
        f"## 🟠 逾期对账 · Top {args.top}（复习过但已逾期）",
        "",
        "| 引用次数 | 卡片 | 复习日期 | 逾期天数 |",
        "|---|---|---|---|",
    ]
    for name, cnt, rd, imp, rep in orange[: args.top]:
        od = (today - datetime.date.fromisoformat(rd)).days if rd else "-"
        lines.append(f"| {cnt} | [[{name}]] | {rd} | {od} |")
    lines += [
        "",
        f"## 🟢 在册待复习 · Top {args.top}（已排期未到期）",
        "",
        "| 引用次数 | 卡片 | repetition | 复习日期 |",
        "|---|---|---|---|",
    ]
    for name, cnt, rd, imp, rep in green[: args.top]:
        lines.append(f"| {cnt} | [[{name}]] | {rep} | {rd or '-'} |")
    lines += [
        "",
        "## 对账纪律",
        "",
        "- 🔴 类卡按引用次数降序喂给 `review_writeback.py --pairs`（复习后评分回写 SM-2）。",
        "- 🟠 类卡并入既有复习队列逾期段，走既有 stagger/defer 脚本。",
        "- 零引用卡不进本对账批（引用频次无杠杆），按既有队列常规节奏。",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[apply] 对账批已写: {out}")


if __name__ == "__main__":
    main()
