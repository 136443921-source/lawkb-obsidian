#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OPC 管理制度登记册 §六 首次实操巡检 —— 取数脚本（只读，不写任何目标文件）"""
import re, json, os, sys
from pathlib import Path

ROOT = Path.home() / "Documents/LawKB/_AI-Memory-Hub/09-OPC"

# 记录类文件识别（不进制度册）
RECORD_PAT = [
    r"^阶段1试点", r"LTI报告", r"LTI溯源校验", r"设备运行日志",
    r"案件档案包", r"推演战报", r"^试点报告", r"_claims\.json$", r"\.json$",
    r" MindModel", r"心智模型", r"^阶段", r"^CLM设备", r"^PROJ-",
]


def rel(p: Path):
    return str(p.relative_to(ROOT))


def is_record(name: str) -> bool:
    return any(re.search(pat, name) for pat in RECORD_PAT)


print("=" * 78)
print("OPC 管理制度登记册 §六 首次实操巡检 · 取数")
print("扫描根:", ROOT)
print("=" * 78)

# ---------- 全量文件 ----------
allf = [p for p in ROOT.rglob("*") if p.is_file()]
md = [p for p in allf if p.suffix == ".md"]
print(f"\n[基数] 全部文件 {len(allf)} | .md {len(md)} | .html {len([p for p in allf if p.suffix=='.html'])} | .json {len([p for p in allf if p.suffix=='.json'])}")

# ---------- 账记录类 ----------
rec = [p for p in md if is_record(p.name)]
inst_like = [p for p in md if not is_record(p.name)]
print(f"[分类] 疑似记录类(不入制度册) {len(rec)} | 疑似制度类(须在册) {len(inst_like)}")

# ---------- 巡检1：在册率 ----------
print("\n" + "-" * 78)
print("巡检1 · 制度在册率 —— 疑似制度类文件逐项看是否登记")
print("-" * 78)
for p in sorted(inst_like, key=lambda x: rel(x)):
    print("  ", rel(p))

# ---------- 巡检2：版本标识一致性 ----------
print("\n" + "-" * 78)
print("巡检2 · 版本标识一致性 —— 页眉版本 vs 文件内变更记录末行")
print("-" * 78)
HDR_RE = re.compile(r"\*\*版本\*\*[：:]\s*([^\s　]+)")
CHG_RE = re.compile(r"\|\s*(v?\d[\d.]*)\s*\|")
for p in sorted(inst_like, key=lambda x: rel(x)):
    try:
        t = p.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"  !! 读取失败 {rel(p)}: {e}"); continue
    hdr = HDR_RE.search(t[:1500])
    hdr_v = hdr.group(1) if hdr else None
    # 页眉格式兼容：① `**版本**：vX` ② frontmatter `version: vX` ③ `｜版本：vX｜`
    if hdr_v is None:
        m2 = re.search(r"^version:\s*(v[\d.]+)", t[:1500], re.M)
        m3 = re.search(r"版本：\s*(v[\d.]+)", t[:1500])
        hdr_v = m2.group(1) if m2 else (m3.group(1) if m3 else "(无页眉版本)")
    # 【v2 修正】变更记录表存在「正序」与「倒序」两种排法，取「末行」不稳。
    # 改为：解析出 (日期, 版本) 二元组，取日期最大的那行 —— 对两种排序都成立。
    tail = t
    m = re.search(r"版本与变更记录", t)
    if m:
        tail = t[m.end():]
    pairs = []
    for line in tail.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        # 版本单元格可能带后缀，如「v1.3（部门更名）」——须放宽匹配，否则整行被跳过
        if not re.match(r"^\s*(?:v|V)?\d[\d.]*", cells[0]):
            continue
        ver = re.match(r"^\s*((?:v|V)?\d[\d.]*)", cells[0]).group(1)
        date_match = re.search(r"(20\d{2}-\d{2}-\d{2})", " ".join(cells[1:3]))
        pairs.append((date_match.group(1) if date_match else "0000-00-00", ver))
    # 【v2.1 修正】同日期多行（当日多次修订）须取「最后出现」的那行，不能用 max()
    # —— max() 在稳定序下返回首个最大值，会取到当日较早的行，产生假 DIFF。
    latest = ("-", "(无变更记录)")
    for d, v in pairs:
        if d >= latest[0]:
            latest = (d, v)
    lv = latest[1]
    lv_key = lv.split("（")[0]
    hv_key = hdr_v.split("（")[0] if hdr_v != "(无页眉版本)" else None
    if hv_key is None:
        flag = "C   "   # 页眉行缺失
    elif lv == "5" or lv == "4" or len(lv) <= 1:
        flag = "?   "   # 表格单元格误捕，无法判定
    elif hv_key == lv_key:
        flag = "OK "
    else:
        flag = "DIFF"
    print(f"  [{flag}] {rel(p)}\n        页眉={hdr_v}  变更记录最新(日期{latest[0]})={lv}")

