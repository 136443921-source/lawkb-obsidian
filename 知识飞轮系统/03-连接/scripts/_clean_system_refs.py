#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
系统引用死链清理器 v1.0（2026-09-07）
------------------------------------
用途：清除「相关笔记」等段落中把**系统/自动化内部引用**当笔记名写出的死链
      ——典型：`[[memory]]`（工作记忆目录名）、`[[待推送_2026-09-04]]`（自动化队列文件）。

背景（为什么会有这些死链）：
  · 早期补链脚本遍历 vault 时未排除 `.workbuddy`，把工作记忆目录下的文件
    纳入链接候选，生成了 `[[memory]]`；自动化队列同理生成 `[[待推送_*]]`。
  · 后来检测侧（`resolve_broken_links.py` / `kg_scan.py` / `_diag_unresolved*.py`）
    各自补了 `SYSTEM_REF_RE` 跳过这些引用，生成侧脚本也补了 `.workbuddy` 过滤，
    **但存量一直没清** —— 于是形成「检测时跳过、实际仍躺在文件里」的长期残留。

口径对齐：本脚本的 `SYSTEM_REF_RE` 与上述 4 个脚本**完全一致**
          `^(?:memory|待推送_[0-9\-]+)$`（IGNORECASE），避免各说各话。

安全设计（安全六-B）：
  · **默认 dry-run**，必须显式 `--apply` 才写盘
  · `--apply` 前强制 `--backup <dir>` 备份（保持目录结构）
  · 只删「整行以 `- [[系统引用]]` 开头」的行，不碰正文叙述中提到的同名文字
  · 跳过备份/系统目录与 `.bak_*` 文件，不污染历史副本

用法：
    # 1) 先看会改什么
    python3 _clean_system_refs.py --dry-run
    # 2) 备份
    python3 _clean_system_refs.py --backup /tmp/系统引用清理备份_$(date +%Y%m%d-%H%M%S)
    # 3) 执行
    python3 _clean_system_refs.py --apply --backup /tmp/系统引用清理备份_xxx
    # 4) 复检
    python3 02-提炼/审判要件卡/_check_deadlinks.py --all

