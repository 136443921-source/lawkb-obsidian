#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M2 本地检索 · 索引构建 CLI（G3 交付物，支持多源语料）

用法
----
  python3 m2_build_index.py --corpus <语料目录> [--corpus <另一目录> ...] --db m2_index.db
  python3 m2_build_index.py --manifest m2_corpus_manifest.txt --db m2_index.db
  python3 m2_build_index.py   # 默认读本目录 m2_corpus_manifest.txt（如有），否则用本目录

说明
----
遍历各 corpus 下全部 .md，按标题切分为片段，生成
  · chunks（原文）  · chunks_fts（FTS5 trigram 全文）  · chunks_vec（sqlite-vec 稠密向量）
索引库为单文件 SQLite，可随单机密文版整体加密归档（见 crypto-l1.sh / m2_secure.sh）。
语料严格限定律师分身资产；manifest 中已排除律所分身目录。
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m2_core import build  # noqa: E402


def _read_manifest(path: str) -> list:
    sources = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            sources.append(line)
    return sources


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="M2 索引构建（多源语料）")
    ap.add_argument(
        "--corpus",
        action="append",
        default=[],
        help="语料根目录（可重复；递归扫描 .md）。与 --manifest 合并",
    )
    ap.add_argument(
        "--manifest",
        default=os.path.join(here, "m2_corpus_manifest.txt"),
        help="语料清单文件：每行一个目录，# 开头为注释",
    )
    ap.add_argument(
        "--db",
        default=os.path.join(here, "m2_index.db"),
        help="输出 SQLite 索引库",
    )
    args = ap.parse_args()

    sources = list(args.corpus)
    if os.path.isfile(args.manifest):
        sources.extend(_read_manifest(args.manifest))
    # 去重、过滤不存在的目录（warns 但不中断）
    seen = set()
    clean = []
    for s in sources:
        s = os.path.expanduser(s)
        if s in seen:
            continue
        if not os.path.isdir(s):
            print("⚠️  跳过不存在的语料目录: {0}".format(s))
            continue
        seen.add(s)
        clean.append(s)

    if not clean:
        print("❌ 无任何可用语料目录（请检查 --corpus / --manifest）")
        sys.exit(2)

    print("🔧 构建 M2 索引：{0} 个语料源 → db={1}".format(len(clean), args.db))
    for s in clean:
        print("   · {0}".format(s))
    stat = build(clean, args.db)
    print(
        "✅ 完成：{sources} 个源、扫描 {files} 个 md 文件，切出 {chunks} 个片段 → {db}".format(**stat)
    )


if __name__ == "__main__":
    main()
