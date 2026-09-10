#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_check_deadlinks.py → v1.3.1：递归展平嵌套列表 + 剥离残留引号"""
import io, os, shutil

P = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/审判要件卡/_check_deadlinks.py"
os.makedirs("/tmp/死链检查器备份_20260908", exist_ok=True)
shutil.copy2(P, "/tmp/死链检查器备份_20260908/_check_deadlinks.py.v1.3.0")
print("💾 已备份 v1.3.0")

s = io.open(P, encoding="utf-8").read()
orig = s

s = s.replace("通用死链自检器 v1.3.0（2026-09-08）",
              "通用死链自检器 v1.3.1（2026-09-08）")

s = s.replace(
    """          修法：抽公共函数 parse_related_links()，str 按 [,，、;；空白] 切分
          并剥离 [] 包裹，list 原样处理。分析器复用同一函数，口径统一。
\"\"\"""",
    """          修法：抽公共函数 parse_related_links()，str 按 [,，、;；空白] 切分
          并剥离 [] 包裹，list 原样处理。分析器复用同一函数，口径统一。
  v1.3.1  🔴 修复「related_links 写成嵌套列表 - - 项」的伪死链。
          实测（运维/LTI防幻觉能力实测评估-2026-08-30.md）：
              related_links:
                - - LTI-文本监察官系统配置说明
          即 list-of-list（Obsidian 双向链接转坏的产物，与 looks_damaged()
          安全网 guarding 的正是同一病）。旧代码对嵌套项 str() 得到
          "['LTI-文本监察官系统配置说明']"，strip("[]") 后仍残留单引号
          → 死链名变成 "'LTI-文本监察官系统配置说明'"，全库查无此物。
          修法：递归展平任意层级嵌套 + 剥离首尾中英文引号。
          与 v1.2.0/v1.3.0 同源：**门禁把「解析错」当「数据坏」**。
\"\"\"""")

OLD = '''def parse_related_links(fm):
    """v1.3.0 公共解析：兼容 list 与 str 两种 related_links 写法。

    坑（2026-09-08 实证）：18 个历史卡把 related_links 写成字符串，
    旧实现 `for x in (fm.get("related_links") or [])` 对 str 逐字符迭代，
    拆出 'R' '-' '8' ',' '医' 等单字符噪声 → 虚报死链数百条。
    """
    rl = fm.get("related_links") or []
    if isinstance(rl, str):
        rl = RL_SPLIT.split(rl)
    out = []
    for x in rl:
        if x is None:
            continue
        x = str(x).strip().strip("[]").strip()
        if x:
            out.append(x)
    return out'''

NEW = '''QUOTES = "'\\u201c\\u201d\\u2018\\u2019`"


def _flatten(x, out):
    """递归展平任意层级嵌套（v1.3.1）

    related_links 被写成 `- - 项`（list-of-list，Obsidian 转坏产物）时，
    逐层 str() 会带出 "['项']" 的方括号与引号。必须递归到标量再清洗。
    """
    if x is None:
        return
    if isinstance(x, (list, tuple)):
        for i in x:
            _flatten(i, out)
        return
    s = str(x).strip()
    if not s:
        return
    s = s.strip("[]").strip(QUOTES).strip()
    if s:
        out.append(s)


def parse_related_links(fm):
    """v1.3.1 公共解析：兼容 list / str / 嵌套 list 三种 related_links 写法。

    坑 1（v1.3.0）：18 个历史卡把 related_links 写成字符串，
        旧实现 for x in <str> 逐字符迭代，拆出 'R' '-' '医' 等噪声。
    坑 2（v1.3.1）：写成 `- - 项` 嵌套列表时，str() 得到 "['项']"，
        strip("[]") 后残留单引号 → 死链名带引号，全库查无此物。
    """
    rl = fm.get("related_links") or []
    if isinstance(rl, str):
        rl = RL_SPLIT.split(rl)
    out = []
    _flatten(rl, out)
    return out'''

assert OLD in s, "❌ 锚点未命中 parse_related_links"
s = s.replace(OLD, NEW)

assert s != orig
io.open(P, "w", encoding="utf-8").write(s)
print("✏️  已写入 v1.3.1")

s2 = io.open(P, encoding="utf-8").read()
ok = all(["v1.3.1" in s2, "def _flatten" in s2, "QUOTES" in s2])
print("🔁 复验：", "✅ 就位" if ok else "❌ 缺失")

# 单元自检
import importlib.util
spec = importlib.util.spec_from_file_location("cdl", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
cases = [
    {"related_links": [["LTI-文本监察官系统配置说明"], ["华宇元典MCP评估与优化建议-2026-08-30"]]},
    {"related_links": "R-SH-024 R-SH-023 R-SH-019"},
    {"related_links": "R-PI-083, [山东某创-原始]"},
    {"related_links": ["R-LN-055", "R-LN-056"]},
    {"related_links": [["a"], ["b"], ["c"]]},
]
print("\n🧪 单元自检：")
for c in cases:
    print("   ", c["related_links"] if not isinstance(c["related_links"], list) or len(str(c["related_links"])) < 50 else str(c["related_links"])[:50],
          "→", m.parse_related_links(c))
