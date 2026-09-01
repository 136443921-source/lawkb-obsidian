#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""复刻 kg_scan v1.4 链接解析逻辑，抓取全部 unresolved(断链) 清单并分类排查。
维度1：目标全量缺失(真断链) vs 目标仅存于 .bak 备份(假断链噪声)
维度2：源笔记所在目录（真知识目录 vs 运维/系统噪声目录）
"""
import os, re, json
from collections import defaultdict, Counter

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
WORKSPACE = "/Users/chenyouqiang/Documents/LawKB"
SKIP_DIRS = {".obsidian", ".trash", "node_modules", "logs"}
META_SKIP = {"孤立笔记检测报告", "知识库压缩去重报告"}
BAK_MARK = ".bak"

def is_backup(name):
    return BAK_MARK in name

# 真知识目录（业务笔记所在）
REAL_DIRS = {"02-提炼", "03-连接", "06-沉淀", "01-采集", "04-巩固",
             "05-调用", "04-LOG", "IMA-Inbox"}
# 噪声目录（运维/系统/快照类，其断链不计入知识健康）
NOISE_DIRS = {"运维", "(根目录)", "复习记录", "系统迭代说明", "task-tracker"}

DATE_ONLY_RE = re.compile(r"^(19|20)\d{2}[-/.年]\d{1,2}([-/.月]\d{1,2})?日?$")
NUM_ONLY_RE = re.compile(r"^\d+$")
URL_RE = re.compile(r"^(https?://|www\.|file://)")
SYSTEM_REF_RE = re.compile(r"^(?:memory|待推送_[0-9\-]+)$", re.IGNORECASE)
fm_re = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
link_re = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]*)?(?:\|[^\]]*)?\]\]")

def parse_fm(text):
    m = fm_re.match(text)
    if not m: return text
    return text[m.end():]

# ---------- 建三个索引 ----------
notes = {}          # rel -> {base, dir1, dir2, body}   （ROOT 内，排除 .bak/META_SKIP）
ws_index = defaultdict(list)        # base -> [full]  （全工作区，排除 .bak）
bak_only_index = defaultdict(list)  # base -> [full]  （仅 .bak 备份内存在，用于判假断链）

for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames
                   if d not in SKIP_DIRS and not d.startswith(".") and not is_backup(d)]
    for fn in filenames:
        if not fn.endswith(".md"): continue
        full = os.path.join(dirpath, fn)
        rel = os.path.relpath(full, ROOT)
        parts = rel.split(os.sep)
        dir1 = parts[0] if len(parts) > 1 else "(根目录)"
        dir2 = parts[1] if len(parts) > 2 else "(直属)"
        base = fn[:-3]
        if any(meta in rel for meta in META_SKIP):
            continue
        try:
            body = parse_fm(open(full, encoding="utf-8", errors="ignore").read())
        except Exception:
            continue
        notes[rel] = {"base": base, "dir1": dir1, "dir2": dir2, "body": body}

for dirpath, dirnames, filenames in os.walk(WORKSPACE):
    dirnames[:] = [d for d in dirnames
                   if d not in SKIP_DIRS and not d.startswith(".")]
    for fn in filenames:
        if not fn.endswith(".md"): continue
        full = os.path.join(dirpath, fn)
        base = fn[:-3]
        if is_backup(full) or is_backup(dirpath):
            bak_only_index[base].append(full)   # 仅记备份副本
        else:
            ws_index[base].append(full)

# ---------- 复刻断链判定 + 抓清单 ----------
unresolved = []   # (source_rel, target_base)
for rel, n in notes.items():
    for m in link_re.finditer(n["body"]):
        target = m.group(1).strip().rstrip("\\").strip()
        if not target: continue
        tbase = os.path.basename(target)
        if tbase.endswith(".md"): tbase = tbase[:-3]
        if any(tbase.endswith(ext) for ext in (".html",".pdf",".docx",".png",".jpg",".jpeg",".gif",".csv",".xlsx")):
            continue
        if tbase.startswith("self.md"): continue
        if re.search(r"^(?:x|wikilink|案件笔记名|规则名|链接|\.\.\.)$|XXX|Rxxx", tbase): continue
        if DATE_ONLY_RE.match(tbase) or NUM_ONLY_RE.match(tbase) or URL_RE.match(tbase): continue
        if SYSTEM_REF_RE.match(tbase): continue
        if not ws_index.get(tbase):
            unresolved.append((rel, tbase))

# ---------- 分类 ----------
real_src, noise_src = [], []
true_missing, bak_noise = [], []
by_dir1 = Counter()
by_target_kind = Counter()

for src, tgt in unresolved:
    d1 = src.split(os.sep)[0]
    by_dir1[d1] += 1
    entry = {"src": src, "tgt": tgt, "src_dir1": d1}
    if d1 in NOISE_DIRS:
        noise_src.append(entry)
    else:
        real_src.append(entry)
    if bak_only_index.get(tgt):
        entry["class"] = "备份噪声(目标仅存.bak)"
        bak_noise.append(entry)
        by_target_kind["备份噪声(目标仅存.bak)"] += 1
    else:
        entry["class"] = "真知识断链(目标全量缺失)"
        true_missing.append(entry)
        by_target_kind["真知识断链(目标全量缺失)"] += 1

# ---------- 输出 ----------
summary = {
    "total_unresolved": len(unresolved),
    "by_source_dir1": dict(by_dir1),
    "by_target_kind": dict(by_target_kind),
    "real_src_count": len(real_src),
    "noise_src_count": len(noise_src),
    "true_missing_count": len(true_missing),
    "bak_noise_count": len(bak_noise),
}
print("===== 摘要 =====")
print(json.dumps(summary, ensure_ascii=False, indent=2))
print("\n===== 真知识断链明细(目标全量缺失) =====")
for e in sorted(true_missing, key=lambda x: (x["src_dir1"], x["src"])):
    print(f"  [{e['src_dir1']}] {e['src']}  ->  [[{e['tgt']}]]")
print("\n===== 备份噪声明细(目标仅存于 .bak) =====")
for e in sorted(bak_noise, key=lambda x: (x["src_dir1"], x["src"])):
    print(f"  [{e['src_dir1']}] {e['src']}  ->  [[{e['tgt']}]]  (仅存: {bak_only_index[e['tgt']][:1]})")
print("\n===== 源噪声目录明细(运维/系统类) =====")
for e in sorted(noise_src, key=lambda x: (x["src_dir1"], x["src"])):
    print(f"  [{e['src_dir1']}] {e['src']}  ->  [[{e['tgt']}]]")

# 落盘明细供复查
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_diag_unresolved.json"), "w", encoding="utf-8") as f:
    json.dump({"summary": summary,
               "true_missing": true_missing,
               "bak_noise": bak_noise,
               "noise_src": noise_src}, f, ensure_ascii=False, indent=2)
print("\n[dump] 明细已写入 _diag_unresolved.json")
