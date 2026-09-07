# -*- coding: utf-8 -*-
r"""
嵌套列表还原器 v1.0（2026-09-07 续 · 治本收尾）
---------------------------------------------
针对 A 方案（frontmatter wiki 转纯文本）覆盖不到的一类历史残留：
    A 方案只剥「含 [[ 的文本」；但有一部分文件里 `[[ ]]` 早已被 Obsidian 重写成
    嵌套列表（如 `related_links: [['R-HT-040|R-HT-040']]` / `[[['X|Y']]]`），
    已经没有 `[[` 可剥。这些文件 YAML 能解析（list-of-list 是合法 YAML），
    但**数据已损坏**——本应是「链接目标名的扁平列表」，却变成了嵌套列表。

本脚本把这种 Obsidian wiki 链接指纹「单元素列表包字符串」逐层剥掉，
并取 `|` 前的链接目标名（与 A 方案 `[[X|Y]]→X` 同口径），还原为纯标量扁平列表。

安全（安全六-B）：
  · 默认 dry-run；--apply 必须带 --backup
  · 跳过 .workbuddy / .backup* / .bak_* / _backup / 回收站 .trash*
  · **外科手术式**：只重写损坏字段的那几行，frontmatter 其他字段、正文一字不动
  · 仅当「所有损坏字段经还原后都不再含 list-of-list」才写盘；存在合法双层列表的跳过人工
"""
import argparse, io, os, re, shutil, sys
import yaml

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
SKIP_DIRS = {".workbuddy", ".git", "node_modules", "__pycache__", ".venv", "venv"}

def itermd():
    for r, dirs, fs in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".backup")]
        for fn in fs:
            if not fn.endswith(".md"): continue
            if ".bak_" in fn or ".bak-" in fn: continue
            p = os.path.join(r, fn)
            if "_backup" in p or "/备份" in p: continue
            if "/.trash" in p or p.startswith(ROOT + "/.trash"): continue
            yield p

FM_KEY_RE = re.compile(r'^([\w\-\u4e00-\u9fa5]+):(.*)$')
FM_INDENT_RE = re.compile(r'^\s+\S')

def locate_fm(lines):
    for i in range(1, len(lines)):
        s = lines[i].strip()
        if s in ("---", "..."): return i, True
        if s == "": continue
        if FM_KEY_RE.match(lines[i]) or FM_INDENT_RE.match(lines[i]): continue
        return i, False
    return len(lines), False

def split_doc(txt):
    if not txt.startswith("---"): return None, txt, False
    lines = txt.split("\n"); end, closed = locate_fm(lines)
    fm = "\n".join(lines[1:end])
    body = "\n".join(lines[end+1:]) if closed else "\n".join(lines[end:])
    return fm, body, not closed

def looks_damaged(d):
    if not isinstance(d, dict): return False
    def bad(v, depth=0):
        if isinstance(v, list):
            if depth >= 1 and any(isinstance(x, (list, dict)) for x in v): return True
            return any(bad(x, depth+1) for x in v)
        if isinstance(v, dict):
            return any(bad(x, depth) for x in v.values())
        return False
    return any(bad(v) for v in d.values())

def strip_alias(s):
    return s.split("|")[0].strip()

def reduce_wiki(v):
    """递归还原 Obsidian wiki 指纹 `[['X|Y']]` / `[[['X|Y']]]` → 'X'。"""
    if not isinstance(v, list):
        return v
    inner = [reduce_wiki(x) for x in v]
    out = []
    for x in inner:
        if isinstance(x, list) and len(x) == 1 and isinstance(x[0], str):
            out.append(strip_alias(x[0]))
        else:
            out.append(x)
    if len(out) == 1 and isinstance(out[0], list):
        return out[0]
    return out

def find_span(fm_lines, key):
    start = None
    for i, ln in enumerate(fm_lines):
        m = re.match(r'^([\w\-\u4e00-\u9fa5]+):', ln)
        if m and m.group(1) == key:
            start = i; break
    if start is None:
        return None
    base_indent = len(fm_lines[start]) - len(fm_lines[start].lstrip())
    end = len(fm_lines)
    for i in range(start + 1, len(fm_lines)):
        stripped = fm_lines[i].strip()
        if stripped == "":
            continue
        indent = len(fm_lines[i]) - len(fm_lines[i].lstrip())
        if indent <= base_indent:
            end = i; break
    return start, end

