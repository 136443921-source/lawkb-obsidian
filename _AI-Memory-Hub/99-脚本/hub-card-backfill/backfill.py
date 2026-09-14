#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Obsidian LawKB 共享记忆中枢 · 按需补卡助手（hub-card-backfill skill）

读一张已写好的卡，自动完成：
  ① 在该卡所在目录的 _索引.md「已沉淀」表末追加一行（wikilink 中的 | 需写成 \\| 转义）
  ② 若「待沉淀」清单有匹配本卡 id/title 的项则删除，空了则移除该节标题
  ③ 精确 git add（卡+索引）+ commit + push origin main（含 index.lock 安全重试）

仅做本地文件读写 + 用户自有仓库的 git 操作，无外部网络 / 凭据访问，可逆（git）。
"""
import os
import re
import sys
import subprocess
import argparse

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
    # 容错：2026-09-14T16:47 -> 2026-09-14（Obsidian update-time-on-edit 插件污染）
    return (d or "").split("T")[0]


def parse_index_ids(idx_path):
    """从「已沉淀」表解析 {id: 文件名(无扩展名)}，用于撞号 / 幂等判定。"""
    if not os.path.exists(idx_path):
        return {}
    out = {}
    for ln in open(idx_path, encoding="utf-8").read().splitlines():
        m = re.match(r"^\|\s*\[\[([^|\]\\]+)\\?\|([^\]]+)\]\]\s*\|\s*([^|]+?)\s*\|", ln)
        if m:
            out[m.group(3).strip()] = m.group(1).strip()
    return out


def update_index(dir_, card_path, fields):
    """更新 dir_/_索引.md：插入已沉淀行 + 删除待沉淀匹配项。
    返回 (inserted, removed)：
      inserted=True  正常插入；False 幂等跳过（同文件已存在）；None 撞号中止（未做任何改动）。
    """
    idx = os.path.join(dir_, "_索引.md")
    if not os.path.exists(idx):
        print(f"[WARN] 无索引文件 {idx}，跳过索引更新（请手动补）")
        return False, 0

    lines = open(idx, encoding="utf-8").read().splitlines(keepends=True)
    id_ = fields.get("id", "")
    title = fields.get("title", "")
    scope = fields.get("scope", "global")
    updated = norm_date(fields.get("updated", ""))
    fname = os.path.splitext(os.path.basename(card_path))[0]
    new_row = f"| [[{fname}\\|{id_}]] | {id_} | {title} | {scope} | {updated} | ✅ active |\n"

    # ── 撞号 / 幂等判定（核心安全网）────────────────────────────
    # 仅比对 id 字符串不够：并发补卡可能让不同卡片抢到同一 id。
    # 必须校验「该 id 在索引中指向的文件是否与本次卡片一致」。
    existing = parse_index_ids(idx)
    if id_ in existing:
        if existing[id_] == fname:
            print(f"[INFO] 索引已含 {id_}（同文件 {fname}），跳过重复插入（幂等）")
            return False, 0
        print(
            f"[ABORT] 撞号！索引中 {id_} 已被另一张卡片占用："
            f"{existing[id_]} ≠ {fname}。\n"
            f"        请为本次卡片改用空闲 id（参考 WF-024 取号器 next_rule_id），"
            f"严禁覆盖他人卡片。未做任何改动。"
        )
        return None, 0

    # 正常插入：定位「待沉淀」节，在它之前插入新行（保证落入已沉淀表）
    # 若其与上表间有空行，则顶掉空行，避免表格被空行截断
    pending_idx = next(
        (i for i, ln in enumerate(lines) if ln.strip().startswith("##") and "待沉淀" in ln),
        None,
    )
    if pending_idx is not None:
        insert_at = pending_idx
        if pending_idx > 0 and lines[pending_idx - 1].strip() == "":
            insert_at = pending_idx - 1
        lines.insert(insert_at, new_row)
    else:
        # 没有待沉淀节：插到最后一个表行之后
        last_table = max((i for i, ln in enumerate(lines) if ln.strip().startswith("|")), default=-1)
        if last_table >= 0:
            lines.insert(last_table + 1, new_row)
        else:
            lines.append("\n" + new_row)

    # 移除「待沉淀」中匹配 id/title 的 bullet
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
                if id_ and id_ in ln or (title and title in ln):
                    removed += 1
                    continue
                pending_has_bullet = True
        cleaned.append(ln)

    # 若待沉淀节变空（无 bullet），移除该节标题及其后空白
    if not pending_has_bullet:
        cleaned = [ln for ln in cleaned if not (ln.strip().startswith("##") and "待沉淀" in ln.strip())]
        # 清掉节标题后可能残留的连续空行（保留至多一段空行）
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


def _git(args, cwd):
    """执行一条 git 命令；遇 index.lock 阻塞则安全处理后重试一次。返回 (ok, stderr)。"""
    try:
        subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
        return True, ""
    except subprocess.CalledProcessError as e:
        stderr = e.stderr or ""
        if "index.lock" in stderr:
            lock = os.path.join(cwd, ".git", "index.lock")
            if os.path.exists(lock):
                ps = subprocess.run(["pgrep", "-fl", "git"], capture_output=True, text=True).stdout
                # 精确判定：真实在 LawKB 仓库执行 git 操作的进程
                # 注意：WorkBuddy 沙箱壳路径含 "/runtime/git/bin"，仅靠 "/git/" 会误判
                real = [l for l in ps.splitlines() if "LawKB" in l and "git" in l]
                if real:
                    return False, "[ABORT] 检测到真实 git 进程，放弃自动推送:\n" + "\n".join(real)
                try:
                    os.remove(lock)
                    print("[INFO] 已移除残留 index.lock，重试")
                    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
                    return True, ""
                except OSError as oe:
                    return False, f"[ERR] 无法移除锁：{oe}"
        return False, stderr


def git_commit_push(changed):
    repo = HUB
    # 精确 add 本次改动文件（卡 + 索引），避免误带中枢内其它遗留未提交改动
    ok1, e1 = _git(["git", "add"] + list(changed), repo)
    if not ok1:
        print("[WARN] git add 失败：" + (e1 or "")); return False
    msg = "chore(memory-hub): 按需补卡 " + ", ".join(os.path.basename(c) for c in changed)
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
    ap.add_argument("--card", required=True, help="已写好的卡片 .md 绝对路径")
    args = ap.parse_args()

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
