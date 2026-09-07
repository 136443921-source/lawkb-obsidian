#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
YAML frontmatter 修复器 v1.0（2026-09-07 · 治本向）
--------------------------------------------------
用途：修复知识飞轮系统中**解析失败的 YAML frontmatter**，让 frontmatter 重新可被机器读取。

🔴 根因（2026-09-07 全库体检实证，330 个坏卡里 307 个＝93% 同源）：
    **Obsidian 双链语法 `[[笔记名|别名]]` 被裸写进 YAML 值。**
    YAML 见到值以 `[` 开头 → 按 **flow sequence** 解析 → 序列内出现 `|`
    （在 flow context 中 `|` 是非法字符）→ 解析失败。
    典型坏例：
        title: [[保证合同纠纷实务100问|保证合同纠纷实务100问]]｜蓝红双视角审查
        tags: [人伤法, 医疗合规, [[医疗纠纷预防和处理|医疗纠纷预防和处理]]条例]
    次因（SKILL 坑 1）：值以半角双引号 `"` 开头 → 被当 quoted scalar，闭合后余字符报错。

为什么算「治本」：
    · 不是逐个改文件，而是**按错误类型自动施治**（加引号包裹），同类一次清完
    · 修复后**用 yaml.safe_load 逐卡验证**，不通过的不写盘、单列待人工
    · 配套在采集/生成模板侧禁用「裸写 wiki 链接进 frontmatter」（见 SKILL 坑 1 与坑 17）

修复策略（最小 diff 优先）：
    1. 逐行扫描 frontmatter
    2. 对「值未加引号但含 `[` `|` 或以 `"` 开头、或含 ': '」的标量 → 用双引号包裹
    3. 对「列表项含 `[[` 或 `|`」的 → 同样包裹
    4. 再次 safe_load 验证；通过才写盘，不通过单列

安全（安全六-B）：
    · 默认 dry-run；`--apply` 必须带 `--backup`
    · 跳过 `.workbuddy` / `.backup*` / `.bak_*` / `_backup`
    · **只改 frontmatter，正文一字不动**

用法：
    PY=/Users/chenyouqiang/.workbuddy/binaries/python/envs/default/bin/python
    $PY _fix_yaml_frontmatter.py --dry-run                       # 看能修多少
    $PY _fix_yaml_frontmatter.py --apply --backup /tmp/xxx       # 备份后写盘
    $PY 02-提炼/审判要件卡/_check_deadlinks.py --all              # 复检（应不再有解析失败）

