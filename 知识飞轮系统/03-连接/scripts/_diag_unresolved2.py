#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""精炼分类：把 kg_scan 标记的 100 条 unresolved 拆成
  (A) 畸形嵌套 wikilink（正则把内层 [[ 抓成目标，链接本身写坏）
  (B) 真知识断链（干净目标且全量不存在）
并验证畸形项的内层干净目标是否真实存在（决定能否靠"修括号"消解）。
"""
import os, re, json
from collections import defaultdict, Counter

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
WORKSPACE = "/Users/chenyouqiang/Documents/LawKB"
SKIP_DIRS = {".obsidian", ".trash", "node_modules", "logs"}
META_SKIP = {"孤立笔记检测报告", "知识库压缩去重报告"}
BAK_MARK = ".bak"
def is_backup(name): return BAK_MARK in name

DATE_ONLY_RE = re.compile(r"^(19|20)\d{2}[-/.年]\d{1,2}([-/.月]\d{1,2})?日?$")
NUM_ONLY_RE = re.compile(r"^\d+$")
URL_RE = re.compile(r"^(https?://|www\.|file://)")
SYSTEM_REF_RE = re.compile(r"^(?:memory|待推送_[0-9\-]+)$", re.IGNORECASE)
fm_re = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
link_re = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]*)?(?:\|[^\]]*)?\]\]")
INNER_RE = re.compile(r"\[\[([^\[\]\|#]+?)\]\]")   # 干净内层目标

def parse_fm(text):
    m = fm_re.match(text)
    return text[m.end():] if m else text

notes = {}
ws_index = defaultdict(list)
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".") and not is_backup(d)]
    for fn in filenames:
        if not fn.endswith(".md"): continue
        full = os.path.join(dirpath, fn); rel = os.path.relpath(full, ROOT)
        if any(meta in rel for meta in META_SKIP): continue
        try: body = parse_fm(open(full, encoding="utf-8", errors="ignore").read())
        except Exception: continue
        notes[rel] = body
for dirpath, dirnames, filenames in os.walk(WORKSPACE):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
    for fn in filenames:
        if not fn.endswith(".md"): continue
        if is_backup(fn) or is_backup(dirpath): continue
        ws_index[fn[:-3]].append(os.path.join(dirpath, fn))

unresolved = []
for rel, body in notes.items():
    for m in link_re.finditer(body):
        t = m.group(1).strip().rstrip("\\").strip()
        if not t: continue
        tb = os.path.basename(t)
        if tb.endswith(".md"): tb = tb[:-3]
        if any(tb.endswith(e) for e in (".html",".pdf",".docx",".png",".jpg",".jpeg",".gif",".csv",".xlsx")): continue
        if tb.startswith("self.md"): continue
        if re.search(r"^(?:x|wikilink|案件笔记名|规则名|链接|\.\.\.)$|XXX|Rxxx", tb): continue
        if DATE_ONLY_RE.match(tb) or NUM_ONLY_RE.match(tb) or URL_RE.match(tb): continue
        if SYSTEM_REF_RE.match(tb): continue
        if not ws_index.get(tb):
            unresolved.append((rel, tb))

malformed, real_missing = [], []
malformed_inner_exists = 0
real_missing_targets = []
for src, tgt in unresolved:
    has_nest = ("[[" in tgt) or tgt.startswith("[")
    if has_nest:
        # 取内层干净目标
        inners = INNER_RE.findall(tgt)
        clean = inners[0] if inners else tgt.lstrip("[")
        clean = clean.strip()
        exists = bool(ws_index.get(clean))
        if exists: malformed_inner_exists += 1
        malformed.append({"src": src, "tgt": tgt, "inner": clean, "inner_exists": exists})
    else:
        real_missing.append({"src": src, "tgt": tgt})
        real_missing_targets.append(tgt)

summary = {
    "total": len(unresolved),
    "malformed_nested": len(malformed),
    "  -> 其中内层目标真实存在(修括号即可消解)": malformed_inner_exists,
    "  -> 其中内层目标也不存在(需建概念页)": len(malformed) - malformed_inner_exists,
    "real_missing_clean": len(real_missing),
}
print("===== 精炼分类摘要 =====")
print(json.dumps(summary, ensure_ascii=False, indent=2))

print(f"\n===== 真知识断链(干净目标且全量缺失) 共 {len(real_missing)} 条 =====")
for e in sorted(real_missing, key=lambda x: x["tgt"]):
    print(f"  {e['tgt']}   <- {e['src']}")

print(f"\n===== 畸形嵌套 wikilink 共 {len(malformed)} 条（抽样前25）=====")
for e in malformed[:25]:
    mark = "✅内层存在" if e["inner_exists"] else "❌内层缺失"
    print(f"  [{mark}] 原:[[{e['tgt']}]]  内层:{e['inner']}  <- {e['src']}")

# 源文件聚合：哪些文件是畸形重灾区
src_counter = Counter(e["src"] for e in malformed)
print("\n===== 畸形来源文件 TOP =====")
for s, c in src_counter.most_common(12):
    print(f"  {c:>3}  {s}")

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_diag_unresolved2.json"), "w", encoding="utf-8") as f:
    json.dump({"summary": summary, "real_missing": real_missing, "malformed": malformed}, f, ensure_ascii=False, indent=2)
print("\n[dump] _diag_unresolved2.json")
