#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
read_hub.py — AI 共享记忆中枢 · 任务前装载器

用法：
    python3 read_hub.py --brief          # 精简装载（推荐，约 200 行内）
    python3 read_hub.py --full           # 全文装载（含全部规则正文）
    python3 read_hub.py --json           # JSON 输出，便于其它 AI 解析
    python3 read_hub.py --only 01        # 只装载某个目录（01=用户偏好）
    python3 read_hub.py --check          # 只做健康检查，不输出内容

设计：零依赖、纯标准库，任何设备 python3 可直接跑。
"""
import os
import re
import sys
import json
import datetime

HUB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 装载顺序：规则 → 偏好 → 项目 → 决策 → 昨日日志
LOAD_ORDER = [
    ("00-全局规则", "🧾 全局规则"),
    ("01-用户偏好", "💗 用户偏好"),
    ("02-当前项目", "🗂 活跃项目"),
    ("03-决策档案", "⚖️ 决策档案"),
]

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
STATUS_RE = re.compile(r"^status:\s*(\S+)", re.MULTILINE)
UPDATED_RE = re.compile(r"^updated:\s*([\d-]+)", re.MULTILINE)
TITLE_RE = re.compile(r"^title:\s*(.+)$", re.MULTILINE)
TYPE_RE = re.compile(r"^type:\s*(\S+)", re.MULTILINE)
ID_RE = re.compile(r"^id:\s*(\S+)", re.MULTILINE)


def field(raw, key):
    m = re.search(r"^%s:\s*(.+)$" % key, raw, re.MULTILINE)
    return m.group(1).strip().strip('"\'') if m else None


def norm_date(value):
    """容错：Obsidian 的 update-time-on-edit 插件可能把日期写成
    2026-09-14T13:02，规范化回 YYYY-MM-DD，避免仲裁/淘汰逻辑失效。"""
    if not value:
        return value
    return str(value).split("T")[0].strip()


def parse_frontmatter(text):
    m = FM_RE.match(text)
    if not m:
        return {}, text
    raw = m.group(1)
    meta = {}
    for key in ("id", "title", "type", "status", "updated", "source_ai",
                "scope", "confidence", "supersedes", "superseded_by",
                "deprecated_reason", "expires"):
        km = re.search(r"^%s:\s*(.+)$" % key, raw, re.MULTILINE)
        if km:
            meta[key] = km.group(1).strip().strip('"\'')
    if meta.get("updated"):
        meta["updated"] = norm_date(meta["updated"])
    body = text[m.end():]
    return meta, body


def list_md(directory):
    if not os.path.isdir(directory):
        return []
    return sorted(f for f in os.listdir(directory)
                  if f.endswith(".md") and not f.startswith("."))


def is_effective(meta):
    """仅 status=active（或缺省）才算有效；守护 dropped / deprecated 条目不误导 AI"""
    st = meta.get("status", "active").lower()
    if st in ("deprecated", "superseded", "draft"):
        return False
    exp = meta.get("expires")
    if exp:
        try:
            if datetime.datetime.strptime(exp, "%Y-%m-%d").date() < datetime.date.today():
                return False
        except ValueError:
            pass
    return True


def truncate(text, limit=60):
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[:limit] + "…"


def collect(directory, want_full=False, body_limit=60):
    out = []
    for fname in list_md(directory):
        path = os.path.join(directory, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            out.append({"file": fname, "error": str(e), "effective": False})
            continue
        meta, body = parse_frontmatter(text)
        out.append({
            "file": fname,
            "meta": meta,
            "effective": is_effective(meta),
            "body": body.strip() if want_full else truncate(body, body_limit),
        })
    return out


def yesterday_log():
    y = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    p = os.path.join(HUB, "04-每日日志", "%s.md" % y)
    if os.path.isfile(p):
        with open(p, "r", encoding="utf-8") as f:
            return y, f.read()
    return y, None


def render_text(results, want_full=False):
    lines = []
    lines.append("=" * 68)
    lines.append("🧠 AI 共享记忆中枢 · 已装载上下文")
    lines.append("   中枢：%s" % HUB)
    lines.append("   时间：%s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("=" * 68)

    for dname, label in LOAD_ORDER:
        if dname not in results:
            continue
        items = results[dname]
        eff = [i for i in items if i.get("effective")]
        stale = [i for i in items if not i.get("effective")]
        lines.append("")
        lines.append("── %s（%s）── %d 条有效 / %d 条已失效" % (label, dname, len(eff), len(stale)))
        for i in eff:
            m = i["meta"]
            lines.append("")
            lines.append("  【%s】%s" % (m.get("id", "?"), m.get("title", i["file"])))
            lines.append("     updated=%s | source=%s | scope=%s | confidence=%s"
                         % (m.get("updated", "?"), m.get("source_ai", "?"),
                            m.get("scope", "?"), m.get("confidence", "?")))
            body = i["body"]
            if want_full:
                for bl in body.splitlines():
                    lines.append("     %s" % bl)
            else:
                lines.append("     %s" % body)
        if stale:
            lines.append("")
            lines.append("  ⛔ 已失效（不执行）：%s"
                         % ", ".join("%s(%s)" % (i["meta"].get("id", "?"),
                                                 i["meta"].get("status", "?"))
                                     for i in stale))

    y, ylog = yesterday_log()
    lines.append("")
    lines.append("── 📅 昨日日志（%s）──" % y)
    if ylog:
        lines.append(ylog.rstrip())
    else:
        lines.append("   （无）")

    lines.append("")
    lines.append("=" * 68)
    lines.append("✅ 装载完成。任务结束请执行 write_back.py 写回新增事实。")
    lines.append("=" * 68)
    return "\n".join(lines)


def health_check(results):
    ok, warn, err = [], [], []
    total = 0
    for dname, _ in LOAD_ORDER:
        for i in results.get(dname, []):
            total += 1
            m = i["meta"]
            for req in ("id", "title", "type", "status", "updated", "source_ai"):
                if not m.get(req):
                    err.append("%s/%s 缺必填字段 %s" % (dname, i["file"], req))
            if i.get("effective") is False:
                warn.append("%s/%s 状态为 %s，已排除" % (dname, i["file"], m.get("status")))
    return {"total": total, "errors": err, "warnings": warn, "ok": not err}


def main():
    argv = sys.argv[1:]
    want_full = "--full" in argv
    as_json = "--json" in argv
    only = None
    for a in argv:
        if a.startswith("--only="):
            only = a.split("=", 1)[1]
        elif a == "--only" and argv.index(a) + 1 < len(argv):
            only = argv[argv.index(a) + 1]

    results = {}
    targets = LOAD_ORDER if not only else [(d, l) for d, l in LOAD_ORDER if d.startswith(only)]
    for dname, _ in targets:
        results[dname] = collect(os.path.join(HUB, dname), want_full or as_json)

    if "--check" in argv:
        print(json.dumps(health_check(results), ensure_ascii=False, indent=2))
        return 0 if health_check(results)["ok"] else 1

    if as_json:
        y, ylog = yesterday_log()
        print(json.dumps({"hub": HUB, "sections": results, "yesterday": {"date": y, "log": ylog}},
                         ensure_ascii=False, indent=2))
    else:
        print(render_text(results, want_full))
    return 0


if __name__ == "__main__":
    sys.exit(main())
