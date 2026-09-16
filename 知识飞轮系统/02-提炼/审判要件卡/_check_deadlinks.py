#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用死链自检器 v1.7.2（2026-09-16）
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
  v1.3.0  🔴 修复「related_links 写成字符串 → 被逐字符迭代」的批量误报。
          实测 18 个文件的 related_links 是 str（如 "R-SH-024 R-SH-023"
          或 "R-PI-083, [xxx-原始]"），旧代码 for x in <str> 逐字符拆出
          'R' '-' '8' ',' '医' 等噪声，全部计入死链。
          **这是「死链 1189」这个数字的绝大部分来源**——与 v1.2.0 同一类病：
          门禁把"解析错了"当成"数据坏了"。
          修法：抽公共函数 parse_related_links()，str 按 [,，、;；空白] 切分
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
  v1.4.0  🔴 加噪声过滤 is_noise()：指纹长度 < 4 的候选不参与死链判定。
          实测 '...' 11 次、'名' 4 次、'-' '0' '医' 等单字符被计为死链。
          这类是 **YAML 折叠/截断的残片**，不是链接 —— 计入死链既虚高数字，
          又会把真问题淹在水里。修法：sig() 只留中英文数字，长度 < 4 视为噪声。
          注意边界：'R-PI-176' 指纹 'rpi176' 长 6 → 保留（是合法编号引用）。

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
  v1.7.2  🔴 修复 v1.7.1 引入的回归（纯编号命名卡专项）：build_basename_set()
          读 frontmatter 提取 aliases 时用 `os.path.join(rt, f)` 拼路径，但 `rt`
          是 root、`f` 只是基名，子目录卡（慈法合规/人伤法/… 全部真实卡）必然
          FileNotFoundError，被 `except` 静默吞掉 → **别名从未入集**，aliases
          消解死链的功能形同虚设。改 `rt→r`（walk 当前目录）。回归验证：R-CF-115
          / R-PI-182 的别名现正确入集。教训：门禁「改了但没生效」= 静默失败，
          须用成员测试（目标别名 in 集合）验证而非只看 exit code。
