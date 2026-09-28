#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_flywheel_daily.py —— 重算 C3 知识飞轮舱「近 7 日真实新增曲线」数据源。

真源：LawKB/知识飞轮系统 git diff-filter=A（按 .md 文件首次入库日统计每日新增，
      含卡片与文档；已剔除 mtime 假象）。
只更新 flywheel-data.js 里 `dailyGrowth: [...]` 这一段，原子写，不动其它字段。
可单独运行，也可接入现有飞轮刷新自动化。

2026-09-27 修订 —— 剔除「跟踪起点假象」：
  --diff-filter=A 统计的是"文件首次纳入 git 跟踪"，而 09-26 00:23~00:24 有一批
  「自动备份：…批量更新（未跟踪·第 N/4 批）」提交，把此前未跟踪的约 2741 个文件
  一次性首次纳管，全被判成"当日新增"（+2741，真实单日最多 211，差一个数量级）。
  现按提交主题前缀「自动备份：」过滤掉这类提交及其文件行。
  ⚠️ 注意：这只是"统计口径"过滤，文件确实在那一刻被纳管了；
     若日后需要按真实纳管日回溯，需另立口径，不要指望本过滤。

用法：
  python3 gen_flywheel_daily.py            # 计算并就地更新 flywheel-data.js
  python3 gen_flywheel_daily.py --print    # 仅打印 dailyGrowth JSON，不改文件
"""
import subprocess, collections, json, datetime, os, re, sys, tempfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
KB = os.path.expanduser("~/Documents/LawKB/知识飞轮系统")
DST = os.path.join(HERE, "flywheel-data.js")


# 「自动备份：」提交把未跟踪文件一次性首次纳管，--diff-filter=A 会把它们全算成当日新增
# （2026-09-26 那批约 2741 个，真实单日最多 211）。这类提交不是真实内容产出，排除。
AUTOBACKUP_PREFIX = "自动备份："
HEAD_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\|([0-9a-f]{40})\|(.*)$")


def compute_daily_growth(end=None, days=7):
    end = end or datetime.date.today()
    since = (end - datetime.timedelta(days=days - 1)).isoformat()
    until = (end + datetime.timedelta(days=1)).isoformat()
    out = subprocess.run(
        ["git", "-C", KB, "log", "--diff-filter=A",
         "--since", since, "--until", until,
         "--date-order", "--date=short",
         "--pretty=format:%ad|%H|%s", "--name-only"],
        capture_output=True, text=True, check=True)
    daily = collections.Counter()
    cur = None
    skipped_commits = set()
    for ln in out.stdout.splitlines():
        s = ln.strip()
        if s == "":
            cur = None
            continue
        m = HEAD_RE.match(s)     # 提交头行：日期|提交号|主题
        if m:
            cur, _, subject = m.group(1), m.group(2), m.group(3)
            cur = None if subject.startswith(AUTOBACKUP_PREFIX) else cur
            if subject.startswith(AUTOBACKUP_PREFIX):
                skipped_commits.add(s[:47])
                continue
            continue
        if cur and s.endswith(".md"):
            daily[cur] += 1
    if skipped_commits:
        print("  ⛔ 已排除「自动备份」首次纳管提交 {0} 个：".format(len(skipped_commits)))
        for c in sorted(skipped_commits):
            print("     " + c)
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
