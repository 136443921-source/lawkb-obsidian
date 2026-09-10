#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_check_deadlinks.py → v1.6.0：区分「无 frontmatter（合法跳过）」与「YAML 损坏（门禁 FAIL）」"""
import io, os, shutil, importlib.util

P = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/审判要件卡/_check_deadlinks.py"
os.makedirs("/tmp/死链检查器备份_20260908", exist_ok=True)
shutil.copy2(P, "/tmp/死链检查器备份_20260908/_check_deadlinks.py.v1.5.0")
print("💾 已备份 v1.5.0")

s = io.open(P, encoding="utf-8").read()
orig = s
s = s.replace("通用死链自检器 v1.5.0（2026-09-08）",
              "通用死链自检器 v1.6.0（2026-09-08）")

s = s.replace(
    """          加载失败时**拒绝静默放行**（坑 17：门禁静默降级）—— 打 WARN 继续严格判。
\"\"\"""",
    """          加载失败时**拒绝静默放行**（坑 17：门禁静默降级）—— 打 WARN 继续严格判。
  v1.6.0  🔴 区分「无 frontmatter」与「YAML 损坏」，前者合法跳过、后者才 FAIL。
          旧实现把两者都塞进 parse_errors，导致 --all 全库扫描时 30 个普通
          文档（入库索引 / 每日报告 / 知识推送日志，本就无 frontmatter）触发
          exit(2)，门禁永远红。**红着的门禁等于没有门禁** —— 与 v1.2.0 反向
          同源：v1.2.0 是「没查当成查过」，v1.6.0 是「不该查的当成查失败」。
          现在：NO_FM 计入 skips（INFO），YAML 解析异常才计 parse_errors（FAIL）。
\"\"\"""")

# check_one：无 frontmatter 返回标记而非错误串
s = s.replace(
    '''    if not txt.startswith("---"):
        return [], 0, "无 frontmatter，跳过链接检查"''',
    '''    if not txt.startswith("---"):
        return [], 0, NO_FM''')

# 定义常量
s = s.replace(
    "NOISE_CHARS = re.compile(",
    'NO_FM = "\\x00NO_FM\\x00"   # v1.6.0：合法跳过标记（非错误）\n\nNOISE_CHARS = re.compile(')

# main 分支
OLD = '''        if err:
            parse_errors.append((name, err))
            print("  🚫 %s：%s" % (name, err))
            continue'''
NEW = '''        if err is NO_FM:
            skips += 1
            continue
        if err:
            parse_errors.append((name, err))
            print("  🚫 %s：%s" % (name, err))
            continue'''
assert OLD in s
s = s.replace(OLD, NEW)

s = s.replace("    parse_errors = []          # v1.2.0：解析失败不再静默吞掉",
              "    parse_errors = []          # v1.2.0：解析失败不再静默吞掉\n    skips = 0                  # v1.6.0：无 frontmatter 的合法跳过计数")

# 汇总输出
OLD2 = '''    # v1.2.0：解析失败优先于死链判定 —— 「没查」不等于「查过了没问题」
    if parse_errors:'''
NEW2 = '''    if skips:
        print("跳过（无 frontmatter 的普通文档，合法）：%d 个" % skips)

    # v1.2.0：解析失败优先于死链判定 —— 「没查」不等于「查过了没问题」
    if parse_errors:'''
assert OLD2 in s
s = s.replace(OLD2, NEW2)

assert s != orig
io.open(P, "w", encoding="utf-8").write(s)
print("✏️  已写入 v1.6.0")

s2 = io.open(P, encoding="utf-8").read()
ok = all(["v1.6.0" in s2, "NO_FM" in s2, "skips = 0" in s2, "err is NO_FM" in s2])
print("🔁 复验：", "✅ 就位" if ok else "❌ 缺失")
