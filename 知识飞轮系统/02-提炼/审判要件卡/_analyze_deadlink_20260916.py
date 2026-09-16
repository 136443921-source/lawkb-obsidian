#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_analyze_deadlink_20260916.py  v1.0
按「门禁同款口径」（直接 import _check_deadlinks 模块，坑 34）拆解真死链构成。

产出：
  1. 真死链去重目标名 + 出现次数（降序）
  2. 分类：编号引用型（R-XX-NNN）/ 语法残片 / 主题名
  3. 编号引用型中「同编号存在但文件名不同」→ 疑似重命名（可安全修）
     vs 「同编号全库无」→ 疑似从未存在/已删（须人工）
"""
import importlib.util
import json
import os
import re
import sys
from collections import Counter, defaultdict

APPLY = "--apply" in sys.argv   # 坑 52：早于任何 sys.argv 改写
_ARGV = list(sys.argv)

GATE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/审判要件卡/_check_deadlinks.py"
spec = importlib.util.spec_from_file_location("gate", GATE)
gate = importlib.util.module_from_spec(spec)
sys.argv = [GATE, "--help"]     # 防门禁 main 误触发
spec.loader.exec_module(gate)
sys.argv = _ARGV                # 用完立即还原

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"

RULE_ID = re.compile(r"^(R-[A-Z]{2}-\d{3})(?:[-_–—]?.*)?$")


def main():
    names = gate.build_basename_set()
    print(f"门禁基名总数：{len(names)}")

    allmd = list(gate.md_files())
    print(f"待检文件：{len(allmd)}")

    dead_counter = Counter()
    dead_files = defaultdict(list)   # link -> [file,...]
    parse_errors = []

    for p in allmd:
        try:
            links, n_err, err = gate.check_one(p, names)
        except Exception as e:
            parse_errors.append((p, str(e)[:80]))
            continue
        if err:
            parse_errors.append((p, err))
        for ln in links:
            dead_counter[ln] += 1
            dead_files[ln].append(os.path.relpath(p, ROOT))

    real, pending = gate.classify_dead(list(dead_counter.keys()))

    real_cnt = {k: dead_counter[k] for k in real}
    print(f"\n真死链：{sum(real_cnt.values())} 次 / {len(real_cnt)} 唯一")
    print(f"待建笔记：{sum(dead_counter[k] for k in pending)} 次 / {len(pending)} 唯一")

    # 分类
    by_rule = {}
    by_frag = {}
    by_topic = {}
    for k, c in real_cnt.items():
        m = RULE_ID.match(k)
        if m:
            by_rule[k] = (m.group(1), c)
        elif gate.is_noise(k) or len(k) <= 4 or re.match(r"^[\d\s\.\-_/]+$", k) or ".md" in k:
            by_frag[k] = c
        else:
            by_topic[k] = c

    print(f"\n【分类】编号引用型 {len(by_rule)} 唯一 / 语法残片 {len(by_frag)} 唯一 / 主题名 {len(by_topic)} 唯一")

    # 编号引用型：同编号是否存在其他基名
    prefix_index = defaultdict(list)
    for n in names:
        m = RULE_ID.match(n)
        if m:
            prefix_index[m.group(1)].append(n)

    renamable = {}    # 编号存在，唯一候选 → 疑似重命名
    ambiguous = {}    # 编号存在，多候选
    ghost = {}        # 编号全库无
    for k, (rid, c) in by_rule.items():
        cands = prefix_index.get(rid, [])
        if not cands:
            ghost[k] = (rid, c)
        elif len(cands) == 1:
            renamable[k] = (cands[0], c)
        else:
            ambiguous[k] = (cands, c)

    print(f"\n【编号引用型细分】")
    print(f"  A. 同编号唯一候选（疑似重命名，可安全修）：{len(renamable)} 唯一 / {sum(v[1] for v in renamable.values())} 次")
    print(f"  B. 同编号多候选（须人工）：{len(ambiguous)} 唯一")
    print(f"  C. 编号全库不存在（须人工）：{len(ghost)} 唯一 / {sum(v[1] for v in ghost.values())} 次")

    out = {
        "meta": {
            "basenames": len(names),
            "files": len(allmd),
            "real_total": sum(real_cnt.values()),
            "real_unique": len(real_cnt),
            "pending_unique": len(pending),
        },
        "A_renamable": {k: {"target": v[0], "count": v[1], "files": dead_files[k][:5]} for k, v in renamable.items()},
        "B_ambiguous": {k: {"cands": v[0], "count": v[1]} for k, v in ambiguous.items()},
        "C_ghost": {k: {"rid": v[0], "count": v[1], "files": dead_files[k][:5]} for k, v in ghost.items()},
        "frag": dict(sorted(by_frag.items(), key=lambda x: -x[1])),
        "topic_top": dict(sorted(by_topic.items(), key=lambda x: -x[1])[:60]),
        "parse_errors": parse_errors,
    }
    dst = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/审判要件卡/_deadlink_analysis_20260916.json"
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n已落：{dst}")

    print("\n【A 类 TOP20 疑似重命名】")
    for k, v in sorted(renamable.items(), key=lambda x: -x[1][1])[:20]:
        print(f"  {v[1]:>3}×  {k}  →  {v[0]}")

    print("\n【C 类 TOP20 编号不存在】")
    for k, v in sorted(ghost.items(), key=lambda x: -x[1][1])[:20]:
        print(f"  {v[1]:>3}×  {k}  (rid={v[0]})")

    print("\n【语法残片 TOP15】")
    for k, c in sorted(by_frag.items(), key=lambda x: -x[1])[:15]:
        print(f"  {c:>3}×  {k!r}")


if __name__ == "__main__":
    main()
