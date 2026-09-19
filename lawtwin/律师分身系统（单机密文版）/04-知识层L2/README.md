---
id: LAWYER-AVATAR-M2-RETRIEVAL
title: 律师分身·单机密文版 · 本地检索 M2 + 密文闭环（G3 / 检索+密文闭环）
status: active
living_doc: true
related:
  - 律师分身系统（单机密文版）/启动包/crypto-l1.sh
  - 律师分身系统（单机密文版）/04-知识层L2/m2_secure.sh
scope: lawyer-avatar-only
updated: 2026-09-18T20:19
created: 2026-09-17T22:46
tags:
  - 密文
  - m2
  - 民事诉讼
  - sh
  - 分身
  - 劳动争议
  - 检索
---

# 本地检索 M2 · sqlite-vec 混合检索 + 密文闭环（G3 交付物）

> **范围声明**：本目录仅服务律师分身（小强律师数字分身系统），不含「律所分身」内容。

## 一、为什么需要 M2

单机密文版要求「数据不出机」。L1 人格层（加密）解决数据保密，M2 解决**本地知识检索**——
让分身在离线状态下也能从 LawKB 知识库召回相关法条/案例/方法论片段，喂给 M1 推理。

## 二、架构

```
查询 ─┬─▶ 稠密向量（sqlite-vec vec0）  离线哈希嵌入（hashing trick）
      │       · 中文 2/3 字文法 → 256 维桶 → L2 归一化
      │       · 零模型下载、纯标准库
      └─▶ 全文检索（SQLite FTS5 · trigram）  中文子串匹配
                  │
                  └─▶ RRF 融合（Reciprocal Rank Fusion）→ top-k 片段
```

**可插拔点**：`m2_core.embed()` 是唯一嵌入入口。未来若部署本地 SBERT/嵌入模型，
只需让该函数返回同维、已归一化的向量，建库与检索逻辑无需改动。

## 三、交付物清单（本目录）

| 文件 | 作用 |
|------|------|
| `m2_core.py` | 核心：哈希嵌入 + 建库（chunks/FTS5/vec0）+ RRF 融合检索；`build()` 支持多源语料 |
| `m2_build_index.py` | 索引构建 CLI：支持 `--corpus`（可重复）+ `--manifest`，遍历律师分身语料 `.md` → 建 SQLite 单文件索引 |
| `m2_query.py` | 查询 CLI：混合检索 top-k，支持 `--json` 供上游消费 |
| `m2_corpus_manifest.txt` | 律师分身语料清单（每行一目录，# 注释；**已排除律所分身目录**） |
| `m2_secure.sh` | **密文闭环工具**：rebuild / seal / query / verify / status 一条龙，把 M2 索引用 crypto-l1.sh 加密归档 |
| `README.md` | 本说明 |

依赖：仅 `sqlite3`（系统自带 3.50.4，含 FTS5）+ `sqlite_vec`（已装入 managed venv）。
**运行必须使用装有 sqlite_vec 的 Python**：
`/Users/chenyouqiang/.workbuddy/binaries/python/envs/default/bin/python`

> ⚠️ **shell 脚本 ASCII 安全铁律**：`m2_secure.sh` 中所有 `$变量` 不得紧贴非 ASCII 标点
> （如 `→` `（）` `「」`）。本环境 bash 字节级解析会把这些多字节字符并入变量名导致
> `unbound variable`。脚本内已统一改用 ASCII（`->` `()` `"`）。

## 四、运维 SOP（密文闭环）

**设计要点**：索引库 `m2_index.db` 是明文 SQLite；常态下以密文 `m2-index.L1.tar.gz.enc`
存储（密钥仅存 macOS 钥匙串 `lawtwin-l1-lawyer-m2-index`）。检索时即时解密到临时目录查询，
用完即焚，**明文库不落盘**（仅 `rebuild` 过程中短暂存在）。→ 「检索能力 + 密文存储」闭环。

```bash
cd 律师分身系统（单机密文版）/04-知识层L2

# 1) 首次 / 语料变更后：依 manifest 重建索引并加密（一条龙）
bash m2_secure.sh rebuild

# 2) 仅把现有明文索引加密归档（不动语料）
bash m2_secure.sh seal

# 3) 检索：自动解密密文到临时目录并查询，结果打印后清理临时明文
bash m2_secure.sh query "工伤认定 工伤保险"
bash m2_secure.sh query "股权转让 意思表示真实"

# 4) 闭环自测：解密密文 + 多类语料内置查询确认有命中
bash m2_secure.sh verify

# 5) 查看密文归档状态
bash m2_secure.sh status
```

**手动底层命令**（等价于上面，调试用）：
```bash
PY=/Users/chenyouqiang/.workbuddy/binaries/python/envs/default/bin/python
# 构建（多源）
$PY m2_build_index.py --manifest m2_corpus_manifest.txt --db m2_index.db
# 查询
$PY m2_query.py "股权转让 意思表示真实" --topk 5
$PY m2_query.py "冒名起诉 驳回" --json   # 供 M1 程序化消费
# 加密（经 crypto-l1.sh，密钥存钥匙串）
bash ../启动包/crypto-l1.sh encrypt . m2-index   # 在含 m2_index.db 的目录内执行
```

## 五、验收记录（2026-09-17 实测）

- [x] 离线哈希嵌入可运行（零模型下载）
- [x] FTS5 trigram 中文子串匹配通过
- [x] vec0 向量召回通过（同文 distance=0）
- [x] 多源语料建库：5 个律师分身源、112 个 md、切出 3378 个片段
- [x] crypto-l1.sh 加密 round-trip（sha256 一致）通过，密文权限 600
- [x] **检索 + 密文闭环**：`query` 从密文解密检索命中；删除明文库后 `verify` 仍通过（仅密文可检索）

## 六、变更日志

- 2026-09-17 初建（G3）。sqlite-vec 向量 + FTS5 trigram 混合，离线确定性嵌入。
- 2026-09-17 扩展：多源语料（`build()` 支持列表 + `--manifest`）+ `m2_secure.sh` 闭环工具 +
  `m2_corpus_manifest.txt`（律师分身语料，排除律所分身）；完成「检索+密文」闭环并实测。