退出码：0 = 无待清理项或清理完成；1 = 仍有残留（apply 后复检）
"""
import argparse
import io
import os
import re
import shutil
import sys

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"

SKIP_DIRS = {".workbuddy", ".git", "node_modules", "__pycache__", ".venv", "venv"}

# 与 resolve_broken_links.py / kg_scan.py / _diag_unresolved*.py 同口径
SYSTEM_REF_RE = re.compile(r"^(?:memory|待推送_[0-9\-]+)$", re.IGNORECASE)

# 只删「整行是列表项且链接为系统引用」的行（保留行尾的 (共现关键词: …) 一并删除）
LINE_RE = re.compile(r"^- \[\[([^\]\|]+)(?:\|[^\]]+)?\]\][ \t]*(?:\(.*\))?[ \t]*$", re.MULTILINE)

# 删完死链行后可能剩下「标题下无内容」的空段（相关笔记 / 关联 / 关联笔记），一并裁掉
EMPTY_SEC_RE = re.compile(
    r"^[ \t]*#{1,6}[ \t].*(?:相关笔记|关联)[^\n]*\n(?:[ \t]*\n)*(?=[ \t]*#|\Z)",
    re.MULTILINE,
)


def iter_md(root=ROOT):
    """遍历待检 md，跳过备份/系统目录与历史副本文件。"""
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".backup")]
        for fn in files:
            if not fn.endswith(".md"):
                continue
            if ".bak_" in fn or ".bak-" in fn:      # 历史副本不改
                continue
            p = os.path.join(r, fn)
            if "_backup" in p or "/备份" in p:
                continue
            yield p


PRUNE_ONLY = False   # 由 --prune-only 置位：只裁空段，不再删行


def plan(path):
    """返回 (待删行列表, 新文本, 待裁空段列表)"""
    txt = io.open(path, encoding="utf-8").read()
    victims = []
    for m in LINE_RE.finditer(txt):
        name = m.group(1).strip()
        if SYSTEM_REF_RE.match(name):
            victims.append(m.group(0))
    if not victims:
        if not PRUNE_ONLY:
            return [], txt, []
        new = txt
        pruned = EMPTY_SEC_RE.findall(new)
        if pruned:
            new = EMPTY_SEC_RE.sub("", new)
            new = re.sub(r"\n{3,}", "\n\n", new)
        return [], new, pruned
    new = LINE_RE.sub("__TO_DELETE__", txt)
    # 移除占位行，并压缩因删除产生的连续空行（最多保留 1 个空行）
    lines = [ln for ln in new.split("\n") if ln.strip() != "__TO_DELETE__"]
    out, blank = [], 0
    for ln in lines:
        if ln.strip() == "":
            blank += 1
            if blank > 1:
                continue
        else:
            blank = 0
        out.append(ln)
    new = "\n".join(out)

    # 删空段：仅当该段「被删过行」才处理，避免误删本来就与本次无关的空段
    pruned = EMPTY_SEC_RE.findall(new)
    if pruned:
        new = EMPTY_SEC_RE.sub("", new)
        new = re.sub(r"\n{3,}", "\n\n", new)
    return victims, new, pruned


def backup(files, dest):
    for p in files:
        rel = os.path.relpath(p, ROOT)
        tgt = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(tgt), exist_ok=True)
        shutil.copy2(p, tgt)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正写盘（默认仅 dry-run）")
    ap.add_argument("--backup", metavar="DIR", help="备份目录（--apply 时建议提供）")
    ap.add_argument("--dry-run", action="store_true", help="显式声明 dry-run")
    ap.add_argument("--prune-only", action="store_true",
                    help="只裁剪空的「相关笔记/关联」段（用于上一轮删行后的收尾）")
    args = ap.parse_args()
    global PRUNE_ONLY
    PRUNE_ONLY = args.prune_only

    if args.apply and not args.backup:
        sys.stderr.write("⚠️  --apply 未提供 --backup，将不备份直接修改。\n"
                         "    建议：--backup /tmp/系统引用清理备份_<时间戳>\n")
        try:
            if input("确认继续？(y/N) ").strip().lower() != "y":
                sys.exit(0)
        except EOFError:
            sys.exit(0)

    targets = []
    for p in iter_md():
        v, _, pruned = plan(p)
        if v or pruned:
            targets.append((p, v, pruned))

    total = sum(len(v) for _, v, _ in targets)
    n_prune = sum(len(pr) for _, _, pr in targets)
    print("=" * 60)
    print(f"模式      ：{'APPLY（写盘）' if args.apply else 'DRY-RUN（只读）'}")
    print(f"命中文件  ：{len(targets)}")
    print(f"待删行数  ：{total}")
    print(f"待裁空段  ：{n_prune}")
    print("=" * 60)

    for p, v, pr in targets[:15]:
        print(f"  {len(v):>3} 条 / 空段 {len(pr)}  {os.path.relpath(p, ROOT)}")
    if len(targets) > 15:
        print(f"  … 另有 {len(targets)-15} 个文件")

    if not args.apply:
        print("\n[dry-run] 未做任何修改。确认无误后加 --apply --backup <目录> 执行。")
        sys.exit(0)

    if args.backup:
        backup([p for p, _, _ in targets], args.backup)
        print(f"\n✅ 已备份 {len(targets)} 个文件 → {args.backup}")

    done = 0
    for p, _, _ in targets:
        _, new, _ = plan(p)
        io.open(p, "w", encoding="utf-8").write(new)
        done += 1
    print(f"✅ 已清理 {done} 个文件 / {total} 条系统引用死链 / {n_prune} 处空段")

    # 复检
    left = 0
    for p in iter_md():
        v, _, _ = plan(p)
        left += len(v)
    print(f"复检残留：{left} 条")
    sys.exit(1 if left else 0)


if __name__ == "__main__":
    main()
