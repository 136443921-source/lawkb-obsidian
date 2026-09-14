#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Obsidian LawKB 共享记忆中枢 · 按需补卡助手（hub-card-backfill skill）

读一张已写好的卡，自动完成：
  ① 在该卡所在目录的 _索引.md「已沉淀」表末追加一行（wikilink 中的 | 需写成 \\| 转义）
  ② 若「待沉淀」清单有匹配本卡 id/title 的项则删除，空了则移除该节标题
  ③ 精确 git add（卡+索引）+ commit + push origin main（含 index.lock 安全重试）

索引撞号/幂等门禁统一复用 index_guard.py（单一真源，见经验卡 EXP-2026-001）。
凡对中枢的 git 提交一律经本文件的 _run_git() 安全通道（PREF-006 强制）。
"""
import os
import re
import sys
import subprocess
import argparse
from index_guard import parse_index_ids, build_row, insert_row, index_gate

HUB = "/Users/chenyouqiang/Documents/LawKB"
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.S)
FIELD_RE = re.compile(r"^([\w-]+):\s*(.+)$", re.M)


def read_frontmatter(path):
    text = open(path, encoding="utf-8").read()
    m = FRONTMATTER_RE.search(text)
    if not m:
        raise SystemExit(f"[ERR] 找不到 frontmatter: {path}")
    fm = m.group(1)
    fields = {}
    for line in fm.splitlines():
        mm = FIELD_RE.match(line)
        if mm:
            fields[mm.group(1)] = mm.group(2).strip()
    return fields


def norm_date(d):
    return (d or "").split("T")[0]


def update_index(dir_, card_path, fields):
    idx = os.path.join(dir_, "_索引.md")
    if not os.path.exists(idx):
        print(f"[WARN] 无索引文件 {idx}，跳过索引更新（请手动补）")
        return False, 0
    id_ = fields.get("id", "")
    title = fields.get("title", "")
    scope = fields.get("scope", "global")
    updated = norm_date(fields.get("updated", ""))
    fname = os.path.splitext(os.path.basename(card_path))[0]
    gate = index_gate(idx, fname, id_)
    if gate == "collision":
        occ = parse_index_ids(idx).get(id_)
        print(
            f"[ABORT] 撞号！索引中 {id_} 已被另一张卡片占用："
            f"{occ} ≠ {fname}。请改用空闲 id（参考 WF-024 取号器），严禁覆盖他人卡片。未做任何改动。"
        )
        return None, 0
    if gate == "idempotent":
        print(f"[INFO] 索引已含 {id_}（同文件 {fname}），跳过重复插入（幂等）")
        return False, 0
    new_row = build_row(fname, id_, title, scope, updated)
    insert_row(idx, new_row, before_pending=True)
    lines = open(idx, encoding="utf-8").read().splitlines(keepends=True)
    cleaned = []
    in_pending = False
    pending_has_bullet = False
    removed = 0
    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("##") and "待沉淀" in stripped:
            in_pending = True
            cleaned.append(ln)
            continue
        if in_pending and stripped.startswith("##") and "待沉淀" not in stripped:
            in_pending = False
        if in_pending:
            if stripped.startswith("-"):
                if (id_ and id_ in ln) or (title and title in ln):
                    removed += 1
                    continue
                pending_has_bullet = True
        cleaned.append(ln)
    if not pending_has_bullet:
        cleaned = [ln for ln in cleaned if not (ln.strip().startswith("##") and "待沉淀" in ln.strip())]
        out_lines = []
        blank = 0
        for ln in cleaned:
            if ln.strip() == "":
                blank += 1
                if blank <= 1:
                    out_lines.append(ln)
            else:
                blank = 0
                out_lines.append(ln)
        cleaned = out_lines
    open(idx, "w", encoding="utf-8").write("".join(cleaned))
    print(f"[OK] 索引更新：插入新行=是，移除待沉淀 {removed} 项")
    return True, removed


def _locate_lock(cwd):
    try:
        git_dir = subprocess.check_output(
            ["git", "rev-parse", "--git-dir"], cwd=cwd, text=True
        ).strip()
    except Exception:
        git_dir = ".git"
    return os.path.abspath(os.path.join(cwd, git_dir, "index.lock"))


def _lock_holder(lock):
    """True=有其它进程真实持有 lock（不应硬删）；False=无持有者（可安全删）。"""
    # 优先用 lsof 直接看文件持有者——能识别 WorkBuddy sandbox-cli 托管的 git 子进程
    try:
        out = subprocess.run(["lsof", lock], capture_output=True, text=True).stdout
        if out.strip():
            return True
    except Exception:
        pass
    # 兜底：pgrep 命中含 LawKB+git 的进程（旧逻辑）
    try:
        ps = subprocess.run(["pgrep", "-fl", "git"], capture_output=True, text=True).stdout
        if any("LawKB" in l and "git" in l for l in ps.splitlines()):
            return True
    except Exception:
        pass
    return False


def _git(args, cwd):
    try:
        subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
        return True, ""
    except subprocess.CalledProcessError as e:
        stderr = e.stderr or ""
        if "index.lock" not in stderr:
            return False, stderr
        lock = _locate_lock(cwd)
        last_err = stderr
        for attempt in range(3):
            if not os.path.exists(lock):
                # 锁已不在（并发可能已释放），直接重试命令
                try:
                    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
                    return True, ""
                except subprocess.CalledProcessError as e2:
                    last_err = e2.stderr or ""
                    if "index.lock" not in last_err:
                        return False, last_err
                    continue
            if _lock_holder(lock):
                return False, "[ABORT] 检测到真实 git 进程持有 index.lock，放弃自动推送（请等其释放后重试）：%s" % lock
            try:
                os.remove(lock)
            except OSError as oe:
                return False, f"[ERR] 无法移除锁：{oe}"
            print("[INFO] 已移除残留 index.lock（%s），重试(%d)" % (lock, attempt + 1))
            try:
                subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
                return True, ""
            except subprocess.CalledProcessError as e2:
                last_err = e2.stderr or ""
                if "index.lock" not in last_err:
                    return False, last_err
                continue
        return False, last_err or "retry_exhausted_after_lock_removal"


def git_commit_push(changed, message=None):
    repo = HUB
    ok1, e1 = _git(["git", "add"] + list(changed), repo)
    if not ok1:
        print("[WARN] git add 失败：" + (e1 or "")); return False
    msg = message or ("chore(memory-hub): 按需补卡 " + ", ".join(os.path.basename(c) for c in changed))
    ok2, e2 = _git(["git", "commit", "-q", "-m", msg], repo)
    if not ok2:
        print("[WARN] git commit 失败：" + (e2 or "")); return False
    ok3, e3 = _git(["git", "push", "origin", "main"], repo)
    if not ok3:
        print("[WARN] git push 失败（索引已更新，请手动检查）：" + (e3 or "")); return False
    print("[OK] git 已 add + commit + push 到 origin/main")
    return True


def main():
    ap = argparse.ArgumentParser(description="Obsidian LawKB 中枢按需补卡助手")
    ap.add_argument("--card", help="已写好的卡片 .md 绝对路径（补卡模式）")
    ap.add_argument("--files", nargs="+", help="直接提交指定文件（通用模式，统一走 _run_git 安全通道，遵守 PREF-006）")
    ap.add_argument("--message", help="提交信息")
    args = ap.parse_args()
    if args.files:
        ok = git_commit_push(
            args.files,
            args.message or "chore(memory-hub): 中枢维护提交（统一走 backfill._run_git 通道）",
        )
        print("[DONE] 通用提交完成" if ok else "[DONE] 提交通道失败，请检查")
        return
    if not args.card:
        raise SystemExit("[ERR] 必须指定 --card（补卡）或 --files（通用提交）")
    card = args.card
    if not os.path.exists(card):
        raise SystemExit(f"[ERR] 卡片不存在: {card}")
    fields = read_frontmatter(card)
    if not fields.get("id"):
        raise SystemExit("[ERR] 卡片 frontmatter 缺少 id")
    d = os.path.dirname(os.path.abspath(card))
    inserted, removed = update_index(d, card, fields)
    if inserted is None:
        raise SystemExit("[ABORT] 撞号中止，未提交。请改用空闲 id 后重试。")
    ok = git_commit_push([card, os.path.join(d, "_索引.md")])
    print("[DONE] 补卡流程完成" if ok else "[DONE] 索引已更新，但 git 推送未自动完成（请手动检查）")


if __name__ == "__main__":
    main()
