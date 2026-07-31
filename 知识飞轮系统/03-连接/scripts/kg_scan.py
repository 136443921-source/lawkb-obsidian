#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知识飞轮系统 知识图谱扫描器（自动化版，动态当前月）
- 遍历 ROOT 下所有 .md，解析 frontmatter、双向链接 `[[文件名]]`、标签。
- 输出机器可读 JSON 到本脚本同目录 kg_data.json，并打印关键统计（首行 JSON 供捕获）。
- 供 kg_html.py 与「周日知识维护批处理」调用。
"""
import os, re, json, datetime
from collections import defaultdict

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {".obsidian", ".trash", "node_modules", "logs"}
# meta 报告目录：其正文中的 `[[...]]` 多为「断链示例」文档说明，非真实链接，不计入断链
META_SKIP = {"孤立笔记检测报告", "知识库压缩去重报告"}
MONTH = datetime.date.today().strftime("%Y-%m")

notes = {}  # rel_path -> {title, tags, created, updated, dir1, base, body}
name_index = defaultdict(list)  # basename(no ext) -> [rel_path]

fm_re = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
link_re = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]*)?(?:\|[^\]]*)?\]\]")

def parse_fm(text):
    m = fm_re.match(text)
    meta = {"title": None, "tags": [], "created": None, "updated": None}
    if not m:
        return meta, text
    body = text[m.end():]
    fm = m.group(1)
    tm = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", fm, re.M)
    if tm: meta["title"] = tm.group(1).strip().strip('*').strip()
    cm = re.search(r"^created:\s*[\"']?([0-9\-T: ]+)", fm, re.M)
    if cm: meta["created"] = cm.group(1).strip()[:10]
    um = re.search(r"^updated:\s*[\"']?([0-9\-T: ]+)", fm, re.M)
    if um: meta["updated"] = um.group(1).strip()[:10]
    tinline = re.search(r"^tags:\s*\[(.*?)\]\s*$", fm, re.M)
    if tinline:
        meta["tags"] = [t.strip().strip("'\"# ") for t in tinline.group(1).split(",") if t.strip()]
    else:
        tblock = re.search(r"^tags:\s*\n((?:\s+-\s+.*\n?)+)", fm, re.M)
        if tblock:
            meta["tags"] = [re.sub(r"^\s+-\s+", "", l).strip().strip("'\"# ") for l in tblock.group(1).strip().splitlines()]
    meta["tags"] = [t for t in meta["tags"] if t and t != "-" and not t.endswith(".md")]
    return meta, body

for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
    for fn in filenames:
        if not fn.endswith(".md"): continue
        full = os.path.join(dirpath, fn)
        rel = os.path.relpath(full, ROOT)
        try:
            with open(full, encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception:
            continue
        meta, body = parse_fm(text)
        base = fn[:-3]
        parts = rel.split(os.sep)
        dir1 = parts[0] if len(parts) > 1 else "(根目录)"
        notes[rel] = {"title": meta["title"] or base, "tags": meta["tags"],
                      "created": meta["created"], "updated": meta["updated"],
                      "dir1": dir1, "base": base, "body": body}
        name_index[base].append(rel)

edges = set()
unresolved = 0
for rel, n in notes.items():
    if any(meta in rel for meta in META_SKIP):
        continue  # meta 报告目录内部示例链接不计入边/断链
    for m in link_re.finditer(n["body"]):
        target = m.group(1).strip()
        tbase = os.path.basename(target)
        if tbase.endswith(".md"): tbase = tbase[:-3]
        # 文件链接（含扩展名）不是笔记链接，跳过（不计入断链）
        if any(tbase.endswith(ext) for ext in (".html",".pdf",".docx",".png",".jpg",".jpeg",".gif",".csv",".xlsx")):
            continue
        cands = name_index.get(tbase)
        if not cands:
            unresolved += 1
            continue
        trel = cands[0]
        if trel != rel:
            edges.add((rel, trel))

in_deg = defaultdict(int); deg = defaultdict(int)
for s, t in edges:
    in_deg[t] += 1; deg[s] += 1; deg[t] += 1
N = len(notes); E = len(edges)
orphans = [r for r in notes if deg[r] == 0]
density = (2*E)/(N*(N-1)) if N > 1 else 0
top10 = sorted(in_deg.items(), key=lambda x: -x[1])[:10]

tag_freq = defaultdict(int)
for n in notes.values():
    for t in n["tags"]: tag_freq[t] += 1
top_tags = sorted(tag_freq.items(), key=lambda x: -x[1])[:60]

dir_count = defaultdict(int)
dir2_count = defaultdict(lambda: defaultdict(int))
for rel, n in notes.items():
    dir_count[n["dir1"]] += 1
    parts = rel.split(os.sep)
    d2 = parts[1] if len(parts) > 2 else "(直属)"
    dir2_count[n["dir1"]][d2] += 1

linked = {r for r in notes if deg[r] > 0}
graph_nodes = []
idmap = {}
for i, r in enumerate(sorted(linked)):
    idmap[r] = i
    graph_nodes.append({"id": i, "label": notes[r]["title"][:30], "dir": notes[r]["dir1"],
                        "ref": in_deg[r], "deg": deg[r]})
graph_edges = [{"source": idmap[s], "target": idmap[t]} for s, t in edges if s in idmap and t in idmap]

out = {
  "month": MONTH, "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
  "total_notes": N, "total_links": E, "orphan_count": len(orphans),
  "density": round(density, 5), "unresolved_links": unresolved,
  "linked_nodes": len(linked),
  "top10": [{"title": notes[r]["title"], "path": r, "refs": c} for r, c in top10],
  "top_tags": [{"tag": t, "n": c} for t, c in top_tags],
  "dir_count": dict(sorted(dir_count.items(), key=lambda x: -x[1])),
  "dir2": {k: dict(sorted(v.items(), key=lambda x: -x[1])) for k, v in dir2_count.items()},
  "nodes": graph_nodes, "edges": graph_edges,
}
with open(os.path.join(SCRIPTS, "kg_data.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
print(json.dumps({k: out[k] for k in ["total_notes","total_links","orphan_count","density","linked_nodes","unresolved_links"]}, ensure_ascii=False))
print("dirs:", json.dumps(out["dir_count"], ensure_ascii=False))
print("top10:", json.dumps(out["top10"], ensure_ascii=False, indent=0)[:800])
