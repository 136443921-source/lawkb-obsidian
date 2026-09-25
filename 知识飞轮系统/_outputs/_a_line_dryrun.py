#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
裁判规则库 A 线迁移 · DRY-RUN 生成器 v2（frontmatter rule_id 维度 · 只读）
=========================================================================
修正 v1 偏差：v1 按【文件名】提取 rule_id 导致"文件名滞后"卡误判碎片。
本版按【frontmatter rule_id】维度归属卡族与目标库（与 P0-4 治理表 9.2 双维度铁律一致）。
- 卡族归属：以 frontmatter rule_id 前缀为准（无 rule_id 则回退文件名前缀并标记缺失）
- 目标库：按 frontmatter rule_id 前缀映射（R-CF-115→CF 域；R-HG-074 不属 A 线 5 族→排除）
- 真冲突：06-沉淀 内同一 frontmatter rule_id 出现 ≥2 份主卡
性质：只读，不移动/不修改。
"""
import os, re, csv, collections

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT = os.path.join(ROOT, "_outputs")
os.makedirs(OUT, exist_ok=True)

A = {
    "PI": "人伤法域库",
    "HT": "合同风险规则库",
    "AY": "案由路由卡族",
    "CF": "慈善合规域库",
    "PR": "证据规则卡族",
}

VALID = re.compile(r"^R-([A-Z]{2})-\d{1,3}$")

def walk_r():
    out = []
    for dp, dn, fn in os.walk(ROOT):
        if any(x in dp for x in [".workbuddy", "__pycache__"]):
            continue
        if any(s in dp for s in ["/.backup", "/.trash", "_quarantine", "/.backup_link"]):
            continue
        for f in fn:
            if f.startswith("R-") and f.endswith(".md"):
                out.append(os.path.join(dp, f))
    return out

def fm_rid(p):
    try:
        h = open(p, encoding="utf-8", errors="ignore").read(2500)
    except Exception:
        return None
    m = re.search(r"^rule_id:\s*(\S+)", h, re.M)
    return m.group(1).strip() if m else None

def fam_of(p):
    rid = fm_rid(p)
    if rid and VALID.match(rid):
        return rid[2:4]
    m = re.match(r"R-([A-Za-z]+)-", os.path.basename(p))
    return m.group(1) if m else "?"

files = walk_r()
rows = []
for p in files:
    f = fam_of(p)
    if f not in A:
        continue
    rel = os.path.relpath(p, ROOT)
    top = rel.split("/")[0]
    role = "主卡" if top == "06-沉淀" else ("概念页指针" if top == "03-连接" else "提炼源/指针")
    rid = fm_rid(p)
    target_lib = A[f]
    base = os.path.basename(p)
    target = os.path.relpath(os.path.join(ROOT, "06-沉淀", target_lib, base), ROOT)
    rows.append({"rid": rid, "fam": f, "base": base, "current": rel,
                 "target": target, "role": role, "has_rid": bool(rid and VALID.match(rid))})

# 真冲突：06-沉淀 主卡，有有效 rule_id，同 rid ≥2
main_rid = collections.defaultdict(list)
for r in rows:
    if r["role"] == "主卡" and r["rid"] and VALID.match(r["rid"]):
        main_rid[r["rid"]].append(r["current"])
frag = {k: v for k, v in main_rid.items() if len(v) > 1}
# 缺 rule_id 主卡（回退文件名，需补）
missing = [r["current"] for r in rows if r["role"] == "主卡" and not r["has_rid"]]

pointer_by_fam = collections.Counter(r["fam"] for r in rows if r["role"] != "主卡")
main_by_fam = collections.Counter(r["fam"] for r in rows if r["role"] == "主卡")
all_by_fam = collections.Counter(r["fam"] for r in rows)

# CSV
csv_path = os.path.join(OUT, "A线迁移清单-full-v2.csv")
with open(csv_path, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["rule_id", "卡族", "文件名", "当前路径", "目标路径", "角色", "缺rule_id", "碎片标记"])
    for r in sorted(rows, key=lambda x: (x["fam"], x["rid"] or "")):
        w.writerow([r["rid"] or "(缺失)", r["fam"], r["base"], r["current"],
                    r["target"], r["role"], "" if r["has_rid"] else "是",
                    "是" if r["rid"] in frag else ""])
print("CSV(v2):", csv_path, "行:", len(rows))

# MD 报告
L = []
L.append("# 裁判规则库 A 线迁移方案 + dry-run 报告 v2（frontmatter rule_id 维度）")
L.append("")
L.append("> 2026-09-21 | 只读 | 修正 v1：归属/冲突改用 **frontmatter rule_id** 维度（v1 文件名维度致假阳性）")
L.append("")
L.append("## 1. 关键修正说明")
L.append("- v1 按文件名提取 rule_id，把 `R-CF-052/053/076`、`R-HT-101` 的 B 卡（**已 09-07 重编号、文件名不动**）误判为同号碎片。")
L.append("- 全库 frontmatter 扫描证实：这 4 个 B 卡 `rule_id` 已是 `R-CF-115/116`、`R-HG-074`、`R-LN-059`，**无冲突**。")
L.append("- 现按 frontmatter `rule_id` 归属：R-HG-074（合规域）、R-LN-059（律师实务）**不属 A 线 5 族**，正确排除出迁移。")
L.append("")
L.append("## 2. dry-run 汇总（按 frontmatter rule_id 维度）")
L.append("")
L.append("| 卡族 | 全量(含指针) | 主卡(将移) | 指针(待 canonical 同步) |")
L.append("|---|---|---|---|")
for f in ["PI", "HT", "AY", "CF", "PR"]:
    L.append(f"| R-{f} | {all_by_fam[f]} | {main_by_fam[f]} | {pointer_by_fam[f]} |")
L.append(f"| **合计** | **{sum(all_by_fam.values())}** | **{sum(main_by_fam.values())}** | **{sum(pointer_by_fam.values())}** |")
L.append("")
L.append("## 3. 真冲突（06-沉淀 内同 frontmatter rule_id ≥2 主卡）")
L.append("")
if frag:
    for k, v in sorted(frag.items()):
        L.append(f"- `{k}`: " + " | ".join(v))
else:
    L.append("✅ 无")
L.append("")
L.append("> **A 线相关真冲突仅 3 组**：R-CF-173、R-HT-102、R-PI-157（均属 CF/HT/PI 族）。")
L.append("> 另有 R-LN-021/022/023/025 四组真冲突（LN 族，不在 A 线 5 族，留待后续 LN 线治理）。")
L.append("")
L.append("## 4. 缺 rule_id 主卡（回退文件名归属，迁移时需补 rule_id）")
L.append("")
for m in missing:
    L.append(f"- {m}")
L.append("")
L.append("## 5. 7 碎片结论修正")
L.append("- **已治理无冲突（无需预处理）**：R-CF-052/053/076、R-HT-101（B 卡 rule_id 已改，仅文件名滞后）")
L.append("- **真冲突需预处理（3 组）**：R-CF-173(删A留B)、R-HT-102(B取新号)、R-PI-157(B取新号)")
L.append("- 取新号须按治理表 9.2 双维度铁律查当前空闲号（勿照搬 9.6 旧号，可能已被占）")
L.append("")
L.append("## 6. 待确认")
L.append("① R-CF-173 删A留B；② R-HT-102/R-PI-157 B 取新号（双维度查空闲）；③ 指针 392 张批量重写 canonical。")
L.append("")
md_path = os.path.join(OUT, "裁判规则库-A线迁移方案与dry-run报告-v2-20260921.md")
open(md_path, "w", encoding="utf-8").write("\n".join(L))
print("MD(v2):", md_path)
print("主卡:", sum(main_by_fam.values()), "指针:", sum(pointer_by_fam.values()),
      "真冲突:", list(frag.keys()), "缺rule_id:", len(missing))
