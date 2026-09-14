#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
write_back.py — AI 共享记忆中枢 · 任务后写回器

用法：
  python3 write_back.py --type preference --title "xxx" --body "yyy" --dry-run
  python3 write_back.py --type decision --title "xxx" --body-file ./a.md --source-ai human
  python3 write_back.py --type project-fact --title "xxx" --body "yyy" --scope project:吊顶案 --tags 案件,民商事

安全设计（六-B 铁律）：
  1. 默认要求 --dry-run 先行；正式写入前会做重复检测 + 冲突提示。
  2. 检测到同主题既有条目时，不静默覆盖 —— 报告冲突，要求显式加 --supersedes <旧id>。
  3. 写入前把目标索引文件 cp -n 备份到 /tmp/<对象>_备份_<时间戳>/。
  4. 写入后自动追加一行到对应 _索引.md。
"""
import os
import re
import sys
import json
import shutil
import difflib
import argparse
import datetime

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TYPE_DIR = {
    "rule": "00-全局规则",
    "preference": "01-用户偏好",
    "project-fact": "02-当前项目",
    "decision": "03-决策档案",
    "workflow": "04-Workflows",
}
TYPE_PREFIX = {
    "rule": "RULE",
    "preference": "PREF",
    "project-fact": "PROJ",
    "decision": "DEC",
    "workflow": "WF",
}
INDEX_FILE = {
    "00-全局规则": None,
    "01-用户偏好": "_索引.md",
    "02-当前项目": "_活跃项目.md",
    "03-决策档案": "_近期决策.md",
    "04-Workflows": "_索引.md",
}
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def read_field(raw, key):
    m = re.search(r"^%s:\s*(.+)$" % key, raw, re.MULTILINE)
    return m.group(1).strip().strip('"\'') if m else None


def scan_existing_ids(prefix):
    ids = []
    for root, _dirs, files in os.walk(HUB):
        if os.path.basename(root) == "05-归档":
            continue
        for f in files:
            if not f.endswith(".md"):
                continue
            p = os.path.join(root, f)
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    head = fh.read(4096)
            except Exception:
                continue
            m = FM_RE.match(head)
            if not m:
                continue
            rid = read_field(m.group(1), "id")
            if rid and rid.startswith(prefix):
                ids.append(rid)
    return ids


def next_id(prefix):
    """分配下一个 id：扫描全库同前缀，取数字最大值 +1，永不复用"""
    nums = []
    for rid in scan_existing_ids(prefix):
        tail = rid[len(prefix):].lstrip("-")
        digits = re.findall(r"\d+", tail)
        if digits:
            nums.append(int(digits[-1]))
    base = max(nums) if nums else 0
    return "%s-%03d" % (prefix, base + 1)


def find_similar(title, directory):
    """返回同目录下标题相似度 >= 0.5 的既有条目"""
    hits = []
    dpath = os.path.join(HUB, directory)
    if not os.path.isdir(dpath):
        return hits
    for f in os.listdir(dpath):
        if not f.endswith(".md"):
            continue
        p = os.path.join(dpath, f)
        with open(p, "r", encoding="utf-8") as fh:
            head = fh.read(4096)
        m = FM_RE.match(head)
        if not m:
            continue
        raw = m.group(1)
        t = read_field(raw, "title") or f
        ratio = difflib.SequenceMatcher(None, title, t).ratio()
        if ratio >= 0.5:
            hits.append({
                "file": f,
                "title": t,
                "id": read_field(raw, "id"),
                "status": read_field(raw, "status"),
                "updated": read_field(raw, "updated"),
                "similarity": round(ratio, 3),
            })
    return sorted(hits, key=lambda x: -x["similarity"])


def backup(target_rel_paths):
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dstdir = "/tmp/hub_writeback_备份_%s" % ts
    os.makedirs(dstdir, exist_ok=True)
    backed = []
    for rel in target_rel_paths:
        src = os.path.join(HUB, rel)
        if os.path.isfile(src):
            dst = os.path.join(dstdir, rel.replace("/", "__"))
            shutil.copy2(src, dst) if not os.path.exists(dst) else None
            backed.append(dst)
    return dstdir, backed


def slugify(title):
    s = re.sub(r"[\\/:*?\"<>|\[\]]", "", title)
    s = re.sub(r"\s+", "-", s.strip())
    return s[:40] or "untitled"


def build_content(args, new_id):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
    fm = ["---"]
    fm.append("id: %s" % new_id)
    fm.append("title: %s" % args.title)
    fm.append("type: %s" % args.type)
    fm.append("status: active")
    fm.append("updated: %s" % today)
    fm.append("source_ai: %s" % (args.source_ai or "unknown"))
    fm.append("scope: %s" % (args.scope or "global"))
    fm.append("confidence: %s" % (args.confidence or "medium"))
    if args.supersedes:
        fm.append("supersedes: %s" % args.supersedes)
    if args.expires:
        fm.append("expires: %s" % args.expires)
    if tags:
        fm.append("tags:")
        for t in tags:
            fm.append("  - %s" % t)
    fm.append("---")
    fm.append("")
    fm.append("# %s" % args.title)
    fm.append("")
    if args.body_file:
        with open(args.body_file, "r", encoding="utf-8") as fh:
            body = fh.read()
    else:
        body = args.body or ""
    fm.append(body.strip())
    fm.append("")
    return "\n".join(fm)


def append_index(directory, new_id, title, updated, scope):
    """把新条目追加到该目录的索引文件"""
    idxname = INDEX_FILE.get(directory)
    if not idxname:
        return None
    ipath = os.path.join(HUB, directory, idxname)
    if not os.path.isfile(ipath):
        return None
    with open(ipath, "r", encoding="utf-8") as f:
        text = f.read()
    row = "| [[%s|%s]] | %s | %s | %s | ✅ active |" % (
        slugify(title), new_id, title, scope, updated)
    if new_id in text:
        return ipath
    # 插到表格最后一行之后
    lines = text.split("\n")
    last_pipe = None
    for i, ln in enumerate(lines):
        if ln.startswith("|"):
            last_pipe = i
    insert_at = (last_pipe + 1) if last_pipe is not None else len(lines)
    lines.insert(insert_at, row)
    with open(ipath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return ipath


def main():
    ap = argparse.ArgumentParser(description="AI 共享记忆中枢 写回器")
    ap.add_argument("--type", required=True, choices=sorted(TYPE_DIR.keys()))
    ap.add_argument("--title", required=True)
    ap.add_argument("--body", help="条目正文")
    ap.add_argument("--body-file", help="从文件读取正文")
    ap.add_argument("--source-ai", default=None,
                    choices=["human", "obsidian-manual", "workbuddy", "claude",
                             "codex", "gemini", "cursor", "unknown"])
    ap.add_argument("--scope", default="global")
    ap.add_argument("--confidence", default="medium", choices=["high", "medium", "low"])
    ap.add_argument("--tags", default="")
    ap.add_argument("--supersedes", default=None, help="显式声明取代哪个旧 id")
    ap.add_argument("--expires", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="相似度 >=0.85 时仍要写入（会在报告里说明）")
    args = ap.parse_args()

    if not args.body and not args.body_file:
        ap.error("必须提供 --body 或 --body-file")

    directory = TYPE_DIR[args.type]
    prefix = TYPE_PREFIX[args.type]
    new_id = next_id(prefix)
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    similar = find_similar(args.title, directory)

    print("=" * 68)
    print("✍️  write_back · %s" % ("DRY-RUN（未写入）" if args.dry_run else "正式写入"))
    print("=" * 68)
    print("目标目录  : %s" % directory)
    print("分配 id   : %s（全库同前缀最大值 +1）" % new_id)
    print("标题      : %s" % args.title)
    print("type/scope: %s / %s" % (args.type, args.scope))
    print("source_ai : %s ｜ confidence: %s ｜ updated: %s"
          % (args.source_ai or "unknown", args.confidence, today))
    print("-" * 68)

    blocked = False
    if similar:
        print("🔍 重复检测：发现 %d 个相似条目" % len(similar))
        for s in similar:
            flag = ""
            if s["similarity"] >= 0.85:
                flag = "  ⚠️ 高度相似 —— 大概率重复"
            print("   • [%s] %s  (status=%s, updated=%s, 相似度=%.2f)%s"
                  % (s["id"], s["title"], s["status"], s["updated"], s["similarity"], flag))
        top = similar[0]
        if top["similarity"] >= 0.85 and not args.supersedes and not args.force:
            print()
            print("⛔ 拦截：标题相似度 %.2f ≥ 0.85。" % top["similarity"])
            print("   中枢原则：禁止静默覆盖。请三选一：")
            print("   1) 若是更新该条目 → 加 --supersedes %s" % top["id"])
            print("   2) 若确实是新条目 → 加 --force 并改个更精确的标题")
            print("   3) 直接改既有条目（recommended，保持 id 不变、仅抬 updated）")
            blocked = True
    else:
        print("🔍 重复检测：无相似条目 ✅")

    print("-" * 68)
    content = build_content(args, new_id)
    print("📄 拟写入内容预览（前 15 行）：")
    for ln in content.split("\n")[:15]:
        print("   " + ln)
    print("-" * 68)

    if blocked:
        print("❌ 未写入（被重复检测拦截）。解决后重试。")
        return 2

    if args.dry_run:
        print("✅ DRY-RUN 完成，磁盘未发生任何写入。确认无误后去掉 --dry-run 执行。")
        return 0

    # ---- 正式写入：先备份 ----
    targets = [os.path.join(directory, INDEX_FILE[directory])] if INDEX_FILE.get(directory) else []
    bkdir, backed = backup(targets)

    slug_title = slugify(args.title)
    fname = "%s-%s.md" % (new_id, slug_title)
    fpath = os.path.join(HUB, directory, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)

    idxp = append_index(directory, new_id, args.title, today, args.scope)

    # 若声明了 supersedes，把旧条目标为 superseded
    if args.supersedes:
        for root, _d, files in os.walk(HUB):
            for ff in files:
                if not ff.endswith(".md"):
                    continue
                p = os.path.join(root, ff)
                with open(p, "r", encoding="utf-8") as fh:
                    txt = fh.read()
                if ("id: %s\n" % args.supersedes) in txt or ("id: %s " % args.supersedes) in txt[:200]:
                    new = txt.replace("status: active", "status: superseded", 1)
                    # 在 frontmatter 结束符前插入反向指针
                    new = re.sub(r"\n---\n", "\nsuperseded_by: %s\n---\n" % new_id, new, count=1)
                    if new != txt:
                        with open(p, "w", encoding="utf-8") as fh:
                            fh.write(new)
                        print("🔗 旧条目 %s 已标记 superseded_by=%s（%s）"
                              % (args.supersedes, new_id, p))

    print("✅ 已写入：%s" % fpath)
    if idxp:
        print("✅ 索引已更新：%s" % idxp)
    print("🗂 备份目录：%s（共 %d 个文件）" % (bkdir, len(backed)))
    print()
    print("💡 提醒：若内容冲突，请以本中枢 status=active 且 updated 最新者为准。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
