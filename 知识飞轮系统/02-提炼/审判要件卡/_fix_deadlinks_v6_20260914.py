#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
死链分级分析与修复器  v6 / 2026-09-14

🔴 坑 34 铁律：基名集必须与门禁**完全一致**。
   本版不自建基名集，直接 `import` 门禁 `_check_deadlinks.py`（有 __main__ 保护），
   复用其 build_basename_set / md_files / check_one / classify_dead —— 物理上杜绝口径漂移。

分级判据（坑 45 三条 + 本轮新增）：
  [A] 安全可修：编号前缀一致 + 候选唯一 + 去标点后**互为子串且差异仅在首尾**
                （首尾增删＝修饰补充；中间字符替换＝语义替换，一律拦截）
  [B] 候选待确认：候选唯一但为**中间字符替换**，或相似度 >= 0.85
  [C] 无候选/多候选：需人工（被重命名？已删除？）
  [D] 编号本身不存在（全库无该编号任何卡）：疑似卡已删除，需人工确认后删链

用法：python _fix_deadlinks_v6_20260914.py [--apply]
"""
import os, re, sys, json, shutil, datetime, importlib.util, difflib

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "_check_deadlinks.py")
ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"

# 🔴 必须在覆盖 sys.argv **之前**取参：否则 --apply 会被吞掉，
#    脚本静默退化为 dry-run，还伪装成「无可修项」（与坑 17/21 同源）。
APPLY = "--apply" in sys.argv
_ARGV_BACKUP = list(sys.argv)

# ── 加载门禁模块（同款口径的唯一真源）────────────────────────
spec = importlib.util.spec_from_file_location("gate", GATE)
gate = importlib.util.module_from_spec(spec)
sys.argv = [GATE, "--help"]          # 防止门禁 main 被误触发
spec.loader.exec_module(gate)
sys.argv = _ARGV_BACKUP              # 立即还原
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
BK = f"/tmp/存量卡巡检死链修复_{STAMP}"

NOISE = re.compile(r"[^\u4e00-\u9fa5A-Za-z0-9]")
NUM_PREFIX = re.compile(r"^(R-[A-Z]{2}-\d+|LC-\d+|IMA-\d+)")


def sig(s):
    return NOISE.sub("", str(s)).lower()


def same_head_tail(a, b):
    """坑 45 关键判据：去标点后互为子串，且差异**仅限首尾**。

    返回 True 表示「修饰补充」（安全），False 表示「中间字符替换」（危险）。
    """
    if a == b:
        return True
    if a in b:
        i = b.find(a)
        return i == 0 or i + len(a) == len(b)      # 只在首或只在尾追加
    if b in a:
        i = a.find(b)
        return i == 0 or i + len(b) == len(b) or i + len(b) == len(a)
    return False


def main():
    names = gate.build_basename_set()
    print(f"门禁同款基名集：{len(names)}")

    files = gate.md_files()
    real_dead = {}      # name -> set(files)
    for p in files:
        bad, total, err = gate.check_one(p, names)
        if err:
            continue
        real, _pending = gate.classify_dead(bad)
        for n in real:
            real_dead.setdefault(n, set()).add(p)

    print(f"真死链去重：{len(real_dead)} 个（出现文件次合计 {sum(len(v) for v in real_dead.values())}）")

    # 按编号建索引，便于找候选
    by_num = {}
    for n in names:
        m = NUM_PREFIX.match(n)
        if m:
            by_num.setdefault(m.group(1), []).append(n)

    A, B, C, D = {}, {}, {}, {}
    for dead, fps in real_dead.items():
        m = NUM_PREFIX.match(dead)
        num = m.group(1) if m else None
        cands = by_num.get(num, []) if num else []
        if not num:
            C[dead] = {"files": sorted(fps), "why": "无编号前缀（语法残片/纯数字），需人工判断"}
            continue
        if not cands:
            D[dead] = {"files": sorted(fps), "why": f"全库无 {num} 任何卡，疑似卡已删除"}
            continue
        # 候选：同编号 + 相似度
        scored = sorted(
            ((difflib.SequenceMatcher(None, sig(dead), sig(c)).ratio(), c) for c in cands),
            reverse=True)
        top_sim, top = scored[0]
        if len(cands) == 1 and same_head_tail(sig(dead), sig(top)):
            A[dead] = {"to": top, "sim": round(top_sim, 3), "files": sorted(fps)}
        elif len(cands) == 1:
            B[dead] = {"to": top, "sim": round(top_sim, 3), "files": sorted(fps),
                       "why": "唯一候选但为中间字符替换（坑45），须人工确认语义同一"}
        elif top_sim >= 0.85:
            B[dead] = {"to": top, "sim": round(top_sim, 3), "files": sorted(fps),
                       "why": f"同编号 {len(cands)} 个候选，best sim={top_sim:.2f}，须人工选定"}
        else:
            C[dead] = {"files": sorted(fps),
                       "why": f"同编号 {len(cands)} 个候选且 best sim={top_sim:.2f} < 0.85"}

    out = {"generated": STAMP, "basename_set": len(names),
           "A_safe": A, "B_candidate": B, "C_manual": C, "D_missing_num": D}
    op = os.path.join(HERE, f"死链分级-20260914.json")
    json.dump(out, open(op, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"\n[A] 安全可修 {len(A)}  [B] 候选待确认 {len(B)}  [C] 需人工 {len(C)}  [D] 编号不存在 {len(D)}")
    for k, v in sorted(A.items()):
        print(f"  A {k}\n     → {v['to']}  (sim={v['sim']}, {len(v['files'])} 文件)")

    if APPLY and A:
        os.makedirs(BK, exist_ok=True)
        hit = 0
        for dead, info in A.items():
            for p in info["files"]:
                t = open(p, encoding="utf-8").read()
                if dead not in t:
                    continue
                shutil.copy2(p, os.path.join(BK, os.path.basename(p)))
                open(p, "w", encoding="utf-8").write(t.replace(dead, info["to"]))
                hit += t.count(dead)
        print(f"\n[APPLY] 替换 {hit} 处，备份 {BK}（{len(os.listdir(BK))} 份）")
    print(f"\n分级结果：{op}")


if __name__ == "__main__":
    main()
