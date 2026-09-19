#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_analyze_deadlink_v3_20260918.py  v1.0（只读分析器，不写任何文件）
🔴 坑 34：基名集直接复用门禁 _check_deadlinks.build_basename_set()，禁止自建子集。
🔴 坑 64：目标为「纯编号命名卡」（R-XX-NNN 无描述）时禁止算术/前缀推断，一律留人工。

输出分类：
  SAFE      唯一候选 + 首尾增删关系（同号，仅描述段差一个前后缀）
  AMBIG     多候选，需人工
  NONE      库里查不到近似物 → 真缺失/待建，非本轮可修
"""
import importlib.util
import json
import os
import re
import sys
from collections import Counter

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
GATE = os.path.join(ROOT, "02-提炼/审判要件卡/_check_deadlinks.py")

spec = importlib.util.spec_from_file_location("gate", GATE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

PURE_CODE = re.compile(r'^R-[A-Z]{2}-\d{3}$')


def levenshtein(a, b, cap=4):
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def main():
    allmd = gate.build_basename_set()
    print("门禁基名集：%d" % len(allmd))

    # 收集全部卡片
    targets = []
    base = os.path.join(ROOT, "06-沉淀/裁判规则库")
    for dp, dns, fns in os.walk(base):
        dns[:] = [d for d in dns if not d.startswith('.backup')]
        for fn in fns:
            if fn.endswith('.md'):
                targets.append(os.path.join(dp, fn))
    for extra in ("02-提炼", "03-连接", "05-调用", "01-采集", "04-巩固"):
        b2 = os.path.join(ROOT, extra)
        for dp, dns, fns in os.walk(b2):
            dns[:] = [d for d in dns if not d.startswith('.backup')]
            if gate.is_quarantine(os.path.basename(dp)):
                continue
            for fn in fns:
                if fn.endswith('.md'):
                    targets.append(os.path.join(dp, fn))

    dead = []
    for p in sorted(set(targets)):
        d, tot, err = gate.check_one(p, allmd)
        if err or not d:
            continue
        for x in d:
            dead.append((os.path.relpath(p, ROOT), x))
    real_pairs = [(c, x) for c, x in dead if gate.classify_dead([x])[0]]
    print("真死链（含重复）：%d 条；去重后 %d 个名字" % (len(real_pairs), len(set(x for _, x in real_pairs))))

    cnt = Counter(x for _, x in real_pairs)
    mdlist = sorted(allmd)

    safe, ambig, none, guard = [], [], [], []
    for name, n in sorted(cnt.items(), key=lambda kv: -kv[1]):
        if PURE_CODE.match(name):
            guard.append((name, n, "坑64：纯编号命名卡，禁止推断"))
            continue
        cands = []
        for m in mdlist:
            if m == name or len(m) < 4:
                continue
            if m.startswith(name) or name.startswith(m):
                cands.append((m, 'prefix'))
            elif len(name) >= 10 and levenshtein(name, m, 2) <= 2:
                cands.append((m, 'edit<=2'))
        cands = sorted(set(cands))
        if not cands:
            none.append((name, n))
        elif len(cands) == 1:
            safe.append((name, n, cands[0][0], cands[0][1]))
        else:
            ambig.append((name, n, [c[0] for c in cands[:4]]))

    print("\n=== SAFE（唯一候选·可安全修）%d ===" % len(safe))
    for name, n, cand, kind in safe:
        print("  %s  ×%d  →  %s   [%s]" % (name[:60], n, cand[:60], kind))
    print("\n=== AMBIG（多候选·需人工）%d ===" % len(ambig))
    for name, n, c in ambig[:20]:
        print("  %s ×%d → %s" % (name[:50], n, ' | '.join(x[:34] for x in c)))
    print("\n=== 坑64 守卫（纯编号）%d ===" % len(guard))
    for name, n, why in guard[:20]:
        print("  %s ×%d  %s" % (name, n, why))
    print("\n=== NONE（库内无近似·非本轮可修）%d ===" % len(none))
    for name, n in none[:25]:
        print("  %s ×%d" % (name[:60], n))

    where = {}
    for c, x in real_pairs:
        where.setdefault(x, []).append(c)
    out = {"safe": [{"dead": a, "n": b, "to": c, "kind": d, "files": where.get(a, [])}
                    for a, b, c, d in safe],
           "ambig": [{"dead": a, "n": b, "cands": c, "files": where.get(a, [])[:5]}
                     for a, b, c in ambig],
           "guard": [{"dead": a, "n": b, "why": c} for a, b, c in guard],
           "none": [{"dead": a, "n": b, "files": where.get(a, [])[:5]} for a, b in none]}
    p = os.path.join(ROOT, "02-提炼/审判要件卡/_deadlink_analysis_20260918.json")
    json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print("\n已落：%s" % p)


if __name__ == "__main__":
    main()
