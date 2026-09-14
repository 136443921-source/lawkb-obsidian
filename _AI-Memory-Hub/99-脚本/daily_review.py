#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
daily_review.py — AI 共享记忆中枢 · 每日复盘

固定动作：扫素材 → 去重 → 解冲突（四级漏斗） → 淘汰过期 → 出报告

用法：
  python3 daily_review.py --dry-run                 # 只出报告不落盘（默认）
  python3 daily_review.py --apply                   # 写入 04-每日日志/YYYY-MM-DD.md + 哨兵
  python3 daily_review.py --date 2026-09-13         # 指定复盘日（默认昨天）
  python3 daily_review.py --check-idempotent        # 只看某日是否已复盘（供 8 点补跑判断）

四类素材源（老强 2026-09-14 选定全开）：
  1. ~/.workbuddy/projects/               WorkBuddy 会话与项目日志
  2. LawKB/.workbuddy/memory/*.md         库内日期日志（已降级只读，只读不回写）
  3. ~/.workbuddy/automations/ + LawKB/logs/  现有 automation 运行报告
  4. ~/Desktop/小强律师办案系统/            本地交付物（**仅读文件名，不读内容**）

红线：
  - 永不自动删除/移动文件。过期条目只进「待确认归档清单」，等老强点头。
  - 个案卷宗（当事人隐私、证据原件）永不上榜，只提炼方法论。
  - 幂等：同一日期已复盘过则跳过（--skip-sentinel 可强制）。
"""
import os
import re
import io
import sys
import time
import json
import difflib
import argparse
import datetime
import collections

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser("~")
LAWKB = os.path.dirname(HUB)
SENTINEL = os.path.join(HUB, "04-每日日志", "_哨兵.md")
LOG_DIR = os.path.join(HUB, "04-每日日志")

SOURCE_WEIGHT = {
    "human": 100, "obsidian-manual": 90, "workbuddy": 60,
    "claude": 50, "codex": 50, "gemini": 40, "cursor": 40, "unknown": 10,
}
CONFIDENCE_WEIGHT = {"high": 3, "medium": 2, "low": 1}

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

SIGNALS = {
    "rule": [r"必须", r"禁止", r"铁律", r"永远不", r"不得", r"红线", r"以后都要", r"一律"],
    "preference": [r"我喜欢", r"我要", r"别用", r"改成", r"偏好", r"统一改成",
                   r"以后按这个", r"不要用", r"讨厌"],
    "decision": [r"决定", r"就这么定", r"选[ABC]", r"定为", r"改回", r"回滚为", r"否决", r"推翻"],
    "workflow": [r"跑通", r"踩坑", r"脚本", r"流水线", r"修复", r"兜底", r"fallback"],
    "project-fact": [r"案号", r"开庭", r"庭后", r"已申请", r"送达", r"结案", r"进展"],
}


def read_text(path, cap=200000):
    try:
        with io.open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(cap)
    except Exception:
        return ""


def field(raw, key):
    m = re.search(r"^%s:\s*(.+)$" % key, raw, re.MULTILINE)
    return m.group(1).strip().strip('"\'') if m else None


def norm_date(value):
    """容错：Obsidian update-time-on-edit 插件可能写成 2026-09-14T13:02，
    规范化回 YYYY-MM-DD，否则 strptime 失败会让条目被静默跳过。"""
    return str(value).split("T")[0].strip() if value else None


def parse_fm(text):
    m = FM_RE.match(text)
    if not m:
        return None, text
    return m.group(1), text[m.end():]


def recent_files(roots, since, exts=(".md",), max_files=400):
    out = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if not d.startswith(".") and d not in ("node_modules", ".git")]
            for fn in filenames:
                if not fn.endswith(exts):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if st.st_mtime >= since:
                    out.append((p, st.st_mtime, st.st_size))
                if len(out) >= max_files:
                    return sorted(out, key=lambda x: -x[1])
    return sorted(out, key=lambda x: -x[1])


def scan_sources(target_date):
    day_start = datetime.datetime.combine(target_date, datetime.time(0, 0)).timestamp()
    buckets = collections.OrderedDict()
    buckets["① WorkBuddy 会话与项目日志"] = recent_files(
        [os.path.join(HOME, ".workbuddy", "projects")], day_start)
    buckets["② LawKB 库内日期日志（只读归档）"] = recent_files(
        [os.path.join(LAWKB, ".workbuddy", "memory")], day_start)
    buckets["③ automation 运行报告"] = recent_files(
        [os.path.join(HOME, ".workbuddy", "automations"), os.path.join(LAWKB, "logs")], day_start)
    buckets["④ 桌面办案系统交付物（仅元数据）"] = recent_files(
        [os.path.join(HOME, "Desktop", "小强律师办案系统")], day_start,
        exts=(".md", ".docx", ".pdf"))
    return buckets


SENT_SPLIT = re.compile(r"[。！？\n；]")


def privacy_guard(sentence):
    risky = [
        r"\d{17}[\dXx]", r"\d{16,19}", r"1[3-9]\d{9}",
        r"[（(]20\d\d[）)]?.{0,10}民初\s*\d+号",
    ]
    return any(re.search(p, sentence) for p in risky)


def extract_candidates(buckets):
    cands, seen = [], set()
    for label, files in buckets.items():
        if label.startswith("④"):
            for p, _mt, _sz in files[:50]:
                cands.append({"type": "project-fact",
                              "sentence": "交付物更新：%s" % os.path.basename(p),
                              "source_label": label, "path": p})
            continue
        for p, _mt, _sz in files:
            text = read_text(p, cap=120000)
            for sent in SENT_SPLIT.split(text):
                s = sent.strip()
                if len(s) < 10 or len(s) > 160:
                    continue
                if s.startswith("#") or s.startswith("|"):
                    continue
                key = s[:40]
                if key in seen:
                    continue
                hit_type = None
                for t, pats in SIGNALS.items():
                    if any(re.search(pt, s) for pt in pats):
                        hit_type = t
                        break
                if not hit_type or privacy_guard(s):
                    continue
                seen.add(key)
                cands.append({"type": hit_type, "sentence": s,
                              "source_label": label, "path": p})
    return cands


def load_hub_items():
    items = []
    for dirpath, _d, files in os.walk(HUB):
        if os.path.basename(dirpath) in ("99-脚本", ".git"):
            continue
        for fn in files:
            if not fn.endswith(".md") or fn.startswith("."):
                continue
            p = os.path.join(dirpath, fn)
            text = read_text(p, cap=40000)
            raw, body = parse_fm(text)
            if raw is None:
                continue
            items.append({
                "path": p,
                "rel": os.path.relpath(p, HUB),
                "id": field(raw, "id"),
                "title": field(raw, "title") or fn,
                "type": field(raw, "type"),
                "status": (field(raw, "status") or "active").lower(),
                "updated": norm_date(field(raw, "updated")),
                "source_ai": field(raw, "source_ai") or "unknown",
                "confidence": (field(raw, "confidence") or "medium").lower(),
                "body_flat": " ".join(body.split())[:300],
            })
    return items


def dedupe(cands, hub_items):
    fresh, dup, conflict = [], [], []
    for c in cands:
        best, br = None, 0.0
        for h in hub_items:
            r = max(difflib.SequenceMatcher(None, c["sentence"], h["title"]).ratio(),
                    difflib.SequenceMatcher(None, c["sentence"], h["body_flat"]).ratio())
            if r > br:
                br, best = r, h
        rec = dict(c, ratio=round(br, 3), match=best)
        if br >= 0.82:
            dup.append(rec)
        elif br >= 0.55 and best and best["status"] == "active":
            conflict.append(rec)
        else:
            fresh.append(rec)
    return fresh, dup, conflict


def arbiter(hub_item):
    hi = hub_item
    if hi["status"] in ("deprecated", "superseded", "draft"):
        return {"winner": "candidate",
                "reason": "既有条目 status=%s（第1级出局），候选上位" % hi["status"],
                "need_human": False}
    today = datetime.date.today().isoformat()
    if (hi["updated"] or "") >= today:
        w_new, w_old = SOURCE_WEIGHT.get("workbuddy", 60), SOURCE_WEIGHT.get(hi["source_ai"], 10)
        if w_new > w_old:
            return {"winner": "candidate",
                    "reason": "updated 并列且候选来源权重 %d > 既有 %d（第3级）" % (w_new, w_old),
                    "need_human": False}
        if w_new < w_old:
            return {"winner": "hub", "reason": "既有条目来源权重更高（第3级）", "need_human": False}
        c_new, c_old = CONFIDENCE_WEIGHT["medium"], CONFIDENCE_WEIGHT.get(hi["confidence"], 2)
        if c_new > c_old:
            return {"winner": "candidate", "reason": "第4级：候选置信度更高", "need_human": False}
        return {"winner": "unknown", "reason": "四级漏斗全部平手 → ⚠️CONFLICT 需人工裁决",
                "need_human": True}
    return {"winner": "candidate", "reason": "候选为更新的事实（第2级：updated 胜出）",
            "need_human": False}


def retire_candidates(hub_items, today):
    out = []
    for h in hub_items:
        if not h["updated"]:
            continue
        try:
            d = datetime.datetime.strptime(h["updated"], "%Y-%m-%d").date()
        except ValueError:
            continue
        age = (today - d).days
        if h["status"] == "deprecated" and age > 90:
            out.append(dict(h, age=age, rule="deprecated 且 >90 天"))
        elif h["status"] == "superseded" and age > 30:
            out.append(dict(h, age=age, rule="superseded 且被替代 >30 天"))
        elif h["status"] == "active" and age > 365 and h["type"] == "project-fact":
            out.append(dict(h, age=age, rule="project-fact 超 365 天未更新（疑似结案）"))
    return sorted(out, key=lambda x: -x["age"])


def already_done(datestr):
    return os.path.isfile(SENTINEL) and datestr in read_text(SENTINEL)


def mark_done(datestr):
    existed = os.path.isfile(SENTINEL)
    with io.open(SENTINEL, "a", encoding="utf-8") as f:
        if not existed:
            f.write("# 🔔 复盘哨兵（幂等标记）\n\n"
                    "> 每行一个已完成复盘的日期。`daily_review.py` 依此避免重复执行。\n\n")
        f.write("- %s\n" % datestr)


VERDICT = {"candidate": "候选胜出", "hub": "中枢胜出", "unknown": "⚠️待人工"}


def build_report(date, buckets, cands, fresh, dup, conflict, retire, decisions):
    L = []
    L += ["---", "type: meta", "title: 每日复盘 %s" % date, "status: active",
          "updated: %s" % datetime.date.today().isoformat(), "source_ai: workbuddy",
          "scope: global", "confidence: medium", "tags:", "  - 复盘", "  - 每日日志", "---", ""]
    L.append("# 🌙 每日复盘 · %s" % date)
    L.append("")
    L.append("> 由 `99-脚本/daily_review.py` 自动生成。冲突以本中枢 `status: active` 且 `updated` 最新者为准。")
    L.append("")
    L.append("## 📊 素材扫描概况")
    L.append("")
    L.append("| 素材源 | 命中文件数 |")
    L.append("|---|---|")
    for label, files in buckets.items():
        L.append("| %s | %d |" % (label, len(files)))
    L.append("")
    L.append("提取候选事实 **%d** 条 → 新增 %d / 重复 %d / 疑似冲突 %d"
             % (len(cands), len(fresh), len(dup), len(conflict)))
    L.append("")
    L.append("## 🆕 新增候选（建议补录，尚未写入）")
    L.append("")
    if fresh:
        by_t = collections.defaultdict(list)
        for c in fresh:
            by_t[c["type"]].append(c)
        for t, cs in by_t.items():
            L.append("### %s（%d 条）" % (t, len(cs)))
            L.append("")
            for c in cs[:20]:
                L.append("- %s" % c["sentence"])
                L.append("  - `来源` %s" % c["source_label"])
            L.append("")
    else:
        L.append("_无_")
        L.append("")
    L.append("## ♻️ 重复（已存在于中枢，无需再写）")
    L.append("")
    if dup:
        for c in dup[:15]:
            L.append("- [%.2f] %s → 已存在 `%s`"
                     % (c["ratio"], c["sentence"][:50], c["match"]["id"]))
    else:
        L.append("_无_")
    L.append("")
    L.append("## ⚖️ 疑似冲突（四级漏斗裁决）")
    L.append("")
    if conflict:
        L.append("| 候选事实 | 既有条目 | 裁决 | 依据 |")
        L.append("|---|---|---|---|")
        for c, d in decisions:
            L.append("| %s | `%s` | **%s** | %s |"
                     % (c["sentence"][:60].replace("|", "/"), d["match"]["id"],
                        VERDICT.get(d["winner"], d["winner"]), d["reason"]))
        need = [d for _c, d in decisions if d.get("need_human")]
        if need:
            L.append("")
            L.append("### 📥 待裁决队列（请老强拍板）")
            L.append("")
            for c, d in decisions:
                if d.get("need_human"):
                    L.append("- ⚠️CONFLICT：「%s…」 vs `%s` %s"
                             % (c["sentence"][:40], d["match"]["id"], d["match"]["title"]))
    else:
        L.append("_无冲突_")
    L.append("")
    L.append("## 🗑 建议淘汰清单（**不会自动执行，等你点头**）")
    L.append("")
    if retire:
        L.append("| id | 标题 | 停用规则 | 静置天数 |")
        L.append("|---|---|---|---|")
        for r in retire:
            L.append("| `%s` | %s | %s | %d |" % (r["id"], r["title"], r["rule"], r["age"]))
        L.append("")
        L.append("> 确认后手动 `mv <file> 05-归档/`。**脚本不会替你删。")
    else:
        L.append("_暂无需淘汰条目_")
    L.append("")
    L.append("---")
    L.append("")
    L.append("_生成时间：%s ｜ 中枢：共享记忆协议 v1.0_"
             % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="AI 共享记忆中枢 每日复盘")
    ap.add_argument("--date", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--skip-sentinel", action="store_true")
    ap.add_argument("--check-idempotent", action="store_true")
    args = ap.parse_args()

    today = datetime.date.today()
    target = (datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
              if args.date else today - datetime.timedelta(days=1))
    dstr = target.isoformat()

    if args.check_idempotent:
        done = already_done(dstr)
        print(json.dumps({"date": dstr, "already_done": done}, ensure_ascii=False))
        return 0 if done else 1

    if already_done(dstr) and not args.skip_sentinel:
        print("⏭  %s 已复盘过（见 _哨兵.md），跳过。强制重跑加 --skip-sentinel。" % dstr)
        return 0

    t0 = time.time()
    print("🔍 复盘 %s …" % dstr)
    buckets = scan_sources(target)
    print("   扫描命中 %d 个文件" % sum(len(v) for v in buckets.values()))
    cands = extract_candidates(buckets)
    print("   提炼候选 %d 条" % len(cands))
    hub_items = load_hub_items()
    print("   装载中枢条目 %d 条" % len(hub_items))
    fresh, dup, conflict = dedupe(cands, hub_items)
    print("   新增 %d / 重复 %d / 冲突 %d" % (len(fresh), len(dup), len(conflict)))
    decisions = [(c, arbiter(c["match"])) for c in conflict if c.get("match")]
    retire = retire_candidates(hub_items, today)
    print("   建议淘汰 %d 条" % len(retire))

    report = build_report(dstr, buckets, cands, fresh, dup, conflict, retire, decisions)

    if not args.apply:
        print()
        print("=" * 68)
        print(report)
        print("=" * 68)
        print()
        print("📝 DRY-RUN：以上为拟写入内容，磁盘未变动。加 --apply 落盘到 04-每日日志/%s.md" % dstr)
        return 0

    os.makedirs(LOG_DIR, exist_ok=True)
    out = os.path.join(LOG_DIR, "%s.md" % dstr)
    with io.open(out, "w", encoding="utf-8") as f:
        f.write(report)
    mark_done(dstr)
    print("✅ 已写入：%s" % out)
    print("✅ 哨兵已标记：%s" % SENTINEL)
    print("⏱ 耗时 %.1fs" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
