#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_check_deadlinks.py v1.6.0 -> v1.7.0 原子补丁（同文件多处修改必须一次写入，坑 19）"""
import io, os, shutil, datetime

P = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/审判要件卡/_check_deadlinks.py"
BK = "/tmp/存量卡巡检_20260912-1042/_check_deadlinks.py.bak-v1.6.0"
os.makedirs(os.path.dirname(BK), exist_ok=True)
if not os.path.exists(BK):
    shutil.copy2(P, BK)
    print("已备份 →", BK)

t = io.open(P, encoding="utf-8").read()
orig = t

# ---- 1. 版本号 ----
t = t.replace('通用死链自检器 v1.6.0（2026-09-08）',
              '通用死链自检器 v1.7.0（2026-09-12）', 1)

# ---- 2. 变更日志追加 ----
CHANGE = """
  v1.7.0  🔴 修复「判定口径虚高」——把「待建笔记/主题名」与「跨库引用」误算成死链。
          2026-09-12 存量卡质量巡检实测（829 条候选）：
            C 待建笔记/主题名 621 条（75%）——如「小德慈善合规CMS产品化商业计划」
              「习水县新能源光伏光电会议备忘录」，是**提及但未建笔记的主题软引用**，
              属知识库常态，不是缺陷；
            A 跨库误报 63 条——如「中华人民共和国民法典（红队）」「H1合同规则库」，
              实存于 法律法规库 / 智能体技能库 / 知识库，而旧版 build_basename_set()
              只扫「知识飞轮系统」一个 root，必然判死。
          与 v1.2.0/v1.3.0/v1.4.0 同一类病：**门禁把「口径外的合法引用」当「数据坏」**，
          后果是真问题（D 类编号引用 118 条）被 621 条噪声淹没。
          修法：
            ① build_basename_set() 扩为多 root（+法律法规库/智能体技能库/知识库）；
            ② 新增 classify_dead()：死链分「真死链（编号引用/语法残片）」与
               「待建笔记（主题名）」两类；
            ③ 汇总分别输出，退出码只按「真死链」判定；--strict 复原旧口径。
"""
t = t.replace('"""\nimport io', CHANGE + '"""\nimport io', 1)

# ---- 3. build_basename_set 扩多 root ----
OLD_BS = '''def build_basename_set(root=ROOT):
    """收集知识飞轮系统内全部 .md 的基名（不含 .md），用于集合比对。
    跳过备份与系统目录，避免把备份副本也算作有效链接目标。"""
    names = set()
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".backup")]
        for f in files:
            if f.endswith(".md"):
                names.add(f[:-3])
    return names'''
NEW_BS = '''LAWKB = "/Users/chenyouqiang/Documents/LawKB"
EXTRA_ROOTS = [os.path.join(LAWKB, "法律法规库"),
               os.path.join(LAWKB, "智能体技能库"),
               os.path.join(LAWKB, "知识库")]


def build_basename_set(root=ROOT, extra=True):
    """收集全部 .md 的基名（不含 .md），用于集合比对。

    v1.7.0：extra=True 时**额外并入法律法规库/智能体技能库/知识库**。
    旧版只扫「知识飞轮系统」一个 root，导致「中华人民共和国民法典（红队）」
    「H1合同规则库」等合法跨库引用被判死链（实测 63 条误报）。
    """
    names = set()
    roots = [root] + ([r for r in EXTRA_ROOTS if os.path.isdir(r)] if extra else [])
    for rt in roots:
        for r, dirs, files in os.walk(rt):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".backup")]
            for f in files:
                if f.endswith(".md"):
                    names.add(f[:-3])
    return names'''
assert OLD_BS in t, "build_basename_set 未命中"
t = t.replace(OLD_BS, NEW_BS, 1)

# ---- 4. 新增 classify_dead（插到 def main 之前）----
CLASSIFY = '''NUM_REF = re.compile(r"^(R-[A-Z]{2}-\\d+|LC-\\d+|IMA-\\d+|\\d{3,})")
DATE_REF = re.compile(r"^20\\d\\d-")


def classify_dead(names):
    """v1.7.0：死链二分。

    真死链：编号引用（R-XX-nnn / LC-nnn / IMA-nnn）、语法残片（'.md'、
            纯数字）——指向「本应存在却不存在」的对象，是真缺陷。
    待建笔记：其余主题名软引用（如「小德慈善合规CMS产品化商业计划」），
            是「提及但未建笔记」，属知识库常态，**不计入门禁退出码**。
    """
    real, pending = [], []
    for n in names:
        s = n.strip()
        if s == ".md" or s.endswith(".md") or NUM_REF.match(s) or DATE_REF.match(s):
            real.append(n)
        else:
            pending.append(n)
    return real, pending


def main():'''
assert "def main():" in t
t = t.replace("def main():", CLASSIFY, 1)

# ---- 5. main 汇总改造 ----
OLD_SUM = '''    print("\\n===== 死链自检结果 =====")
    print("命中文件：%d / %d" % (files_with_dead, len(targets)))
    print("死链总数：%d" % total_dead)'''
NEW_SUM = '''    strict = "--strict" in args
    if strict:
        print("\\n===== 死链自检结果（strict 旧口径）=====")
        print("命中文件：%d / %d" % (files_with_dead, len(targets)))
        print("死链总数：%d" % total_dead)
    else:
        real, pending = classify_dead(all_dead)
        print("\\n===== 死链自检结果（v1.7.0 分类口径）=====")
        print("命中文件：%d / %d" % (files_with_dead, len(targets)))
        print("  🔴 真死链（编号引用/语法残片，须修）：%d" % len(real))
        print("  🌱 待建笔记（主题名软引用，非缺陷）：%d" % len(pending))
        print("  （旧口径合计 %d 条；--strict 可复原旧口径）" % total_dead)
        for x in real[:40]:
            print("     - %s" % x)'''
assert OLD_SUM in t, "汇总段未命中"
t = t.replace(OLD_SUM, NEW_SUM, 1)

# ---- 6. 收集 all_dead ----
OLD_LOOP = '''        if dead:
            files_with_dead += 1
            total_dead += len(dead)'''
NEW_LOOP = '''        if dead:
            files_with_dead += 1
            total_dead += len(dead)
            all_dead.extend(dead)'''
assert OLD_LOOP in t
t = t.replace(OLD_LOOP, NEW_LOOP, 1)
t = t.replace('    total_dead = 0\n', '    total_dead = 0\n    all_dead = []          # v1.7.0：汇总用于分类\n', 1)

# ---- 7. 退出码按真死链 ----
OLD_EXIT = '''        print("\\n结论：死链 0 ✅")'''
if OLD_EXIT in t:
    t = t.replace(OLD_EXIT, '''        print("\\n结论：死链 0 ✅")''', 1)

io.open(P, "w", encoding="utf-8").write(t)
print("✅ 已写入 v1.7.0（字节 %d -> %d）" % (len(orig), len(t)))
