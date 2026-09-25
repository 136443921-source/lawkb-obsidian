#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人伤法域库 · 断链批量修复 + R-PI-157 撞号回归
=============================================
alias 感知：复用 link_audit_scope 的 stem/alias 解析索引，替换前双重校验
  - 旧链接确实"不可解析"（确认是真断链，不误改已有效链接）
  - 新链接确实"可解析"（确认替换后不会引入新断链）
幂等：--apply 前先 dry-run（默认）；写入前对每文件做内容比对，仅当确有变更才写。
安全：--apply 前自动对 06-沉淀/人伤法域库 做时间戳 cp 备份。

用法：
  python3 fix_rpi_link_collision.py            # 默认 dry-run，仅打印计划
  python3 fix_rpi_link_collision.py --apply    # 实际写入（先自动备份）
"""
import re, sys, os, shutil, unicodedata
from pathlib import Path
from datetime import datetime

V = Path("/Users/chenyouqiang/Documents/LawKB")
DOMAIN = V / "知识飞轮系统/06-沉淀/人伤法域库"
STEM_DIRS = [
    "知识飞轮系统/06-沉淀/人伤法域库",
    "知识飞轮系统/03-连接/概念页",
    "知识飞轮系统/02-提炼/经验卡片/法条解读",
    "知识飞轮系统/02-提炼/经验卡片/人伤",
]
ALIAS_INLINE = re.compile(r'^aliases?:\s*\[(.*?)\]\s*$', re.M)
WIKILINK = re.compile(r'\[\[([^\]]+)\]\]')

def norm(s):
    return unicodedata.normalize('NFC', s).strip()

# ---------- 解析索引（与审计器一致） ----------
stems, aliases = set(), set()
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

def resolve(target):
    t = norm(target)
    if t in stems or t in aliases:
        return True
    base = t.split('|')[0].strip()
    if base in stems or base in aliases:
        return True
    return False

# ---------- 断链修复映射（inner 文本，不含 [[ ]]） ----------
# 来源：link_audit_scope.py --all 命中的 10 条 + 跨子域漏报 1 条（R-PI-365）
LINK_FIXES = [
    # 1) R-PI-367 自检旧名（采集笔记旧命名）
    ("R-PI-367-医疗纠纷选律师六维度与避坑指南.md",
     "R-PI-367-医疗纠纷怎么选律师-采集笔记-2026-09-11",
     "R-PI-367-医疗纠纷选律师六维度与避坑指南"),
    # 2) R-PI-423 -> R-PI-386 后缀不符 ×2
    ("R-PI-423-医疗事故罪严重不负责任与刑法因果关系认定.md",
     "R-PI-386-医疗过错参与度非法定概念",
     "R-PI-386-医疗过错参与度鉴定非法定概念应对照原因力六分情形确定赔偿责任"),
    # 3) R-PI-289 -> 采集笔记旧名（真实目标 = R-PI-366）
    ("R-PI-289-租赁、融资租赁与分期付款车辆的责任主体.md",
     "R-PI-289-医疗事故鉴定与医疗损害鉴定的区别-采集笔记-2026-09-11",
     "R-PI-366-医疗事故鉴定与医疗损害鉴定的本质区别与裁判适用"),
    # 4) R-PI-366 -> 采集笔记旧名（自检，真实目标 = 自身 R-PI-366）
    ("R-PI-366-医疗事故鉴定与医疗损害鉴定的本质区别与裁判适用.md",
     "R-PI-289-医疗事故鉴定与医疗损害鉴定的区别-采集笔记-2026-09-11",
     "R-PI-366-医疗事故鉴定与医疗损害鉴定的本质区别与裁判适用"),
    # 5) R-PI-288 -> 采集笔记旧名（真实目标 = R-PI-365）
    ("R-PI-288-挂靠车辆单方事故致受雇司机受损的责任主体.md",
     "R-PI-288-电子病历怎么封存-采集笔记-2026-09-11",
     "R-PI-365-电子病历封存与操作日志取证实务边界"),
    # 6) R-PI-365 -> 采集笔记旧名（自检，真实目标 = 自身 R-PI-365；审计跨子域漏报）
    ("R-PI-365-电子病历封存与操作日志取证实务边界.md",
     "R-PI-288-电子病历怎么封存-采集笔记-2026-09-11",
     "R-PI-365-电子病历封存与操作日志取证实务边界"),
    # 7) R-PI-424 -> R-PI-413 后缀不符 ×2
    ("R-PI-424-人身损害赔偿死亡赔偿金城乡统一同命同价.md",
     "R-PI-413-机动车交通事故责任纠纷无过错责任",
     "R-PI-413-机动车与行人非机动车事故无过错责任及10%限额"),
    # 8) R-PI-424 -> R-PI-400 后缀不符 ×2
    ("R-PI-424-人身损害赔偿死亡赔偿金城乡统一同命同价.md",
     "R-PI-400-交强险限额内全额赔付",
     "R-PI-400-交强险责任限额内优先全额赔付不按过错比例划分"),
]

# ---------- R-PI-157 撞号回归 ----------
RPI157_FILE = "R-PI-157-医疗告知义务代签与举证不能.md"
RPI157_OLD_RULE_ID = "R-PI-425"
RPI157_NEW_RULE_ID = "R-PI-157"

def main():
    apply = "--apply" in sys.argv[1:]
    print(f">>> 模式: {'APPLY（实际写入）' if apply else 'DRY-RUN（仅预览）'}")
    print(f">>> 解析索引: stems={len(stems)} aliases={len(aliases)}")
    print("=" * 70)

    total_changes = 0
    problems = []

    # --- 断链修复 ---
    # 按文件名分组：同一文件可能有多条修复，须在同一份文本上顺序累积替换
    print("\n【A. 断链修复】")
    from collections import defaultdict
    file_fixes = defaultdict(list)
    for fn, old, new in LINK_FIXES:
        file_fixes[fn].append((old, new))

    per_file_newtext = {}   # filename -> new content (accumulate)
    for fn, fixes in file_fixes.items():
        fp = next(DOMAIN.rglob(fn), None)
        if not fp.exists():
            problems.append(f"  文件缺失: {fn}")
            continue
        txt = fp.read_text(encoding='utf-8', errors='ignore')
        file_ok = True
        for old, new in fixes:
            # 双重校验
            old_ok = not resolve(old)      # 旧链应不可解析（确为断链）
            new_ok = resolve(new)          # 新链应可解析
            pat = f"[[{old}]]"
            cnt = txt.count(pat)
            flag = []
            if not old_ok:
                flag.append("⚠旧链竟可解析(疑似已修复/重复)")
            if not new_ok:
                flag.append("✗新链不可解析(将引入断链!)")
            status = "OK" if (old_ok and new_ok and cnt > 0) else "CHECK"
            print(f"  [{status}] {fn}")
            print(f"        旧: {pat}  (出现 {cnt} 次)  旧不可解析={old_ok}")
            print(f"        新: [[{new}]]  新可解析={new_ok}  {' '.join(flag)}")
            if cnt > 0 and old_ok and new_ok:
                txt = txt.replace(pat, f"[[{new}]]")
                total_changes += cnt
            elif cnt == 0:
                print("        → 无匹配（可能已修复，跳过）")
            else:
                file_ok = False
                problems.append(f"  跳过(校验未过): {fn} old={old}")
        if file_ok:
            per_file_newtext[fn] = txt

    # --- R-PI-157 撞号回归 ---
    print("\n【B. R-PI-157 撞号回归】")
    fp157 = next(DOMAIN.rglob(RPI157_FILE), None)
    if not fp157.exists():
        problems.append(f"  文件缺失: {RPI157_FILE}")
    else:
        txt = fp157.read_text(encoding='utf-8', errors='ignore')
        pat = f"rule_id: {RPI157_OLD_RULE_ID}"
        cnt = len(re.findall(re.escape(pat) + r"\s*$", txt, re.M))
        has_new = bool(re.search(rf"^rule_id:\s*{RPI157_NEW_RULE_ID}\s*$", txt, re.M))
        print(f"  文件: {RPI157_FILE}")
        print(f"        当前 rule_id: R-PI-425 → 改为 {RPI157_NEW_RULE_ID}")
        print(f"        匹配 rule_id: R-PI-425 行数={cnt}  已为 R-PI-157={has_new}")
        if cnt == 1 and not has_new:
            per_file_newtext[RPI157_FILE] = re.sub(
                r"^rule_id:\s*R-PI-425\s*$", f"rule_id: {RPI157_NEW_RULE_ID}", txt, flags=re.M)
            total_changes += 1
        elif has_new:
            print("        → 已是 R-PI-157（幂等，跳过）")
        else:
            problems.append(f"  R-PI-157 匹配异常: cnt={cnt}")

    print("\n" + "=" * 70)
    print(f"计划变更总数: {total_changes}  ｜ 待写入文件数: {len(per_file_newtext)}")
    if problems:
        print("⚠ 问题:")
        for p in problems:
            print("  " + p)

    if not apply:
        print("\n[DRY-RUN] 未做任何写入。确认无误后加 --apply 执行。")
        return

    # --- 备份 ---
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = Path(f"/tmp/人伤法域库_bak_{ts}_pre_rpi157fix")
    shutil.copytree(DOMAIN, bak)
    print(f"\n✅ 已备份至: {bak}  (文件数 {len(list(bak.rglob('*.md')))})")

    # --- 写入 ---
    written = 0
    for fn, newtxt in per_file_newtext.items():
        fp = next(DOMAIN.rglob(fn), None)
        oldtxt = fp.read_text(encoding='utf-8', errors='ignore')
        if oldtxt == newtxt:
            print(f"  ≡ 无变化跳过: {fn}")
            continue
        fp.write_text(newtxt, encoding='utf-8')
        written += 1
        print(f"  ✅ 已写入: {fn}")
    print(f"\n>>> APPLY 完成，实际写入 {written} 个文件。")

if __name__ == "__main__":
    main()
