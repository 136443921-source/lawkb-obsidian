#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1:1 还原 小强总驾驶舱·内部操作版
源 = 公网 xiaoqiang-cockpit-hub (wbapp_8oxQaImtlGQF5gmODMx19W)
     localDir: /Users/chenyouqiang/WorkBuddy/2026-09-05-03-33-49/cockpit-portal/portal
做法：
  1. 门户 6 文件 1:1 复制（index/auth/rbac/scorecard_data/workbench/rescan）
  2. 7 个原生子屏复制进 subapps/（cheji/feilun/juesi/jifen/lti/mock-trial-center/案件生命周期大屏）
  3. rbac.js 中 7 个已下线的外部 sandbox 链接 → 改为本地 subapps 路径
     （cardfamily / cloud 仍指向在线外链，原样保留）
"""
import os, shutil, json, re, sys, datetime

SRC_PORTAL = "/Users/chenyouqiang/WorkBuddy/2026-09-05-03-33-49/cockpit-portal/portal"
SRC_SUB    = "/Users/chenyouqiang/WorkBuddy/2026-09-05-03-33-49/cockpit-portal"
CLM_FULL   = "/Users/chenyouqiang/WorkBuddy/Claw/case-lifecycle/dashboard/案件生命周期大屏.html"
OUT = "/Users/chenyouqiang/WorkBuddy/2026-09-12-01-29-05/outputs/cockpit-hub-ops"

# ============================================================
# 🔴 破坏性护栏（2026-09-14 加）：本脚本是从【旧源】1:1 覆盖式还原，
#    会冲掉 OUT 下已定制的 index.html / auth.js / rbac.js /
#    scorecard_data.json / workbench.html —— 包括：
#      · C0–C9 编号标注（rbac cno / scorecard cno / workbench cno）
#      · 按 C1→C9→C0 的排序（三处）
#      · C5 小德、C0 云监控两条新屏（含“不纳入评分”）
#      · index.html 的 ?v= 缓存击穿
#    ⚠ 另注：旧源 index.html 自带一个 script 标签错配 bug（缺 <script> 开标签，
#      致 1828 字符 JS 源码裸奔成页面可见文本）。本脚本第 5 步会自动修复该 bug。
#    默认拒绝执行，必须显式 `python3 build_restore.py --force`；
#    加 --force 时先自动备份到 /tmp 再覆盖。
# ============================================================
CUSTOMIZED = ["index.html", "auth.js", "rbac.js", "scorecard_data.json", "workbench.html"]
if "--force" not in sys.argv:
    print("⚠ 已拦截：build_restore.py 会用【旧源】覆盖以下已定制文件：")
    for f in CUSTOMIZED:
        print("    · " + f)
    print("  会丢失：C0–C9 编号、按编号排序、C5 小德 / C0 云监控新屏、缓存击穿参数。")
    print("  另：旧源 index.html 自带 script 标签错配 bug（JS 源码裸奔），本脚本第 5 步会自动修复。")
    print("  如确需 1:1 还原，请运行：python3 build_restore.py --force （会先自动备份到 /tmp）")
    sys.exit(2)

BK = "/tmp/cockpit_hub_ops_restore_backup_" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
os.makedirs(BK, exist_ok=True)
for f in CUSTOMIZED:
    p = os.path.join(OUT, f)
    if os.path.exists(p):
        shutil.copy2(p, os.path.join(BK, f))
print("✓ 覆盖前已备份现有文件 →", BK)

# 1) 门户文件 1:1
portal_files = ["index.html", "auth.js", "rbac.js", "scorecard_data.json",
                "workbench.html", "rescan_scorecard.py"]
os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(OUT, "subapps"), exist_ok=True)
for f in portal_files:
    s = os.path.join(SRC_PORTAL, f)
    if os.path.exists(s):
        shutil.copy2(s, os.path.join(OUT, f))
        print("✓ portal", f, os.path.getsize(s), "bytes")
    else:
        print("✗ MISSING portal", f)

# 2) 子屏 1:1 复制（原生单文件）
subs = {
    "ev":       (os.path.join(SRC_SUB, "cheji/index.html"),   "车机驾驶舱"),
    "flywheel": (os.path.join(SRC_SUB, "feilun/index.html"),  "知识飞轮中台"),
    "decision": (os.path.join(SRC_SUB, "juesi/index.html"),   "决策思维树"),
    "credits":  (os.path.join(SRC_SUB, "jifen/index.html"),   "积分监测看板"),
    "lti":      (os.path.join(SRC_SUB, "lti/index.html"),     "AI 幻觉监控看板"),
    "mock":     (os.path.join(SRC_SUB, "mock-trial-center/index.html"), "模拟法庭控制中台"),
    "clm":      (CLM_FULL, "案件生命周期大屏"),
}
for key, (src, label) in subs.items():
    dst = os.path.join(OUT, "subapps", key, "index.html")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"✓ subapps/{key}  ({label})  {os.path.getsize(src)} bytes")
    else:
        print(f"✗ MISSING subapps/{key}  <- {src}")

# 3) rbac.js：7 个下线外链 → 本地 subapps
rbac_path = os.path.join(OUT, "rbac.js")
txt = open(rbac_path, encoding="utf-8").read()
repl = [
    ('url: "https://93a0d6458e084c0eb62529531a22b48c.app.workbuddy.link"',
     'url: "./subapps/mock/index.html"'),
    ('url: "https://xq-cockpit-sub.app.workbuddy.host/cheji/index.html"',
     'url: "./subapps/ev/index.html"'),
    ('url: "https://xq-cockpit-sub.app.workbuddy.host/feilun/index.html"',
     'url: "./subapps/flywheel/index.html"'),
    ('url: "https://xq-cockpit-sub.app.workbuddy.host/juesi/index.html"',
     'url: "./subapps/decision/index.html"'),
    ('url: "https://xq-cockpit-sub.app.workbuddy.host/jifen/index.html"',
     'url: "./subapps/credits/index.html"'),
    ('url: "https://clm-internal.app.workbuddy.host"',
     'url: "./subapps/clm/index.html"'),
    ('url: "https://lti-hallucination-monitor.app.workbuddy.host/"',
     'url: "./subapps/lti/index.html"'),
]
n=0
for a,b in repl:
    if a in txt:
        txt = txt.replace(a,b); n+=1
    else:
        print("  ⚠ 未匹配（可能已改）:", a[:60])
open(rbac_path, "w", encoding="utf-8").write(txt)
print(f"\nrbac.js 已本地化 {n}/7 个下线外链（cardfamily / cloud 保留在线外链）")

# 4) 校验 scorecard 真实评分
sc = json.load(open(os.path.join(OUT,"scorecard_data.json"), encoding="utf-8"))
print(f"评分数据: total={sc.get('total')} grade={sc.get('grade')} generated={sc.get('generated_at')} screens={len(sc.get('screens',[]))}")

# 5) 裸奔 JS 体检 + 修复（旧源 index.html 缺 <script> 开标签，JS 源码会裸奔成页面文本）
idx_path = os.path.join(OUT, "index.html")
if os.path.exists(idx_path):
    s = open(idx_path, encoding="utf-8").read()
    opens  = len(re.findall(r'<script\b', s))
    closes = len(re.findall(r'</script\s*>', s))
    bare   = bool(re.search(r'</script>\s*\n\s*(?:\*|/\*|\(function|window\.__|var\s)', s))
    if bare or opens != closes:
        print(f"\n⚠ 检出 script 标签错配（<script> {opens} / </script> {closes}，裸奔JS={bare}）→ 自动补 <script> 开标签")
        s2, n = re.subn(r'(</script>\s*\n)(\s*/\*\s*=+\s*卡片跳转)', r'\1  <script>\n\2', s, count=1)
        if n == 1:
            open(idx_path, "w", encoding="utf-8").write(s2)
            o2 = len(re.findall(r'<script\b', s2)); c2 = len(re.findall(r'</script\s*>', s2))
            b2 = bool(re.search(r'</script>\s*\n\s*(?:\*|/\*|\(function|window\.__|var\s)', s2))
            print(f"  ✓ 已修复：<script> {o2} / </script> {c2}，裸奔JS={b2}")
            if b2 or o2 != c2:
                print("  🔴 修复后仍异常，请人工检查 index.html")
        else:
            print(f"  🔴 未匹配到裸奔段（命中 {n} 次），请人工检查 index.html")
    else:
        print(f"\n✓ script 标签体检：{opens} 对齐全，无裸奔 JS")

print("\n✅ 1:1 还原完成 →", OUT)
