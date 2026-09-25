#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人伤法域库 · 方案 A 物理子目录搬移
=================================
在 06-沉淀/人伤法域库/ 内建四个子目录（医疗人损/交通人损/工伤人损/其它人损），
按各卡 frontmatter 的 sub_domain 字段物理搬移文件（保留文件名 → Obsidian wikilink
按 note 名解析，移目录不断链）。
默认 dry-run 打印计划与计数；--apply 实际搬移。
幂等：源文件已不在根目录（已搬过）则自然跳过；目标已存在且非同源则不覆盖、跳过。

用法：
  python3 move_rpi_subdir_A.py            # 默认 dry-run，仅预览
  python3 move_rpi_subdir_A.py --apply    # 实际搬移（建议先 cp 备份）
"""
import re, sys, shutil
from pathlib import Path
from datetime import datetime

V = Path("/Users/chenyouqiang/Documents/LawKB")
DOMAIN = V / "知识飞轮系统/06-沉淀/人伤法域库"
SUBDIRS = ["医疗人损", "交通人损", "工伤人损", "其它人损"]
DEFAULT_SUB = "其它人损"

def get_subdomain(fp):
    txt = fp.read_text(encoding='utf-8', errors='ignore')
    m = re.search(r"^---\n(.*?)\n---", txt, re.S)
    if not m:
        return None
    sd = re.search(r"^sub_domain:\s*(\S+)", m.group(1), re.M)
    return sd.group(1).strip() if sd else None

def main():
    apply = "--apply" in sys.argv[1:]
    print(f">>> 模式: {'APPLY（实际搬移）' if apply else 'DRY-RUN（仅预览）'}")
    files = sorted(DOMAIN.glob("R-PI-*.md"))   # 当前平铺，非递归
    print(f">>> 根目录 R-PI 文件数: {len(files)}")
    plan, counts, missing = [], {s: 0 for s in SUBDIRS}, 0
    for fp in files:
        sd = get_subdomain(fp)
        if sd not in SUBDIRS:
            if sd is None:
                missing += 1
                print(f"  ⚠ 无 sub_domain: {fp.name} → 归 {DEFAULT_SUB}")
            else:
                print(f"  ⚠ 非法 sub_domain={sd}: {fp.name} → 归 {DEFAULT_SUB}")
            sd = DEFAULT_SUB
        dst = DOMAIN / sd / fp.name
        plan.append((fp, dst, sd))
        counts[sd] += 1
    print(">>> 计划搬移计数:")
    for s in SUBDIRS:
        print(f"    {s}: {counts[s]}")
    print(f"    合计: {sum(counts.values())}  ｜ 缺失/非法 sub_domain 归默认: {missing}")
    if not apply:
        print("\n[DRY-RUN] 未做任何搬移。确认无误后加 --apply 执行。")
        return
    for s in SUBDIRS:
        (DOMAIN / s).mkdir(exist_ok=True)
    moved = skipped = 0
    for fp, dst, sd in plan:
        if dst.exists():
            if fp.resolve() == dst.resolve():
                skipped += 1
                continue
            print(f"  ✗ 目标已存在且非同源，避免覆盖跳过: {dst.name}")
            skipped += 1
            continue
        shutil.move(str(fp), str(dst))
        moved += 1
    print(f"\n>>> APPLY 完成：搬移 {moved} 个，跳过 {skipped} 个。")
    remaining_root = sorted(DOMAIN.glob("R-PI-*.md"))
    sub_total = sum(len(list((DOMAIN / s).glob("R-PI-*.md"))) for s in SUBDIRS)
    print(f">>> 根目录残留 R-PI: {len(remaining_root)} ｜ 子目录合计: {sub_total}")

if __name__ == "__main__":
    main()
