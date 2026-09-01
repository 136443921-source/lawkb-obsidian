#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连接层 · 源链接修复器 (v1.0)
=======================
清理知识飞轮系统内历史遗留的畸形/标记化双向链接，使断链消解器可生成干净概念页。
非破坏性（飞轮系统为 git 仓库，可整体回滚）。

修复项：
  1. 畸形链接  [[数字-[[案件名]]  ->  [[案件名]]   （源文件，排除概念页目录）
  2. 红/蓝队标记  [[X（红队）]] / [[X（蓝队）]] / [[X（红）]] / [[X（蓝）]] -> [[X]]
  3. 空链接  [[]]  ->  双向链接  （说明文字中的占位符，非真实链接）
  4. 删除垃圾概念页：文件名含 [[ / ]] / # / （红队） / （蓝队） 的概念页（上一轮误建）
  5. 括号归一（v1.1 新增，覆盖概念页目录）：消解 kg_scan 误判的"畸形嵌套 wikilink"
       5a. 三重/多重开括号折叠  [[[X]]] -> [[X]]  /  ]]] -> ]]
       5b. 引用式嵌套剥离      [[A [[B]] -> A [[B]]（剥离外层多余 [[，保留内层有效链接）
       说明：本项对概念页目录也生效（W35 排查发现 88/100 假阳断链源于概念桩页三重括号），
            但 meta 报告目录（示例链接）仍跳过。
用法：python3 fix_source_links.py [--apply]
"""
import os, re, json, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONCEPT_DIR = os.path.join(ROOT, "03-连接", "概念页")
SKIP_DIRS = {".git", ".obsidian", ".trash", "node_modules"}
# meta 报告目录：其内部 `[[...]]` 多为断链示例，不修改这些文件
META_SKIP = {"孤立笔记检测报告", "知识库压缩去重报告"}

md_files = []
for dp, dn, fn in os.walk(ROOT):
    if any(s in dp.split(os.sep) for s in SKIP_DIRS):
        continue
    for f in fn:
        if f.endswith(".md"):
            md_files.append(os.path.join(dp, f))

existing = {os.path.splitext(os.path.basename(f))[0] for f in md_files}

MALFORM = re.compile(r"\[\[\d+-\[\[(.+?)\]\]")          # [[35-[[X]]
REDBLUE = re.compile(r"\[\[([^\[\]]*?)（(?:红队|蓝队|红|蓝)）(\|[^\]]*?)?\]\]")  # [[X（红队）]] 或 [[X（红队）|别名]]
EMPTY = re.compile(r"\[\[\s*\]\]")                       # [[]] 或 [[ ]]
# 去重重定向：[[X_N]] -> [[X]]（当 X 存在；处理压缩去重后残留的旧名链接，如 合同纠纷-模板_1）
DEDUP = re.compile(r"\[\[([^\[\]|#]+?)_(\d+)\]\]")

# 括号归一（v1.1 新增）：折叠畸形嵌套 wikilink，使 kg_scan 不再误判
BRACKET_OPEN = re.compile(r"\[{3,}")            # 3+ 个连续 [ -> [[
BRACKET_CLOSE = re.compile(r"\]{3,}")           # 3+ 个连续 ] -> ]]
REF_NEST = re.compile(r"\[\[([^\[\]]*?)\[\[")  # [[A [[  ->  A [[（剥离外层多余 [[，保留内层 [[B]]）

def _normalize_brackets(s):
    """幂等折叠：三重/多重括号 -> [[ ]]；引用式嵌套 [[A [[B]] -> A [[B]]。最多迭代 5 次收敛。"""
    cur = s
    for _ in range(5):
        t = BRACKET_OPEN.sub("[[", cur)
        t = BRACKET_CLOSE.sub("]]", t)
        t = REF_NEST.sub(r"\1[[", t)
        if t == cur:
            break
        cur = t
    return cur

def in_skip(f):
    """旧4规则：概念页目录 + meta 报告目录 均跳过。"""
    rel = f.replace(ROOT, "")
    return ("/概念页/" in rel) or any(meta in rel for meta in META_SKIP)

def in_meta_skip(f):
    """新括号归一规则：仅跳过 meta 报告目录（示例链接），概念页目录不跳过。"""
    rel = f.replace(ROOT, "")
    return any(meta in rel for meta in META_SKIP)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    # ---- 1) 源文件修复（旧4规则排除概念页；括号归一覆盖概念页）----
    stat = {"malformed": 0, "redblue": 0, "empty": 0, "dedup": 0, "bracket": 0, "files": 0}
    for f in md_files:
        txt = open(f, encoding="utf-8", errors="ignore").read()
        new = txt
        # 旧4规则：跳过概念页 + meta 报告目录
        if not in_skip(f):
            new, n1 = MALFORM.subn(r"[[\1]]", new)
            new, n2 = REDBLUE.subn(lambda m: "[[" + m.group(1) + (m.group(2) or "") + "]]", new)
            new, n3 = EMPTY.subn("双向链接", new)
            # 去重重定向
            def _ded(m):
                base = m.group(1)
                return "[[" + base + "]]" if base in existing else m.group(0)
            new, n4 = DEDUP.subn(_ded, new)
        else:
            n1 = n2 = n3 = n4 = 0
        # 新括号归一（v1.1）：仅跳过 meta 报告目录，概念页也处理
        if not in_meta_skip(f):
            new2 = _normalize_brackets(new)
            n5 = 1 if new2 != new else 0
            new = new2
        else:
            n5 = 0
        if n1 or n2 or n3 or n4 or n5:
            stat["malformed"] += n1; stat["redblue"] += n2; stat["empty"] += n3
            stat["dedup"] += n4; stat["bracket"] += n5; stat["files"] += 1
            if args.apply:
                open(f, "w", encoding="utf-8").write(new)
    print(f"[源修复] 文件={stat['files']} | 畸形={stat['malformed']} | 红蓝队={stat['redblue']} | 空链接={stat['empty']} | 去重重定向={stat['dedup']} | 括号归一={stat['bracket']}")
    if not args.apply:
        print("[dry-run] 加 --apply 实际写入。")

    # ---- 2) 删除垃圾概念页 ----
    junk_markers = ["[[", "]]", "#", "（红队）", "（蓝队）"]
    junk = [f for f in os.listdir(CONCEPT_DIR) if any(m in f for m in junk_markers)] if os.path.isdir(CONCEPT_DIR) else []
    print(f"[垃圾概念页] 待删 {len(junk)} 个")
    if args.apply:
        for f in junk:
            os.remove(os.path.join(CONCEPT_DIR, f))
        print(f"[删除] 已删 {len(junk)} 个垃圾概念页")

if __name__ == "__main__":
    main()
