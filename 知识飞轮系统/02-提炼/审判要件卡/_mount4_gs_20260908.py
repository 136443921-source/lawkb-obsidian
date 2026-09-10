# -*- coding: utf-8 -*-
"""破产案件批·六层挂载 之四：消费方主载体卡组索引表同步（227→353 + 破产行）"""
import re, os
CONS1 = "/Users/chenyouqiang/Documents/LawKB/小强律师数字分身系统/07-系统搭建与Skill配置/法律类skill 配置迭代-九阳神功/AI模拟法庭法官skill 配置说明书.md"
src = open(CONS1, encoding="utf-8").read()

# 1) 导语张数
src = src.replace(
    "**截至 2026-09-07，在库 227 张**，覆盖 **9 个类案**（第七批新增婚姻家庭 52 张）。",
    "**截至 2026-09-08，在库 353 张**，覆盖 **10 个类案**（第九批新增破产案件 90 张）。", 1)
# 2) 索引标题
src = src.replace("### 三、在库卡组索引（227 张）", "### 三、在库卡组索引（353 张）", 1)

# 3) 索引表补「破产案件」行（插到表尾：找最后一个 | 行）
lines = src.split("\n")
idx = None
for i, l in enumerate(lines):
    if l.startswith("### 三、在库卡组索引"):
        idx = i
        break
assert idx is not None
# 定位该节表格末尾
j = idx
while j < len(lines) and not lines[j].startswith("| "):
    j += 1
k = j
while k < len(lines) and lines[k].startswith("| "):
    k += 1
row = "| **破产案件** | R-GS-005~094 | 90 | 公司法 | 破产原因、管理人、债务人财产、共益债务、重整、和解、清算、衍生诉讼、实质合并 |"
if any("R-GS-005~094" in x for x in lines[j:k]):
    print("破产行已存在，跳过")
else:
    lines.insert(k, row)
src = "\n".join(lines)

open(CONS1, "w", encoding="utf-8").write(src)
print(f"消费方主载体已同步: {os.path.getsize(CONS1)} bytes")
for l in src.split("\n"):
    if "353 张" in l or "R-GS-005~094" in l:
        print("  ✓", l.strip()[:110])
