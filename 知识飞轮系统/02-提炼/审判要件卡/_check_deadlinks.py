#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用死链自检器 v1.2.0（2026-09-07）
--------------------------------
用途：检查任意规则卡 / 审判要件卡 / 工程事故卡 / 案由路由卡的
      frontmatter.related_links 与正文 [[...]] 是否为真实存在的笔记基名。

背景（SKILL 坑 9 两代教训）：
  · 第一代（2026-09-04）：生成器对文件名做标点清洗/截断 → 死链 17 条
  · 第二代（2026-09-07）：拿 frontmatter `title` 当文件名推导 → R-LN-055
    引用错 3 处（漏「的」/ 多破折号 / 脑补副标题），肉眼读起来完全合理

关键认知：**title 与文件名基名是两个独立字段，不可互相推导。**
          标题求可读（加副标题、调助词），文件名求简洁（缩短）。
          因此只能靠「与物理文件名集合做集合运算」发现，肉眼无效。

用法：
    python3 _check_deadlinks.py <卡文件路径> [<卡文件路径2> ...]
    python3 _check_deadlinks.py --dir <目录>          # 批量检查整个目录
    python3 _check_deadlinks.py --all                 # 检查整个裁判规则库

退出码：0 = 无死链；1 = 发现死链；2 = 解析失败（均可用于 CI / 交付门禁）

依赖：pyyaml（缺失时拒绝静默降级，直接报错退出 —— 见坑 2）
环境：/Users/chenyouqiang/.workbuddy/binaries/python/envs/default/bin/python

变更：
  v1.1.0  搜索根扩至全库（原只扫裁判规则库→误报 3 条）；normalize() 支持
          Obsidian 四种写法（原未处理别名/锚点/路径→虚高 3857 条）
  v1.2.0  🔴 修复「YAML 解析失败被静默吞掉」——原实现遇 YAML 错误只打印
          ⚠️ 后 continue，既不进命中数也不进死链数，最终仍 exit(0) 报
          「死链 0 ✅」。这与本卡治理的「校验通过≠交付合格」是同一类病：
          **门禁把"没查"当成"查过了没问题"**。现改为：解析失败计入
          parse_errors，汇总时优先报 FATAL 并 exit(2)。
