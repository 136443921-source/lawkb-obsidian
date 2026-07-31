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

def in_skip(f):
    rel = f.replace(ROOT, "")
    return ("/概念页/" in rel) or any(meta in rel for meta in META_SKIP)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    # ---- 1) 源文件修复（排除概念页目录与 meta 报告目录）----
    stat = {"malformed": 0, "redblue": 0, "empty": 0, "dedup": 0, "files": 0}
    for f in md_files:
        if in_skip(f):
            continue
        txt = open(f, encoding="utf-8", errors="ignore").read()
        new = txt
        new, n1 = MALFORM.subn(r"[[\1]]", new)
        new, n2 = REDBLUE.subn(lambda m: "[[" + m.group(1) + (m.group(2) or "") + "]]", new)
        new, n3 = EMPTY.subn("双向链接", new)
        # 去重重定向
        def _ded(m):
            base = m.group(1)
            return "[[" + base + "]]" if base in existing else m.group(0)
        new, n4 = DEDUP.subn(_ded, new)
        if n1 or n2 or n3 or n4:
            stat["malformed"] += n1; stat["redblue"] += n2; stat["empty"] += n3
            stat["dedup"] += n4; stat["files"] += 1
            if args.apply:
                open(f, "w", encoding="utf-8").write(new)
    print(f"[源修复] 文件={stat['files']} | 畸形={stat['malformed']} | 红蓝队={stat['redblue']} | 空链接={stat['empty']} | 去重重定向={stat['dedup']}")
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
