#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""resolve_broken_links.py 括号校验（v1.2）单元测试：不写磁盘，仅验证归一与生成侧净化。"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_broken_links as r

fail = 0
def check(cond, msg):
    global fail
    print(("PASS" if cond else "FAIL"), msg)
    if not cond:
        fail += 1

# 1) clean_target：三重括号 / 引用嵌套 -> 内层目标
check(r.clean_target("[[[民法典第1218条") == "民法典第1218条", "clean_target 三重开括号 -> 内层")
check(r.clean_target("第五章 [[医院人力资源管理法律实务") == "第五章 医院人力资源管理法律实务",
      "clean_target 引用嵌套剥离多余括号")
check(r.clean_target("R-PI-130-[[医疗损害鉴定") == "R-PI-130-医疗损害鉴定", "clean_target 前缀嵌套")
check(r.clean_target("正常概念名") == "正常概念名", "clean_target 干净名原样返回")

# 2) bare_target：生成侧净化，绝不产出 [[[
for bad in ["[民法典第1218条", "第五章 [[医院人力资源管理法律实务",
             "[[[合同法]]]", "R-PI-130-[[医疗损害鉴定", "正常概念名"]:
    out = r.bare_target(bad)
    check("[[" not in out and "]]" not in out, f"bare_target 无多重括号: {bad!r} -> {out!r}")
    check(out == out.strip().strip("[]"), f"bare_target 裸名: {bad!r} -> {out!r}")

# 3) build_page 生成侧：含畸形同簇目标时，输出不得出现 [[[
r.concept_targets = [("[民法典第1218条", 1), ("医疗损害责任", 1), ("正常概念A", 1)]
for target, cl in [("[民法典第1218条", "通用"), ("正常概念A", "通用"),
                   ("《民法典》第1218条", "通用")]:
    pg = r.build_page(target, cl)
    check("[[[" not in pg, f"build_page 无 [[[ : {target!r}")
    check("]]]" not in pg, f"build_page 无 ]]] : {target!r}")
    # 脏名同簇目标不得被互链写入
    if "[民法典第1218条" in [t for t, _ in r.concept_targets]:
        check("- [[[民法典第1218条]]" not in pg, "build_page 未写入畸形同簇互链")

print("\n==== 结果:", "ALL PASS" if fail == 0 else f"{fail} FAIL ====")
sys.exit(1 if fail else 0)
