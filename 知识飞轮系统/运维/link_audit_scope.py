#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方案 C · 按子域精准链接校验器（link_audit --scope 版）
========================================================
复用 link_audit 的全局 stem/alias 索引构建逻辑，但把「断链报告」过滤到
指定 sub_domain 内的卡片——即只为「指向本子域卡片却解析失败」的链接报警，
从而让索引校验按子域精准，不被全库噪声干扰。

用法：
  python3 link_audit_scope.py --sub 医疗人损
  python3 link_audit_scope.py --sub 交通人损 --quiet
  python3 link_audit_scope.py --all            # 四个子域各跑一遍
退出码：0 = 该子域内无断链   1 = 有断链
"""
import re, sys, os, glob, unicodedata
from pathlib import Path
from collections import defaultdict

V = Path("/Users/chenyouqiang/Documents/LawKB")
DOMAIN_DIR = V / "知识飞轮系统/06-沉淀/人伤法域库"
SKIP = ['.backup', '/.git', '.obsidian', '.trash', 'node_modules', '/_recovery_tmp/']
SUBS = ["医疗人损", "交通人损", "工伤人损", "其它人损"]

def norm(s):
    return unicodedata.normalize('NFC', s).strip()

# ---------- 建解析索引（限定到 R-PI 卡片实际所在目录，避免全库扫描） ----------
STEM_DIRS = [
    "知识飞轮系统/06-沉淀/人伤法域库",
    "知识飞轮系统/03-连接/概念页",
    "知识飞轮系统/02-提炼/经验卡片/法条解读",
    "知识飞轮系统/02-提炼/经验卡片/人伤",
]
stems, aliases = set(), set()
ALIAS_INLINE = re.compile(r'^aliases?:\s*\[(.*?)\]\s*$', re.M)
for d in STEM_DIRS:
    base = V / d
    if not base.exists():
        continue
    for p in base.rglob("*.md"):
        stems.add(norm(p.stem))
        stems.add(norm(p.name))
        try:
            txt = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        for am in ALIAS_INLINE.finditer(txt):
            for a in re.findall(r'"([^"]+)"|\'([^\']+)\'|([^,\]]+)', am.group(1)):
                aliases.add(norm((a[0] or a[1] or a[2]).strip()))

# ---------- 加载 sub_domain 映射 ----------
def norm_key(s):
    m = re.match(r"(R-PI-\d+)", s)
    return m.group(1) if m else s

sub_map = {}
for f in DOMAIN_DIR.rglob("R-PI-*.md"):
    txt = f.read_text(encoding='utf-8', errors='ignore')
    m = re.search(r"^---\n(.*?)\n---", txt, re.S)
    if not m:
        continue
    rid = norm_key(f.name)
    sd = re.search(r"^sub_domain:\s*(\S+)", m.group(1), re.M)
    sub_map[rid] = sd.group(1) if sd else "其它人损"

WIKILINK = re.compile(r'\[\[([^\]]+)\]\]')

def resolve(target):
    t = norm(target)
    if t in stems or t in aliases:
        return True
    # 去除 | 别名后再试
    base = t.split('|')[0].strip()
    if base in stems or base in aliases:
        return True
    return False

def audit(sub):
    targets = {rid for rid, s in sub_map.items() if s == sub}
    broken = []
    checked = 0
    for f in DOMAIN_DIR.rglob("R-PI-*.md"):
        rid = norm_key(f.name)
        if sub_map.get(rid) != sub:
            continue
        txt = f.read_text(encoding='utf-8', errors='ignore')
        for wl in WIKILINK.finditer(txt):
            inner = wl.group(1)
            tgt = norm(inner.split('|')[0].strip())
            m = re.match(r"(R-PI-\d+)", tgt)
            if not m:
                continue
            if m.group(1) in targets:  # 指向本子域卡片
                checked += 1
                if not resolve(tgt):
                    broken.append((rid, inner))
    return targets, checked, broken

if __name__ == "__main__":
    args = sys.argv[1:]
    if "--all" in args:
        subs = SUBS
        rc = 0
        for s in subs:
            tgt, chk, brk = audit(s)
            print(f"【{s}】卡片 {len(tgt)} 张 ｜ 域内链接校验 {chk} 条 ｜ 断链 {len(brk)} 条")
            for r, link in brk[:20]:
                print(f"   ❌ {r} -> [[{link}]]")
            if brk:
                rc = 1
        sys.exit(rc)
    # 单子域
    if "--sub" not in args:
        print("用法: python3 link_audit_scope.py --sub 医疗人损 | --all")
        sys.exit(2)
    sub = args[args.index("--sub") + 1]
    quiet = "--quiet" in args
    tgt, chk, brk = audit(sub)
    if not quiet:
        print(f"【{sub}】卡片 {len(tgt)} 张 ｜ 域内链接校验 {chk} 条 ｜ 断链 {len(brk)} 条")
        for r, link in brk[:50]:
            print(f"   ❌ {r} -> [[{link}]]")
    sys.exit(1 if brk else 0)
