#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_fix_deadlinks_v9_20260918.py  v1.0
死链白名单修复器（严格白名单，禁止任何推断/算术偏移）

🔴 准入判据（三条全满足才收）：
  1. 死链名与现有卡 **同 rule_id**（前 9 位编号一致）
  2. 两者描述 **语义同一主题**（人工逐条比对，非字符相似度）
  3. 现有卡 **唯一**
🔴 排除（坑 63/64/68）：PI-280~289 / HT-249~251 / R-PI-094 等「同号不同主题」
   一律不修 —— 修剪成纯编号会把 N 条链接指向完全无关的卡，制造沉默错链。

用法：默认 dry-run；--apply 写盘（先 cp -n 备份到 /tmp/<主题>_<ts>/）
"""
import os
import re
import shutil
import sys
import time
from datetime import datetime

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
APPLY = "--apply" in sys.argv
RECENT_SEC = 1800  # 坑 62

# 严格白名单：死链名 → 真实基名（人工逐条确认语义同一）
WL = {
    "R-PI-246-交通事故护理费计算标准": "R-PI-246-护理费的计算口径与护理依赖",
    "R-PI-243-雇主责任险理赔款支付工伤待遇后不得重复主张": "R-PI-243-雇主责任险理赔款与工伤保险待遇的关系",
    "R-PI-247-人身损害赔偿项目及计算标准一览表": "R-PI-247-人身损害赔偿项目计算总表",
    "R-PI-244-指导案例24号受害人无过错体质不减轻侵权人责任": "R-PI-244-受害人无过错时体质因素不减轻侵权人责任",
    "R-PI-245-交通事故营养费索赔指南": "R-PI-245-营养费的计算标准与证据清单",
    "R-PI-240-医疗事故罪严重不负责任与以鉴代审否定": "R-PI-240-医疗事故罪严重不负责任的认定与鉴定意见的证据地位",
    "R-CF-090-疫情捐赠全额扣除": "R-CF-090-疫情防控捐赠税收优惠全额扣除要点",
    "R-LN-034-代理词三性与庭后提交": "R-LN-034-民事代理词三性标准与庭后提交书面代理词规则",
    "R-PI-190-急诊PCI诊疗过错医疗损害责任": "R-PI-190-具备介入条件的医院未及时行急诊PCI构成过错",
    "R-CF-114-韩红6000万采购疑云风控": "R-CF-114-韩红基金会6000万救护车采购疑云风控要点",
    "R-CF-146-项目进展反馈合规操作卡": "R-CF-146-项目进展反馈合规审查卡",
    "R-PI-130-[[医疗损害鉴定": "R-PI-130-医疗损害鉴定陈述法定程序与实战五步准备框架",
    "R-PI-183-医疗事故罪刑法因果关系与韩杰案再审五争点":
        "R-PI-183-医疗事故罪刑法因果关系多环节介入与尸检缺失存疑有利被告",
}

TS = datetime.now().strftime("%Y%m%d-%H%M%S")
BACKUP = f"/tmp/存量卡巡检死链修复_{TS}"


def build_patterns():
    pats = []
    for dead, to in WL.items():
        d = re.escape(dead)
        pats.append((re.compile(r'\[\[' + d + r'(\|[^\]]*)?\]\]'),
                     lambda m, to=to: '[[' + to + (m.group(1) or '') + ']]'))
        pats.append((re.compile(r'(?m)^(\s*-\s*)' + d + r'[ \t]*$'),
                     lambda m, to=to: m.group(1) + to))
    return pats


def main():
    pats = build_patterns()
    targets = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [x for x in dns if not x.startswith('.backup')]
        if '_隔离_' in dp or '_quarantine' in dp or '/.workbuddy' in dp:
            continue
        for fn in fns:
            if fn.endswith('.md'):
                targets.append(os.path.join(dp, fn))

    now = time.time()
    hits, skipped = [], []
    for p in targets:
        try:
            t = open(p, encoding='utf-8').read()
        except Exception:
            continue
        if not any(d in t for d in WL):
            continue
        rel = os.path.relpath(p, ROOT)
        age = now - os.path.getmtime(p)
        if age < RECENT_SEC:
            skipped.append((rel, int(age)))
            continue
        new = t
        cnt = 0
        for pat, rep in pats:
            new, n = pat.subn(rep, new)
            cnt += n
        if cnt and new != t:
            hits.append((p, rel, cnt, new))

    print(f"命中 {len(hits)} 个文件，共 {sum(h[2] for h in hits)} 处替换")
    for p, rel, cnt, _ in hits:
        print(f"   {cnt:>3} 处  {rel}")
    if skipped:
        print(f"\n⏳ 坑62 并发保护跳过 {len(skipped)} 个：")
        for r, a in skipped[:10]:
            print(f"   {r}（{a}s 前写入）")

    if not APPLY or not hits:
        print("\n[dry-run] 未写盘。加 --apply 执行。")
        return
    os.makedirs(BACKUP, exist_ok=True)
    for p, rel, cnt, new in hits:
        shutil.copy2(p, os.path.join(BACKUP, rel.replace('/', '__')))
        with open(p, 'w', encoding='utf-8') as f:
            f.write(new)
    print(f"\n✅ 已写盘 {len(hits)} 个文件；备份 → {BACKUP}")


if __name__ == "__main__":
    main()
