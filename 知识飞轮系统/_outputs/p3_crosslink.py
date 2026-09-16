# -*- coding: utf-8 -*-
import re, glob, os, sys

DIR = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库/慈法合规"
os.chdir(DIR)

DRY = "--apply" not in sys.argv

# 1) rule_id -> stem（文件名去 .md）
rid2stem = {}
for f in glob.glob("R-CF-*.md"):
    stem = f[:-3]
    m = re.match(r"(R-CF-\d+)", stem)
    if m:
        rid2stem[m.group(1)] = stem

def L(rid):
    return "[[%s]]" % rid2stem["R-CF-%d" % rid]

# 2) 映射
B_TO_C = {
 143:[162], 144:[158], 145:[160], 146:[160], 147:[161],
 148:[164,162], 149:[165], 150:[157,162], 151:[166], 152:[160],
}
C_TO_JUDGE = {
 156:[128], 157:[150,119], 158:[144], 159:[130,131], 160:[145,146,152],
 161:[147], 162:[143,148,150], 163:[136,137], 164:[147,148], 165:[149,139],
 166:[151], 167:[119], 168:[149,134], 169:[145,137], 170:[151], 171:[],
}
B_RIDS = list(B_TO_C.keys())
C_RIDS = list(C_TO_JUDGE.keys())

def make_block(is_b, rid):
    if rid == 171:
        return ("- **判准↔操作 双向对应**（本卡＝B+C 全系列「术语/工具速查索引卡」，"
                "检索入口见 [[连接枢纽-慈法合规]]）")
    if is_b:
        items = "\n".join("  - %s" % L(c) for c in B_TO_C[rid])
        return ("- **判准↔操作 双向对应**（本卡＝判准/审查红线卡，下列为对应**操作指引卡**）：\n"
                + items)
    else:
        items = "\n".join("  - %s" % L(j) for j in C_TO_JUDGE[rid])
        return ("- **判准↔操作 双向对应**（本卡＝操作指引卡，下列为对应**判准/审查红线卡**，"
                "依标题区分 B 批或 P0 批）：\n" + items)

def clean_link_line(line, self_stem):
    # 仅处理纯链接缩进行：  - [[A]] · [[B]] · ...
    if not re.match(r'^\s{2,}-\s+\[\[', line):
        return line
    # 取行内所有 [[...]]
    toks = re.findall(r'\[\[[^\]]+\]\]', line)
    seen = set()
    out = []
    for t in toks:
        inner = t[2:-2]
        if inner == self_stem:
            continue  # 去掉自链接
        if t in seen:
            continue  # 去重
        seen.add(t)
        out.append(t)
    if not out:
        return None  # 整行清空则删除
    return "  - " + " · ".join(out)

def process(rid, is_b):
    stem = rid2stem["R-CF-%d" % rid]
    path = stem + ".md"
    txt = open(path, encoding="utf-8").read()
    lines = txt.split("\n")

    # 找关联段头
    hdr_idx = None
    for i, l in enumerate(lines):
        if re.match(r'^##\s*关联', l):
            hdr_idx = i
            break
    if hdr_idx is None:
        print("[跳过·无关联段]", path); return

    # 清理：关联段内的链接行
    new_lines = []
    in_assoc = False
    for i, l in enumerate(lines):
        if i == hdr_idx:
            new_lines.append(l); in_assoc = True; continue
        if in_assoc and l.startswith("## ") and i != hdr_idx:
            in_assoc = False
        if in_assoc:
            cl = clean_link_line(l, stem)
            if cl is None:
                continue  # 删除空行
            new_lines.append(cl)
        else:
            new_lines.append(l)

    txt2 = "\n".join(new_lines)

    # 插入双向对应块（幂等：已存在则跳过）
    if "判准↔操作 双向对应" not in txt2:
        blk = make_block(is_b, rid)
        hdr_line = new_lines[hdr_idx]
        # 在 hdr 后插入
        insert_at = hdr_idx + 1
        new_lines2 = new_lines[:insert_at] + ["", blk, ""] + new_lines[insert_at:]
        txt2 = "\n".join(new_lines2)
    else:
        print("[已存在·跳过插入]", path)

    if DRY:
        # 打印关联段
        m = re.search(r'^##\s*关联.*$', txt2, re.M)
        print("="*60); print("FILE:", path); print(m.group(0))
        print(txt2[m.end():].rstrip() if m else txt2)
    else:
        open(path, "w", encoding="utf-8").write(txt2)
        print("[已写]", path)

for rid in B_RIDS:
    process(rid, True)
for rid in C_RIDS:
    process(rid, False)

print("\n=== DRY=", DRY, "===")
