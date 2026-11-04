#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_registry_sync.py —— 清单挂载自检器  v1.0
配套规则卡：WF-132-清单挂载自检（写文件时扫「新增了 X，该加 X 的清单没加」）

背景（2026-11-02）：
    把 `execution-docs-generator` 挂进 CLM 时，同一轮文件里出现两处"漏挂"：
      ① 标题已写 v2.1.0，变更日志表末行却停在 v2.0.5 —— 版本号与日志脱节
      ② §4.6 新增了技能，§4.3「其余类似法律智能体（全部纳入·10 项）」表里没加
    共同点：**新增了 X，但"该加 X 的清单"没跟上**。
    这两类错误肉眼极难发现（表就在旁边，但没人去数行数、没人去比对版本号末位）。

四项检查：
    1. COUNT  计数一致 —— 正文声明"N 项" vs 该表实际数据行数        → 🔴 FAIL
    2. VLOG   版本一致 —— frontmatter version vs 标题 vs 变更日志末行 → 🔴 FAIL
    3. TWIN   同源一致 —— 配置声明的同源文档，右段标识符覆盖率        → 🟠 WARN
    4. ORPHAN 全集漏挂 —— 全文高频实体 vs 全集表已登记实体（--deep）  → 🟠 WARN

设计取舍（吸取 check_mirror_staleness v1.0 误报 15/17 的教训）：
    - COUNT / VLOG 为纯机械比对，**零容忍、不设阈值**，报了就是真错
    - TWIN 用**单向覆盖率**（右段内容应能在左段找到），不用 Jaccard
      —— 因为一侧常是详述、另一侧是摘要，双向比对必然报错
    - ORPHAN 误报面最大，**默认关闭**，须显式 --deep；且定位为"提示人工确认"，不阻断

用法：
    python3 check_registry_sync.py                    # 扫默认目标（CLM 目录）
    python3 check_registry_sync.py --file X.md        # 只扫单文件（写入后自检）
    python3 check_registry_sync.py --deep             # 加开 ORPHAN 漏挂检查
    python3 check_registry_sync.py --json             # 机读输出
    python3 check_registry_sync.py --quiet            # 只报错不报通过项

退出码：0 全清 ｜ 1 有 WARN ｜ 2 有 FAIL

