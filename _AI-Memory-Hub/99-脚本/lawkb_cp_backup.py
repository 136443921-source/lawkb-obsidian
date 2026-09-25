#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lawkb_cp_backup.py — LawKB 单源重建时间戳 cp 备份（防覆盖）

纪律依据（老强铁律）：
- cp 备份铁律：单源文件重建前必须 cp 备份，防覆盖
- cp -n 防覆盖：已存在则跳过，绝不静默覆盖
- dry-run 优先：先打印将要执行的命令，确认无虞再实跑

用途：LawKB 独立仓库作为「法人核心资产单源」，提供时间戳快照，
供中枢/仓库意外损坏时单源重建。不碰系统配置、不回传外网。

要点：默认排除 git/插件缓存/垃圾等派生目录（这些由 git 或应用自身
恢复，不该进「单源重建」快照），只备份真实知识资产。

用法：
    python3 lawkb_cp_backup.py                 # 实跑，备份到 /tmp
    python3 lawkb_cp_backup.py --dry-run       # 只打印，不执行
    python3 lawkb_cp_backup.py --dest ~/backups # 指定目标根目录
    python3 lawkb_cp_backup.py --src 09-OPC     # 只备份某子目录（单源聚焦）
"""
import os
import sys
import argparse
import datetime
import subprocess

SRC = "/Users/chenyouqiang/Documents/LawKB"
DEFAULT_DEST = "/tmp"

# 派生/缓存/版本内部目录：由 git 或应用自身恢复，不进单源重建快照
EXCLUDE = {
    ".git", ".obsidian", ".trash", ".vault-coach", ".learnings",
    ".workbuddy", ".DS_Store", "node_modules", ".cache",
}


def cp_n(src, dest, dry):
    """cp -nR：防覆盖递归复制。已存在的条目跳过。"""
    cmd = ["cp", "-nR", src, dest]
    if dry:
        print(f"[DRY-RUN] {' '.join(cmd)}")
        return 0
    r = subprocess.run(cmd, capture_output=True, text=True)
    # BSD cp -n 在目标存在时静默跳过（returncode 0）；仅打印真实错误
    if r.returncode != 0 and r.stderr.strip() and "not overwrite" not in r.stderr:
        print(f"[ERR] {cmd}\n{r.stderr}", file=sys.stderr)
        return r.returncode
    return 0


def main():
    ap = argparse.ArgumentParser(description="LawKB 时间戳 cp 备份（cp -n 防覆盖）")
    ap.add_argument("--dry-run", action="store_true", help="只打印命令不执行")
    ap.add_argument("--dest", default=DEFAULT_DEST, help="目标根目录（默认 /tmp）")
    ap.add_argument("--src", default="", help="只备份 SRC 下的子目录（如 09-OPC），留空备份整仓真实资产")
    args = ap.parse_args()

    base = SRC if not args.src else os.path.join(SRC, args.src)
    if not os.path.isdir(base):
        print(f"[FATAL] 源不存在: {base}", file=sys.stderr)
        return 2

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    tag = (f"LawKB_{args.src.replace('/', '_')}_backup_{ts}"
           if args.src else f"LawKB_backup_{ts}")
    dest = os.path.join(args.dest, tag)
    print(f"源: {base}")
    print(f"目标: {dest}" + ("  [DRY-RUN]" if args.dry_run else ""))

    if not args.dry_run:
        os.makedirs(dest, exist_ok=True)

    names = sorted(os.listdir(base))
    skipped = 0
    copied = 0
    excluded = 0
    for name in names:
        if name in EXCLUDE:
            print(f"[EXCLUDE] 派生目录跳过: {name}")
            excluded += 1
            continue
        s = os.path.join(base, name)
        d = os.path.join(dest, name)
        if os.path.exists(d):
            print(f"[SKIP] 已存在，跳过: {d}")
            skipped += 1
            continue
        rc = cp_n(s, dest, args.dry_run)
        if rc == 0:
            print(f"[OK] {name}")
            copied += 1
    print(f"完成: 复制 {copied} 项，跳过 {skipped} 项，排除派生 {excluded} 项"
          + ("  [DRY-RUN]" if args.dry_run else f"\n快照: {dest}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
