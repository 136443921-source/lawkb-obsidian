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

# ── 索引撞号/幂等门禁（与 backfill.py 共用 index_guard 单一真源，见经验卡 EXP-2026-001）──
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "hub-card-backfill"))
import index_guard

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


def _id_pattern(rid, prefix):
    """提取 id 的「格式签名」：纯数字段替换为 N。

    DEC-2026-007 -> DEC-N-N ／ DEC-006 -> DEC-N ／ PREF-007 -> PREF-N
    """
    tail = rid[len(prefix):].lstrip("-")
    segs = tail.split("-") if tail else []
    return prefix + "-" + "-".join(
        "N" if re.fullmatch(r"\d+", s) else s for s in segs
    )


def _is_incrementable(rid, prefix):
    """最后一段是否含数字（可被 +1 递增）。"""
    body = rid[len(prefix):].lstrip("-")
    segs = body.split("-") if body else []
    return bool(segs) and bool(re.search(r"\d+", segs[-1]))


def _next_in_group(rids, prefix):
    """给定同格式、末段可递增的一组 id，返回其 +1 结果（宽度对齐末段数字）。"""
    sample = max(rids)  # 字典序最大 ⇒ 年份/序号最新
    body = sample[len(prefix):].lstrip("-")
    segs = body.split("-")
    last = segs[-1]
    m = re.search(r"\d+", last)
    if not m:
        return None
    num = int(m.group())
    width = m.end() - m.start()
    new_last = last[:m.start()] + str(num + 1).zfill(width) + last[m.end():]
    segs[-1] = new_last
    return prefix + "-" + "-".join(segs)


def next_id(prefix, directory=None):
    """分配下一个 id（v3 · 2026-09-15 修复「末段非数字 / 多格式并列取错主流」）。

    事故复盘（v2 的不足）：
      • RULE 目录下唯一条目 `RULE-TRAINING-WRITEBACK-技能训练记录回写铁律` 末段为
        中文非数字 → v2 把数字 zfill 到中文串长度 → 产出
        `RULE-TRAINING-WRITEBACK-0000000001` 这种荒谬 id（"报错/乱号"）。
      • PROJ 目录下 `PROJ-N`（PROJ-001/002）与 `PROJ-LAW-N`（PROJ-LAW-6658/6660）
        各 2 条并列，v2 按「签名更长者」取主流 → 误产 `PROJ-LAW-6661`，
        偏离通用新项目应有的 `PROJ-003`。

    新规则（v3）：
      ① 双源取并集（文件系统 ∪ 索引），防漏登记撞号。
      ② **只从「末段可递增」的格式组里挑主流**，避免选中纯文本末段导致乱号。
      ③ 主流排序：条目数最多 → 段数更少（更通用）→ 签名更短（确定性 tie-break）。
      ④ 组内对样本末段数字 +1，保持宽度对齐，其余段（如年份）照抄样本。
      ⑤ 若所有现存 id 末段均非数字（如纯自由文本 RULE）：回退 `PREFIX-001`
         并自增避让，保证唯一不撞号。
    """
    cands = set(scan_existing_ids(prefix))  # 文件系统（全库，排除 05-归档）
    if directory:
        idx = INDEX_FILE.get(directory)
        if idx:
            ip = os.path.join(HUB, directory, idx)
            if os.path.isfile(ip):
                try:
                    cands |= {i for i in index_guard.parse_index_ids(ip)
                              if i.startswith(prefix)}
                except Exception:
                    pass
    cands = {c for c in cands if c.startswith(prefix + "-")}
    if not cands:
        return "%s-%03d" % (prefix, 1)

    # ② 分组 + 区分「末段可递增」与「不可递增（纯文本末段）」
    incr, non_incr = {}, {}
    for rid in cands:
        bucket = incr if _is_incrementable(rid, prefix) else non_incr
        bucket.setdefault(_id_pattern(rid, prefix), []).append(rid)

    if incr:
        # ③ 主流格式：条目最多 → 段数更少（更通用）→ 签名更短（确定性 tie-break）
        def _score(kv):
            pat, items = kv
            return (len(items), -len(pat.split("-")), -len(pat))
        pat = max(incr.items(), key=_score)[0]
        nxt = _next_in_group(incr[pat], prefix)
        if nxt:
            return nxt

    # ⑤ 全不可递增（或递增组异常）→ 回退 PREFIX-NNN 并自增避让，保证唯一不撞号
    i = 1
    while "%s-%03d" % (prefix, i) in cands:
        i += 1
    return "%s-%03d" % (prefix, i)


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


def append_index(directory, fname, new_id, title, updated, scope):
    """把新条目追加到该目录的索引文件（经 index_guard 门禁）。
    返回 ipath；若撞号(collision)则打印 ABORT 警告并跳过本次写入（绝不覆盖他人卡）。"""
    idxname = INDEX_FILE.get(directory)
    if not idxname:
        return None
    ipath = os.path.join(HUB, directory, idxname)
    if not os.path.isfile(ipath):
        return None
    # ── 撞号 / 幂等门禁（单一真源 index_guard，见 EXP-2026-001）──
    gate = index_guard.index_gate(ipath, fname, new_id)
    if gate == "idempotent":
        print("  索引门禁：%s 已由同文件占用，幂等跳过" % new_id)
        return ipath
    if gate == "collision":
        print("  ⚠️ [ABORT] 撞号：%s 已被另一卡片占用，本次不写入索引（绝不覆盖他人卡）。" % new_id)
        return None
    row = index_guard.build_row(fname, new_id, title, scope, updated)
    index_guard.insert_row(ipath, row, before_pending=True)
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
    new_id = next_id(prefix, directory)
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
    fname_noext = "%s-%s" % (new_id, slug_title)
    fpath = os.path.join(HUB, directory, fname)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)

    idxp = append_index(directory, fname_noext, new_id, args.title, today, args.scope)

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
    elif idxp is None:
        print("⚠️ 索引写回被门禁跳过（撞号保护），卡片已落盘但未入索引，请人工核对。")
    print("🗂 备份目录：%s（共 %d 个文件）" % (bkdir, len(backed)))
    print()
    print("💡 提醒：若内容冲突，请以本中枢 status=active 且 updated 最新者为准。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
