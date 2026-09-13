#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
死链精准修复 v4（2026-09-13）—— 只修「去标点后完全一致」的安全项
🔴 坑 34 铁律：基名集必须与门禁同款（全库 + 法律法规库 + 智能体技能库 + 知识库）
🔴 安全阈值：仅替换 sim==1.0（归一化去标点后逐字一致）的映射，
   即「括号全半角／连接符差异」这类纯标点漂移；
   0.85 ≤ sim < 1.0 的一律登记为【候选·待人工确认】，不自动改（R2 铁律）
🔴 与 v2/v3 的差异：v2/v3 只处理正文 [[...]]，本版同时处理
   frontmatter related_links 裸名（本轮 82 条真死链中 69 条在此）
用法：python _fix_deadlinks_v4_20260913.py [--apply]
"""
import os, re, sys, shutil, glob, json, difflib, importlib.util

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
LAWKB = "/Users/chenyouqiang/Documents/LawKB"
APPLY = "--apply" in sys.argv
BK = "/tmp/存量卡巡检死链修复_20260913-1105"
os.makedirs(BK, exist_ok=True)
SKIP = {".backup", ".git", "node_modules", "Backups"}

# ---- 门禁同款口径 ----
spec = importlib.util.spec_from_file_location(
    "cd", os.path.join(BASE, "02-提炼/审判要件卡/_check_deadlinks.py"))
cd = importlib.util.module_from_spec(spec); spec.loader.exec_module(cd)
ALL = cd.build_basename_set(extra=True)
print(f"门禁同款基名集：{len(ALL)}")

NUM = re.compile(r'^(R-[A-Z]{2}-\d{3})(?:[-~](.*))?$')


def norm(a):
    return re.sub(r'[-—_·、,，:：()（）\[\]【】\s]', '', a or '')


def sim(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def build_safe_map():
    """扫全库真死链，产出 {错名: 正确名} 仅含 sim==1.0 的安全映射"""
    targets = cd.md_files(os.path.join(BASE, "06-沉淀"))
    dead_all = set()
    for p in targets:
        dead, total, err = cd.check_one(p, ALL)
        if not dead:
            continue
        real, pend = cd.classify_dead(dead)
        dead_all.update(real)
    safe, cand = {}, {}
    for k in dead_all:
        mm = NUM.match(k)
        if not mm:
            continue
        pre, desc = mm.group(1), mm.group(2) or ''
        cands = [x for x in ALL if x.startswith(pre + '-')]
        if not cands:
            continue
        best = max(cands, key=lambda x: sim(desc, x[len(pre) + 1:]))
        s = sim(desc, best[len(pre) + 1:])
        if len(cands) == 1 and s >= 0.999:
            safe[k] = best
        elif s >= 0.85:
            cand[k] = (best, round(s, 2), len(cands))
    return safe, cand


SAFE, CAND = build_safe_map()
print(f"[A] 安全可修映射：{len(SAFE)} 条")
print(f"[B] 候选待人工确认：{len(CAND)} 条（本脚本不改）")
for k, v in list(SAFE.items())[:5]:
    print(f"    {k[:46]:<48} -> {v[:50]}")


def md_files(roots):
    out = []
    for rt in roots:
        for r, dirs, files in os.walk(rt):
            dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".backup")]
            for f in files:
                if f.endswith(".md"):
                    out.append(os.path.join(r, f))
    return out


n_file, n_rep, samples = 0, 0, []
targets = md_files([os.path.join(BASE, d) for d in
                    ["06-沉淀", "02-提炼", "03-连接", "04-巩固", "05-调用"]])
for p in targets:
    try:
        t = open(p, encoding="utf-8").read()
    except Exception:
        continue
    newt = t
    for bad, good in SAFE.items():
        if bad not in newt:
            continue
        # 只替换「完整链接单元」：frontmatter 列表项 或 [[...]] 内
        pat = re.compile(r'(?m)(^(\s*-\s*")?)' + re.escape(bad) + r'(")?\s*$|\[\[' + re.escape(bad) + r'(\|[^\]]*)?\]\]')
        def _r(m):
            global n_rep
            n_rep += 1
            if m.group(0).startswith('[['):
                return m.group(0).replace(bad, good, 1)
            return m.group(0).replace(bad, good, 1)
        newt = pat.sub(_r, newt)
    if newt != t:
        n_file += 1
        if len(samples) < 3:
            samples.append(os.path.relpath(p, BASE))
        if APPLY:
            rel = os.path.relpath(p, BASE)
            dst = os.path.join(BK, rel.replace("/", "__"))
            if not os.path.exists(dst):
                shutil.copy2(p, dst)
            open(p, "w", encoding="utf-8").write(newt)

print(f"模式：{'APPLY' if APPLY else 'DRY-RUN'}")
print(f"命中文件 {n_file} 个，替换链接 {n_rep} 处")
for s in samples:
    print("   ", s)
json.dump({"safe": SAFE, "cand": {k: {"to": v[0], "sim": v[1], "cand_n": v[2]}
                                  for k, v in CAND.items()}},
          open("/tmp/deadlink_safe_map_0913.json", "w"), ensure_ascii=False, indent=1)
print("映射已存 /tmp/deadlink_safe_map_0913.json")
