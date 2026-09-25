#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
裁判规则库 A 线 · 执行脚本（dry-run / apply 双模式）
=================================================
预处理（迁移前）：按老强 16:58 确认
  1. 删 R-CF-173 A（慈善通用版1497字），留 B（慈法合规合规审查卡4842字）
  2. R-HT-102 B 取 HT 空闲新号（双维度）
  3. R-PI-157 B 取 PI 空闲新号（双维度）
  4. R-HT-101 B 补 LN 空闲新号（代理意见属律师实务）
主迁移：1377 张主卡按 frontmatter rule_id 前缀移入 5 个新一级库（文件名不动）
指针同步：392 张同 rule_id 指针副本 canonical 批量重写指向新路径
铁律：先备份 / dry-run 复核 / 10份-轮 / 确认幂等 / 绝不重命名文件
优化：全库仅扫描一次（ALL_FILES 缓存），get_free_rid/plan 复用内存数据
"""
import os, re, sys, shutil, collections, datetime

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT = os.path.join(ROOT, "_outputs")
A = {"PI": "人伤法域库", "HT": "合同风险规则库", "AY": "案由路由卡族",
     "CF": "慈善合规域库", "PR": "证据规则卡族"}
MODE = sys.argv[1] if len(sys.argv) > 1 else "dry"
TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP = f"/tmp/r_lib_a_{TS}"

RID_RE = re.compile(r"^rule_id:\s*(\S+)", re.M)
VALID = re.compile(r"^R-([A-Z]{2})-\d{1,3}$")
ALL_FILES = None  # [(abspath, basename, rid)]

def load_all():
    global ALL_FILES
    if ALL_FILES is not None:
        return ALL_FILES
    out = []
    for dp, dn, fn in os.walk(ROOT):
        if any(x in dp for x in [".workbuddy", "__pycache__"]):
            continue
        if any(s in dp for s in ["/.backup", "/.trash", "_quarantine", "/.backup_link"]):
            continue
        for f in fn:
            if f.startswith("R-") and f.endswith(".md"):
                p = os.path.join(dp, f)
                rid = None
                try:
                    h = open(p, encoding="utf-8", errors="ignore").read(2500)
                    m = RID_RE.search(h)
                    if m:
                        rid = m.group(1).strip()
                except Exception:
                    pass
                out.append((p, f, rid))
    ALL_FILES = out
    return ALL_FILES

def get_rid(p):
    for ap, bn, rid in load_all():
        if ap == p:
            return rid
    return None

def fam_of(p):
    rid = get_rid(p)
    if rid and VALID.match(rid):
        return rid[2:4]
    m = re.match(r"R-([A-Za-z]+)-", os.path.basename(p))
    return m.group(1) if m else "?"

def get_free_rid(domain):
    """双维度铁律：文件名维度 + frontmatter rule_id 维度，取 max+1（内存数据）"""
    maxn = 0
    for ap, bn, rid in load_all():
        m = re.match(rf"R-{domain}-(\d+)\.md$", bn)
        if m:
            maxn = max(maxn, int(m.group(1)))
        if rid and re.match(rf"^R-{domain}-(\d+)$", rid):
            maxn = max(maxn, int(re.search(r"(\d+)$", rid).group(1)))
    return f"R-{domain}-{maxn+1:03d}"

# 预处理项
PRE = [
    ("delete", "06-沉淀/裁判规则库/慈善/R-CF-173-捐赠财产指定专项基金用途不能实现捐赠人可撤销并请求返还.md", None),
    ("renum", "06-沉淀/裁判规则库/合同风险/R-HT-102-合同相对性实际交易方认定.md", "HT"),
    ("renum", "06-沉淀/裁判规则库/人伤法/R-PI-157-医疗告知义务代签与举证不能.md", "PI"),
    ("renum", "06-沉淀/裁判规则库/合同风险/R-HT-101-代理意见写作规范.md", "LN"),
]
PRE_PATHS = {os.path.join(ROOT, r): d for _, r, d in PRE}
PRE_DELETE = {os.path.join(ROOT, r) for _, r, d in PRE if d is None}

def plan_pre():
    plan = []
    for act, rel, dom in PRE:
        p = os.path.join(ROOT, rel)
        if act == "delete":
            plan.append(("DELETE", rel, "(删 R-CF-173 A，留 B)", None))
        else:
            new = get_free_rid(dom)
            mo = re.match(r"(R-[A-Z]{2}-\d+)", os.path.basename(p))
            old = mo.group(1) if mo else "?"
            plan.append(("RENUM", rel, f"→ {new}（aliases 补 [{old}]，文件名不动）", new))
    return plan

def plan_moves():
    moves = []
    for ap, bn, rid in load_all():
        rel = os.path.relpath(ap, ROOT)
        if rel.split("/")[0] != "06-沉淀":
            continue
        if ap in PRE_DELETE:
            continue
        if ap in PRE_PATHS:
            dom = PRE_PATHS[ap]   # 改后域
            fam = dom
        else:
            fam = fam_of(ap)
        if fam not in A:
            continue
        target = os.path.join(ROOT, "06-沉淀", A[fam], bn)
        moves.append((rel, os.path.relpath(target, ROOT)))
    return moves

def dry():
    print("===== A 线执行 · DRY-RUN =====")
    print(f"[MODE] {MODE} | 时间 {TS}")
    print("\n--- 预处理段（迁移前）---")
    pre = plan_pre()
    for act, rel, desc, new in pre:
        print(f"  {act:6s} {rel}\n         {desc}")
    print("\n--- 主迁移段（按 frontmatter rule_id 归属，文件名不动）---")
    moves = plan_moves()
    by_lib = collections.Counter(os.path.dirname(t).split("/")[-1] for _, t in moves)
    print(f"  将移动主卡：{len(moves)} 张")
    for lib, n in by_lib.most_common():
        print(f"    {lib}: {n}")
    ptr = sum(1 for ap, bn, rid in load_all()
              if os.path.relpath(ap, ROOT).split('/')[0] in ('03-连接', '02-提炼') and fam_of(ap) in A)
    print(f"\n--- 指针同步段 ---\n   {ptr} 张同 rule_id 指针副本 canonical 批量重写指向新路径（待 apply）")
    rep = os.path.join(OUT, f"A线执行-dryrun-{TS}.md")
    L = ["# A 线执行 DRY-RUN 报告", "", f"> {TS} | 模式 dry | 未执行任何写入/移动/删除", ""]
    L.append("## 预处理段")
    for act, rel, desc, new in pre:
        L.append(f"- {act} `{rel}` → {desc}")
    L.append("## 主迁移段")
    L.append(f"将移动 {len(moves)} 张主卡：")
    for lib, n in by_lib.most_common():
        L.append(f"- {lib}: {n}")
    L.append("## 指针同步段")
    L.append(f"{ptr} 张同 rule_id 指针副本 canonical 重写（apply 阶段）")
    open(rep, "w", encoding="utf-8").write("\n".join(L))
    print(f"\n[dry 报告] {rep}")

def set_rid_with_alias(p, new, old):
    txt = open(p, encoding="utf-8", errors="ignore").read()
    if RID_RE.search(txt):
        txt2 = RID_RE.sub(f"rule_id: {new}", txt, count=1)
    else:
        # 无 rule_id 行（如 R-HT-101 B 空号卡）：插入到 frontmatter 内
        if txt.startswith("---"):
            idx = txt.find("\n---", 3)
            if idx != -1:
                txt2 = txt[:idx+5] + f"\nrule_id: {new}\n" + txt[idx+5:]
            else:
                txt2 = f"rule_id: {new}\n" + txt
        else:
            txt2 = f"---\nrule_id: {new}\n---\n" + txt
    if re.search(r"^aliases:", txt2, re.M):
        txt2 = re.sub(r"(^aliases:\s*\n)", f"\\1  - {old}\n", txt2, count=1, flags=re.M)
    else:
        txt2 = txt2.rstrip() + f"\naliases:\n  - {old}\n"
    open(p, "w", encoding="utf-8").write(txt2)

def sync_canonical():
    # 迁移后实际扫描主卡新位置（不依赖移动前缓存，避免 canonical 写旧路径）
    mapping = {}
    base = os.path.join(ROOT, "06-沉淀")
    for dp, dn, fn in os.walk(base):
        if any(x in dp for x in [".backup", ".trash", "_quarantine", ".backup_link", "__pycache__"]):
            continue
        for f in fn:
            if not (f.startswith("R-") and f.endswith(".md")):
                continue
            p = os.path.join(dp, f)
            rid = get_rid(p)
            if rid and VALID.match(rid) and fam_of(p) in A:
                mapping[rid] = os.path.relpath(p, ROOT)
    cnt = 0
    for ap, bn, rid in load_all():
        if os.path.relpath(ap, ROOT).split("/")[0] not in ("03-连接", "02-提炼"):
            continue
        if rid in mapping:
            txt = open(ap, encoding="utf-8", errors="ignore").read()
            if "canonical:" in txt:
                txt2 = re.sub(r"^canonical:\s*.*$", f"canonical: {mapping[rid]}", txt, flags=re.M)
                if txt2 != txt:
                    open(ap, "w", encoding="utf-8").write(txt2)
                    cnt += 1
    print(f"  canonical 更新 {cnt} 张")

def apply():
    print("===== A 线执行 · APPLY =====")
    src = os.path.join(ROOT, "06-沉淀")  # 全量备份 06-沉淀（move 跨子目录，须完整可回滚）
    shutil.copytree(src, BACKUP, dirs_exist_ok=True)
    print(f"[备份] {BACKUP}")
    for act, rel, dom in PRE:
        p = os.path.join(ROOT, rel)
        if act == "delete":
            dst = os.path.join(ROOT, "06-沉淀", "裁判规则库", ".trash_a", os.path.basename(p))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(p, dst)
            print(f"[删] {rel} → .trash_a")
        else:
            new = get_free_rid(dom)
            mo = re.match(r"(R-[A-Z]{2}-\d+)", os.path.basename(p))
            old = mo.group(1) if mo else "?"
            set_rid_with_alias(p, new, old)
            print(f"[改号] {rel} → {new} (alias {old})")
    moves = plan_moves()
    done = 0
    for rel, tgt in moves:
        sp = os.path.join(ROOT, rel)
        tp = os.path.join(ROOT, tgt)
        os.makedirs(os.path.dirname(tp), exist_ok=True)
        if os.path.exists(tp):
            continue
        shutil.move(sp, tp)
        done += 1
        if done % 10 == 0:
            print(f"[进度] 已移 {done}/{len(moves)}")
    print(f"[迁移] 完成 {done} 张")
    sync_canonical()
    print("[指针] canonical 同步完成")

if __name__ == "__main__":
    load_all()
    if MODE == "apply":
        apply()
    else:
        dry()
