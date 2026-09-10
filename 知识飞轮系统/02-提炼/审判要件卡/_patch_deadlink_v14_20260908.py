#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_check_deadlinks.py → v1.4.0：过滤解析噪声，不再把垃圾算作死链"""
import io, os, shutil, importlib.util

P = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/审判要件卡/_check_deadlinks.py"
os.makedirs("/tmp/死链检查器备份_20260908", exist_ok=True)
shutil.copy2(P, "/tmp/死链检查器备份_20260908/_check_deadlinks.py.v1.3.1")
print("💾 已备份 v1.3.1")

s = io.open(P, encoding="utf-8").read()
orig = s

s = s.replace("通用死链自检器 v1.3.1（2026-09-08）",
              "通用死链自检器 v1.4.0（2026-09-08）")

s = s.replace(
    """          与 v1.2.0/v1.3.0 同源：**门禁把「解析错」当「数据坏」**。
\"\"\"""",
    """          与 v1.2.0/v1.3.0 同源：**门禁把「解析错」当「数据坏」**。
  v1.4.0  🔴 加噪声过滤 is_noise()：指纹长度 < 4 的候选不参与死链判定。
          实测 '...' 11 次、'名' 4 次、'-' '0' '医' 等单字符被计为死链。
          这类是 **YAML 折叠/截断的残片**，不是链接 —— 计入死链既虚高数字，
          又会把真问题淹在水里。修法：sig() 只留中英文数字，长度 < 4 视为噪声。
          注意边界：'R-PI-176' 指纹 'rpi176' 长 6 → 保留（是合法编号引用）。
\"\"\"""")

# 插入 sig / is_noise（放在 normalize 之后）
ANCHOR = '''def check_one(path, allmd):'''
NOISE_FN = '''NOISE_CHARS = re.compile(r"[^\\u4e00-\\u9fa5A-Za-z0-9]")


def sig(s):
    """指纹：只留中文/字母/数字（v1.4.0）"""
    return NOISE_CHARS.sub("", str(s)).lower()


def is_noise(name):
    """解析噪声判定（v1.4.0）

    实测噪声样本：'-' '0' '2' 'R' '8' '6' 'H' '1' ',' '医' '"' '疗' '...' '名'
    来源：YAML 折叠残片、逐字符拆分、被截断的 wiki 链接。
    判据：指纹长度 < 4 —— 真实笔记名（含最短的 R-PI-176 → 'rpi176' 长 6）均 > 4。
    """
    return len(sig(name)) < 4


def check_one(path, allmd):'''
assert ANCHOR in s
s = s.replace(ANCHOR, NOISE_FN, 1)

# 死链过滤加 is_noise
OLD = """    bad = [l for l in cand if l and not is_concept(l) and l not in allmd]"""
NEW = """    bad = [l for l in cand if l and not is_noise(l)
            and not is_concept(l) and l not in allmd]"""
assert OLD in s, "❌ 锚点未命中 bad ="
s = s.replace(OLD, NEW)

assert s != orig
io.open(P, "w", encoding="utf-8").write(s)
print("✏️  已写入 v1.4.0")

s2 = io.open(P, encoding="utf-8").read()
ok = all(["v1.4.0" in s2, "def is_noise" in s2, "def sig" in s2,
          "and not is_noise(l)" in s2])
print("🔁 复验：", "✅ 就位" if ok else "❌ 缺失")

spec = importlib.util.spec_from_file_location("cdl", P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print("\n🧪 噪声判定自检：")
for t in ["...", "名", "-", "0", "医", "R-PI-176", "第十五章  医疗纠纷", "民法典"]:
    print(f"    {t!r:28} → {'噪声' if m.is_noise(t) else '有效'}  (sig={m.sig(t)!r})")
