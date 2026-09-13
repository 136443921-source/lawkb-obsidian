#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法条依据段标题「虚标权威核填」修正（2026-09-13）
背景：模板标题标配写作「## 四、法条依据（元典核填·现行有效，含官方核验指引）」，
      但部分卡实际条文全部/部分为「待回源」——标题与内容不符，
      违反「绝不虚标元典/法宝核填」铁律（坑 31 / 坑 40 同源：
      宁可暴露不确定性，不可制造确定性的假象）。
规则：
  - 零真核填（全待回源） → 「⏳ 待回源·未核填」
  - 部分核填且仍有待回源 → 「部分核填·含待回源」
  - 已全核填 → 不动（本轮 0 张）
只改标题行，不动正文与法条块。
用法：python _fix_statute_heading_20260913.py [--apply]
"""
import os, re, glob, shutil, json, sys

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
APPLY = "--apply" in sys.argv
BK = "/tmp/存量卡巡检标题修正_20260913-1112"
os.makedirs(BK, exist_ok=True)

# 权威核填的两种真标注形态
REAL = re.compile(r'\[(?:企查查·法律数据核填|北大法宝核填|华宇元典核填)[^\]]*\]\(http'
                  r'|\*(?:企查查·法律数据核填|北大法宝核填|华宇元典核填)·现行有效\*')
HEAD = re.compile(r'^(#{1,4}\s*[四4][、.．]\s*法条依据[（(])([^）)]*)([）)])', re.M)
VIRTUAL = re.compile(r'元典核填|北大法宝核填|企查查·法律数据核填')

changed, skipped = [], []
for p in sorted(glob.glob(os.path.join(BASE, "06-沉淀/裁判规则库/**/R-*.md"), recursive=True)):
    t = open(p, encoding="utf-8").read()
    if not re.search(r'(?m)^statute_text_pending: true', t):
        continue
    n_real = len(REAL.findall(t))
    n_pend = t.count("待回源")
    m = HEAD.search(t)
    if not m:
        continue
    old_qual = m.group(2)
    if not VIRTUAL.search(old_qual):
        continue
    if n_real > 0 and n_pend == 0:
        skipped.append((os.path.basename(p), "已全核填，不动"))
        continue
    new_qual = "⏳ 待回源·未核填" if n_real == 0 else "部分核填·含待回源"
    newt = t[:m.start(2)] + new_qual + t[m.end(2):]
    if newt == t:
        continue
    changed.append((os.path.relpath(p, BASE), old_qual, new_qual, n_real, n_pend))
    if APPLY:
        rel = os.path.relpath(p, BASE)
        dst = os.path.join(BK, rel.replace("/", "__"))
        if not os.path.exists(dst):
            shutil.copy2(p, dst)
        open(p, "w", encoding="utf-8").write(newt)

print(f"模式：{'APPLY' if APPLY else 'DRY-RUN'}")
print(f"修正标题：{len(changed)} 张 | 跳过：{len(skipped)} 张")
for c in changed[:8]:
    print(f"   {os.path.basename(c[0])[:46]}")
    print(f"      「{c[1]}」→「{c[2]}」  (真核填{c[3]}/待回源{c[4]})")
if len(changed) > 8:
    print(f"   … 另 {len(changed)-8} 张")
json.dump([{"card": c[0], "old": c[1], "new": c[2], "n_real": c[3], "n_pend": c[4]}
           for c in changed], open("/tmp/heading_fix_0913.json", "w"),
          ensure_ascii=False, indent=1)
