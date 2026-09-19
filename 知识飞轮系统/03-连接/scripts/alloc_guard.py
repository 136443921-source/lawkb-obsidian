#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
alloc_guard.py —— P0-4 编号治理·取号双保险门禁（防御性纵深）

====================================================================
背景（2026-09-18 实证撞号事故）
--------------------------------------------------------------------
裁量尺度卡第六批取号时用了裸 `find` 取 LD 056~061，但本日 08:37 已有
「通用裁判规则卡 R-LD-056-工伤与第三人侵权竞合」在**取号流程外直接落盘**
占用了 056 → 09:11 本批落盘时撞号，违反取号铁律。

根因：`next_rule_id.py` 的 24h 预留只防「同样走取号器的并发流水线」，
挡不住两类撞号：
  ① 取号流程外直接建卡（工伤卡 R-LD-056 即此例）；
  ② 取号 → 落盘之间的时间窗口（并行/外部会话插入）。

解法（老强拍板，P0-4 编号治理）：在取号器预留之外，再加两道物理闸——
  ① **写入前最后一刻再 find 一次**（不看预留文件，直接查磁盘）—— catch 任何
     已落盘的同号卡（含流程外建卡）；
  ② **写入后回查同域重号**—— catch 任何漏网的重复 rule_id / 文件名号。
构成「预留 + 物理 find + 回查」三道防线。

====================================================================
用法
--------------------------------------------------------------------
# 1) 落盘前最后一刻 find（预检，任何已落盘同号即 abort，exit 2）
python3 alloc_guard.py pre  --domain LD --nums 057 058 059 060 061 062
python3 alloc_guard.py pre  --domain WT --range 001 004

# 2) 落盘后回查同域重号（post，exit 2 表示有重复/缺号）
python3 alloc_guard.py post --domain LD --nums 057 058 059 060 061 062
# 或直接对刚写的文件列表校验（同时核对每个文件的 rule_id/文件名号==预期）：
python3 alloc_guard.py post --domain LD --files f1.md f2.md ...

