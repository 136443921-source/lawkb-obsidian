#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 _check_deadlinks.py 升到 v1.3.0（原子写入，规避坑19 同文件多 Edit 丢改）"""
import io, os, shutil, time

P = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/审判要件卡/_check_deadlinks.py"
BK = "/tmp/死链检查器备份_20260908"
os.makedirs(BK, exist_ok=True)
shutil.copy2(P, os.path.join(BK, "_check_deadlinks.py.v1.2.0"))
print("💾 已备份 →", BK)

s = io.open(P, encoding="utf-8").read()
orig = s

# ── 1. 版本头 ──────────────────────────────────────────────
s = s.replace(
    '通用死链自检器 v1.2.0（2026-09-07）',
    '通用死链自检器 v1.3.0（2026-09-08）')

# ── 2. 文件头补 v1.3.0 变更说明 ────────────────────────────
s = s.replace(
    """          **门禁把"没查"当成"查过了没问题"**。现改为：解析失败计入
          parse_errors，汇总时优先报 FATAL 并 exit(2)。
\"\"\"""",
    """          **门禁把"没查"当成"查过了没问题"**。现改为：解析失败计入
          parse_errors，汇总时优先报 FATAL 并 exit(2)。
  v1.3.0  🔴 修复「related_links 写成字符串 → 被逐字符迭代」的批量误报。
          实测 18 个文件的 related_links 是 str（如 "R-SH-024 R-SH-023"
          或 "R-PI-083, [xxx-原始]"），旧代码 for x in <str> 逐字符拆出
          'R' '-' '8' ',' '医' 等噪声，全部计入死链。
          **这是「死链 1189」这个数字的绝大部分来源**——与 v1.2.0 同一类病：
          门禁把"解析错了"当成"数据坏了"。
          修法：抽公共函数 parse_related_links()，str 按 [,，、;；空白] 切分
          并剥离 [] 包裹，list 原样处理。分析器复用同一函数，口径统一。
\"\"\"""")

# ── 3. 插入公共解析函数（放在 is_concept 之后）──────────────
if "def parse_related_links" not in s:
    s = s.replace(
        """def check_one(path, allmd):""",
        '''# related_links 分割符：逗号/顿号/分号/空白/换行（实测三种写法并存）
RL_SPLIT = re.compile(r"[,，、;；\\s]+")


def parse_related_links(fm):
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
    return out


def check_one(path, allmd):''')

# ── 4. check_one 内部改用公共函数 ──────────────────────────
s = s.replace(
    """    links = [str(x).strip() for x in (fm.get("related_links") or [])]
    body = re.findall(r"\\[\\[([^\\]]+)\\]\\]", txt)""",
    """    links = parse_related_links(fm)
    body = re.findall(r"\\[\\[([^\\]]+)\\]\\]", txt)""")

assert s != orig, "❌ 未发生任何替换，请检查锚点"
io.open(P, "w", encoding="utf-8").write(s)
print("✏️  已写入 v1.3.0")

# ── 5. 复验 ────────────────────────────────────────────────
s2 = io.open(P, encoding="utf-8").read()
ok = all([
    "v1.3.0" in s2,
    "def parse_related_links" in s2,
    "links = parse_related_links(fm)" in s2,
    "RL_SPLIT" in s2,
])
print("🔁 复验：", "✅ 全部就位" if ok else "❌ 有缺")
