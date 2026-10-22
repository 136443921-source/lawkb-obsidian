#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
决策卡 frontmatter 完整性门禁 v1.1.0
用途：核验 `04-LOG/决策日志/` 下每张决策卡的 frontmatter 字段完整性与合法性，
      落实「决策思维层字段不留空」纪律，防止 domain/verdict 缺失复发。

背景（2026-10-20 三断点诊断）：
   实测 35 张决策卡中 30 张缺 `domain`、21 张缺 `verdict`，且「对了/错了/结论对但理由错」
   合计 0 张 → 分层思维指纹无从切出、命中率与 AI 异议成真率永久无法产出。
   本门禁把「写卡即校验」固化，避免同类缺失再次积累。

校验项：
   ① domain  非空且属于六域枚举（办案/诉讼策略/证据取舍/客户沟通/职业发展/个人成长）  → **硬门禁**
   ② verdict 非空且属于四档判定（待验证/对了/错了/结论对但理由错）                    → **硬门禁**
   ③ 标题   frontmatter 需有 title 或以文件名兜底                                    → 提示
   ④ 溯源   补标过的卡须带 domain_backfilled 标记（提示性，不判失败）
   ⑤ ③-B 区「信号触发后的立即动作」子栏已填且非模板占位（2026-10-20 新增）      → **新建卡硬门禁**
      依据：雅菲案 6660（判「错了」）与 6658 案 34 号（判「对了」）两案重复踩中
      「信号全数精准命中、但因缺立即动作而零行动」的缺口。
      存量卡多为模板占位（未逐条填具体动作），故存量模式仅提示、不阻断。

⚠️ **严重级别设计（2026-10-20 修正）**：
   建卡时 verdict 必然为「待验证」（新决策尚未有结果），因此对**新建卡**而言
   verdict 缺失确实应拦。
   但**批量校验存量库**时，工具/训练/制度类卡本就无案件结果可依——
   强行补一个 verdict 属于伪造判定，违反「四档判定必须有事实支撑」原则。
   故本脚本：
   - **新建卡路径**（`--new <文件>`）：domain 与 verdict 均为硬门禁，缺一即退出码 1；
   - **存量库路径**（默认全量扫描）：domain 缺失 = 硬失败（退出码 1）；
     verdict 缺失 = **警告**，计入告警但**不影响退出码**。
   这样既能防止新卡缺字段复发，又不会逼着系统给无结果的卡硬凑判定。

⚠️ 关键：frontmatter 解析必须逐文件用正则截取首个 `---` 块，
   不得用 `grep '^domain:'` 全文件搜索——正文中的同名提及会造成误判。
   （2026-08-28 `_check_call_traceability.py` 已踩过"块状 YAML 误判"坑，此处同理加固。）

变更日志：
   v1.0.0（2026-10-20）初版：domain / verdict 校验，双模式（--new 硬门禁 / 存量库扫描）
   v1.1.0（2026-10-20）新增 ③-B 区「信号触发后的立即动作」校验（新建卡硬门禁）
          —— 依据：雅菲案 6660（判「错了」）与 6658 案 34 号（判「对了」）两案重复踩中
          「信号全数精准命中、但因缺立即动作而零行动」的缺口

用法：
   python3 _check_decision_card_integrity.py                # 全量扫描（存量库模式）
   python3 _check_decision_card_integrity.py --quiet        # 仅打印汇总
   python3 _check_decision_card_integrity.py --new <文件>   # 新建卡校验（硬门禁）