"""
import io
import os
import re
import sys

# 搜索根：整个知识飞轮系统（不只用裁判规则库）
# 教训（2026-09-07）：首版只扫 06-沉淀/裁判规则库，把真实存在的
#   「02-提炼/经验卡片/婚姻家庭/经验卡片-赵某离婚案」误报为死链 3 条。
#   → 与坑 14 同源：**「MISS」不等于「不存在」，先怀疑检索范围，再怀疑数据。**
ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"

# 跳过的目录（备份 / 系统目录，不参与基名集合）
SKIP_DIRS = {".backup", ".backup_link_20260830_152052", ".backup_link_20260830_153501",
             ".backup_link_20260830_153728", ".workbuddy", ".git", "node_modules",
             "__pycache__", ".venv", "venv"}

# 概念页 / 枢纽页：不以 .md 卡片形式存在于规则库，视为合法链接
CONCEPT_PREFIXES = (
    "连接枢纽",
    "审判要件卡",
    "知识飞轮",
    "小强律师",
)

try:
    import yaml
except ImportError:
    sys.stderr.write("FATAL: 缺 pyyaml，校验器拒绝静默降级。\n"
                     "请用：/Users/chenyouqiang/.workbuddy/binaries/python/envs/default/bin/python\n")
    sys.exit(2)


def build_basename_set(root=ROOT):
    """收集知识飞轮系统内全部 .md 的基名（不含 .md），用于集合比对。
    跳过备份与系统目录，避免把备份副本也算作有效链接目标。"""
    names = set()
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".backup")]
        for f in files:
            if f.endswith(".md"):
                names.add(f[:-3])
    return names


def md_files(root=ROOT):
    """列出待检 md 文件（同样跳过备份目录）"""
    out = []
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".backup")]
        for f in files:
            if f.endswith(".md"):
                out.append(os.path.join(r, f))
    return out


def is_concept(name):
    return name.startswith(CONCEPT_PREFIXES)


def normalize(link):
    """归一化 wiki 链接 → 纯基名。

    必须处理的四种 Obsidian 写法（2026-09-07 全库体检实证，漏一个就大量误报）：
      1. [[笔记名]]            → 剥离方括号
      2. [[笔记名|显示别名]]    → 取 `|` 之前的部分
      3. [[路径/笔记名]]        → 取最后一段（basename）
      4. [[笔记名#锚点]]        → 取 `#` 之前的部分
    """
    if link is None:
        return ""
    s = str(link).strip()
    s = s.strip("[]")
    s = s.split("|")[0]        # 别名：取前段
    s = s.split("#")[0]        # 锚点：取前段
    s = s.rstrip("/")
    if "/" in s:
        s = s.rsplit("/", 1)[-1]   # 路径：取 basename
    return s.strip()


def check_one(path, allmd):
    """检查单张卡，返回 (死链列表, 链接总数)"""
    txt = io.open(path, encoding="utf-8").read()
    if not txt.startswith("---"):
        return [], 0, "无 frontmatter，跳过链接检查"

    try:
        fm = yaml.safe_load(txt.split("---")[1]) or {}
    except Exception as e:
        return [], 0, "YAML 解析失败：%s" % e

    links = [str(x).strip() for x in (fm.get("related_links") or [])]
    body = re.findall(r"\[\[([^\]]+)\]\]", txt)

    # 归一化：剥离 [[]]、别名、锚点、路径前缀（见 normalize 文档）
    cand = [normalize(l) for l in links] + [normalize(b) for b in body]
    cand = [c for c in cand if c]

    total = len(cand)
    bad = [l for l in cand if l and not is_concept(l) and l not in allmd]
    # 去重保持顺序
    seen, uniq = set(), []
    for b in bad:
        if b not in seen:
            seen.add(b)
            uniq.append(b)
    return uniq, total, None


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    if args[0] == "--all":
        targets = md_files()
    elif args[0] == "--dir":
        d = args[1]
        targets = [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".md")]
    else:
        targets = args

    allmd = build_basename_set()
    print("规则库笔记基名总数：%d" % len(allmd))
    print("待检卡片：%d 张\n" % len(targets))

    total_dead = 0
    files_with_dead = 0
    parse_errors = []          # v1.2.0：解析失败不再静默吞掉
    for p in sorted(targets):
        dead, total, err = check_one(p, allmd)
        name = os.path.basename(p)
        if err:
            parse_errors.append((name, err))
            print("  🚫 %s：%s" % (name, err))
            continue
        if dead:
            files_with_dead += 1
            total_dead += len(dead)
            print("  ❌ %s（链接 %d 条，死链 %d 条）" % (name, total, len(dead)))
            for d in dead:
                print("       - %s" % d)
        else:
            print("  ✅ %s（链接 %d 条，死链 0）" % (name, total))

    print("\n===== 死链自检结果 =====")
    print("命中文件：%d / %d" % (files_with_dead, len(targets)))
    print("死链总数：%d" % total_dead)

    # v1.2.0：解析失败优先于死链判定 —— 「没查」不等于「查过了没问题」
    if parse_errors:
        print("解析失败：%d 个文件（门禁 FAIL）" % len(parse_errors))
        for n, e in parse_errors:
            print("   🚫 %s → %s" % (n, str(e).split("\n")[0][:120]))
        print("\n结论：❌ 存在解析失败，门禁不通过（先修 YAML 再复检）")
        sys.exit(2)

    if total_dead:
        print("\n处置：用 `ls <落盘目录>/ | grep \"^R-<域>-<号>\"` 取真实文件名基名后替换；")
        print("      替换须 dry-run 先行，并用本脚本复检至死链 0。")
        sys.exit(1)
    print("结论：死链 0 ✅")
    sys.exit(0)


if __name__ == "__main__":
    main()
