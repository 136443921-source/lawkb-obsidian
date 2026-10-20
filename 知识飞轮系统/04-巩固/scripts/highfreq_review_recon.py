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

运维补强（v2 · 2026-10-18）：
  - 已知隐患：macOS iCloud 把不常用文件标记为 `compressed,dataless`（云端卸载），
    读取此类文件会 **无限阻塞** 且 try/except 捕不到，导致整批静默卡死且不报错。
  - 三重保险：
    1) dataless 跳过：启动时用 `find -flags +dataless` 标记，扫描直接跳过；
    2) 读取超时：`safe_read_bytes` 对单文件读取加 SIGALRM 超时，任何阻塞都会被兜底跳过；
    3) 覆盖率标注：报告与打印均标注「已扫描/跳过」与引用边下限，dataless>0 时明确提示重跑。

用法：
  python3 highfreq_review_recon.py --top 30            # dry-run 预览
  python3 highfreq_review_recon.py --top 30 --apply    # 写对账批报告
"""

import os
import re
import argparse
import datetime
import subprocess
import signal
from collections import Counter
from pathlib import Path

BASE = Path("/Users/chenyouqiang/Documents/LawKB/知识飞轮系统")
CARDS_DIR = BASE / "02-提炼" / "经验卡片"
LAYERS = ["01-采集", "02-提炼", "03-连接", "04-巩固", "05-调用", "06-沉淀"]
OUT_DIR = BASE / "04-巩固" / "Spaced-Repetition"

# 读取超时（秒）：防止 dataless / 任意阻塞型文件把整批卡死
READ_TIMEOUT = 8
FM_TIMEOUT = 4  # frontmatter 读取超时（更快跳过）

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


def build_dataless_set():
    """用系统 find 标记 iCloud 已卸载(dataless)的 md，避免读取时无限阻塞。
    非 macOS 或 find 不支持时返回空集合（此时由读取超时兜底）。"""
    s = set()
    for layer in LAYERS:
        d = BASE / layer
        if not d.exists():
            continue
        try:
            out = subprocess.run(
                ["find", str(d), "-name", "*.md", "-flags", "+dataless", "-print"],
                capture_output=True, text=True, timeout=60,
            )
            for line in out.stdout.splitlines():
                line = line.strip()
                if line:
                    s.add(line)
        except Exception:
            pass
    return s


def safe_read_bytes(path, timeout=READ_TIMEOUT):
    """带超时的二进制读取。超时或异常返回 None（视为不可读，跳过）。
    主线程用 SIGALRM 实现超时；非 Unix 平台退化为普通读取。"""
    if not hasattr(signal, "SIGALRM"):
        try:
            with open(path, "rb") as fh:
                return fh.read()
        except Exception:
            return None

    def _handler(signum, frame):
        raise TimeoutError("read blocked")

    prev = signal.signal(signal.SIGALRM, _handler)
    signal.alarm(timeout)
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except Exception:
        return None
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, prev)


def scan_cards(dataless):
    """返回 {卡名(不含.md): (path, review_date, importance, repetition, dataless)}"""
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
            pstr = str(fp)
            if pstr in dataless:
                # dataless 卡片：登记但标脏，跳过实际读取，避免阻塞
                cards[name] = {"path": fp, "review_date": None, "importance": None,
                               "repetition": 0, "dataless": True}
                continue
            try:
                head = safe_read_bytes(pstr, FM_TIMEOUT)
            except Exception:
                head = None
            head = (head or b"").decode("utf-8", errors="ignore")[:4096]
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
            cards[name] = {"path": fp, "review_date": rd, "importance": imp,
                           "repetition": rep, "dataless": False}
    return cards


def count_backlinks(cards, dataless):
    """扫六层全部 md 的 wiki 链接，统计每张卡被引用次数。返回 (Counter, 总md, 已扫md)。"""
    counter = Counter()
    total_md = 0
    scanned_md = 0
    for layer in LAYERS:
        layer_dir = BASE / layer
        if not layer_dir.exists():
            continue
        for root, dirs, files in os.walk(layer_dir):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                if not f.endswith(".md"):
                    continue
                total_md += 1
                fp = Path(root) / f
                pstr = str(fp)
                if pstr in dataless:
                    continue  # dataless 源文件跳过，不阻塞
                scanned_md += 1
                data = safe_read_bytes(pstr, READ_TIMEOUT)
                if not data:
                    continue
                content = data.decode("utf-8", errors="ignore")
                for m in WIKI_PATTERN.finditer(content):
                    target = m.group(1).strip()
                    if target in cards:
                        counter[target] += 1
    return counter, total_md, scanned_md


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=30)
    ap.add_argument("--apply", action="store_true", help="写对账批报告（默认 dry-run）")
    args = ap.parse_args()

    today = datetime.date.today()
    dataless = build_dataless_set()
    cards = scan_cards(dataless)
    counter, total_md, scanned_md = count_backlinks(cards, dataless)

    total_links = sum(counter.values())
    zero_link = len(cards) - len(counter)
    dataless_cards = {n for n, c in cards.items() if c.get("dataless")}
    skipped_md = total_md - scanned_md

    # 分类（口径：review_date 三分——未排期🔴 / 逾期🟠 / 在册🟢；dataless 单列⚪）
    red, orange, green, gray = [], [], [], []
    for name, cnt in counter.most_common():
        c = cards[name]
        row = (name, cnt, c["review_date"], c["importance"], c["repetition"])
        if c.get("dataless"):
            gray.append(row)
            continue
        rd = c["review_date"]
        if rd is None:
            red.append(row)  # 从未入复习队列
        elif rd < today.isoformat():
            orange.append(row)  # 已排期但逾期
        else:
            green.append(row)  # 在册待复习
    # dataless 卡片未出现在 counter 中的，按 cnt=0 补入 ⚪
    for name in dataless_cards:
        if name not in counter:
            c = cards[name]
            gray.append((name, 0, c["review_date"], c["importance"], c["repetition"]))
    gray.sort(key=lambda r: r[1], reverse=True)

    print(f"== 高频引用卡复习对账（{today}）==")
    print(f"经验卡总数: {len(cards)} ｜ 被引用卡: {len(counter)} ｜ 零引用卡: {zero_link} ｜ 总引用边: {total_links}")
    print(f"🔴 未排期: {len(red)} ｜ 🟠 逾期: {len(orange)} ｜ 🟢 在册: {len(green)} ｜ ⚪ dataless未扫描: {len(gray)}")
    print(f"覆盖率：引用源 md 扫描 {scanned_md}/{total_md}（dataless 跳过 {skipped_md}）｜ 卡片 dataless 跳过 {len(dataless_cards)}")

    print(f"\nTop {args.top} 高频卡（含状态）:")
    for name, cnt in counter.most_common(args.top):
        c = cards[name]
        rd = c["review_date"]
        if c.get("dataless"):
            state = "⚪未扫描"
        elif rd is None:
            state = "🔴未排期"
        elif rd < today.isoformat():
            state = "🟠逾期"
        else:
            state = "🟢在册"
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
        f"> 数据：经验卡 {len(cards)} 张（dataless 跳过 {len(dataless_cards)}），被引用 {len(counter)} 张，总引用边 {total_links}（下限）；🔴 {len(red)} ｜ 🟠 {len(orange)} ｜ 🟢 {len(green)} ｜ ⚪ 未扫描 {len(gray)}。",
        f"> 覆盖率：引用源 md {scanned_md}/{total_md} 已扫描（dataless 跳过 {skipped_md}）。⚠️ 当 dataless>0 时引用边为下限，建议 `brctl download \"/Users/chenyouqiang/Documents/LawKB/知识飞轮系统\"` 取回本地后重跑以获得完整计数。",
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
    # ⚪ dataless 未扫描段
    show_gray = gray[: max(args.top * 3, 100)]
    lines += [
        "",
        f"## ⚪ dataless 未扫描 · {len(gray)}（iCloud 云端卸载，本次未计入引用计数）",
        "",
        "> 这些卡/源文件处于 iCloud `compressed,dataless` 状态，读取会无限阻塞；本批已安全跳过并加了单文件读取超时兜底。",
        "> 用 `brctl download \"/Users/chenyouqiang/Documents/LawKB/知识飞轮系统\"` 或对其逐层取回本地后重跑，计数即补全。",
        "",
        "| 被引用次数 | 卡片 | review_date |",
        "|---|---|---|",
    ]
    for name, cnt, rd, imp, rep in show_gray:
        lines.append(f"| {cnt} | [[{name}]] | {rd or '未设/未读'} |")
    if len(gray) > len(show_gray):
        lines.append(f"| … | （其余 {len(gray) - len(show_gray)} 张未列，已计入上方 ⚪ 计数） | … |")
    lines += [
        "",
        "## 对账纪律",
        "",
        "- 🔴 类卡按引用次数降序喂给 `review_writeback.py --pairs`（复习后评分回写 SM-2）。",
        "- 🟠 类卡并入既有复习队列逾期段，走既有 stagger/defer 脚本。",
        "- ⚪ 类卡先 `brctl download` 取回、重跑本对账批后再按上面口径入队。",
        "- 零引用卡不进本对账批（引用频次无杠杆），按既有队列常规节奏。",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[apply] 对账批已写: {out}")


if __name__ == "__main__":
    main()
