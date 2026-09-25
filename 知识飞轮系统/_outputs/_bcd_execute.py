#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B/C/D 线执行（dry / apply）
阶段：① B线异类移出(学习笔记/公众号/案例) ② C/D线按 rule_id 域升一级库 + 零散归并
铁律：先备份(裁判规则库+02-提炼+01-采集) → 按 frontmatter rule_id 归属(文件名不动) → canonical 同步(直接读 rule_id 建映射,修复A线坑) → 10份/轮 → 幂等。
"""
import os, re, shutil, collections, datetime, sys

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT = os.path.join(ROOT, "_outputs")
MODE = sys.argv[1] if len(sys.argv) > 1 else "dry"
TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
RID_RE = re.compile(r"^rule_id:\s*(\S+)", re.M)
VALID = re.compile(r"^R-([A-Z]{2})-\d{1,3}$")
SKIP = [".backup", ".trash", "_quarantine", ".backup_link", "__pycache__"]

CR = os.path.join(ROOT, "06-沉淀", "裁判规则库")

# 域 → 新一级库名
DOMAIN_MAP = {
    "LN": "律师实务域库", "GS": "公司法域库", "HY": "婚姻家庭域库",
    "LD": "劳动人事域库", "GZ": "劳动人事域库",   # 工伤并入劳动
    "HG": "合规域库", "SH": "商事纠纷域库", "XS": "刑事域库",
    "JG": "建设工程域库", "CS": "案例库",
    # 零散兜底
    "TQ": "通用裁判规则库", "WT": "通用裁判规则库", "RA": "通用裁判规则库",
    "RK": "通用裁判规则库", "CL": "通用裁判规则库", "IP": "通用裁判规则库",
    "RG": "通用裁判规则库", "RY": "通用裁判规则库", "RM": "通用裁判规则库",
    "YS": "通用裁判规则库", "XR": "通用裁判规则库", "RL": "通用裁判规则库",
    "RS": "通用裁判规则库", "RN": "通用裁判规则库", "HJ": "通用裁判规则库",
}
# B线异类子目录 → 外部目标（相对 ROOT）
B_LINE = {
    "学习笔记": "02-提炼/经验卡片",
    "公众号": "01-采集",
    "案例": "06-沉淀/案例库",
}

def rid_of(p):
    try:
        h = open(p, encoding="utf-8", errors="ignore").read(2500)
        m = RID_RE.search(h)
        return m.group(1).strip() if m else None
    except Exception:
        return None

def is_card(p):
    """真·域卡：文件名 R-2字母-数字 或 rule_id 合法 R-2字母-数字（排除元数据/旧R0XX遗留）。"""
    if VALID.match(os.path.splitext(os.path.basename(p))[0]):
        return True
    rid = rid_of(p)
    return bool(rid and VALID.match(rid))

def fam_of(p):
    rid = rid_of(p)
    if rid and VALID.match(rid):
        return rid[2:4]
    m = re.match(r"R-([A-Za-z]+)-", os.path.basename(p))
    return m.group(1) if m else "?"

def plan():
    moves = []  # (src_abs, dst_rel)
    # 阶段 B：异类子目录整体移出
    for sub, dest in B_LINE.items():
        d = os.path.join(CR, sub)
        if not os.path.exists(d):
            continue
        for dp, dn, fn in os.walk(d):
            if any(x in dp for x in SKIP):
                continue
            for f in fn:
                if f.endswith(".md"):
                    moves.append((os.path.join(dp, f), os.path.join(ROOT, dest, f)))
    # 阶段 C/D：裁判规则库剩余卡片按域升库（仅真·域卡；元数据/旧R0XX遗留留原处）
    stay = []
    for dp, dn, fn in os.walk(CR):
        if any(x in dp for x in SKIP):
            continue
        rel = os.path.relpath(dp, CR)
        if rel.split("/")[0] in B_LINE:   # B线已处理
            continue
        for f in fn:
            if not f.endswith(".md"):
                continue
            p = os.path.join(dp, f)
            if not is_card(p):
                stay.append(os.path.relpath(p, ROOT))
                continue
            fam = fam_of(p)
            lib = DOMAIN_MAP.get(fam, "通用裁判规则库")
            moves.append((p, os.path.join(ROOT, "06-沉淀", lib, f)))
    plan.STAY = stay
    return moves

def dry():
    moves = plan()
    by_dst = collections.Counter(os.path.dirname(t) for _, t in moves)
    print("===== B/C/D DRY-RUN =====")
    print(f"[模式] {MODE} | [时间] {TS}")
    print(f"将移动主卡：{len(moves)} 张")
    for dst in sorted(by_dst, key=lambda x: -by_dst[x]):
        print(f"  {os.path.relpath(dst, ROOT):40s} {by_dst[dst]}")
    # 碰撞检测：目标是否已存在同名文件
    coll = 0
    for s, t in moves:
        if os.path.exists(t):
            coll += 1
            if coll <= 20:
                print(f"  [碰撞] {os.path.basename(s)} 目标已存在: {os.path.relpath(t, ROOT)}")
    print(f"目标同名碰撞: {coll} 张 {'⚠️将跳过保幂等' if coll else '✅'}")
    stay = getattr(plan, "STAY", [])
    print(f"留原处(元数据/旧R0XX遗留, 不迁移): {len(stay)} 张")
    rep = os.path.join(OUT, f"BCD-dryrun-{TS}.md")
    L = ["# B/C/D Dry-Run", "", f"> {TS} | 模式 {MODE} | 移动 {len(moves)} 张 | 留原处 {len(stay)} 张", "",
         "## 各目标计数"] + [f"- {os.path.relpath(d, ROOT)}: {n}" for d, n in sorted(by_dst.items(), key=lambda x:-x[1])]
    L += [f"## 碰撞: {coll}", "", f"## 留原处(不迁移, 待人工定夺): {len(stay)}"] + [f"- {s}" for s in stay]
    open(rep, "w", encoding="utf-8").write("\n".join(L))
    print(f"[dry报告] {rep}")

def backup_file(p, tag=""):
    """精准备份单文件到 /tmp/bcd_<ts>/<tag>/<relpath>（避免整目录 copytree 超时）。"""
    rel = os.path.relpath(p, ROOT)
    dst = os.path.join(f"/tmp/bcd_{TS}", tag, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(p, dst)

def sync_canonical():
    # 直接逐文件建映射（修复A线缓存坑）
    mapping = {}
    for base in [os.path.join(ROOT, "06-沉淀"), os.path.join(ROOT, "02-提炼"), os.path.join(ROOT, "01-采集")]:
        for dp, dn, fn in os.walk(base):
            if any(x in dp for x in SKIP):
                continue
            for f in fn:
                if not (f.startswith("R-") and f.endswith(".md")):
                    continue
                p = os.path.join(dp, f)
                rid = rid_of(p)
                if rid and VALID.match(rid):
                    mapping[rid] = os.path.relpath(p, ROOT)
    cnt = 0
    for d in ["03-连接", "02-提炼"]:
        for dp, dn, fn in os.walk(os.path.join(ROOT, d)):
            if any(x in dp for x in SKIP):
                continue
            for f in fn:
                if not f.endswith(".md"):
                    continue
                p = os.path.join(dp, f)
                rid = rid_of(p)
                if rid in mapping:
                    txt = open(p, encoding="utf-8", errors="ignore").read()
                    if "canonical:" in txt:
                        txt2 = re.sub(r"^canonical:\s*.*$", f"canonical: {mapping[rid]}", txt, flags=re.M)
                        if txt2 != txt:
                            backup_file(p, "canonical")
                            open(p, "w", encoding="utf-8").write(txt2)
                            cnt += 1
    print(f"[canonical 更新] {cnt} 张")

def apply():
    print("===== B/C/D APPLY =====")
    moves = plan()
    done = 0
    skipped = 0
    for s, t in moves:
        os.makedirs(os.path.dirname(t), exist_ok=True)
        if os.path.exists(t):
            skipped += 1
            continue
        backup_file(s, "move_src")   # 先备份源(精准)
        shutil.move(s, t)
        done += 1
        if done % 10 == 0:
            print(f"[进度] 已移 {done}/{len(moves)}")
    print(f"[迁移] 完成 {done} 张，跳过(碰撞) {skipped} 张")
    print(f"[备份] /tmp/bcd_{TS}/move_src （{done} 源）")
    sync_canonical()
    print("[完成] B/C/D 三线 apply + canonical 同步结束")

if __name__ == "__main__":
    if MODE == "apply":
        apply()
    else:
        dry()
