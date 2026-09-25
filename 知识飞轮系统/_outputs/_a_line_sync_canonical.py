#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A 线 · 指针 canonical 同步（独立修复脚本 v2）
=======================================
仅重写 03-连接 / 02-提炼 中同 rule_id 指针副本的 canonical 字段，
指向 06-沉淀 下 5 个新一级库的实际新路径。
修复点：直接从每个文件读取 rule_id（不依赖 apply 前的 ALL_FILES 缓存）。
优化：仅备份「实际会被改写」的指针文件（不整目录复制），避免超时。
铁律：先备份命中文件 → 再改写 → 写报告。
"""
import os, re, shutil, datetime

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT = os.path.join(ROOT, "_outputs")
A = {"PI", "HT", "AY", "CF", "PR"}  # 5 个新库对应域
RID_RE = re.compile(r"^rule_id:\s*(\S+)", re.M)
VALID = re.compile(r"^R-([A-Z]{2})-\d{1,3}$")
TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
SKIP = [".backup", ".trash", "_quarantine", ".backup_link", "__pycache__"]

def rid_direct(p):
    try:
        h = open(p, encoding="utf-8", errors="ignore").read(2500)
        m = RID_RE.search(h)
        return m.group(1).strip() if m else None
    except Exception:
        return None

def build_mapping():
    mapping = {}
    base = os.path.join(ROOT, "06-沉淀")
    for dp, dn, fn in os.walk(base):
        if any(x in dp for x in SKIP):
            continue
        for f in fn:
            if not (f.startswith("R-") and f.endswith(".md")):
                continue
            p = os.path.join(dp, f)
            rid = rid_direct(p)
            if rid and VALID.match(rid):
                fam = rid[2:4]
                if fam in A:
                    mapping[rid] = os.path.relpath(p, ROOT)
    return mapping

def main():
    mapping = build_mapping()
    print(f"[映射] 主卡新位置 {len(mapping)} 条")

    # 预扫：收集实际会被改写的指针文件
    to_change = []  # (abspath, new_canon)
    for d in ["03-连接", "02-提炼"]:
        for dp, dn, fn in os.walk(os.path.join(ROOT, d)):
            if any(x in dp for x in SKIP):
                continue
            for f in fn:
                if not f.endswith(".md"):
                    continue
                p = os.path.join(dp, f)
                rid = rid_direct(p)
                if rid in mapping:
                    try:
                        txt = open(p, encoding="utf-8", errors="ignore").read()
                    except Exception:
                        continue
                    if "canonical:" in txt:
                        to_change.append((p, mapping[rid]))
    print(f"[命中] 待改写指针 {len(to_change)} 张")

    # 仅备份命中文件（保留相对路径）
    bak = f"/tmp/r_lib_a_sync_{TS}"
    os.makedirs(bak, exist_ok=True)
    for p, _ in to_change:
        rel = os.path.relpath(p, ROOT)
        dst = os.path.join(bak, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(p, dst)
    print(f"[备份] {bak}（{len(to_change)} 张）")

    # 改写
    cnt = 0
    changed = []
    for p, new_canon in to_change:
        txt = open(p, encoding="utf-8", errors="ignore").read()
        txt2 = re.sub(r"^canonical:\s*.*$", f"canonical: {new_canon}", txt, flags=re.M)
        if txt2 != txt:
            open(p, "w", encoding="utf-8").write(txt2)
            cnt += 1
            changed.append((os.path.relpath(p, ROOT), new_canon))
    print(f"[canonical 更新] {cnt} 张")

    rep = os.path.join(OUT, f"A线-指针同步报告-{TS}.md")
    L = ["# A 线指针 canonical 同步报告", "",
         f"> {TS} | 独立修复 v2 | 更新 {cnt} 张 | 备份 {bak}", ""]
    L.append("## 改写明细")
    for rel, np in changed:
        L.append(f"- `{rel}` → `canonical: {np}`")
    open(rep, "w", encoding="utf-8").write("\n".join(L))
    print(f"[报告] {rep}")

if __name__ == "__main__":
    main()
