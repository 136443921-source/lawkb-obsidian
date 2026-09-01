#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知识飞轮系统 知识图谱扫描器 v1.4（自动化版，动态当前月；断链判定含工作区全量索引+日期/数字/URL护栏）
- 遍历 ROOT 下所有 .md，解析 frontmatter、双向链接 `[[文件名]]`、标签。
- 输出机器可读 JSON 到本脚本同目录 kg_data.json，并打印关键统计（首行 JSON 供捕获）。
- 供 kg_html.py 与「周日知识维护批处理」调用。
"""
import os, re, json, datetime
from collections import defaultdict

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
WORKSPACE = "/Users/chenyouqiang/Documents/LawKB"
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {".obsidian", ".trash", "node_modules", "logs"}
# meta 报告目录：其正文中的 `[[...]]` 多为「断链示例」文档说明，非真实链接，不计入断链
META_SKIP = {"孤立笔记检测报告", "知识库压缩去重报告"}
MONTH = datetime.date.today().strftime("%Y-%m")

# 护栏（v1.4 收紧，与 resolve_broken_links.py 保持一致）：
# 日期型（2026-07-07 / 2026年7月7日）、纯数字、URL —— 非笔记概念，不计断链、不建概念页
DATE_ONLY_RE = re.compile(r"^(19|20)\d{2}[-/.年]\d{1,2}([-/.月]\d{1,2})?日?$")
NUM_ONLY_RE = re.compile(r"^\d+$")
URL_RE = re.compile(r"^(https?://|www\.|file://)")
# 系统/自动化内部引用（工作记忆 memory、自动化队列文件 待推送_*）：非笔记概念，跳过
SYSTEM_REF_RE = re.compile(r"^(?:memory|待推送_[0-9\-]+)$", re.IGNORECASE)

notes = {}  # rel_path -> {title, tags, created, updated, dir1, base, body}
name_index = defaultdict(list)  # basename(no ext) -> [rel_path]（ROOT 内，用于建边/图谱）
ws_index = defaultdict(list)    # basename(no ext) -> [abs_path]（工作区全量，用于断链判定；ROOT 外真实文件算已解析）

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

# 工作区全量索引（ROOT 外真实文件亦算已解析，避免误判断链、误建概念页）
for dirpath, dirnames, filenames in os.walk(WORKSPACE):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
    for fn in filenames:
        if not fn.endswith(".md"): continue
        full = os.path.join(dirpath, fn)
        ws_index[fn[:-3]].append(full)

edges = set()
unresolved = 0
for rel, n in notes.items():
    if any(meta in rel for meta in META_SKIP):
        continue  # meta 报告目录内部示例链接不计入边/断链
    for m in link_re.finditer(n["body"]):
        target = m.group(1).strip().rstrip("\\").strip()  # 去尾随反斜杠（模板footer误带，如 [[知识图谱-2026-07.html\]]）
        if not target:
            continue  # 空链接 [[ ]] 非真实目标
        tbase = os.path.basename(target)
        if tbase.endswith(".md"): tbase = tbase[:-3]
        # 文件链接（含扩展名）不是笔记链接，跳过（不计入断链）
        if any(tbase.endswith(ext) for ext in (".html",".pdf",".docx",".png",".jpg",".jpeg",".gif",".csv",".xlsx")):
            continue
        # 生成笔记自引用占位（如 [[self.md-20260805]]），非真实目标，跳过
        if tbase.startswith("self.md"):
            continue
        # 模板/规范文档中的示意链接占位符（如 [[x]] [[经验卡片-XXX]] [[规则名]] [[链接]]），非真实目标，跳过
        if re.search(r"^(?:x|wikilink|案件笔记名|规则名|链接|\.\.\.)$|XXX|Rxxx", tbase):
            continue
        # 护栏 v1.4：日期/纯数字/URL 非笔记概念，跳过（不计断链、不建概念页）
        if DATE_ONLY_RE.match(tbase) or NUM_ONLY_RE.match(tbase) or URL_RE.match(tbase):
            continue
        # 系统/自动化内部引用（memory / 待推送_*）：跳过
        if SYSTEM_REF_RE.match(tbase):
            continue
        # 断链判定用工作区全量索引：ROOT 外真实文件（Obsidian配置指南.md 等在 LawKB 根/其他目录）算已解析
        if not ws_index.get(tbase):
            unresolved += 1
            continue
        cands = name_index.get(tbase)  # ROOT 内同名：建边/图谱
        if not cands:
            continue  # 仅存在于 ROOT 外：已解析但不入图谱（避免图节点引用 ROOT 外文件）
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
