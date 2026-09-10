# -*- coding: utf-8 -*-
"""破产案件批·六层挂载 之一：03-连接总索引（§4.11 + 总数 + version）
用脚本一次性写入，规避坑 19（同文件多个 Edit 静默丢改）。
"""
import importlib.util, re, os, io

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
D = f"{BASE}/02-提炼/审判要件卡"
IDX = f"{BASE}/03-连接/概念页/审判要件卡-卡型定义与总索引.md"

def load(f):
    spec = importlib.util.spec_from_file_location("m_" + f[:-3], f"{D}/{f}")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m.CARDS

ALL = []
for f in ["_gs_cards1_20260908.py", "_gs_cards2_20260908.py",
          "_gs_cards3_20260908.py", "_gs_cards4_20260908.py"]:
    ALL += load(f)
BY = {c["no"]: c for c in ALL}

GROUPS = [
    ("A 组 · 概述与审理难点（第一章、第二章）", [("005", "006")]),
    ("B 组 · 申请与受理（第三章一）", [("007", "021")]),
    ("C 组 · 管理人及其法律责任（第三章二）", [("022", "032")]),
    ("D 组 · 债务人财产（第三章三）", [("033", "039")]),
    ("E 组 · 债权申报和债权人会议（第三章四）", [("040", "047")]),
    ("F 组 · 破产费用和共益债务（第三章五）", [("048", "053")]),
    ("G 组 · 破产重整（第三章六）", [("054", "064")]),
    ("H 组 · 破产和解（第三章七）", [("065", "068")]),
    ("I 组 · 破产清算（第三章八）", [("069", "078")]),
    ("J 组 · 破产衍生诉讼（第三章九）", [("079", "089")]),
    ("K 组 · 附录案例（第四章）", [("090", "094")]),
]

def brief(c, n=52):
    s = c["rule"].replace("\n", "")
    s = re.sub(r"\s+", "", s)
    return s[:n] + ("…" if len(s) > n else "")

out = []
out.append("### 4.11 破产案件（GS 域 · R-GS-005~094，第九批，90 张）")
out.append("")
out.append("> **母本位置**：《贵州法院类案审判要件指南（第二卷）》第九部分「破产案件审判要件指南」（PDF页448-513 / 书页418-485）")
out.append("> **落盘目录**：`06-沉淀/裁判规则库/公司法/`（GS 域，物理 max 004 → 起始号 005，一次性连续取满 005~094）")
out.append("> **计划 vs 实拆**：计划 27 张 → 实拆 **90 张**（按「一卡一争点」，第三章九节约 100 个争点 + 附录 5 则案例各自独立成卡）。")
out.append("")
out.append("> **⚠️ 价值登记**：破产案件与婚姻家庭、抚养同属不同域但**程序叠床架屋**——申请受理（含刑民交叉）、管理人、债务人财产、债权申报、破产费用与共益债务、重整、和解、清算、衍生诉讼九大块，覆盖破产全流程。**最高价值争点是「共益债务的边界」**（R-GS-048~053）：重整计划执行期间债务不属共益债务，与重整期间规则截然不同，是实务最易混淆之处。")
out.append("")
for gname, ranges in GROUPS:
    out.append(f"**{gname}**")
    out.append("")
    out.append("| 编号 | 卡片 | 审理环节 |")
    out.append("|------|------|----------|")
    for a, b in ranges:
        for n in range(int(a), int(b) + 1):
            no = f"{n:03d}"
            c = BY.get(no)
            if not c: continue
            out.append(f"| [[R-GS-{no}-{c['title']}]] | {brief(c)} | {c['step']} |")
    out.append("")
block = "\n".join(out)

src = open(IDX, encoding="utf-8").read()
assert "### 4.11" not in src, "§4.11 已存在，勿重复写入"

anchor = "## 五、消费方式：法官心智四步推理链（judge_reviewer）"
assert anchor in src
src = src.replace(anchor, block + anchor, 1)

# 总数
old_h = "## 四、卡片总索引（共 263 张 · 2026-09-07）"
assert old_h in src, "总数标题未找到"
src = src.replace(old_h, "## 四、卡片总索引（共 353 张 · 2026-09-08）", 1)

# version + updated（规范升版两处同步）
src = src.replace("version: 1.8.0", "version: 1.9.0", 1)
src = re.sub(r"^updated: .*$", "updated: 2026-09-08T12:00", src, count=1, flags=re.M)

open(IDX, "w", encoding="utf-8").write(src)
print(f"总索引已更新: {IDX}")
print(f"  文件大小: {os.path.getsize(IDX)} bytes")
print(f"  §4.11 卡片行数: {block.count('| [[')}")
print(f"  version -> 1.9.0；总数 -> 353")
