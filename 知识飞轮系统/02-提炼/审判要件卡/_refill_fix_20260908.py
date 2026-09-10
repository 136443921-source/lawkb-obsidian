# -*- coding: utf-8 -*-
"""修正：核填内容同步到「带书名号」的原键（卡片引用键），并删除无书名号副本"""
import json
P = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/审判要件卡/贵州类案指南第二卷-破产案件-法条回填库.json"
L = json.load(open(P, encoding="utf-8"))

PAIRS = [
    ("最高人民法院关于审理企业破产案件确定管理人报酬的规定第二条",
     "《最高人民法院关于审理企业破产案件确定管理人报酬的规定》第二条"),
    ("最高人民法院关于审理企业破产案件确定管理人报酬的规定第十三条",
     "《最高人民法院关于审理企业破产案件确定管理人报酬的规定》第十三条"),
    ("最高人民法院关于审理企业破产案件确定管理人报酬的规定第十四条",
     "《最高人民法院关于审理企业破产案件确定管理人报酬的规定》第十四条"),
    ("最高人民法院关于刑事裁判涉财产部分执行的若干规定第十条第二款、第三款",
     "《最高人民法院关于刑事裁判涉财产部分执行的若干规定》第十条第二款、第三款"),
    ("最高人民法院关于刑事裁判涉财产部分执行的若干规定第十一条第二款",
     "《最高人民法院关于刑事裁判涉财产部分执行的若干规定》第十一条第二款"),
]
moved = 0
for src_k, dst_k in PAIRS:
    if src_k in L and dst_k in L:
        L[dst_k] = L.pop(src_k)      # 内容搬过去，删副本
        moved += 1
    elif src_k in L and dst_k not in L:
        L[dst_k] = L.pop(src_k)
        moved += 1
    else:
        print(f"  ⚠️ 未处理: {src_k}")

json.dump(L, open(P, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
n1 = sum(1 for v in L.values() if v["source"] in ("北大法宝核填", "华宇元典核填"))
pend = [k for k, v in L.items() if v["source"] not in ("北大法宝核填", "华宇元典核填")]
print(f"内容搬移: {moved} 条")
print(f"总键数: {len(L)}")
print(f"已核填（法宝/元典真调用）: {n1} 条")
print(f"仍待回源（据实标注）: {len(pend)} 条")
for k in sorted(pend):
    print(f"   - {k}")