退出码：0 通过 ｜ 2 发现冲突（可接 CI / 交付门禁，与 rule_id_guard.py 口径一致）
====================================================================
"""

import os
import re
import sys
import argparse
import subprocess

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库"

# 文件名口径：R-{域}-{号}-...
FILE_RE = re.compile(r'^(R-([A-Z]{2})-(\d{1,4}))-')
# frontmatter rule_id 口径：只看首段 frontmatter 的 rule_id:
RULE_ID_RE = re.compile(r'^rule_id:\s*"?\s*(R-([A-Z]{2})-(\d{1,4}))', re.M)


def _collect_paths(root, domain):
    """快速定位 `R-{domain}-*.md`，排除备份/隐藏目录（避免慢 + 误占）。

    用 find 做 C 级目录遍历（不读文件内容），再回退 os.walk 仅比文件名。
    只返回文件名已命中 `R-{domain}-` 前缀的路径，后续再读这些文件的头部即可。
    """
    pat = f"R-{domain}-*.md"
    try:
        out = subprocess.run(
            ["find", root, "-not", "-path", "*/.*", "-name", pat],
            capture_output=True, text=True, timeout=60,
        )
        paths = [p for p in out.stdout.splitlines() if p.strip()]
    except Exception:
        paths = []
    if not paths:  # find 不可用/超时 → 回退 os.walk（仅比文件名，不读内容）
        for dp, _, fs in os.walk(root):
            if "/." in dp:
                continue
            for fn in fs:
                if fn.startswith(f"R-{domain}-") and fn.endswith(".md"):
                    paths.append(os.path.join(dp, fn))
    return paths


def scan_domain(root, domain):
    """返回 {号str: [文件路径...]}。

    占用判定双口径（任一命中即视为该号已被占）：
      - 文件名前缀为 `R-{domain}-{号}-`；
      - frontmatter `rule_id:` 为 `R-{domain}-{号}`。
    仅对文件名已命中的少量文件读头部，避免全库逐文件读取（性能关键）。
    """
    occ = {}
    for fp in _collect_paths(root, domain):
        fn = os.path.basename(fp)
        fm = FILE_RE.match(fn)
        fm_num = fm.group(3) if (fm and fm.group(2) == domain) else None
        try:
            with open(fp, 'r', encoding='utf-8') as fh:
                head = fh.read(4096)
        except Exception:
            head = ''
        rm = RULE_ID_RE.search(head)
        rm_num = rm.group(3) if (rm and rm.group(2) == domain) else None
        for num in {x for x in (fm_num, rm_num) if x}:
            occ.setdefault(num, [])
            if fp not in occ[num]:
                occ[num].append(fp)
    return occ


def normalize_nums(nums, rng):
    if rng:
        start, end = int(rng[0]), int(rng[1])
        if start > end:
            start, end = end, start
        # 至少补零到 3 位（R-NNN 命名惯例），若输入本身更长则跟随
        pad = max(3, len(rng[0]))
        return [str(n).zfill(pad) for n in range(start, end + 1)]
    # --nums：保留用户传入的位数；1~2 位补零到 3 位（R-NNN 惯例）
    out = []
    for n in nums:
        n = str(n)
        out.append(n.zfill(3) if len(n) <= 2 else n)
    return out


def cmd_pre(args):
    occ = scan_domain(args.root, args.domain)
    nums = normalize_nums(args.nums, args.range)
    collisions = [(n, occ[n]) for n in nums if n in occ]
    if collisions:
        print("🔴 PRE-WRITE 冲突：以下号已在磁盘落盘，禁止写入（最后一刻 find 拦截）：")
        for n, fps in collisions:
            print(f"  R-{args.domain}-{n} 被占用：")
            for fp in fps:
                print(f"    └─ {fp}")
        print(f"\n→ 请重新取号（让出已被占用的号），不要覆盖既有卡。")
        sys.exit(2)
    print(f"✅ PRE-WRITE 通过：R-{args.domain}-{{{', '.join(nums)}}} 磁盘上均空闲（最后一刻 find OK）")
    sys.exit(0)


def cmd_post(args):
    occ = scan_domain(args.root, args.domain)
    nums = normalize_nums(args.nums, args.range) if (args.nums or args.range) else []
    problems = []

    # ① 每个预期号必须恰好 1 个文件，否则缺号或重号
    for n in nums:
        files = occ.get(n, [])
        if not files:
            problems.append(f"R-{args.domain}-{n}: 写入后未找到（落盘失败？）")
        elif len(files) > 1:
            problems.append(f"R-{args.domain}-{n}: 同号重复 {len(files)} 个文件 → {files}")

    # ② 若给了 --files，逐一核对其 rule_id 与文件名号 == 预期，且不被其他文件共用
    if args.files:
        for fp in args.files:
            fn = os.path.basename(fp)
            fm = FILE_RE.match(fn)
            expected = None
            if fm and fm.group(2) == args.domain:
                expected = fm.group(3)
            try:
                with open(fp, 'r', encoding='utf-8') as fh:
                    head = fh.read(4096)
            except Exception as e:
                problems.append(f"{fp}: 无法读取（{e}）")
                continue
            rm = RULE_ID_RE.search(head)
            rid_num = rm.group(3) if (rm and rm.group(2) == args.domain) else None
            if expected and rid_num and expected != rid_num:
                problems.append(f"{fp}: 文件名号 {expected} ≠ rule_id 号 {rid_num}")
            if rid_num and len(occ.get(rid_num, [])) > 1:
                problems.append(f"{fp}: rule_id R-{args.domain}-{rid_num} 与 {occ[rid_num]} 同号冲突")

    if problems:
        print("🔴 POST-WRITE 回查失败：")
        for p in problems:
            print(f"  - {p}")
        sys.exit(2)
    print(f"✅ POST-WRITE 通过：R-{args.domain}-{{{', '.join(nums)}}} 同域无重号、落盘齐全")
    sys.exit(0)


def main():
    ap = argparse.ArgumentParser(description="P0-4 编号治理·取号双保险门禁")
    ap.add_argument("--root", default=ROOT, help="裁判规则库根目录")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_pre = sub.add_parser("pre", help="写入前最后一刻 find：同号已落盘则 abort")
    p_pre.add_argument("--domain", required=True, help="域码，如 LD / WT")
    p_pre.add_argument("--nums", nargs="+", help="预期号列表，如 057 058 059")
    p_pre.add_argument("--range", nargs=2, metavar=("START", "END"), help="号段，如 001 004")
    p_pre.set_defaults(func=cmd_pre)

    p_post = sub.add_parser("post", help="写入后回查同域重号")
    p_post.add_argument("--domain", required=True)
    p_post.add_argument("--nums", nargs="+")
    p_post.add_argument("--range", nargs=2, metavar=("START", "END"))
    p_post.add_argument("--files", nargs="+", help="直接校验这些刚写的文件")
    p_post.set_defaults(func=cmd_post)

    args = ap.parse_args()
    if not args.nums and not args.range and args.cmd == "pre":
        ap.error("pre 模式需 --nums 或 --range")
    if not args.nums and not args.range and not args.files and args.cmd == "post":
        ap.error("post 模式需 --nums / --range / --files 之一")
    args.func(args)


if __name__ == "__main__":
    main()