退出码：0 = 全部修复或无待修项；1 = 仍有无法自动修复的（会打印清单）
"""
import argparse
import io
import os
import re
import shutil
import sys

import yaml

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
SKIP_DIRS = {".workbuddy", ".git", "node_modules", "__pycache__", ".venv", "venv"}

# 「键: 值」——顶格或缩进的标量行（排除列表项 `- `）
SCALAR_RE = re.compile(r'^(\s*)([\w\-\u4e00-\u9fa5]+):(\s+)(.*)$')
# 列表项
ITEM_RE = re.compile(r'^(\s*)- (.*)$')

# Obsidian 双链：`[[笔记名]]` / `[[笔记名|别名]]`
WIKI_RE = re.compile(r'\[\[([^\]\|]+)(?:\|([^\]]+))?\]\]')


def strip_wiki_in_fm(fm):
    """🔴 治本（老强 2026-09-07 拍板 A 方案）：
    frontmatter 内的 `[[笔记名|别名]]` → `笔记名`（保留链接目标，丢语法与别名）。

    为什么必须剥：Obsidian 对 frontmatter 中的 wiki 链接有**独立链接语义**，
    引号都挡不住（见 SKILL 坑 18），只要它重写文件就落成嵌套序列、`[[ ]]` 被吃。
    正解＝frontmatter 只存**纯文本标识符**，链接一律放正文。

    注意：**只处理 frontmatter，正文的 `[[...]]` 一字不动**。
    """
    return WIKI_RE.sub(lambda m: m.group(1).strip(), fm)


def itermd():
    for r, dirs, fs in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".backup")]
        for fn in fs:
            if not fn.endswith(".md"):
                continue
            if ".bak_" in fn or ".bak-" in fn:
                continue
            p = os.path.join(r, fn)
            if "_backup" in p or "/备份" in p:
                continue
            if "/.trash" in p or p.startswith(ROOT + "/.trash"):   # 回收站不动
                continue
            yield p


def quote(v):
    """用双引号包裹，内部双引号转义。"""
    s = v.strip()
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def line_parses(ln):
    """逐行试解析——比启发式判断准确得多。

    启发式的坑（v1.0 初版踩过）：值以 `"` 开头就以为"已加引号"从而跳过，
    但 `title: ""R-HG-049-xxx""` 这种**引号不成对/多余**的同样非法。
    逐行交给 YAML 自己判，天然覆盖所有类型（wiki 链接 / 引号 / 冒号 / Tab…）。
    """
    if not ln.strip():
        return True
    try:
        yaml.safe_load(ln + "\n")
        return True
    except Exception:
        return False


# 「伪块标量」：`key: > 文本` / `key: |文本` —— 指示符**同一行还有内容**。
# 采集模板本意是把「以 > 开头的引用句」当普通文本，YAML 却当块标量指示符，
# 于是去下一行找缩进内容而不得 → `while scanning a block scalar`。
# 真正的块标量写作 `key: |` 后换行缩进，**同行无内容**，故不会被误伤。
PSEUDO_BLOCK_RE = re.compile(r'^(\s*)([\w\-\u4e00-\u9fa5]+):(\s+)([|>][-+0-9]*)(\s+)(\S.*)$')


def fix_frontmatter(fm):
    """返回修复后的 frontmatter 文本：逐行试解析，坏行加引号重解析。"""
    out = []
    for ln in fm.split("\n"):
        # 伪块标量优先处理（单独试解析会"假成功"，必须提前拦）
        m = PSEUDO_BLOCK_RE.match(ln)
        if m:
            ind, key, sp, indi, sp2, rest = m.groups()
            cand = f"{ind}{key}:{sp}{quote(indi + sp2 + rest)}"
            out.append(cand if line_parses(cand) else ln)
            continue

        # 🔴 含 wiki 双链 `[[\u2026]]` 的标量 / 列表项 → **无条件加引号**
        #    教训（2026-09-07）：`title: [[a|b]]` **单行试解析是"成功"的**——
        #    YAML 把它读成嵌套列表 `[["a|b"]]`，于是 v1.0 不加引号放过去；
        #    随后 Obsidian 按"列表"重新序列化 → 落成 `title:\n  - - a|b`，
        #    `[[`/`]]` 被吃掉，**42 个文件数据损坏**（已回滚）。
        #    正确做法：凡含 `[[` 就加引号，锁死为字符串，杜绝被曲解。
        m = SCALAR_RE.match(ln)
        if m and "[[" in m.group(4):
            ind, key, sp, val = m.groups()
            cand = f"{ind}{key}:{sp}{quote(val)}"
            out.append(cand if line_parses(cand) else ln)
            continue
        m = ITEM_RE.match(ln)
        if m and "[[" in m.group(2):
            ind, val = m.group(1), m.group(2)
            cand = f"{ind}- {quote(val)}"
            out.append(cand if line_parses(cand) else ln)
            continue

        if line_parses(ln):
            out.append(ln)
            continue
        m = SCALAR_RE.match(ln)
        if m:
            indent, key, sp, val = m.groups()
            for cand in (f"{indent}{key}:{sp}{quote(val)}",
                         f"{indent}{key}:{sp}'{val.strip()}'"):
                if line_parses(cand):
                    out.append(cand)
                    break
            else:
                out.append(ln)
            continue
        m = ITEM_RE.match(ln)
        if m:
            indent, val = m.group(1), m.group(2)
            for cand in (f"{indent}- {quote(val)}", f"{indent}- '{val.strip()}'"):
                if line_parses(cand):
                    out.append(cand)
                    break
            else:
                out.append(ln)
            continue
        out.append(ln)
    return "\n".join(out)


# frontmatter 行形态：顶格 `key: …`；或任意缩进续行（列表项 `  - x`、块标量内容）
FM_KEY_RE = re.compile(r'^([\w\-\u4e00-\u9fa5]+):(.*)$')
FM_INDENT_RE = re.compile(r'^\s+\S')


def locate_fm(lines):
    """结构感知地定位 frontmatter 结束位置。

    🔴 为什么不能 `txt.find("\\n---", 3)`：
       2026-09-07 实证 58 个文件的 frontmatter **根本没有闭合 `---`**（采集模板漏写），
       `find` 会一路找到**正文里的分隔线**，把整段正文当成 frontmatter，
       于是报出莫名的 "while scanning a block scalar"（其实是正文里的 `> 引用句`）。
       本函数按「行形态」判断边界，不再依赖闭合符一定存在。

    返回 (end_index, closed)；`closed=False` 表示缺闭合符，需要补。
    """
    for i in range(1, len(lines)):
        s = lines[i].strip()
        if s in ("---", "..."):
            return i, True
        if s == "":
            continue
        if FM_KEY_RE.match(lines[i]) or FM_INDENT_RE.match(lines[i]):
            continue
        return i, False        # 顶格又不是 key → frontmatter 到此为止
    return len(lines), False


def split_doc(txt):
    """拆出 (frontmatter 原文, 正文, 是否缺闭合符)。无 frontmatter → (None, txt, False)。"""
    if not txt.startswith("---"):
        return None, txt, False
    lines = txt.split("\n")
    end, closed = locate_fm(lines)
    fm = "\n".join(lines[1:end])
    body = "\n".join(lines[end + 1:]) if closed else "\n".join(lines[end:])
    return fm, body, not closed


def plan(path):
    """返回 (状态, 新全文)。状态：ok / stripped / stripped_closed / fixed / fixed_closed / failed"""
    txt = io.open(path, encoding="utf-8").read()
    fm, body, missing_close = split_doc(txt)
    if fm is None:
        return "ok", txt

    # ① 先剥 frontmatter 的 wiki 语法（治本，优先级最高）
    if "[[" in fm:
        stripped = strip_wiki_in_fm(fm)
        try:
            d = yaml.safe_load(stripped)
            if not looks_damaged(d):
                new = "---\n" + stripped + "\n---\n" + body
                return ("stripped_closed" if missing_close else "stripped"), new
        except yaml.YAMLError:
            pass
        fm = stripped          # 剥完仍失败 → 带着剥离结果继续走行级修复

    try:
        yaml.safe_load(fm)
        if not missing_close:
            return "ok", txt
        new = "---\n" + fm + "\n---\n" + body      # 仅补闭合符
        return "fixed_closed", new
    except yaml.YAMLError:
        pass
    new_fm = fix_frontmatter(fm)
    try:
        d = yaml.safe_load(new_fm)
    except yaml.YAMLError:
        return "failed", txt
    # 🛡️ 安全网：修复后若出现「嵌套列表」，说明字符串值被曲解成列表 → 拒绝写盘
    if looks_damaged(d):
        return "failed", txt
    # 修复后统一补/保留闭合符
    new = "---\n" + new_fm + "\n---\n" + body
    return ("fixed_closed" if missing_close else "fixed"), new


def looks_damaged(d):
    """安全网（2026-09-07 回滚事故后加装）：
    frontmatter 中出现 list-of-list，几乎必然是「原为字符串的 `[[a|b]]`
    被 YAML/Obsidian 读成嵌套列表」——宁可不修，也不能写坏。"""
    if not isinstance(d, dict):
        return False

    def bad(v, depth=0):
        if isinstance(v, list):
            if depth >= 1 and any(isinstance(x, (list, dict)) for x in v):
                return True
            return any(bad(x, depth + 1) for x in v)
        if isinstance(v, dict):
            return any(bad(x, depth) for x in v.values())
        return False

    return any(bad(v) for v in d.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--backup", metavar="DIR")
    ap.add_argument("--dry-run", action="store_true", help="显式声明只读（默认即只读）")
    args = ap.parse_args()

    if args.apply and not args.backup:
        sys.stderr.write("⚠️  --apply 未提供 --backup。建议先备份。\n")
        try:
            if input("确认继续？(y/N) ").strip().lower() != "y":
                sys.exit(0)
        except EOFError:
            sys.exit(0)

    fixed, failed = [], []
    for p in itermd():
        st, _ = plan(p)
        if st in ("fixed", "fixed_closed", "stripped", "stripped_closed"):
            fixed.append(p)
        elif st == "failed":
            failed.append(p)

    print("=" * 64)
    print(f"模式          ：{'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"可自动修复    ：{len(fixed)}")
    print(f"无法自动修复  ：{len(failed)}")
    print("=" * 64)
    for p in failed[:20]:
        print(f"   ❌ {os.path.relpath(p, ROOT)}")
    if len(failed) > 20:
        print(f"   … 另有 {len(failed)-20} 个")

    if not args.apply:
        print("\n[dry-run] 未写盘。确认后加 --apply --backup <目录>。")
        sys.exit(0)

    if args.backup:
        for p in fixed:
            rel = os.path.relpath(p, ROOT)
            tgt = os.path.join(args.backup, rel)
            os.makedirs(os.path.dirname(tgt), exist_ok=True)
            shutil.copy2(p, tgt)
        print(f"\n✅ 已备份 {len(fixed)} 个文件 → {args.backup}")

    for p in fixed:
        _, new = plan(p)
        io.open(p, "w", encoding="utf-8").write(new)
    print(f"✅ 已修复 {len(fixed)} 个文件")

    left = sum(1 for p in itermd() if plan(p)[0] == "failed")
    print(f"复检：仍无法解析 {left} 个")
    sys.exit(1 if left else 0)


if __name__ == "__main__":
    main()