def render_block(key, val):
    block = yaml.safe_dump({key: val}, sort_keys=False, allow_unicode=True, default_flow_style=False).rstrip("\n")
    lines = block.split("\n")
    # 列表项加 2 空格缩进，贴合 vault 风格
    for i in range(1, len(lines)):
        if lines[i].startswith("- "):
            lines[i] = "  " + lines[i]
    return lines

def plan(path):
    txt = io.open(path, encoding="utf-8").read()
    fm, body, missing_close = split_doc(txt)
    if fm is None:
        return "ok", txt, None
    try:
        d = yaml.safe_load(fm)
    except Exception:
        return "ok", txt, None   # 解析失败不归本脚本管（已另有流程）
    if not isinstance(d, dict) or not looks_damaged(d):
        return "ok", txt, None
    # 严格判定损坏键（walk）：含 list-of-list 的顶层键
    def walk(v, depth=0):
        if isinstance(v, list):
            if depth >= 1 and any(isinstance(x, (list, dict)) for x in v): return True
            return any(walk(x, depth+1) for x in v)
        if isinstance(v, dict):
            return any(walk(x, depth) for x in v.values())
        return False
    bad_keys = [k for k, v in d.items() if walk(v, 0)]
    fm_lines = fm.split("\n")
    new_fm_lines = list(fm_lines)
    all_fixed = True
    for k in bad_keys:
        newval = reduce_wiki(d[k])
        # 还原后该键仍损坏 → 存在合法双层列表，整文件跳过人工
        if walk(newval, 0):
            all_fixed = False
            break
        span = find_span(new_fm_lines, k)
        if span is None:
            all_fixed = False; break
        s, e = span
        new_fm_lines[s:e] = render_block(k, newval)
    if not all_fixed:
        return "skip", txt, None
    new_fm = "\n".join(new_fm_lines)
    # 再次校验整体
    try:
        nd = yaml.safe_load(new_fm)
    except Exception:
        return "skip", txt, None
    if looks_damaged(nd):
        return "skip", txt, None
    new = "---\n" + new_fm + "\n---\n" + body
    return "fixed", new, (len(bad_keys), bad_keys)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--backup", metavar="DIR")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    fixed, skipped = [], []
    for p in itermd():
        st, _, info = plan(p)
        if st == "fixed":
            fixed.append((p, info))
        elif st == "skip":
            skipped.append(p)
    print("=" * 64)
    print(f"模式            ：{'APPLY' if args.apply else 'DRY-RUN'}")
    print(f"可还原(嵌套→标量)：{len(fixed)}")
    print(f"跳过(含合法双层) ：{len(skipped)}")
    print("=" * 64)
    if fixed:
        print("\n[可还原样本]")
        for p, info in fixed[:30]:
            print(f"   {os.path.relpath(p, ROOT)}  键={info[1]}")
        if len(fixed) > 30:
            print(f"   … 另有 {len(fixed)-30} 个")
    if skipped:
        print("\n[跳过样本]")
        for p in skipped[:20]:
            print(f"   ⚠ {os.path.relpath(p, ROOT)}")
    if not args.apply:
        print("\n[dry-run] 未写盘。确认后加 --apply --backup <目录>。")
        sys.exit(0)
    if args.backup:
        for p, _ in fixed:
            rel = os.path.relpath(p, ROOT)
            tgt = os.path.join(args.backup, rel)
            os.makedirs(os.path.dirname(tgt), exist_ok=True)
            shutil.copy2(p, tgt)
        print(f"\n✅ 已备份 {len(fixed)} 个文件 → {args.backup}")
    n_written = 0
    for p, _ in fixed:
        _, new, _ = plan(p)
        io.open(p, "w", encoding="utf-8").write(new)
        n_written += 1
    print(f"✅ 已还原 {n_written} 个文件")
    # 复检
    left = 0
    for p in itermd():
        st, _, _ = plan(p)
        if st in ("fixed", "skip"):
            left += 1
    print(f"复检：仍有嵌套损坏 {left} 个")
    sys.exit(0)

if __name__ == "__main__":
    main()
