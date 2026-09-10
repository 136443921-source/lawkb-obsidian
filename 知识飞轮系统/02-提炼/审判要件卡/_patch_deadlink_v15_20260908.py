#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_check_deadlinks.py → v1.5.0：支持外部链接白名单（跨库引用不算死链）"""
import io, os, shutil, importlib.util

P = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/审判要件卡/_check_deadlinks.py"
D = os.path.dirname(P)
os.makedirs("/tmp/死链检查器备份_20260908", exist_ok=True)
shutil.copy2(P, "/tmp/死链检查器备份_20260908/_check_deadlinks.py.v1.4.0")
print("💾 已备份 v1.4.0")

s = io.open(P, encoding="utf-8").read()
orig = s
s = s.replace("通用死链自检器 v1.4.0（2026-09-08）",
              "通用死链自检器 v1.5.0（2026-09-08）")

s = s.replace(
    """    **宁可放过噪声，不可误杀真链接**。改 2 后：'...' '' '0' 'R' '医' '名' 全为噪声，
    「民法典」「民法典合同编」等短真名保留。
\"\"\"""",
    """    **宁可放过噪声，不可误杀真链接**。改 2 后：'...' '' '0' 'R' '医' '名' 全为噪声，
    「民法典」「民法典合同编」等短真名保留。
  v1.5.0  🔴 外部链接白名单：跨库引用不再计为死链。
          2026-09-08 实测：155 个「死链」中 99 个（212 次）目标真实存在，
          只是位于 LawKB 之外（桌面办案系统 / Documents / IMA 缓存）。
          Obsidian wiki 链接跨 vault 本就无效 —— **链接失效 ≠ 链接错误**。
          白名单文件：_external_links_whitelist.json（指纹 → 外部真实路径），
          由 _build_external_whitelist_20260908.py 生成，保留路径可追溯。
          加载失败时**拒绝静默放行**（坑 17：门禁静默降级）—— 打 WARN 继续严格判。
\"\"\"""")

ANCHOR = "def check_one(path, allmd):"
FN = '''# ── 外部链接白名单（v1.5.0）────────────────────────────────
_WL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "_external_links_whitelist.json")
EXTERNAL_WL = {}
if os.path.exists(_WL_PATH):
    try:
        _w = json.load(io.open(_WL_PATH, encoding="utf-8"))
        EXTERNAL_WL = _w.get("entries") or {}
    except Exception as e:
        sys.stderr.write(f"WARN: 外部白名单加载失败（{e}），本次按严格模式判定\\n")
else:
    sys.stderr.write("WARN: 未找到 _external_links_whitelist.json，本次按严格模式判定\\n")


def is_external(name):
    """命中外部白名单 → 目标在 LawKB 之外真实存在，不算死链"""
    return sig(name) in EXTERNAL_WL


def check_one(path, allmd):'''
assert ANCHOR in s
s = s.replace(ANCHOR, FN, 1)

OLD = """    bad = [l for l in cand if l and not is_noise(l)
            and not is_concept(l) and l not in allmd]"""
NEW = """    bad = [l for l in cand if l and not is_noise(l)
            and not is_concept(l) and not is_external(l) and l not in allmd]"""
assert OLD in s
s = s.replace(OLD, NEW)

# 依赖：json（顶部已 import io/os/re/sys，需补 json）
if "\nimport json\n" not in s:
    s = s.replace("import io\nimport os\n", "import io\nimport json\nimport os\n", 1)

assert s != orig
io.open(P, "w", encoding="utf-8").write(s)
print("✏️  已写入 v1.5.0")

s2 = io.open(P, encoding="utf-8").read()
ok = all(["v1.5.0" in s2, "def is_external" in s2,
          "and not is_external(l)" in s2, "import json" in s2])
print("🔁 复验：", "✅ 就位" if ok else "❌ 缺失")

spec = importlib.util.spec_from_file_location("cdl", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print(f"\n🧪 白名单载入 {len(m.EXTERNAL_WL)} 条")
for t in ["推演纪要_6658_二开_举证质证主战场", "AI 行为规则", "民法典", "不存在的东西xyz"]:
    print(f"    {t[:30]:32} → {'外部(放行)' if m.is_external(t) else '库内判定'}")
