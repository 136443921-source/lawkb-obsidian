# -*- coding: utf-8 -*-
"""
M2 本地检索 · 核心模块（G3 交付物，律师分身·单机密文版）

设计
----
单机密文版要求「数据不出机、零外部依赖」。本模块用两层本地检索融合：
  1. 稠密向量（sqlite-vec vec0）：离线确定性「哈希嵌入」（hashing trick），
     对中文做字级 2~3 元文法哈希到固定维向量并 L2 归一化。无需下载任何模型，
     纯标准库即可运行；预留 `embed()` 单一替换点，未来可接本地 SBERT/嵌入模型。
  2. 全文检索（SQLite FTS5 · trigram 分词）：天然适配中文子串匹配。

两者经 RRF（Reciprocal Rank Fusion）融合，返回 top-k 片段。

零外部依赖：仅用 sqlite3 + sqlite_vec（已装入 managed venv）+ 标准库。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sqlite_vec

# 向量维度（哈希嵌入桶数）。调大可降冲突，但检索精度取决于语料规模。
DIM = 256
# 单片段最大字数（按字符计），超出则切分
CHUNK_MAX = 480
# trigram 要求查询至少 3 字符才能走 FTS；更短退化为纯向量
_FTS_MIN = 3


def embed(text: str, dim: int = DIM) -> list:
    """确定性哈希嵌入：中文 2/3 字文法 → 桶计数 → L2 归一化。

    替换点：若未来接入本地 SBERT，只需让本函数返回同维、已归一化的向量即可，
    下游建库/检索逻辑无需改动。
    """
    text = re.sub(r"\s+", "", text or "")
    if not text:
        return [0.0] * dim
    vec = [0.0] * dim
    grams = set()
    # 2 字文法
    for i in range(len(text) - 1):
        grams.add(text[i : i + 2])
    # 3 字文法
    for i in range(len(text) - 2):
        grams.add(text[i : i + 3])
    # 单字（CJK）也纳入，缓解极短查询
    for ch in text:
        if ord(ch) > 0x2E80:  # 含 CJK 及扩展区
            grams.add("①" + ch)
    for g in grams:
        h = hashlib.md5(g.encode("utf-8")).digest()
        # 取前 4 字节映射到一个桶
        idx = int.from_bytes(h[:4], "big") % dim
        vec[idx] += 1.0
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def connect(db_path: str) -> sqlite3.Connection:
    """打开（或创建）M2 索引库，加载 sqlite_vec 扩展并建立表结构。"""
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            source TEXT,
            heading TEXT,
            text TEXT
        )
        """
    )
    # 全文索引：trigram 分词，适配中文子串匹配
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts "
        "USING fts5(text, source, tokenize='trigram')"
    )
    # 稠密向量索引
    conn.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec "
        f"USING vec0(embedding float[{DIM}])"
    )
    conn.commit()
    return conn


def _chunk_markdown(text: str, source: str):
    """把一份 markdown 切成若干带标题上下文的片段。"""
    lines = text.splitlines()
    chunks = []
    cur_heading = ""
    buf = []
    buf_len = 0

    def _flush():
        nonlocal buf, buf_len, cur_heading
        if buf:
            body = "\n".join(buf).strip()
            if body:
                chunks.append((cur_heading, body))
            buf = []
            buf_len = 0

    for line in lines:
        m = re.match(r"^\s{0,3}(#{1,4})\s+(.*)$", line)
        if m:
            _flush()
            cur_heading = m.group(2).strip()
            continue
        line = line.strip()
        if not line:
            continue
        buf.append(line)
        buf_len += len(line)
        if buf_len >= CHUNK_MAX:
            _flush()
    _flush()
    return chunks


def build(corpus_dir, db_path: str) -> dict:
    """遍历一个或多个 corpus 目录（列表/单目录皆可）下所有 .md，建 M2 索引。

    为向后兼容，corpus_dir 既可为单个目录字符串，也可为目录列表。
    多个目录的片段统一入库，rel 路径以各自目录为根。返回统计。
    """
    sources = corpus_dir if isinstance(corpus_dir, (list, tuple)) else [corpus_dir]
    conn = connect(db_path)
    # 清空旧索引（幂等重建）
    conn.execute("DELETE FROM chunks")
    conn.execute("DELETE FROM chunks_fts")
    conn.execute("DELETE FROM chunks_vec")
    conn.commit()

    files = []
    for src in sources:
        for root, _dirs, names in os.walk(src):
            for n in names:
                if n.lower().endswith(".md"):
                    files.append(os.path.join(root, n))

    n_chunks = 0
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except Exception:
            continue
        # 跳过明显非内容文件（如每日日志归档），仅作轻量启发式
        # 多源时 rel 用「目录名/相对路径」以区分来源
        rel = os.path.relpath(fp, os.path.commonpath([fp, *sources])) if len(sources) > 1 else os.path.relpath(fp, sources[0])
        for heading, body in _chunk_markdown(text, rel):
            emb = embed(body)
            cur = conn.execute(
                "INSERT INTO chunks(source, heading, text) VALUES (?,?,?)",
                (rel, heading, body),
            )
            rid = cur.lastrowid
            conn.execute(
                "INSERT INTO chunks_fts(rowid, text, source) VALUES (?,?,?)",
                (rid, body, rel),
            )
            conn.execute(
                "INSERT INTO chunks_vec(rowid, embedding) VALUES (?,?)",
                (rid, json.dumps(emb)),
            )
            n_chunks += 1
    conn.commit()
    conn.close()
    return {"sources": len(sources), "files": len(files), "chunks": n_chunks, "db": db_path}


def _rrf(ranks: list, k: int = 60) -> dict:
    """Reciprocal Rank Fusion：把多个排序列表融合为 {id: score}。"""
    score = {}
    for r in ranks:
        for pos, item in enumerate(r):
            rid = item[0]
            score[rid] = score.get(rid, 0.0) + 1.0 / (k + pos + 1)
    return score


def search(db_path: str, query: str, top_k: int = 5) -> list:
    """混合检索：向量 + 全文 → RRF 融合 → 返回 top_k 片段。"""
    conn = connect(db_path)
    q_emb = embed(query)
    results = []

    # 1) 向量召回
    vec_rows = []
    try:
        vec_rows = conn.execute(
            "SELECT rowid, distance FROM chunks_vec "
            "WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
            (json.dumps(q_emb), top_k * 4),
        ).fetchall()
    except Exception:
        vec_rows = []

    # 2) 全文召回（trigram，查询≥3字才走）
    fts_rows = []
    q_clean = re.sub(r"\s+", "", query or "")
    if len(q_clean) >= _FTS_MIN:
        try:
            fts_rows = conn.execute(
                "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? "
                "ORDER BY bm25(chunks_fts) LIMIT ?",
                (q_clean, top_k * 4),
            ).fetchall()
        except Exception:
            fts_rows = []

    fused = _rrf([vec_rows, fts_rows])
    # 取融合分最高的 top_k
    ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    for rid, score in ordered:
        row = conn.execute(
            "SELECT source, heading, text FROM chunks WHERE id=?", (rid,)
        ).fetchone()
        if row:
            results.append(
                {
                    "source": row[0],
                    "heading": row[1],
                    "text": row[2],
                    "score": round(score, 6),
                }
            )
    conn.close()
    return results
