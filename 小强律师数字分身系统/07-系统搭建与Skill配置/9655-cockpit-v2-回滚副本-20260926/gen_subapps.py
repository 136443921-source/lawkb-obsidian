#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
9655 单机驾驶舱 · 非律所 9 屏 9360 风格薄壳生成器
----------------------------------------------------
把 9 个非律所子屏（C1/C2/C3/C8 + D1/D2/D4/D5/D6）替换为
统一引用 subapp_shell.css / subapp_shell.js 的 9360 风格薄壳：
  <body data-cno="...">  ← subapp_shell.js 据此取 scorecard_data.json 切片
  <div id="app"></div>   ← 渲染器落点
  <a href="/index.html"> ← 返回作战地图（C0 门户）

律所 4 屏（C4/C5/C6/C7）保留 9360 原文件，不在此处理。
运行：python3 gen_subapps.py
"""
import os

V2 = os.path.dirname(os.path.abspath(__file__))
REV = "20260918d"

# (目录, cno, 标题)
SCREENS = [
    ("ev",                  "C1", "车机驾驶舱"),
    ("decision",            "C2", "决策思维舱"),
    ("flywheel",            "C3", "知识飞轮舱"),
    ("lti",                 "C8", "AI 幻觉监控舱"),
    ("credits",             "D1", "积分监测中台"),
    ("conflict-arbitration","D2", "知识冲突中台"),
    ("mind-models",         "D4", "心智模型中台"),
    ("permcenter",          "D5", "权限管理中心"),
    ("d6permcenter",        "D6", "权限调用中台"),
    ("agenthub",            "D7", "智能体中台"),
    ("workflowhub",         "D8", "工作流中台"),
]

TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>9655 · {name}</title>
<link rel="stylesheet" href="/subapp_shell.css?v={rev}">
</head>
<body data-cno="{cno}">
  <div class="wrap">
    <div class="topbar"><a class="back" href="/index.html">&larr; 返回作战地图</a></div>
    <div id="app"></div>
  </div>
  <script src="/subapp_shell.js?v={rev}"></script>
</body>
</html>
"""


def main():
    for d, cno, name in SCREENS:
        out = os.path.join(V2, "subapps", d, "index.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        html = TPL.format(name=name, cno=cno, rev=REV)
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print("✅ {0:<22} {1} {2:<16} → {3}".format(d, cno, name, out))


if __name__ == "__main__":
    main()
