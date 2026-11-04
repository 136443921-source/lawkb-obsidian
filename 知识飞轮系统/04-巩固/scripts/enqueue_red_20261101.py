#!/usr/bin/env python3
"""
🔴 未排期卡入队脚本（enqueue_red_20261101.py）
功能：
  将高频引用对账批（2026-11-01）中 🔴 类卡（review_date 未设）按引用次数降序
  错峰排期入队：起始 2026-11-02，14 天摊完，约 15 张/天；只新增/写入
  frontmatter 的 review_date 字段，不动卡片其他内容。

安全铁律（六-B）：
  - 默认 dry-run；--apply 才写盘。
  - 写盘前逐文件 cp 备份到 /tmp/highfreq_enqueue_20261101/（按相对路径），
    并落 manifest.json（含旧新值），支持整批回滚。
  - 无 frontmatter 的卡不写入，单列报告待人工处理。
  - 写入后逐文件回读验证 review_date 落地。

用法：
  python3 enqueue_red_20261101.py            # dry-run 预览
  python3 enqueue_red_20261101.py --apply    # 执行写入
"""

import os
import re
import sys
import json
import shutil
import signal
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import highfreq_review_recon as recon  # 复用对账脚本的扫描/防卡死逻辑

BASE = Path("/Users/chenyouqiang/Documents/LawKB/知识飞轮系统")
BACKUP_DIR = Path("/tmp/highfreq_enqueue_20261101")
START_DATE = datetime.date(2026, 11, 2)
DAYS = 14

FM_PATTERN = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
RD_LINE = re.compile(r"^review_date:", re.MULTILINE)


def main():
    ap_ok = "--apply" in sys.argv
    today = datetime.date.today()

    dataless = recon.build_dataless_set()
    cards = recon.scan_cards(dataless)
    counter, total_md, scanned_md = recon.count_backlinks(cards, dataless)

    red = []
    no_fm = []          # 无 frontmatter，需人工
    has_rd_dirty = []   # 有 review_date 但被判红（理论上不该出现）
    for name, cnt in counter.most_common():
        c = cards[name]
        if c.get("dataless"):
            continue
        if c["review_date"] is None:
            red.append((name, cnt, c["path"]))
    # 零引用且无 rd 的也算 🔴 口径外——本批只收被引用卡，与对账批口径一致
    red.sort(key=lambda r: (-r[1], r[0]))

    print(f"== 🔴 未排期卡入队（{today}）==")
    print(f"被引用且无 review_date 的卡: {len(red)} 张 ｜ 目标: {DAYS} 天摊完")
    print(f"覆盖率：引用源 md {scanned_md}/{total_md}（dataless 跳过 {total_md - scanned_md}）")

    # 排期：引用次数降序， ties 按卡名；约 15 张/天
    per_day = -(-len(red) // DAYS)
    assignments = []
    for i, (name, cnt, path) in enumerate(red):
        day = START_DATE + datetime.timedelta(days=i // per_day)
        assignments.append({"name": name, "citations": cnt,
                            "path": str(path), "review_date": day.isoformat()})

    by_date = {}
    for a in assignments:
        by_date.setdefault(a["review_date"], []).append(a)
    print(f"\n按日期分布（{per_day} 张/天）:")
    for d in sorted(by_date):
        top = max(by_date[d], key=lambda x: x["citations"])
        print(f"  {d}: {len(by_date[d])} 张（当日最高引用 {top['citations']} 次）")

    # 前置检查：frontmatter 状态
    skippable = []
    for a in assignments:
        try:
            head = open(a["path"], "rb").read().decode("utf-8", errors="ignore")[:16384]
        except Exception:
            skippable.append((a["name"], "读取失败"))
            continue
        if not FM_PATTERN.match(head):
            no_fm.append((a["name"], a["path"]))
        elif RD_LINE.search(FM_PATTERN.match(head).group(1)):
            has_rd_dirty.append((a["name"], a["path"]))

    if no_fm:
        print(f"\n⚠️ 无 frontmatter 卡 {len(no_fm)} 张（本批跳过，待人工）:")
        for n, _ in no_fm[:10]:
            print(f"   - {n}")
    if has_rd_dirty:
        print(f"\n⚠️ 异常：已有 review_date 却被判红 {len(has_rd_dirty)} 张（本批跳过）:")
        for n, _ in has_rd_dirty[:10]:
            print(f"   - {n}")

    todo = [a for a in assignments
            if a["name"] not in {n for n, _ in no_fm}
            and a["name"] not in {n for n, _ in has_rd_dirty}
            and a["name"] not in {n for n, _ in skippable}]
    print(f"\n本批实际写入目标: {len(todo)} 张")

    if not ap_ok:
        print("\n[dry-run] 未写盘。加 --apply 执行。")
        return

    # ---- apply ----
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    manifest, changed, failed = [], 0, 0
    for a in todo:
        fp = Path(a["path"])
        try:
            content = fp.read_text(encoding="utf-8")
            m = FM_PATTERN.match(content)
            fm = m.group(1)
            # 备份
            rel = fp.relative_to(BASE)
            bak = BACKUP_DIR / rel
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fp, bak)
            # 在 frontmatter 末尾插入 review_date
            new_content = content[: m.end(1)] + f"\nreview_date: {a['review_date']}" + content[m.end(1):]
            fp.write_text(new_content, encoding="utf-8")
            # 回读验证（窗口 16KB：R-HT 族 frontmatter 可达 5KB+，4096 会截断误判）
            check = open(fp, "rb").read().decode("utf-8", errors="ignore")[:16384]
            fm2 = FM_PATTERN.match(check).group(1)
            ok = re.search(rf"^review_date:\s*{a['review_date']}\s*$", fm2, re.MULTILINE)
            if not ok:
                raise RuntimeError("回读验证失败：review_date 未落地")
            changed += 1
            manifest.append({"file": str(rel), "card": a["name"],
                             "citations": a["citations"],
                             "review_date": a["review_date"]})
        except Exception as e:
            failed += 1
            print(f"  ❌ 失败: {a['name']} -> {e}")

    (BACKUP_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ 完成: 写入 {changed} 张，失败 {failed} 张")
    print(f"🗄  备份目录: {BACKUP_DIR}")
    print(f"📋 manifest: {BACKUP_DIR / 'manifest.json'}")
    print(f"↩️  回滚命令: cd '{BACKUP_DIR}' && rsync -a --ignore-errors ./ '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/'")


if __name__ == "__main__":
    main()