退出码：0=通过  1=存在硬门禁失败  2=目录不存在
"""
import re
import sys
import os
from collections import Counter

CARD_DIR = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/04-LOG/决策日志"

VALID_DOMAIN = {"办案", "诉讼策略", "证据取舍", "客户沟通", "职业发展", "个人成长"}
VALID_VERDICT = {"待验证", "对了", "错了", "结论对但理由错"}


def parse_frontmatter(text):
    """截取首个 --- 块；失败返回 None。支持 inline 与块状两种 YAML。"""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    return m.group(1)


def field(fm, key):
    """取 frontmatter 字段值；块状写法（下一行是 '- xxx'）返回列表。"""
    m = re.search(rf"^{key}:\s*(.*)$", fm, re.M)
    if not m:
        return None
    val = m.group(1).strip()
    if val == "":
        # 可能是块状写法
        rest = fm[m.end():]
        items = re.findall(r"^\s*-\s*(.+)$", rest, re.M)
        # 只取紧邻的连续列表项
        block = []
        for line in rest.split("\n"):
            mm = re.match(r"^\s*-\s*(.+)$", line)
            if mm:
                block.append(mm.group(1).strip())
            elif line.strip() == "":
                continue
            else:
                break
        return block if block else None
    return val


def check(new_mode=False, new_file=None):
    if new_mode:
        if not os.path.isfile(new_file):
            print(f"❌ 文件不存在: {new_file}")
            return 2
        files = [os.path.basename(new_file)]
        scan_dir = os.path.dirname(os.path.abspath(new_file))
    else:
        if not os.path.isdir(CARD_DIR):
            print(f"❌ 决策卡目录不存在: {CARD_DIR}")
            return 2
        files = sorted(
            f for f in os.listdir(CARD_DIR)
            if f.endswith(".md") and not f.startswith("_模板")
        )
        scan_dir = CARD_DIR
    issues = []
    warnings = []
    dom_c, ver_c = Counter(), Counter()
    total = len(files)

    for f in files:
        path = os.path.join(scan_dir, f)
        text = open(path, encoding="utf-8").read()
        fm = parse_frontmatter(text)
        if fm is None:
            issues.append((f, "frontmatter 缺失或格式异常", "无法解析首个 --- 块"))
            continue

        dom = field(fm, "domain")
        ver = field(fm, "verdict")
        body = text[text.find("\n---\n", 4) + 5:] if "\n---\n" in text[4:] else text

        if dom is None or (isinstance(dom, str) and not dom.strip()):
            issues.append((f, "domain 缺失", "无 domain 字段或值为空"))
        elif isinstance(dom, list):
            issues.append((f, "domain 格式异常", f"块状写法: {dom}"))
        elif dom not in VALID_DOMAIN:
            issues.append((f, "domain 非法值", f"'{dom}' 不在六域枚举 {sorted(VALID_DOMAIN)}"))
        else:
            dom_c[dom] += 1

        if ver is None or (isinstance(ver, str) and not ver.strip()):
            if new_mode:
                issues.append((f, "verdict 缺失", "无 verdict 字段或值为空（新建卡硬门禁）"))
            else:
                warnings.append((f, "verdict 缺失", "无 verdict 字段或值为空（存量卡无结果可依，"
                              "不硬凑判定——待案件结果落地后由事件触发回填）"))

        elif isinstance(ver, list):
            issues.append((f, "verdict 格式异常", f"块状写法: {ver}"))
        elif ver not in VALID_VERDICT:
            issues.append((f, "verdict 非法值", f"'{ver}' 不在四档判定 {sorted(VALID_VERDICT)}"))
        else:
            ver_c[ver] += 1

        # ③-B 区「信号触发后的立即动作」检查（仅新建卡硬门禁）
        has_3b = ("③-B" in body) or ("信号触发后的立即动作" in body)
        if not has_3b:
            if new_mode:
                issues.append((f, "③-B 区缺失", "模板新增必填子栏「信号触发后的立即动作」未写入"
                              "（每条推翻信号须跟「→ 我立刻做 X（对象+时限）」）"))
            else:
                warnings.append((f, "③-B 区缺失", "无「信号触发后的立即动作」子栏"
                              "（存量卡多为建卡于该子栏加入之前，属历史存量）"))
        else:
            # 已含 ③-B 区，检查是否仍是未填的模板占位
            m3b = re.search(r"###\s*③-B[^\n]*\n(.*?)(?=\n##|\n---|\Z)", body, re.S)
            seg = m3b.group(1) if m3b else ""
            # 去掉注释块后再看是否还有实质内容
            # 先剔除所有下划线占位符（连续 3 个及以上 _），再判断是否仍有实质内容
            seg_nc = re.sub(r"<!--.*?-->", "", seg, flags=re.S)
            seg_clean = re.sub(r"_{3,}", "", seg_nc)
            filled = bool(re.search(r"\u2192\s*\u6211\u7acb\u5373\u505a", seg_clean)) or \
                     bool(re.search(r"\u515c\u5e95\u8def\u5f84[^\n]{0,60}\u6539\u8d70\s*\S", seg_clean))
            if not filled:
                msg = ("③-B 区存在但仍是未填模板占位（未写具体动作/兜底路径）"
                       if new_mode else "③-B 区存在但仍是未填模板占位（历史存量）")
                if new_mode:
                    issues.append((f, "③-B 区未填", msg))
                else:
                    warnings.append((f, "③-B 区未填", msg))

    print("=" * 62)
    print("决策卡 frontmatter 完整性门禁 v1.0.0")
    print("=" * 62)
    print(f"扫描目录: {scan_dir}")
    print(f"模式: {'新建卡校验（硬门禁）' if new_mode else '存量库全量扫描（domain 硬门禁 / verdict 警告）'}")
    print(f"卡片总数: {total}")
    print()
    print("── domain 分布 ──")
    for k in sorted(VALID_DOMAIN):
        n = dom_c.get(k, 0)
        bar = "█" * min(n, 20)
        print(f"  {k:8s} {n:2d}  {bar}")
    zero = [k for k in VALID_DOMAIN if dom_c.get(k, 0) == 0]
    if zero:
        print(f"  ⚠️ 零覆盖域: {zero}")
    print()
    print("── verdict 分布 ──")
    for k in sorted(VALID_VERDICT):
        n = ver_c.get(k, 0)
        bar = "█" * min(n, 20)
        print(f"  {k:8s} {n:2d}  {bar}")
    judged = sum(ver_c.get(k, 0) for k in ("对了", "错了", "结论对但理由错"))
    if judged == 0:
        print("  ⚠️ 已判定 0 张 → 命中率与 AI 异议成真率无法产出（见三断点诊断报告）")
    print()
    print(f"── 合规判定 ──")
    if issues:
        print(f"  ❌ {len(issues)} 项硬门禁失败：")
        for f, kind, detail in issues:
            print(f"     · {f[:46]:48s} [{kind}] {detail}")
    else:
        print(f"  ✅ 无硬门禁失败（{total} 张）")
    if warnings:
        print(f"  ⚠️ {len(warnings)} 项警告（不阻断）：")
        for f, kind, detail in warnings:
            print(f"     · {f[:46]:48s} [{kind}] {detail}")
    print()
    return 1 if issues else 0


if __name__ == "__main__":
    quiet = "--quiet" in sys.argv
    new_file = None
    if "--new" in sys.argv:
        idx = sys.argv.index("--new")
        if idx + 1 < len(sys.argv):
            new_file = sys.argv[idx + 1]
    if quiet:
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = check(bool(new_file), new_file)
        summary = buf.getvalue()
        ok = "PASS" if code == 0 else "FAIL"
        print(f"[决策卡门禁] {ok} · {len(summary.splitlines())} 行明细已折叠")
        sys.exit(code)
    sys.exit(check(bool(new_file), new_file))
