#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M2 本地检索 · 查询 CLI（G3 交付物）

用法
----
  python3 m2_query.py "股权转让 意思表示真实" [--db m2_index.db] [--topk 5]

输出：top-k 相关片段（来源 / 标题 / 融合分 / 正文摘要），全部本地完成。
"""

from __future__ import annotations

import argparse
import os
import sys
import json as _json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m2_core import search  # noqa: E402


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="M2 本地检索查询")
    ap.add_argument("query", help="检索问句/关键词")
    ap.add_argument("--db", default=os.path.join(here, "m2_index.db"), help="SQLite 索引库")
    ap.add_argument("--topk", type=int, default=5, help="返回片段数")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出（便于上游程序消费）")
    args = ap.parse_args()

    if not os.path.isfile(args.db):
        print("❌ 索引库不存在: {0}（请先跑 m2_build_index.py）".format(args.db))
        sys.exit(2)

    results = search(args.db, args.query, top_k=args.topk)
    if args.json:
        print(_json.dumps(results, ensure_ascii=False, indent=2))
        return
    if not results:
        print("（无命中）")
        return
    print("🔍 命中 {0} 个片段（向量+全文 RRF 融合）：".format(len(results)))
    for i, r in enumerate(results, 1):
        print("─" * 72)
        print("[{0}] 分={1:.4f} | {2}  ›  {3}".format(i, r["score"], r["source"], r["heading"]))
        snippet = r["text"].replace("\n", " ")
        print("    {0}".format(snippet[:160]))


if __name__ == "__main__":
    main()
