#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
存量卡质量巡检 · 真实死链判定器（R29，2026-10-20）
------------------------------------------------
复用 R27 沙箱适配版 `_check_deadlinks_r27.py` 的 safe_read 函数（非阻塞），
复刻 R27/R28 的「前缀/别名判定」复核口径：

  classify_dead 把死链分为 真死链(编号/语法残片) 与 待建笔记(主题名软引用)；
  对 真死链 再做前缀判定 —— 若其前导编号（R-XX-NNN / LC-NNN / IMA-NNN / 数字串）
  在跨库基名集中存在同名前缀卡片，则属「标题变体/别名引用」，非真实缺陷，不计可修。

输出：真实死链（前缀无任何匹配）列表 + 计数。
"""
import importlib.util
import os
import re

R27 = "/tmp/_check_deadlinks_r27.py"
spec = importlib.util.spec_from_file_location("r27", R27)
r27 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r27)

PREF = re.compile(r'^(R-[A-Z]{2}-\d+|LC-\d+|IMA-\d+|\d{3,})')

def main():
    allmd = r27.build_basename_set()
    # 前缀索引：前导编号 -> 存在的基名列表
    prefix_index = {}
    for name in allmd:
        m = PREF.match(name)
        if m:
            prefix_index.setdefault(m.group(1), []).append(name)

    targets = r27.md_files()
    all_dead = []
    for p in sorted(targets):
        dead, total, err = r27.check_one(p, allmd)
        all_dead.extend(dead)

    real, pending = r27.classify_dead(all_dead)

    genuine = []
    alias_matched = 0
    for link in real:
        norm = r27.normalize(link)
        m = PREF.match(norm)
        if m and m.group(1) in prefix_index:
            alias_matched += 1
            continue
        genuine.append((norm, m.group(1) if m else None))

    print("基名集总数（跨库）: %d" % len(allmd))
    print("朴素真死链（编号/语法残片）: %d" % len(real))
    print("  其中前缀命中（标题变体/别名引用，非缺陷）: %d" % alias_matched)
    print("🌱 待建笔记（主题名软引用，非缺陷）: %d" % len(pending))
    print("")
    print("🔴 真实死链（前缀无任何匹配，须人工路由/P0-4）: %d" % len(genuine))
    for g, code in genuine:
        print("   - [%s] %s" % (code or "?", g))

if __name__ == "__main__":
    main()
