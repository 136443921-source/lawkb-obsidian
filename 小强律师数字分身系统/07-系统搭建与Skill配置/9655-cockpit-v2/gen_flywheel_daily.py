#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_flywheel_daily.py —— 重算 C3 知识飞轮舱「近 7 日真实新增曲线」数据源。

真源：LawKB/知识飞轮系统 git diff-filter=A（按 .md 文件首次入库日统计每日新增，
      含卡片与文档；已剔除 mtime 假象）。
只更新 flywheel-data.js 里 `dailyGrowth: [...]` 这一段，原子写，不动其它字段。
可单独运行，也可接入现有飞轮刷新自动化。

用法：
  python3 gen_flywheel_daily.py            # 计算并就地更新 flywheel-data.js
  python3 gen_flywheel_daily.py --print    # 仅打印 dailyGrowth JSON，不改文件
"""
import subprocess, collections, json, datetime, os, re, sys, tempfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
KB = os.path.expanduser("~/Documents/LawKB/知识飞轮系统")
DST = os.path.join(HERE, "flywheel-data.js")


def compute_daily_growth(end=None, days=7):
    end = end or datetime.date.today()
    since = (end - datetime.timedelta(days=days - 1)).isoformat()
    until = (end + datetime.timedelta(days=1)).isoformat()
    out = subprocess.run(
        ["git", "-C", KB, "log", "--diff-filter=A",
         "--since", since, "--until", until,
         "--pretty=format:%ad", "--date=short", "--name-only"],
        capture_output=True, text=True, check=True)
    daily = collections.Counter()
    cur = None
    for ln in out.stdout.splitlines():
        s = ln.strip()
        if s == "":
            cur = None
            continue
        if s[:4].isdigit():      # 提交日期行 YYYY-MM-DD
            cur = s
            continue
        if cur and s.endswith(".md"):
            daily[cur] += 1
    arr = []
    for i in range(days - 1, -1, -1):
        d = (end - datetime.timedelta(days=i)).isoformat()
        arr.append({"date": d, "add": daily.get(d, 0)})
    return arr


def inject_daily_growth(js_text, arr):
    block = "  dailyGrowth: [\n" + ",\n".join(
        '    {{"date": "{d}", "add": {a}}}'.format(d=x["date"], a=x["add"]) for x in arr
    ) + "\n  ]"
    # 若已有 dailyGrowth 段 → 替换为新值；否则插入到 `  metrics: [` 之前
    pat = re.compile(r"  dailyGrowth:\s*\[[\s\S]*?\],\s*\n\s*metrics:", re.M)
    if pat.search(js_text):
        return pat.sub(block + ",\n  metrics:", js_text)
    return js_text.replace("  metrics: [", block + ",\n  metrics: [", 1)


def main():
    arr = compute_daily_growth()
    js_text = open(DST, encoding="utf-8").read()
    new_text = inject_daily_growth(js_text, arr)
    if "--print" in sys.argv:
        print(json.dumps(arr, ensure_ascii=False, indent=2))
        print("合计新增 .md =", sum(x["add"] for x in arr))
        return
    # 原子写：先写临时文件再 rename，避免覆盖过程中断致文件损坏
    fd, tmp = tempfile.mkstemp(suffix=".js", dir=HERE)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(new_text)
    shutil.move(tmp, DST)
    print("✅ dailyGrowth 已更新 -> {0}（近 7 日合计 {1} 个 .md 新增）".format(
        DST, sum(x["add"] for x in arr)))


if __name__ == "__main__":
    main()
