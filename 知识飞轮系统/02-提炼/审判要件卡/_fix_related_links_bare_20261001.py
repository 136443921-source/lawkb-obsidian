#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
裸 related_links / 裸编号引用 补全器 v1（2026-10-01，立项）
==================================================
背景（质量巡检 R16 发现）：
  _fix_deadlinks_v2_20260912.py 只重写 `[[...]]` **wikilink 形态**的截断名。
  门禁 `_check_deadlinks.py` v1.7.2 的「真死链」还统计 frontmatter `related_links`
  里**裸 R 编号**（无 `[ ]` 括号，如 `- R-CF-065`）与 aliases 未覆盖项。
  → 这是「fix 改 347 条 / 门禁只降 18 唯一名」的口径差异根因，非脚本 bug。

本补全器目标：把裸 `R-XX-NNN` 编号引用（含 related_links 裸项、正文裸 token）按
**与 fix 脚本完全相同的铁律口径**补全为唯一全名，补齐盲区。

🔴 安全口径（与 _fix_deadlinks_v2 一致，绝不为降数字硬修）：
  - 基名集 = 门禁同款口径（知识飞轮系统 + 法律法规库 + 智能体技能库 + 知识库）
  - inner 已在全库集 → 不动（已合法 / 靠 aliases 解析）
  - 全库内存在**唯一** k 满足 k.startswith(inner + "-") → 补全为 k
  - 歧义（≥2 候选）/ 无匹配 → 不动（留作【候选·待人工确认】）
匹配形态：裸 R 编号 token（负向前/后断言，避免吞已带后缀的全名，
          也不吞 `[` 前的 wikilink——wikilink 由 fix 脚本已处理，此处仅兜底）
用法：python _fix_related_links_bare_20261001.py [--apply]
"""
import os, re, sys, shutil, io
from datetime import datetime

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
LAWKB = "/Users/chenyouqiang/Documents/LawKB"
APPLY = "--apply" in sys.argv
SKIP = {".backup", ".git", "node_modules", "Backups"}

TS = datetime.now().strftime("%Y%m%d-%H%M%S")
BK = f"/tmp/裸related_links补全_{TS}"
os.makedirs(BK, exist_ok=True)


def extract_aliases(txt):
    """轻量提取 frontmatter aliases（与门禁 build_basename_set 同口径）。
    门禁把 aliases 并入基名集 → `[[别名]]` / 裸别名引用不再判死链。
    补全器必须复用同一口径，否则会把「靠别名已解析」的引用误判为待修（硬修陷阱）。"""
    if not txt.startswith("---"):
        return []
    parts = txt.split("---", 2)
    if len(parts) < 3:
        return []
    block = parts[1]
    out = []
    m = re.search(r"^aliases:\s*\[(.*?)\]\s*$", block, re.M)
    if m:
        for a in m.group(1).split(","):
            a = a.strip().strip("\"'[]").strip()
            if a:
                out.append(a)
        return out
    lines = block.splitlines()
    for i, ln in enumerate(lines):
        if re.match(r"^aliases:\s*$", ln):
            j = i + 1
            while j < len(lines) and re.match(r"^\s*-\s+(.+)$", lines[j]):
                a = re.match(r"^\s*-\s+(.+)$", lines[j]).group(1).strip().strip("\"'")
                if a:
                    out.append(a)
                j += 1
            break
    return out


def basenames(roots):
    s = set()
    for rt in roots:
        for r, dirs, files in os.walk(rt):
            dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".backup")]
            for f in files:
                if f.endswith(".md"):
                    s.add(f[:-3])
                    try:
                        with io.open(os.path.join(r, f), encoding="utf-8") as _fh:
                            _t = _fh.read(8192)
                        for _al in extract_aliases(_t):
                            s.add(_al)
                    except Exception:
                        pass
    return s


def md_files(roots):
    out = []
    for rt in roots:
        for r, dirs, files in os.walk(rt):
            dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".backup")]
            for f in files:
                if f.endswith(".md"):
                    out.append(os.path.join(r, f))
    return out


ALL = basenames([BASE, os.path.join(LAWKB, "法律法规库"),
                 os.path.join(LAWKB, "智能体技能库"), os.path.join(LAWKB, "知识库")])
print(f"门禁同款基名集：{len(ALL)}")

# 裸 R 编号 token（不吞全名后缀、不吞 wikilink 内形态）
BARE = re.compile(r"(?<![\w-])R-[A-Z]{2}-\d+(?![\w-])")
n_fix = [0]
samples = []
touched = []


def repl(m):
    inner = m.group(0)
    if inner in ALL:                      # 已合法（含 aliases 解析）→ 不动
        return inner
    hits = [k for k in ALL if k.startswith(inner + "-")]
    if len(hits) == 1:
        n_fix[0] += 1
        if len(samples) < 12:
            samples.append((inner, hits[0]))
        return hits[0]
    return inner                           # 歧义 / 无匹配 → 不动


targets = md_files([os.path.join(BASE, d) for d in
                    ["06-沉淀", "02-提炼", "03-连接", "04-巩固", "05-调用"]])
for p in targets:
    try:
        t = open(p, encoding="utf-8").read()
    except Exception:
        continue
    if "R-" not in t:
        continue
    newt = BARE.sub(repl, t)
    if newt != t:
        touched.append(p)
        if APPLY:
            rel = os.path.relpath(p, BASE).replace("/", "__")
            dst = os.path.join(BK, rel)
            if not os.path.exists(dst):
                shutil.copy2(p, dst)
            open(p, "w", encoding="utf-8").write(newt)

print(f"模式：{'APPLY' if APPLY else 'DRY-RUN'}")
print(f"命中文件 {len(touched)} 个，补全裸编号引用 {n_fix[0]} 条")
for a, b in samples:
    print(f"   {a:<14} -> {b[:60]}")
