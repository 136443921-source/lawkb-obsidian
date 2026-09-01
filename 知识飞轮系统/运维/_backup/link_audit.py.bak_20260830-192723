#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
断链判定器 v3（alias 感知版，带单点断言自检）
========================================================
相对 v2 升级：
  * 新增 alias 索引——读取所有 .md frontmatter 的 `aliases` / `alias`
    （支持 inline `aliases: [A, B]` 与 block 写法），使 `[[R-PI-166]]`
    这类裸号链接在「卡片采用描述后缀命名」时也能判定为正常。
  * 新增 R-PI-166 / R-PI-174 为 alias 解析断言目标。
  * 支持 --threshold <pct> 与退出码（> 阈值退出 1，供自动化门禁）。

用法：
  python3 link_audit.py                  # 详细报告
  python3 link_audit.py --quiet         # 仅汇总行
  python3 link_audit.py --threshold 0.5 # 自定义断链率门禁
退出码：0 = 断链率 ≤ 阈值   1 = 超过阈值
"""
import re, sys, unicodedata
from pathlib import Path
from collections import Counter

V = Path("/Users/chenyouqiang/Documents/LawKB")
SKIP = ['.backup', '/.git', '.obsidian', '.trash', 'node_modules', '/_recovery_tmp/']
THRESHOLD = 0.5
if '--threshold' in sys.argv:
    i = sys.argv.index('--threshold')
    THRESHOLD = float(sys.argv[i + 1])
QUIET = '--quiet' in sys.argv


def norm(s: str) -> str:
    # NFC 归一化 + 去首尾空白（macOS 文件系统可能返回 NFD）
    return unicodedata.normalize('NFC', s).strip()


# ---------- 建索引：stem / 相对路径 / alias ----------
stems, relpaths, aliases = set(), set(), set()
ALIAS_INLINE = re.compile(r'^aliases?:\s*\[(.*?)\]\s*$', re.M)
ALIAS_BLOCK = re.compile(r'^aliases?:\s*$', re.M)

for p in V.rglob("*"):
    if not p.is_file():
        continue
    s = str(p)
    if any(k in s for k in SKIP):
        continue
    rel = p.relative_to(V)
    stems.add(norm(p.stem))
    stems.add(norm(p.name))                      # 含扩展名也算（[[x.html]]）
    relpaths.add(norm(str(rel)))
    relpaths.add(norm(str(rel.with_suffix(''))))

    # frontmatter 内的 alias
    try:
        txt = p.read_text(encoding='utf-8')
    except Exception:
        continue
    if not txt.startswith('---'):
        continue
    end = txt.find('\n---', 3)
    if end < 0:
        continue
    fm = txt[3:end]
    m = ALIAS_INLINE.search(fm)
    if m:
        for a in m.group(1).split(','):
            a = norm(a.strip().strip('"').strip("'"))
            if a:
                aliases.add(a)
    elif ALIAS_BLOCK.search(fm):
        for ln in fm.split('\n'):
            mm = re.match(r'^\s+-\s+(.+)$', ln)
            if mm:
                a = norm(mm.group(1).strip().strip('"').strip("'"))
                if a:
                    aliases.add(a)


def resolved(tgt: str) -> bool:
    t = norm(tgt)
    if not t:
        return True
    if t in stems or t in relpaths or t in aliases:
        return True
    # 带路径的链接：取最后一段再比 stem
    last = norm(t.split('/')[-1])
    if last in stems or last in aliases:
        return True
    # 去掉扩展名再比
    if '.' in last and norm(last.rsplit('.', 1)[0]) in stems:
        return True
    return False


# ---------- 自检断言 ----------
ASSERT_EXIST = [
    "知识飞轮系统/03-连接/概念页/小强律师数字分身系统-使用指导手册-v3.0.0",
    "对外版分身人格蒸馏方案-v1.0",
    "R-HT-109-约定违约金过高按LPR1.5倍调整",
    "LTI文本监控器v4.0迁移与调用规范",
    "self.md-20260805",
    "法律检索报告_王某某贷款担保纠纷案_20260527_v1.1",
    "R-PI-166",   # alias 解析断言目标
    "R-PI-174",   # alias 解析断言目标
]
print("=== 判定器自检（以下目标已实地确认存在，必须全部判为「正常」）===")
ok = True
for t in ASSERT_EXIST:
    r = resolved(t)
    print(f"  {'✅' if r else '🔴 误判为断链'} {t}")
    if not r:
        ok = False
print(f"自检结果: {'通过 ✅' if ok else '未通过 🔴（判定器仍有 bug，数字不可信）'}\n")
if not ok:
    sys.exit(2)

# ---------- 全库扫描 ----------
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
pat = re.compile(r'\[\[([^\[\]\n]+?)\]\]')
total = normal = datetag = 0
broken = Counter()
broken_src = {}
for p in V.rglob("*.md"):
    s = str(p)
    if any(k in s for k in SKIP):
        continue
    try:
        txt = p.read_text(encoding='utf-8')
    except Exception:
        continue
    for m in pat.finditer(txt):
        raw = m.group(1)
        tgt = raw.split('|')[0].split('#')[0].strip()
        total += 1
        if DATE.match(tgt):
            datetag += 1
            continue
        if resolved(tgt):
            normal += 1
        else:
            broken[tgt] += 1
            broken_src.setdefault(tgt, set()).add(str(p.relative_to(V)))

nb = sum(broken.values())
denom = total - datetag
rate = nb / denom * 100 if denom else 0.0
print(f"链接总数: {total} | 日期标签(非链接): {datetag} | 有效分母: {denom}")
print(f"正常: {normal} | 真断链: {nb}  → 断链率 {rate:.3f}%  (门禁 {THRESHOLD}%)")
print(f"断链唯一目标数: {len(broken)}  | alias 已索引: {len(aliases)} 个")
if not QUIET:
    print("\n--- 断链 TOP 20 ---")
    for t, c in broken.most_common(20):
        print(f"  {c:4d}  [[{t}]]   (源文件 {len(broken_src[t])} 个)")

sys.exit(0 if rate <= THRESHOLD else 1)
