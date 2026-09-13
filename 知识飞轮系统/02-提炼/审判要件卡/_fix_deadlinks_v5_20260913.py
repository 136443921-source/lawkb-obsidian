#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
死链 [B] 类安全映射修复器  v5 / 2026-09-13

判据（三条全中才修，缺一即留人工）：
  1. 编号前缀完全一致（R-XX-NNN 相同）
  2. 候选唯一（cand_n == 1）
  3. 去标点后死链名与目标名互为子串，且**语义同一**（人工逐条复核过的白名单）

🔴 已拦截（不修，需人工裁定）：
  - R-AY-013-姓名权纠纷 → R-AY-013-名誉权纠纷     姓名权 ≠ 名誉权（权利类型位移）
  - R-AY-017-名誉权纠纷 → R-AY-017-荣誉权纠纷     名誉权 ≠ 荣誉权（权利类型位移）
  - R-PI-289 / R-CF-123                            候选 >1，存在歧义

用法：python _fix_deadlinks_v5_20260913.py [--apply]
"""
import json, os, re, sys, shutil, datetime, glob

ROOT = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统'
SRC = os.path.join(ROOT, '02-提炼/审判要件卡/死链安全映射与候选-20260913.json')
APPLY = '--apply' in sys.argv
STAMP = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
BK = f'/tmp/存量卡巡检死链B类_{STAMP}'

# 🟢 人工复核通过的安全映射（cand_n=1 且语义同一）
SAFE = {
    'R-AY-107-网络域名权属侵权单案由路由卡': 'R-AY-107-网络域名权属-侵权纠纷单案由路由卡',
    'R-AY-105-侵害企业名称权单案由路由卡': 'R-AY-105-侵害企业名称权纠纷单案由路由卡',
    'R-AY-106-侵害特殊标志专有权单案由路由卡': 'R-AY-106-侵害特殊标志专有权纠纷单案由路由卡',
    'R-AY-104-集成电路布图设计专有权权属侵权单案由路由卡': 'R-AY-104-集成电路布图设计专有权权属-侵权纠纷单案由路由卡',
    'R-AY-103-植物新品种权权属侵权单案由路由卡': 'R-AY-103-植物新品种权权属-侵权纠纷单案由路由卡',
    'R-AY-119-商业贿赂不正当竞争单案由路由卡': 'R-AY-119-商业贿赂不正当竞争纠纷单案由路由卡',
    'R-AY-124-串通投标不正当竞争单案由路由卡': 'R-AY-124-串通投标不正当竞争纠纷单案由路由卡',
    'R-HT-232-检验期限与质量异议抗辩边界': 'R-HT-232-买受人检验期限与质量异议抗辩边界',
    'R-HT-261-物保与人保并存清偿顺序与追偿举证': 'R-HT-261-物保与人保并存（混合担保）清偿顺序与追偿举证',
}

# 🔴 拦截清单（记录在案，永不自动修）
BLOCKED = {
    'R-AY-013-姓名权纠纷单案由路由卡': ('R-AY-013-名誉权纠纷单案由路由卡', '姓名权≠名誉权，权利类型位移，疑似案由编号分配错位'),
    'R-AY-017-名誉权纠纷单案由路由卡': ('R-AY-017-荣誉权纠纷单案由路由卡', '名誉权≠荣誉权，权利类型位移，疑似案由编号分配错位'),
    'R-PI-289-医疗事故鉴定与医疗损害鉴定的本质区别': ('候选3个', '同编号多候选，需人工选定'),
    'R-CF-123-基金会不是合规通行证药企合作穿透式稽查': ('候选2个（其一为-采集笔记）', '同编号多候选，且其一指向采集笔记非正卡'),
}


def main():
    # 目标文件存在性校验（坑 34：目标必须在真实基名集内）
    basenames = set()
    for p in glob.glob(os.path.join(ROOT, '**/*.md'), recursive=True):
        if '/.backup' in p or '/_archive' in p:
            continue
        basenames.add(os.path.splitext(os.path.basename(p))[0])

    miss = [v for v in SAFE.values() if v not in basenames]
    if miss:
        print('🔴 目标文件不存在，终止：')
        for m in miss:
            print('   ', m)
        return

    files = []
    for pat in ('06-沉淀/**/*.md', '02-提炼/**/*.md', '03-连接/**/*.md'):
        files += glob.glob(os.path.join(ROOT, pat), recursive=True)

    if APPLY:
        os.makedirs(BK, exist_ok=True)

    total_hit = 0
    touched = []
    for p in files:
        try:
            t = open(p, encoding='utf-8').read()
        except Exception:
            continue
        o = t
        n = 0
        for k, v in SAFE.items():
            if k in t:
                c = t.count(k)
                n += c
                t = t.replace(k, v)
        if t == o:
            continue
        total_hit += n
        touched.append((p, n))
        if APPLY:
            shutil.copy2(p, os.path.join(BK, os.path.basename(p)))
            open(p, 'w', encoding='utf-8').write(t)

    print(f'{"[APPLY]" if APPLY else "[DRY-RUN]"} 安全映射 {len(SAFE)} 条 | 命中文件 {len(touched)} | 替换 {total_hit} 处')
    for p, n in sorted(touched, key=lambda x: -x[1])[:10]:
        print(f'   {n:3d} 处  {os.path.relpath(p, ROOT)}')
    if len(touched) > 10:
        print(f'   ... 另 {len(touched)-10} 个文件')
    print(f'\n🔴 已拦截不修 {len(BLOCKED)} 条：')
    for k, (to, why) in BLOCKED.items():
        print(f'   {k[:46]}')
        print(f'      → {why}')
    if APPLY:
        print(f'\n备份：{BK}（{len(os.listdir(BK))} 份）')


if __name__ == '__main__':
    main()
