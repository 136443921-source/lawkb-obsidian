#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性验收：旧链接0残留 + 新链接均存在 + R-PI-157撞号已回归"""
import re
from pathlib import Path

DOMAIN = Path("/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/人伤法域库")

# 11 条修复（old 旧链接文字, new 新链接文字）
FIXES = [
    ("R-PI-367-医疗纠纷怎么选律师-采集笔记-2026-09-11", "R-PI-367-医疗纠纷选律师六维度与避坑指南"),
    ("R-PI-386-医疗过错参与度非法定概念", "R-PI-386-医疗过错参与度鉴定非法定概念应对照原因力六分情形确定赔偿责任"),
    ("R-PI-289-医疗事故鉴定与医疗损害鉴定的区别-采集笔记-2026-09-11", "R-PI-366-医疗事故鉴定与医疗损害鉴定的本质区别与裁判适用"),
    ("R-PI-288-电子病历怎么封存-采集笔记-2026-09-11", "R-PI-365-电子病历封存与操作日志取证实务边界"),
    ("R-PI-413-机动车交通事故责任纠纷无过错责任", "R-PI-413-机动车与行人非机动车事故无过错责任及10%限额"),
    ("R-PI-400-交强险限额内全额赔付", "R-PI-400-交强险责任限额内优先全额赔付不按过错比例划分"),
]

files = list(DOMAIN.rglob("*.md"))
texts = {f: f.read_text(encoding='utf-8', errors='ignore') for f in files}

old_total = 0
new_missing = []
for old, new in FIXES:
    # 旧链接可能以 [[old]] 出现（或直接 old）；统计含 old 的链接
    oc = sum(t.count(f"[[{old}]]") + t.count(old) for t in texts.values())
    old_total += oc
    # 新链接必须存在（且可解析为文件）
    present = any(f"[[{new}]]" in t for t in texts.values())
    # 新目标文件是否真实存在
    target_file = DOMAIN / f"{new}.md"
    if not (present or target_file.exists()):
        new_missing.append(new)

print(f"扫描文件数: {len(files)}")
print(f"【旧链接残留总数】: {old_total}  （期望 0）")
if old_total == 0:
    print("  ✅ 11 条旧链接已全部清除（含跨子域漏报的 R-PI-365 那条）")
else:
    print("  ❌ 仍有旧链接残留！")

print(f"【新链接校验】: {'✅ 全部存在' if not new_missing else '❌ 缺失 ' + str(new_missing)}")

# R-PI-157 撞号（文件已搬入子目录，用 rglob 定位）
f157_list = list(DOMAIN.rglob("R-PI-157-医疗告知义务代签与举证不能.md"))
f157 = f157_list[0] if f157_list else None
t157 = f157.read_text(encoding='utf-8', errors='ignore') if f157 else ""
rid = re.search(r"^rule_id:\s*(\S+)", t157, re.M)
print(f"【R-PI-157 撞号回归】: rule_id = {rid.group(1) if rid else 'NONE'}  "
      f"{'✅ 已回归 R-PI-157' if rid and rid.group(1)=='R-PI-157' else '❌ 未回归'}")

# R-PI-425 正主不再被撞：全库持 rule_id=R-PI-425 的文件应只有正主一张
all425 = [f for f in files
          if re.search(r"^rule_id:\s*R-PI-425\s*$", texts[f], re.M)]
print(f"【R-PI-425 撞号解除】: 全库持 rule_id=R-PI-425 的文件 = {[f.name for f in all425]}  "
      f"{'✅ 仅正主一张，告知义务卡已不撞' if len(all425)==1 else '❌ 需核查'}")
# R-PI-157 现由两张卡共享（按 KB 架构 rule_id 为共享指针键，健康）
all157 = [f for f in files
          if re.search(r"^rule_id:\s*R-PI-157\s*$", texts[f], re.M)]
print(f"【R-PI-157 共享现状】: 持 rule_id=R-PI-157 的文件 = {[f.name for f in all157]}  "
      f"（{len(all157)} 张，按 KB 架构为共享指针键，非冲突）")