"""
import io
import json
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

# v1.7.1：隔离区（回收站 / 垃圾概念页）必须排除——否则「隔离」形同虚设，
# 被隔离的坏文件仍会拉黑门禁（exit=2）。判据：目录名以 .trash 开头，或含「隔离_」。
def is_quarantine(d):
    return d.startswith(".trash") or "_隔离_" in d or d.startswith("_quarantine")

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


LAWKB = "/Users/chenyouqiang/Documents/LawKB"
EXTRA_ROOTS = [os.path.join(LAWKB, "法律法规库"),
               os.path.join(LAWKB, "智能体技能库"),
               os.path.join(LAWKB, "知识库")]


def extract_aliases(txt):
    """v2026-09-16（纯编号命名卡专项）：从 frontmatter 轻量提取 aliases。

    不全量 YAML 解析（5000+ 文件 × yaml.safe_load 太慢），只取首段 frontmatter
    （前 8K 足够），支持两种 Obsidian 写法：
      行内：aliases: [名称A, 名称B]
      块式：aliases:\n  - 名称A\n  - 名称B
    返回的别名并入基名集，使 [[别名]] 不再判死链。
    """
    if not txt.startswith("---"):
        return []
    parts = txt.split("---", 2)
    if len(parts) < 3:
        return []
    block = parts[1]
    out = []
    # 行内形式
    m = re.search(r"^aliases:\s*\[(.*?)\]\s*$", block, re.M)
    if m:
        for a in m.group(1).split(","):
            a = a.strip().strip("\"'[]").strip()
            if a:
                out.append(a)
        return out
    # 块形式
    lines = block.splitlines()
    for i, ln in enumerate(lines):
        if re.match(r"^aliases:\s*$", ln):
            j = i + 1
            while j < len(lines) and re.match(r"^\s*-\s+(.+)$", lines[j]):
                a = re.match(r"^\s*-\s+(.+)$", lines[j]).group(1).strip().strip("\"'")
                if a:
                    out.append(a)
                j += 1
            break
    return out


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
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".backup") and not is_quarantine(d)]
            for f in files:
                if f.endswith(".md"):
                    names.add(f[:-3])
                    # v2026-09-16：别名也并入基名集（轻量提取，不全量 YAML）
                    # ⚠️ 必须用 walk 当前目录 r 拼路径，rt 是 root 只首层巧合匹配，
                    # 子目录卡会 FileNotFoundError 被 except 吞掉 → 别名永不入集（已修 2026-09-16）
                    try:
                        with io.open(os.path.join(r, f), encoding="utf-8") as _fh:
                            _t = _fh.read(8192)
                        for _al in extract_aliases(_t):
                            names.add(_al)
                    except Exception:
                        pass
    return names


def md_files(root=ROOT):
    """列出待检 md 文件（同样跳过备份目录）"""
    out = []
    for r, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".backup") and not is_quarantine(d)]
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


# related_links 分割符：逗号/顿号/分号/空白/换行（实测三种写法并存）
RL_SPLIT = re.compile(r"[,，、;；\s]+")


QUOTES = "'\u201c\u201d\u2018\u2019`"


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
    return out


NO_FM = "\x00NO_FM\x00"   # v1.6.0：合法跳过标记（非错误）

NOISE_CHARS = re.compile(r"[^\u4e00-\u9fa5A-Za-z0-9]")


def sig(s):
    """指纹：只留中文/字母/数字（v1.4.0）"""
    return NOISE_CHARS.sub("", str(s)).lower()


def is_noise(name):
    """解析噪声判定（v1.4.0）

    实测噪声样本：'-' '0' '2' 'R' '8' '6' 'H' '1' ',' '医' '"' '疗' '...' '名'
    来源：YAML 折叠残片、逐字符拆分、被截断的 wiki 链接。
    判据：指纹长度 < 2。
    阈值校准（2026-09-08）：初版设 4，误伤「民法典」（指纹 3 字，是真笔记名）——
    **宁可放过噪声，不可误杀真链接**。改 2 后：'...' '' '0' 'R' '医' '名' 全为噪声，
    「民法典」「民法典合同编」等短真名保留。
    """
    return len(sig(name)) < 2


# ── 外部链接白名单（v1.5.0）────────────────────────────────
_WL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "_external_links_whitelist.json")
EXTERNAL_WL = {}
if os.path.exists(_WL_PATH):
    try:
        _w = json.load(io.open(_WL_PATH, encoding="utf-8"))
        EXTERNAL_WL = _w.get("entries") or {}
    except Exception as e:
        sys.stderr.write(f"WARN: 外部白名单加载失败（{e}），本次按严格模式判定\n")
else:
    sys.stderr.write("WARN: 未找到 _external_links_whitelist.json，本次按严格模式判定\n")


def is_external(name):
    """命中外部白名单 → 目标在 LawKB 之外真实存在，不算死链"""
    return sig(name) in EXTERNAL_WL


def check_one(path, allmd):
    """检查单张卡，返回 (死链列表, 链接总数)"""
    txt = io.open(path, encoding="utf-8").read()
    if not txt.startswith("---"):
        return [], 0, NO_FM

    try:
        fm = yaml.safe_load(txt.split("---")[1]) or {}
    except Exception as e:
        return [], 0, "YAML 解析失败：%s" % e

    links = parse_related_links(fm)
    body = re.findall(r"\[\[([^\]]+)\]\]", txt)

    # 归一化：剥离 [[]]、别名、锚点、路径前缀（见 normalize 文档）
    cand = [normalize(l) for l in links] + [normalize(b) for b in body]
    cand = [c for c in cand if c]

    total = len(cand)
    bad = [l for l in cand if l and not is_noise(l)
            and not is_concept(l) and not is_external(l) and l not in allmd]
    # 去重保持顺序
    seen, uniq = set(), []
    for b in bad:
        if b not in seen:
            seen.add(b)
            uniq.append(b)
    return uniq, total, None


NUM_REF = re.compile(r"^(R-[A-Z]{2}-\d+|LC-\d+|IMA-\d+|\d{3,})")
DATE_REF = re.compile(r"^20\d\d-")


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
    all_dead = []          # v1.7.0：汇总用于分类
    files_with_dead = 0
    parse_errors = []          # v1.2.0：解析失败不再静默吞掉
    skips = 0                  # v1.6.0：无 frontmatter 的合法跳过计数
    for p in sorted(targets):
        dead, total, err = check_one(p, allmd)
        name = os.path.basename(p)
        if err is NO_FM:
            skips += 1
            continue
        if err:
            parse_errors.append((name, err))
            print("  🚫 %s：%s" % (name, err))
            continue
        if dead:
            files_with_dead += 1
            total_dead += len(dead)
            all_dead.extend(dead)
            print("  ❌ %s（链接 %d 条，死链 %d 条）" % (name, total, len(dead)))
            for d in dead:
                print("       - %s" % d)
        else:
            print("  ✅ %s（链接 %d 条，死链 0）" % (name, total))

    strict = "--strict" in args
    if strict:
        print("\n===== 死链自检结果（strict 旧口径）=====")
        print("命中文件：%d / %d" % (files_with_dead, len(targets)))
        print("死链总数：%d" % total_dead)
    else:
        real, pending = classify_dead(all_dead)
        print("\n===== 死链自检结果（v1.7.0 分类口径）=====")
        print("命中文件：%d / %d" % (files_with_dead, len(targets)))
        print("  🔴 真死链（编号引用/语法残片，须修）：%d" % len(real))
        print("  🌱 待建笔记（主题名软引用，非缺陷）：%d" % len(pending))
        print("  （旧口径合计 %d 条；--strict 可复原旧口径）" % total_dead)
        for x in real[:40]:
            print("     - %s" % x)

    if skips:
        print("跳过（无 frontmatter 的普通文档，合法）：%d 个" % skips)

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
