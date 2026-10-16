#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LawKB [[ ]] 双链完整性检查器（Task 44）
在 Obsidian vault 范围（LawKB 根目录）内解析所有 md 的 [[双链]]，
判定每条链接能否解析到真实笔记，输出断链报告。

口径（重要）：
- vault = LawKB 根目录（法条银行只是其子库）—— 双链可指向库外的笔记/经验卡，
  故不能只扫法条银行，否则大量误报。
- 解析规则按 Obsidian：取链接目标 basename 或相对路径，去掉 [[ ]] 与 |显示名，
  忽略 #锚点 与 ^块引用；命中「任一目录下同名文件」即视为可解析。
- 排除：银行治理层生成物、_archive、代码块/行内代码中的 [[ ]]。

用法：
  python3 check_obsidian_links.py                 # 全库，输出断链明细
  python3 check_obsidian_links.py --scope 法条银行  # 仅法条银行子库发起源
  python3 check_obsidian_links.py --out 报告.md    # 写报告
"""
import os, re, sys, glob, collections

VAULT = "/Users/chenyouqiang/Documents/LawKB"
LINK = re.compile(r"\[\[([^\[\]]+?)\]\]")
CODE_FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]*`")
# 目标索引跳过的大目录：仅跳系统/临时目录。
# 知识飞轮系统虽大但**必须索引**——法条银行大量双链指向其中的经验卡/规则卡，
# 不索引会造成大面积误报（已实测 7367 篇，os.walk 可在数秒内完成）。
SKIP_DIRS = {".git", ".obsidian", ".trash", "node_modules", "__pycache__"}

def args():
    a = sys.argv[1:]
    def g(flag, default=None):
        return a[a.index(flag)+1] if flag in a else default
    return g("--scope"), g("--out")

def load_notes(scope=None):
    """建立 vault 内所有笔记的 basename 集合 + 相对路径集合（os.walk，跳过大目录）"""
    names = collections.defaultdict(list)
    rels = set()
    root = VAULT
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for f in filenames:
            if not f.endswith(".md"):
                continue
            p = os.path.join(dirpath, f)
            rel = os.path.relpath(p, root)
            base = f[:-3]
            names[base].append(rel)
            rels.add(rel[:-3])
    return names, rels

def extract_links(text):
    """剥离围栏代码块后抽 [[ ]]。
    注意：**不剥离行内代码**——Obsidian 的 [[ ]] 目标名可合法含反引号
    （如 RULE-039-旧无指纹件-`xx.md`(2012通过版)…），剥离会把链接截断造成误报。
    行内代码里的 [[ ]] 极少且危害小于误报，故不处理。"""
    text = CODE_FENCE.sub("", text)
    return LINK.findall(text)

def resolve(target, names, rels):
    t = target.split("|")[0].strip()
    t = t.split("#")[0].strip()      # 去锚点
    t = t.split("^")[0].strip()      # 去块引用
    if not t:
        return None
    base = os.path.basename(t)
    if base in names:
        return names[base][0]
    if t in rels:
        return t
    return None

def collect_srcs(scope):
    """按 scope 收集源文件（scope 相对 vault；默认 法条银行）
    发起源额外排除 _archive 与 银行治理层（存档卡与本工具自身的报告不纳入统计）"""
    root = os.path.join(VAULT, scope) if scope else VAULT
    src_skip = SKIP_DIRS | {"_archive", "银行治理层"}
    srcs = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in src_skip and not d.startswith(".")]
        for f in filenames:
            if f.endswith(".md"):
                srcs.append(os.path.join(dirpath, f))
    return srcs

def main():
    scope, out = args()
    if scope is None:
        scope = "法条银行"   # 默认只做法条银行发起源（库内双链完整性）
    names, rels = load_notes()
    print(f"[vault] 已索引(跳过{'/'.join(sorted(SKIP_DIRS))}) 笔记 basename {len(names)} 个 / 路径 {len(rels)} 条")

    srcs = collect_srcs(scope)
    total_links = 0
    broken = []   # (src_rel, target, reason)
    for p in srcs:
        try:
            txt = open(p, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        rel = os.path.relpath(p, VAULT)
        seen = set()
        for lk in extract_links(txt):
            key = lk.split("|")[0].strip()
            if key in seen:
                continue
            seen.add(key)
            total_links += 1
            if resolve(lk, names, rels) is None:
                broken.append((rel, lk.split("|")[0].strip()))

    print(f"[扫描] 范围={scope} 源文件 {len(srcs)} 个，去重双链 {total_links} 条")
    print(f"[结果] 断链 {len(broken)} 条")
    # 断链按目标聚类，看哪些最常见（优先修高频）
    by_target = collections.Counter(t for _, t in broken)
    if by_target:
        print("\n—— 断链目标 TOP20（按出现次数）——")
        for t, c in by_target.most_common(20):
            print(f"  {c:3d}×  {t}")

    lines = []
    lines.append(f"# LawKB 双链完整性报告\n")
    lines.append(f"- vault：`{VAULT}`\n- 源文件：{len(srcs)} · 去重双链：{total_links} · 断链：{len(broken)}\n")
    if by_target:
        lines.append("\n## 断链目标（按频次）\n")
        lines.append("| 次数 | 断链目标 |")
        lines.append("|---|---|")
        for t, c in by_target.most_common():
            lines.append(f"| {c} | {t} |")
        lines.append("\n## 断链明细（源 → 目标）\n")
        for s, t in sorted(broken):
            lines.append(f"- `{s}` → [[{t}]]")
    if out:
        open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
        print(f"\n[OK] 报告已写出：{out}")

if __name__ == "__main__":
    main()