#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
死链精准修复 v2（2026-09-12，回滚 v1 误操作后重做）
🔴 v1 教训：用自己的缩小基名集（仅 06-沉淀 1516）替代门禁集（全库 4319），
   把 03-连接/概念页 里「纯编号命名的合法概念页」（如 R-PI-146.md）误判为死链改坏。
   → 本版**强制复用门禁同款口径**：先判 inner 是否已在全库基名集中，命中即不动。
判定规则（只修「编号引用型真死链」）：
   - inner 已在全库基名集 → 不动
   - 全库内存在唯一 k 满足 k.startswith(inner+"-") → 替换为 k（截断名补全）
   - 全库内存在唯一 k 满足 inner.startswith(k+"-") 且 k 是完整基名 → 不动（已合法）
用法：python _fix_deadlinks_v3_20260913.py [--apply]
"""
import os, re, sys, shutil, glob

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
LAWKB = "/Users/chenyouqiang/Documents/LawKB"
APPLY = "--apply" in sys.argv
BK = "/tmp/存量卡巡检_20260913-1052"
os.makedirs(BK, exist_ok=True)
SKIP = {".backup", ".git", "node_modules", "Backups"}


def basenames(roots):
    s = set()
    for rt in roots:
        for r, dirs, files in os.walk(rt):
            dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".backup")]
            for f in files:
                if f.endswith(".md"):
                    s.add(f[:-3])
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


# 门禁同款口径：知识飞轮系统 + 法律法规库 + 智能体技能库 + 知识库
ALL = basenames([BASE, os.path.join(LAWKB, "法律法规库"),
                 os.path.join(LAWKB, "智能体技能库"), os.path.join(LAWKB, "知识库")])
print(f"门禁同款基名集：{len(ALL)}")

NUM = re.compile(r"^R-[A-Z]{2}-\d+")
n_fix = [0]
samples = []
touched = []


def rep(m):
    inner = m.group(1).strip().split("|")[0].split("#")[0].split("/")[-1].strip()
    if not NUM.match(inner):
        return m.group(0)
    if inner in ALL:                      # 🔴 关键：已合法则不动
        return m.group(0)
    hits = [k for k in ALL if k.startswith(inner + "-")]
    if len(hits) == 1:
        n_fix[0] += 1
        if len(samples) < 12:
            samples.append((inner, hits[0]))
        return m.group(0).replace("[[" + m.group(1), "[[" + hits[0], 1)
    return m.group(0)


targets = md_files([os.path.join(BASE, d) for d in
                    ["06-沉淀", "02-提炼", "03-连接", "04-巩固", "05-调用"]])
for p in targets:
    try:
        t = open(p, encoding="utf-8").read()
    except Exception:
        continue
    if "[[" not in t:
        continue
    newt = re.sub(r"\[\[([^\[\]|]+)(?:\|[^\]]*)?\]\]", rep, t)
    if newt != t:
        touched.append(p)
        if APPLY:
            rel = os.path.relpath(p, BASE)
            dst = os.path.join(BK, rel.replace("/", "__"))
            if not os.path.exists(dst):
                shutil.copy2(p, dst)
            open(p, "w", encoding="utf-8").write(newt)

print(f"模式：{'APPLY' if APPLY else 'DRY-RUN'}")
print(f"命中文件 {len(touched)} 个，替换链接 {n_fix[0]} 条")
for a, b in samples:
    print(f"   {a[:34]:<36} -> {b[:56]}")
