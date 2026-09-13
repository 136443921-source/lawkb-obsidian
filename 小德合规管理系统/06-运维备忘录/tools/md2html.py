#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
md → 自包含 HTML 阅读版（离线可打开，内联 CSS，无外部依赖）
用于 LawKB 运维手册类长文档的可视化交付。
用法: python md2html.py <input.md> <output.html>
"""
import sys
import re
import html
import markdown

CSS = """
:root{
  --bg:#f7f8fa; --panel:#ffffff; --ink:#1f2328; --ink2:#4a5260;
  --line:#e3e6ea; --accent:#1f6feb; --accent2:#0d419d;
  --red:#c0392b; --amber:#b7791f; --green:#1e7e34; --code:#f2f4f7;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font:16px/1.75 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
}
.wrap{display:flex; max-width:1500px; margin:0 auto; align-items:flex-start}
/* 侧栏目录 */
nav{
  position:sticky; top:0; width:290px; flex:0 0 290px; height:100vh; overflow-y:auto;
  background:var(--panel); border-right:1px solid var(--line); padding:20px 14px 60px;
}
nav h3{font-size:13px; color:var(--ink2); letter-spacing:1px; margin:0 0 12px 6px; text-transform:uppercase}
nav a{
  display:block; color:var(--ink2); text-decoration:none; font-size:13px; line-height:1.5;
  padding:5px 8px; border-radius:6px; margin-bottom:2px;
}
nav a:hover{background:#eef2f7; color:var(--accent2)}
nav a.lv1{font-weight:600; color:var(--ink); margin-top:8px}
nav a.lv2{padding-left:20px; font-size:12.5px}
main{flex:1; min-width:0; padding:36px 48px 100px; background:var(--bg)}
.card{background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:28px 34px; box-shadow:0 1px 3px rgba(0,0,0,.04)}
h1{font-size:27px; margin:0 0 6px; line-height:1.35; letter-spacing:-.2px}
h2{font-size:21px; margin:34px 0 12px; padding-bottom:8px; border-bottom:2px solid var(--accent); color:var(--accent2)}
h3{font-size:17.5px; margin:24px 0 10px; color:var(--ink)}
h4{font-size:15.5px; margin:18px 0 8px; color:var(--ink2)}
p{margin:9px 0}
ul,ol{padding-left:24px; margin:9px 0}
li{margin:4px 0}
strong{color:#0b1320}
code{
  background:var(--code); padding:2px 6px; border-radius:4px; font-size:13.5px;
  font-family:"SF Mono",Menlo,Consolas,monospace; color:#b3275a;
}
pre{background:#1f2430; color:#e6e9ef; padding:16px 18px; border-radius:9px; overflow-x:auto; line-height:1.6}
pre code{background:none; color:inherit; padding:0; font-size:13px}
blockquote{
  margin:14px 0; padding:12px 18px; background:#f0f4fa; border-left:4px solid var(--accent);
  border-radius:0 8px 8px 0; color:var(--ink2);
}
blockquote p{margin:5px 0}
table{border-collapse:collapse; width:100%; margin:14px 0; font-size:14px; display:block; overflow-x:auto}
th,td{border:1px solid var(--line); padding:8px 11px; text-align:left; vertical-align:top}
th{background:#eef2f7; font-weight:600; color:var(--ink); white-space:nowrap}
tr:nth-child(even) td{background:#fafbfc}
hr{border:0; border-top:1px solid var(--line); margin:26px 0}
a{color:var(--accent)}
.meta{display:flex; flex-wrap:wrap; gap:8px; margin:14px 0 22px}
.badge{
  background:#eef2f7; color:var(--ink2); border-radius:20px; padding:3px 12px;
  font-size:12.5px; border:1px solid var(--line);
}
.badge.ver{background:#e8f0fe; color:var(--accent2); font-weight:600}
.topbar{
  position:sticky; top:0; z-index:9; background:rgba(255,255,255,.94); backdrop-filter:blur(8px);
  border:1px solid var(--line); border-radius:10px; padding:10px 16px; margin-bottom:18px;
  display:flex; justify-content:space-between; align-items:center; font-size:13px; color:var(--ink2);
}
@media (max-width:960px){
  nav{display:none} main{padding:20px}
}
@media print{
  nav,.topbar{display:none} main{padding:0} .card{border:0; box-shadow:none}
}
"""


def build(md_path, out_path):
    with open(md_path, encoding="utf-8") as f:
        raw = f.read()

    # 拆分 frontmatter
    fm = {}
    body = raw
    if raw.startswith("---"):
        m = re.match(r"^---\n(.*?)\n---\n", raw, re.S)
        if m:
            for line in m.group(1).split("\n"):
                mm = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
                if mm:
                    fm[mm.group(1)] = mm.group(2).strip()
            body = raw[m.end():]

    # 去掉代码块内的 # 干扰后再抽标题
    heads = []
    for m in re.finditer(r"^(#{1,3})\s+(.+)$", body, re.M):
        level = len(m.group(1))
        title = m.group(2).strip()
        heads.append((level, title))

    # 目录
    toc = ['<h3>目录</h3>']
    for level, title in heads:
        if level > 2:
            continue
        anchor = "h-" + re.sub(r"[^\w\u4e00-\u9fff]+", "-", title).strip("-")
        cls = "lv1" if level == 1 else "lv2"
        toc.append(f'<a class="{cls}" href="#{anchor}">{html.escape(title)}</a>')

    def slug(title):
        return "h-" + re.sub(r"[^\w\u4e00-\u9fff]+", "-", title).strip("-")

    # 给标题加锚点
    def add_anchor(m):
        level = len(m.group(1))
        title = m.group(2).strip()
        return f'<h{level} id="{slug(title)}">{title}</h{level}>'

    body = re.sub(r"^(#{1,3})\s+(.+)$", add_anchor, body, flags=re.M)

    html_body = markdown.markdown(
        body,
        extensions=["tables", "fenced_code", "toc", "attr_list", "sane_lists"],
    )

    title = fm.get("title") or (heads[0][1] if heads else "文档")
    badges = []
    for k, label in [("version", "版本"), ("status", "状态"), ("maturity", "成熟度"),
                     ("owner", "负责人"), ("updated", "更新")]:
        if k in fm:
            cls = "badge ver" if k == "version" else "badge"
            badges.append(f'<span class="{cls}">{label}：{html.escape(fm[k])}</span>')
    if "parent" in fm:
        badges.append(f'<span class="badge">母本：{html.escape(fm["parent"][:60])}</span>')

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style></head>
<body>
<div class="wrap">
<nav>{''.join(toc)}</nav>
<main><div class="card">
<div class="topbar"><span>📘 LawKB · 小德合规管理系统</span><span>离线阅读版 · 自包含</span></div>
<h1>{html.escape(title)}</h1>
<div class="meta">{''.join(badges)}</div>
{html_body}
</div></main>
</div></body></html>"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"✅ 生成 → {out_path}  ({len(doc)} chars, {len(heads)} 标题)")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
