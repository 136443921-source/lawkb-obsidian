#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成知识图谱HTML（D3.js力导向图 + 标签云 + 统计面板 + 分类树）
- 输入：本脚本同目录 kg_data.json（由 kg_scan.py 生成，含当前月统计与图数据）
- 环比基线：读取上一月 知识图谱-数据-{prev_month}.json（不存在则无基线）
- 输出：03-连接/知识图谱-{month}.html（交互图） + 知识图谱-数据-{month}.json（当月快照，供下月对比）
"""
import os, json, datetime
from collections import defaultdict

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT_DIR = os.path.join(ROOT, "03-连接")

with open(os.path.join(SCRIPTS, "kg_data.json"), encoding="utf-8") as f:
    D = json.load(f)

MONTH = D["month"]
y, m = map(int, MONTH.split("-"))
prev_m = m - 1 or 12
prev_y = y - 1 if m == 1 else y
PREV_MONTH = f"{prev_y:04d}-{prev_m:02d}"

# 环比基线：上一月数据
prev_path = os.path.join(OUT_DIR, f"知识图谱-数据-{PREV_MONTH}.json")
prev = None
if os.path.exists(prev_path):
    try:
        with open(prev_path, encoding="utf-8") as f:
            prev = json.load(f)
    except Exception:
        prev = None

prev_exist = prev is not None
delta_notes = (D["total_notes"] - prev["total_notes"]) if prev_exist else 0
delta_links = (D["total_links"] - prev["total_links"]) if prev_exist else 0
delta_orphans = (D["orphan_count"] - prev["orphan_count"]) if prev_exist else 0
delta_density = (round(D["density"] - prev["density"], 5)) if prev_exist else 0

graph_json = json.dumps({"nodes": D["nodes"], "links": D["edges"]}, ensure_ascii=False)
top_tags = D["top_tags"][:50]
max_tag = top_tags[0]["n"] if top_tags else 1

DIR_COLORS = {"01-采集":"#5b8cff","02-提炼":"#9b6bff","03-连接":"#2dd4bf","04-巩固":"#f59e0b",
              "05-调用":"#ef6a9e","06-沉淀":"#22c55e","IMA-Inbox":"#94a3b8","系统迭代说明":"#64748b",
              "案件库":"#e879f9","04-LOG":"#475569"}
def color_of(d): return DIR_COLORS.get(d, "#7c8db5")

tag_html = "".join(
    f"<span class='tag' style='font-size:{11 + round(11*t['n']/max_tag)}px;opacity:{0.55+0.45*t['n']/max_tag:.2f}'>#{t['tag']} <em>{t['n']}</em></span>"
    for t in top_tags)

top10_html = "".join(
    f"<tr><td>{i+1}</td><td title='{t['path']}'>{t['title']}</td><td class='num'>{t['refs']}</td></tr>"
    for i, t in enumerate(D["top10"]))

tree_html = ""
for d1, cnt in D["dir_count"].items():
    subs = D["dir2"].get(d1, {})
    sub_html = "".join(f"<li><span>{k}</span><b>{v}</b></li>" for k, v in list(subs.items())[:12])
    more = len(subs) - 12
    if more > 0: sub_html += f"<li class='more'>… 另 {more} 个子目录</li>"
    tree_html += (f"<details {'open' if cnt>=50 else ''}><summary><i style='background:{color_of(d1)}'></i>"
                  f"{d1}<b>{cnt}</b></summary><ul>{sub_html}</ul></details>")

legend_html = "".join(f"<span class='lg'><i style='background:{color_of(d)}'></i>{d}</span>"
                      for d in list(D["dir_count"].keys())[:8])

if prev_exist:
    cmp_rows = (
        f"<tr><td>笔记总数</td><td class='num'>{prev['total_notes']} → {D['total_notes']}（{delta_notes:+d}）</td></tr>"
        f"<tr><td>链接总数</td><td class='num'>{prev['total_links']} → {D['total_links']}（{delta_links:+d}）</td></tr>"
        f"<tr><td>孤儿笔记</td><td class='num'>{prev['orphan_count']} → {D['orphan_count']}（{delta_orphans:+d}）</td></tr>"
        f"<tr><td>网络密度</td><td class='num'>{prev['density']:.4f} → {D['density']:.4f}（{delta_density:+.4f}）</td></tr>"
    )
    cmp_note = f"对比基线：{PREV_MONTH} 知识图谱数据快照（知识图谱-数据-{PREV_MONTH}.json）。"
else:
    cmp_rows = (
        f"<tr><td>笔记总数</td><td class='num'>— → {D['total_notes']}</td></tr>"
        f"<tr><td>链接总数</td><td class='num'>— → {D['total_links']}</td></tr>"
        f"<tr><td>孤儿笔记</td><td class='num'>— → {D['orphan_count']}</td></tr>"
        f"<tr><td>网络密度</td><td class='num'>— → {D['density']:.4f}</td></tr>"
    )
    cmp_note = f"无上一月基线（{PREV_MONTH} 快照缺失），本期起建立机器可读基线。"

html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LawKB 知识图谱 — {D['month']}</title>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<style>
:root{{--bg:#0f1424;--card:#1a2036;--line:#26304f;--txt:#e6e9f0;--sub:#8a93ad;--acc:#5b8cff;}}
*{{box-sizing:border-box}}
body{{font-family:-apple-system,'PingFang SC',sans-serif;background:var(--bg);color:var(--txt);margin:0;padding:22px;}}
h1{{font-size:22px;margin:0 0 4px}} .sub{{color:var(--sub);font-size:13px;margin-bottom:18px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:18px}}
.stat{{background:var(--card);border-radius:12px;padding:14px 16px;box-shadow:0 4px 14px rgba(0,0,0,.25)}}
.stat .v{{font-size:26px;font-weight:700}} .stat .k{{color:var(--sub);font-size:12px;margin-top:2px}}
.stat .d{{font-size:12px;margin-top:4px}} .up{{color:#22c55e}} .flat{{color:var(--sub)}}
.grid{{display:grid;grid-template-columns:2fr 1fr;gap:16px}}
@media(max-width:960px){{.grid{{grid-template-columns:1fr}}}}
.card{{background:var(--card);border-radius:14px;padding:16px 18px;margin-bottom:16px;box-shadow:0 4px 14px rgba(0,0,0,.25)}}
h2{{font-size:16px;border-left:4px solid var(--acc);padding-left:10px;margin:0 0 12px}}
#graph{{width:100%;height:640px;border-radius:10px;background:#12182b;cursor:grab}}
.lg{{display:inline-flex;align-items:center;gap:5px;margin-right:12px;font-size:12px;color:var(--sub)}}
.lg i,summary i{{display:inline-block;width:10px;height:10px;border-radius:3px}}
.tag{{display:inline-block;background:#222b48;color:#9fb4ff;border-radius:8px;padding:2px 9px;margin:3px;line-height:1.7}}
.tag em{{font-style:normal;color:var(--sub);font-size:.8em}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
td{{padding:6px 8px;border-bottom:1px solid var(--line)}} td.num{{text-align:right;color:var(--acc);font-weight:700}}
details{{margin:6px 0;border:1px solid var(--line);border-radius:10px;padding:8px 12px}}
summary{{cursor:pointer;display:flex;align-items:center;gap:8px;font-size:14px}}
summary b,li b{{margin-left:auto;color:var(--acc)}}
details ul{{list-style:none;margin:8px 0 2px;padding-left:18px}}
details li{{display:flex;font-size:12.5px;color:#b9c2d8;padding:2px 0;border-bottom:1px dashed #202945}}
details li.more{{color:var(--sub)}}
#tip{{position:fixed;pointer-events:none;background:#0b1020ee;border:1px solid var(--line);border-radius:8px;
padding:8px 10px;font-size:12px;display:none;max-width:280px;z-index:9}}
.note{{font-size:12px;color:var(--sub);margin-top:8px;line-height:1.6}}
</style></head><body>
<h1>🕸️ LawKB 知识飞轮 · 知识图谱 — {D['month']}</h1>
<div class="sub">生成于 {D['generated']}（周日维护批处理 · 连接层自动刷新）｜ 范围：知识飞轮系统/ 全部 Markdown 笔记</div>

<div class="stats">
<div class="stat"><div class="v">{D['total_notes']}</div><div class="k">笔记总数</div><div class="d up">{'▲ '+format(delta_notes,'+d')+'（对比 '+PREV_MONTH+'）' if prev_exist else '本期起建立基线'}</div></div>
<div class="stat"><div class="v">{D['total_links']}</div><div class="k">双向链接总数</div><div class="d flat">{'▲ '+format(delta_links,'+d') if prev_exist else '本期起建立基线'}</div></div>
<div class="stat"><div class="v">{D['orphan_count']}</div><div class="k">孤儿笔记（无链接）</div><div class="d flat">占比 {D['orphan_count']*100//D['total_notes']}%</div></div>
<div class="stat"><div class="v">{D['density']:.4f}</div><div class="k">网络密度</div><div class="d flat">{'▲ '+format(delta_density,'+.4f') if prev_exist else '本期起建立基线'}</div></div>
<div class="stat"><div class="v">{D['linked_nodes']}</div><div class="k">联通节点数</div><div class="d flat">占比 {D['linked_nodes']*100//D['total_notes']}%</div></div>
</div>

<div class="grid">
<div>
  <div class="card"><h2>力导向图（节点=笔记 · 边=双向链接 · 节点大小=被引用次数）</h2>
    <div style="margin-bottom:8px">{legend_html}</div>
    <svg id="graph"></svg>
    <div class="note">滚轮缩放 · 拖拽平移/移动节点 · 悬停查看标题与引用数。仅渲染有链接的 {D['linked_nodes']} 个节点。</div>
  </div>
  <div class="card"><h2>标签云（Top 50）</h2>{tag_html}</div>
</div>
<div>
  <div class="card"><h2>Top 10 高引用笔记</h2><table>{top10_html}</table></div>
  <div class="card"><h2>分类树（按目录）</h2>{tree_html}</div>
  <div class="card"><h2>环比对比（vs {PREV_MONTH}）</h2>
    <table>{cmp_rows}</table>
    <div class="note">{cmp_note}</div>
  </div>
</div>
</div>
<div id="tip"></div>

<script>
const DATA = {graph_json};
const COLORS = {json.dumps(DIR_COLORS, ensure_ascii=False)};
const svg = d3.select("#graph");
const W = document.getElementById("graph").clientWidth, H = 640;
svg.attr("viewBox", [0,0,W,H]);
const g = svg.append("g");
svg.call(d3.zoom().scaleExtent([0.15,6]).on("zoom", e => g.attr("transform", e.transform)));
const sim = d3.forceSimulation(DATA.nodes)
  .force("link", d3.forceLink(DATA.links).id(d=>d.id).distance(46).strength(0.5))
  .force("charge", d3.forceManyBody().strength(-60))
  .force("center", d3.forceCenter(W/2, H/2))
  .force("collide", d3.forceCollide(d => 4 + Math.sqrt(d.ref)*3));
const link = g.append("g").attr("stroke","#33406b").attr("stroke-opacity",0.55)
  .selectAll("line").data(DATA.links).join("line").attr("stroke-width",0.8);
const node = g.append("g").selectAll("circle").data(DATA.nodes).join("circle")
  .attr("r", d => 3.2 + Math.sqrt(d.ref)*2.6)
  .attr("fill", d => COLORS[d.dir] || "#7c8db5")
  .attr("stroke","#0f1424").attr("stroke-width",1)
  .call(d3.drag()
    .on("start",(e,d)=>{{if(!e.active)sim.alphaTarget(0.25).restart();d.fx=d.x;d.fy=d.y;}})
    .on("drag",(e,d)=>{{d.fx=e.x;d.fy=e.y;}})
    .on("end",(e,d)=>{{if(!e.active)sim.alphaTarget(0);d.fx=null;d.fy=null;}}));
const tip = document.getElementById("tip");
node.on("mousemove",(e,d)=>{{tip.style.display="block";tip.style.left=(e.clientX+14)+"px";
  tip.style.top=(e.clientY+10)+"px";
  tip.innerHTML="<b>"+d.label+"</b><br>目录: "+d.dir+"<br>被引用: "+d.ref+" · 总链接: "+d.deg;}})
  .on("mouseout",()=>tip.style.display="none");
const label = g.append("g").selectAll("text").data(DATA.nodes.filter(d=>d.ref>=8)).join("text")
  .text(d=>d.label).attr("font-size",10).attr("fill","#c6d0e8").attr("dx",8).attr("dy",3);
sim.on("tick",()=>{{
  link.attr("x1",d=>d.source.x).attr("y1",d=>d.source.y).attr("x2",d=>d.target.x).attr("y2",d=>d.target.y);
  node.attr("cx",d=>d.x).attr("cy",d=>d.y);
  label.attr("x",d=>d.x).attr("y",d=>d.y);
}});
</script>
</body></html>"""

out_html = os.path.join(OUT_DIR, f"知识图谱-{MONTH}.html")
with open(out_html, "w", encoding="utf-8") as f:
    f.write(html)

# 当月快照（供下月对比）
baseline = {k: D[k] for k in ["month","generated","total_notes","total_links","orphan_count","density","linked_nodes","dir_count"]}
baseline["top10"] = D["top10"]
with open(os.path.join(OUT_DIR, f"知识图谱-数据-{MONTH}.json"), "w", encoding="utf-8") as f:
    json.dump(baseline, f, ensure_ascii=False, indent=1)
print("OK", out_html, len(html), "| prev:", PREV_MONTH, "exist" if prev_exist else "missing")