作者：小强（WorkBuddy）  2026-11-02
"""
import os
import re
import sys
import json
import argparse

# ─────────────────────────── 配置区 ───────────────────────────

# 默认扫描目标（目录递归 *.md）
DEFAULT_TARGETS = [
    "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统",
    "/Users/chenyouqiang/Documents/LawKB/_AI-Memory-Hub/04-Workflows",
]

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".obsidian",
             "05-归档", "_backups", ".trash"}

# 同源文档对：一侧改动必须同步另一侧。覆盖率 = 右段标识符在左段中出现的比例
TWINS = [
    {
        "name": "执行文书生成技能定义（运维手册 §4.6 ↔ SOP 表 5）",
        "left": {
            "file": "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/"
                    "00-运维手册-案件生命周期管理系统.md",
            "anchor": "### 4.6 执行文书生成技能",
        },
        "right": {
            "file": "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/"
                    "02-智能体路由与生命周期SOP清单.md",
            "anchor": "### 表 5 · 执行文书生成技能配置",
        },
        # 实体差集判定：右段出现的具名实体（技能/连接器/脚本名）若左段完全没有，
        # 即报漂移。不用覆盖率——比例阈值对"只加一两条"根本不敏感。
        "allow_missing": [],
    },
]

# COUNT 检查：正文声明"N 项"的写法
DECL_PATTERNS = [
    r"以上\s*(\d+)\s*项",
    r"共\s*(\d+)\s*项",
    r"全部纳入[·・\-一 ]*(\d+)\s*项",
    r"(\d+)\s*项\s*(?:全部纳入|全纳入|已全部纳入)",
    r"全部为\s*(\d+)\s*项",
]

# 标题括号内的计数：如「…（全部纳入·11 项）」「…（4 项）及应对」
# 🔴 只在**标题行**采信。正文里「（1 项）（2 项）」常是并列列举，
#    当作声明会让 6 篇文书集体误报（2026-11-02 实测）。
HEADING_DECL_PAT = r"[（(][^（()）\n]{0,24}?(\d+)\s*项[^（()）\n]{0,24}?[）)]"

# ORPHAN 检查的黑名单：技术通用词 / 目录名，不算"应登记实体"
ENTITY_BLACKLIST = {
    "case-state", "case-state.json", "meta.agents", "meta", "agents",
    "lti", "clm", "sop", "api", "mcp", "json", "yaml", "yml", "docx",
    "xlsx", "pptx", "pdf", "md", "py", "sh", "html", "css", "js",
    "reject", "pass", "todo", "active", "status", "version", "updated",
    "created", "tags", "type", "scope", "rule_id", "frontmatter",
    "workbuddy", "obsidian", "github", "npm", "python3", "pip",
    "gate-config", "adapter.md", "skill.md", "readme.md", "memory.md",
    "g0", "g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8", "g9",
    "g9-a", "g9-b", "l1", "l2", "l3", "p0", "p1", "p2",
    # 目录名 / 非实体标识（2026-11-02 实测噪音）
    "_local-patches", "artifacts", "scripts", "references", "assets",
    "workflows", "templates", "skills", "plugins", "cache",
}

# 视为"文件而非实体"的后缀
FILE_SUFFIX = (".md", ".json", ".py", ".yaml", ".yml", ".sh",
               ".html", ".htm", ".css", ".js", ".txt", ".toml",
               ".ini", ".log", ".csv", ".db", ".lock")

# "具名实体"形态：kebab-case（至少两段连字符），或已知连接器后缀。
# 用于把 `case-file-review`（技能名）与 `statute_text_pending`（代码字段）
# 区分开——首版不区分，--deep 报出的 5 条全是字段名，属噪音（2026-11-02 实测）。
ENTITY_NAME_PAT = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$")


# ─────────────────────────── 基础工具 ───────────────────────────

def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def iter_md_files(target):
    """target 可以是文件或目录"""
    if os.path.isfile(target):
        yield target
        return
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if fn.endswith(".md"):
                yield os.path.join(root, fn)


def is_table_row(line):
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 2


def is_sep_row(line):
    """表格分隔行 |---|---|"""
    s = line.strip()
    if not is_table_row(s):
        return False
    body = s.strip("|")
    return bool(re.fullmatch(r"[\s:\-|]+", body)) and "-" in body


def parse_tables(lines):
    """
    返回表格块列表：{start, end, header, rows:[(lineno, cells)], ncols}
    start/end 为 0-based 行下标（end 为最后一行数据行下标）
    """
    tables = []
    i = 0
    n = len(lines)
    while i < n:
        if is_table_row(lines[i]) and not is_sep_row(lines[i]):
            start = i
            j = i
            block = []
            while j < n and is_table_row(lines[j]):
                block.append((j, lines[j]))
                j += 1
            if len(block) >= 2 and is_sep_row(block[1][1]):
                header = split_cells(block[0][1])
                rows = [(ln, split_cells(txt)) for ln, txt in block[2:]]
                rows = [(ln, c) for ln, c in rows if any(x.strip() for x in c)]
                tables.append({
                    "start": start,
                    "end": block[-1][0],
                    "header": header,
                    "rows": rows,
                    "ncols": len(header),
                })
                i = j
                continue
        i += 1
    return tables


def split_cells(line):
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    # 保护转义竖线
    s = s.replace("\\|", "\x00")
    cells = [c.strip().replace("\x00", "|") for c in s.split("|")]
    return cells


def strip_code_ticks(s):
    return s.replace("`", "").strip()


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def coverage(right, left):
    """右段标识符有多少能在左段找到"""
    if not right:
        return 1.0
    return len(right & left) / len(right)


TOKEN_PAT = re.compile(r"`([A-Za-z_~/][A-Za-z0-9._\-/~]{2,})`")
ARTICLE_PAT = re.compile(r"第\s*\d+\s*条")


def extract_tokens(text, with_articles=False):
    """
    抽英文标识符（+ 可选法条号），用于同源比对。

    法条号默认排除：同源文档往往一详一略——详述侧讲机制、摘要侧列全法条，
    把法条纳入比对会稳定误报（2026-11-02 实测 §4.6 vs 表 5 覆盖率被拉到 17%）。
    """
    toks = set()
    for m in TOKEN_PAT.finditer(text):
        t = m.group(1).strip()
        # 路径取末段
        if "/" in t:
            t = t.rstrip("/").split("/")[-1]
        if len(t) >= 3:
            toks.add(t.lower())
    if with_articles:
        for m in ARTICLE_PAT.finditer(text):
            toks.add(re.sub(r"\s+", "", m.group(0)))
    return toks


def section_text(text, anchor):
    """取锚点标题起、到下一个同级或更高级标题之前的正文"""
    lines = text.split("\n")
    idx = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith(anchor.strip()):
            idx = i
            break
    if idx is None:
        return None
    m = re.match(r"^(#+)", lines[idx].strip())
    level = len(m.group(1)) if m else 3
    out = [lines[idx]]
    for ln in lines[idx + 1:]:
        s = ln.strip()
        mm = re.match(r"^(#+)\s", s)
        if mm and len(mm.group(1)) <= level:
            break
        out.append(ln)
    return "\n".join(out)


# ─────────────────────────── 检查一：COUNT ───────────────────────────

# 豁免词：这些行里出现的"N 项"是在**叙述**而非**声明**
COUNT_EXEMPT = ("误报", "示例", "例如", "举例", "比如", "旧版", "原写", "曾写")

# 引述符号：紧跟其后的"N 项"是被引用的字符串，不是真声明
QUOTE_CHARS = "「『\"'`"

def check_count(path, text):
    """
    正文声明"N 项" vs 该表实际数据行数

    方向判定（v1.0 → v1.1 修正）：
      - 声明写在**标题行**里（如「### 4.3 其余类似法律智能体（全部纳入·11 项）」）
        → 它描述的是**该标题下的表**，须**向下**找
      - 声明写在**正文**里（表格下方的「以上 N 项全部纳入」）
        → 须**向上**找最近一张表
      首版一律向上找，导致标题声明错配到上一节的表，误报（2026-11-02 实测）。

    豁免（v1.2）：
      - 表格行内的"N 项"是**数据**，不是对某张表的元声明 → 跳过
      - 引号内的（「（全部纳入·11 项）」）是**引述** → 跳过
      - 含"误报/示例/例如"等词的行是**叙述** → 跳过
      以上三条均由 WF-132 自身被误报触发（误报样本库那两行里就引用了这个字符串）。
    """
    findings = []
    seen = set()
    lines = text.split("\n")
    tables = parse_tables(lines)

    for pat, heading_only in [(p, False) for p in DECL_PATTERNS] + [(HEADING_DECL_PAT, True)]:
        for m in re.finditer(pat, text):
            declared = int(m.group(1))
            lineno = text[:m.start()].count("\n")
            raw = lines[lineno].strip()
            is_heading = bool(re.match(r"^#{1,6}\s", raw))

            # 括号计数只在标题行采信
            if heading_only and not is_heading:
                continue
            # 豁免一：表格行内是数据
            if raw.startswith("|"):
                continue
            # 豁免二：引述
            if any(c in text[max(0, m.start() - 3):m.start()] for c in QUOTE_CHARS):
                continue
            # 豁免三：叙述性行
            if any(w in raw for w in COUNT_EXEMPT):
                continue

            if is_heading:
                cand = [t for t in tables if t["start"] > lineno]
                if not cand:
                    continue
                tbl = min(cand, key=lambda t: t["start"])
                if tbl["start"] - lineno > 15:
                    continue
            else:
                cand = [t for t in tables if t["end"] < lineno]
                if not cand:
                    continue
                tbl = max(cand, key=lambda t: t["end"])
                if lineno - tbl["end"] > 60:
                    continue

            actual = len(tbl["rows"])
            key = (lineno, declared, actual)
            if key in seen:
                continue
            seen.add(key)

            if actual != declared:
                findings.append({
                    "kind": "COUNT",
                    "level": "FAIL",
                    "path": path,
                    "line": lineno + 1,
                    "msg": f"声明 {declared} 项，表格实际 {actual} 行"
                           f"（表在 {tbl['start'] + 1} 行，"
                           f"{'标题内声明→向下找表' if is_heading else '正文声明→向上找表'}）",
                    "declared": declared,
                    "actual": actual,
                })
    return findings


# ─────────────────────────── 检查二：VLOG ───────────────────────────

VLOG_HEAD_PAT = re.compile(r"^#{1,4}\s*.*(变更日志|版本记录|版本历史|更新日志|修订记录)")


def check_vlog(path, text):
    """frontmatter version vs 标题 version vs 变更日志末行 version"""
    findings = []
    lines = text.split("\n")

    # 1) frontmatter version
    fm_ver = None
    if lines and lines[0].strip() == "---":
        for ln in lines[1:]:
            if ln.strip() == "---":
                break
            m = re.match(r"^version:\s*([\d.]+)", ln.strip())
            if m:
                fm_ver = m.group(1)
                break
    if not fm_ver:
        return findings  # 无 frontmatter version，不检查

    # 2) 大标题里的 version
    title_ver = None
    for ln in lines:
        if ln.startswith("# "):
            m = re.search(r"v(\d+\.\d+(?:\.\d+)?)", ln)
            if m:
                title_ver = m.group(1)
            break

    # 3) 变更日志表末行版本
    log_ver = None
    log_line = None
    for i, ln in enumerate(lines):
        if VLOG_HEAD_PAT.match(ln):
            seg = "\n".join(lines[i:])
            seg_lines = seg.split("\n")
            tbls = parse_tables(seg_lines)
            if tbls:
                t = tbls[0]
                if t["rows"]:
                    last_no, cells = t["rows"][-1]
                    m = re.search(r"v?(\d+\.\d+(?:\.\d+)?)", cells[0])
                    if m:
                        log_ver = m.group(1)
                        log_line = i + last_no + 1
            break

    def norm(v):
        return v if not v else v.rstrip(".")

    checks = []
    if title_ver and norm(title_ver) != norm(fm_ver):
        checks.append(("标题", title_ver, fm_ver))
    if log_ver and norm(log_ver) != norm(fm_ver):
        checks.append(("变更日志末行", log_ver, fm_ver))

    for where, got, want in checks:
        findings.append({
            "kind": "VLOG",
            "level": "FAIL",
            "path": path,
            "line": log_line or 1,
            "msg": f"版本号不一致：frontmatter={want}，{where}={got}",
            "got": got,
            "want": want,
        })
    return findings


# ─────────────────────────── 检查三：TWIN ───────────────────────────

def check_twins(scanned=None):
    """
    同源一致性：右段（摘要侧）的标识符应都能在左段（详述侧）找到。

    局限（必须知道，别指望它全能）：
      它只抓「摘要里出现了详述没有的新东西」＝**新增型漂移**。
      反过来「悄悄从摘要里删了一行」不会触发——删内容只会让覆盖率上升。
      删行只能靠 COUNT（表标题写"N 项"）或人工兜。

    v1.0 → v1.1 修正：原固定读配置路径，--file 传入副本时测不到。
    现改为**按锚点定位**——先在被扫描内容里找含该锚点的文件，找不到才回落到配置路径。
    """
    scanned = scanned or {}
    findings = []

    def pick(cfg):
        key = cfg["anchor"].strip()
        for p, t in scanned.items():
            if key in t:
                return p, t, True
        t = read_text(cfg["file"])
        return cfg["file"], t, False

    for tw in TWINS:
        lp, lt, lok = pick(tw["left"])
        rp, rt, rok = pick(tw["right"])
        if lt is None or rt is None:
            findings.append({
                "kind": "TWIN", "level": "WARN", "path": tw["left"]["file"],
                "line": 0,
                "msg": f"同源检查「{tw['name']}」：文件不可读，跳过",
            })
            continue

        lseg = section_text(lt, tw["left"]["anchor"])
        rseg = section_text(rt, tw["right"]["anchor"])
        if lseg is None:
            findings.append({
                "kind": "TWIN", "level": "WARN", "path": lp, "line": 0,
                "msg": f"同源检查「{tw['name']}」：左段锚点未找到"
                       f"（{tw['left']['anchor']}）",
            })
            continue
        if rseg is None:
            findings.append({
                "kind": "TWIN", "level": "WARN", "path": rp, "line": 0,
                "msg": f"同源检查「{tw['name']}」：右段锚点未找到"
                       f"（{tw['right']['anchor']}）",
            })
            continue

        ltoks = extract_tokens(lseg)
        rtoks = extract_tokens(rseg)
        allow = {a.lower() for a in tw.get("allow_missing", [])}
        missing = sorted(t for t in (rtoks - ltoks) if t not in allow)

        if missing:
            findings.append({
                "kind": "TWIN", "level": "WARN", "path": rp, "line": 0,
                "msg": f"同源漂移「{tw['name']}」：右段出现左段没有的实体 → "
                       f"{'、'.join(missing[:8])}"
                       f"（要么补进左段详述，要么加进 allow_missing 并注明理由）",
                "missing": missing,
            })
        else:
            findings.append({
                "kind": "TWIN", "level": "OK", "path": rp, "line": 0,
                "msg": f"同源一致「{tw['name']}」：右段 {len(rtoks)} 个实体全部可在左段印证",
            })
    return findings


# ─────────────────────────── 检查四：ORPHAN ───────────────────────────

def check_orphan(path, text):
    """
    全集漏挂：全文高频实体 vs 已进任何清单表的实体

    判定口径（v1.0 → v1.1 修正）：
      - registered 取**全文所有表格**前两列的具名实体，而不是只认"自称全集"的表。
        首版只认含「全部纳入/其余类似」字样的表，导致已登记在表 4 的
        `case-file-review` 被误报成漏挂（2026-11-02 实测）。
      - orphans = 全文出现 ≥3 次的英文标识符 − registered
    """
    findings = []
    lines = text.split("\n")
    tables = parse_tables(lines)
    if not tables:
        return findings

    registered = set()
    for t in tables:
        for _ln, cells in t["rows"]:
            for cell in cells[:2]:
                for m in TOKEN_PAT.finditer(cell):
                    v = m.group(1).strip().lower()
                    if "/" in v:
                        v = v.rstrip("/").split("/")[-1]
                    if len(v) >= 3:
                        registered.add(v)
                base = re.split(r"[\s（(]", strip_code_ticks(cell))[0].strip()
                if base:
                    registered.add(base.lower())

    freq = {}
    for m in TOKEN_PAT.finditer(text):
        t = m.group(1).strip().lower()
        if "/" in t:
            t = t.rstrip("/").split("/")[-1]
        if len(t) < 4:
            continue
        if t in ENTITY_BLACKLIST:
            continue
        if t.endswith(FILE_SUFFIX):
            continue
        # 只认具名实体（kebab-case），排除 snake_case 代码字段
        if not ENTITY_NAME_PAT.match(t):
            continue
        freq[t] = freq.get(t, 0) + 1

    orphans = {k: v for k, v in freq.items()
               if v >= 3 and k not in registered
               and not any(k in r or r in k for r in registered)}

    if orphans:
        top = sorted(orphans.items(), key=lambda x: -x[1])[:10]
        findings.append({
            "kind": "ORPHAN", "level": "WARN", "path": path, "line": 0,
            "msg": "疑似漏挂（高频提及但未进任何清单表，请人工确认）："
                   + "、".join(f"`{k}`×{v}" for k, v in top),
            "orphans": dict(top),
        })
    return findings


# ─────────────────────────── 主流程 ───────────────────────────

def run(targets, deep=False, quiet=False):
    all_findings = []
    scanned = 0
    scanned_map = {}

    for tgt in targets:
        for path in iter_md_files(tgt):
            text = read_text(path)
            if text is None:
                continue
            scanned += 1
            scanned_map[path] = text
            all_findings.extend(check_count(path, text))
            all_findings.extend(check_vlog(path, text))
            if deep:
                all_findings.extend(check_orphan(path, text))

    all_findings.extend(check_twins(scanned_map))
    return all_findings, scanned


LEVEL_MARK = {"FAIL": "🔴 FAIL", "WARN": "🟠 WARN", "OK": "✅ OK"}


def main():
    ap = argparse.ArgumentParser(description="清单挂载自检器")
    ap.add_argument("--file", action="append", default=None,
                    help="只扫指定文件（可多次）")
    ap.add_argument("--deep", action="store_true", help="加开 ORPHAN 漏挂检查")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    ap.add_argument("--quiet", action="store_true", help="只报 FAIL/WARN")
    args = ap.parse_args()

    targets = args.file if args.file else DEFAULT_TARGETS
    findings, scanned = run(targets, deep=args.deep, quiet=args.quiet)

    fails = [f for f in findings if f["level"] == "FAIL"]
    warns = [f for f in findings if f["level"] == "WARN"]

    if args.json:
        print(json.dumps({
            "scanned": scanned,
            "fail": len(fails),
            "warn": len(warns),
            "findings": findings,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"清单挂载自检 · 扫描 {scanned} 个文件 · "
              f"FAIL={len(fails)} WARN={len(warns)}")
        print("─" * 64)
        shown = [f for f in findings
                 if not args.quiet or f["level"] in ("FAIL", "WARN")]
        if not shown:
            print("✅ 全部通过")
        for f in shown:
            loc = os.path.basename(f["path"])
            line = f" :{f['line']}" if f.get("line") else ""
            print(f"{LEVEL_MARK.get(f['level'], f['level'])}  {loc}{line}")
            print(f"          {f['msg']}")
        print("─" * 64)
        if fails:
            print("结论：有 FAIL，须修正后重扫（见 WF-132 处置规程）")
        elif warns:
            print("结论：无阻断项，WARN 建议人工确认")
        else:
            print("结论：全清")

    if fails:
        return 2
    if warns:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