# ---------- 巡检3：受控状态 ----------
print("\n" + "-" * 78)
print("巡检3 · 受控状态有效性 —— 🟡草案 / ⏸待批准 停留时长与路径")
print("-" * 78)

# ---------- 巡检4：使用人可追溯 ----------
print("\n" + "-" * 78)
print("巡检4 · 使用人可追溯 —— 主表使用人列空值 / 非法角色码")
print("-" * 78)
reg = (ROOT / "管理制度登记册.md").read_text(encoding="utf-8")
sec4 = reg.split("## 四、制度登记主表")[1].split("## 五、")[0]
code_ok = set("ABCDEFGH· ")
bad = []
for line in sec4.splitlines():
    if not line.startswith("|"): continue
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) < 5 or re.match(r"^\|?\s*-{3,}", line): continue
    if cells[0] in ("编号", ""): continue
    name_cell = cells[1] if len(cells) > 1 else ""
    if re.match(r"^[-: ]+$", name_cell): continue
    who = cells[3] if len(cells) >= 4 else ""
    if not who or who in ("—", "-", "（略）"):
        bad.append((cells[0], name_cell, "空"))
    else:
        codes = re.findall(r"[A-H]", who)
        if not codes:
            bad.append((cells[0], name_cell, f"无角色码: {who}"))
print(f"  主表行数(含分组标题行) 检查；异常 {len(bad)} 项")
for b in bad:
    print("   !!", b)

# ---------- 巡检8：三册边界 ----------
print("\n" + "-" * 78)
print("巡检8 · 三册边界不重叠 —— 制度册/资产册/花名册 串登检查")
print("-" * 78)
ar_path = Path.home() / "Documents/LawKB/_AI-Memory-Hub/OPC 一人公司/00-数字资产登记册/asset_registry.json"
if ar_path.exists():
    try:
        d = json.loads(ar_path.read_text(encoding="utf-8"))
        cats = d.get("categories") or d.get("data", {}).get("categories") or []
        ks = list(d.keys())
        print(f"  资产册存在，顶层键: {ks}")
        print(f"  大类数: {len(cats)}")
    except Exception as e:
        print(f"  资产册读取失败: {e}")
else:
    print("  (资产册路径不存在，跳过)")

roster = ROOT / "09-5数字员工花名册/数字员工花名册.json"
if roster.exists():
    try:
        rd = json.loads(roster.read_text(encoding="utf-8"))
        print(f"  花名册 JSON 顶层键: {list(rd.keys())}")
        s = json.dumps(rd, ensure_ascii=False)
        hit = [k for k in ["受控状态", "制度编号", "asset_registry", "asset_id"] if k in s]
        print(f"  花名册中疑似串登字段: {hit if hit else '无（边界清晰）'}")
    except Exception as e:
        print(f"  花名册读取失败: {e}")

print("\n完成（只读，未改动任何文件）")
