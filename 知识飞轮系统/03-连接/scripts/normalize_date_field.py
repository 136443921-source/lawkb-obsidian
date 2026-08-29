#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalize_date_field.py  v1.0  (2026-08-29)

用途：一次性批处理 —— 规范化裁判规则卡 frontmatter 的日期字段。
背景：merge_rules_monthly.py 仅识别 `date:` 字段来判定"当月新增卡"；但 06-沉淀/裁判规则库
     下 604 张 R-*.md 中仅 488 张有 `date:`、仅 424 张有 `created_month:`。初版正则
     （初版正则仅匹配「R-大写字母-数字」与「R+数字」两类）漏掉了"描述式后缀"命名卡
     （如 R-SH-027-有限公司…md、R030-提供劳务…md，共约 180 张），导致这批卡既无 date 也无
     created_month。本脚本把日期字段统一为 `date: YYYY-MM-DD`，并默认追加
     `created_month: YYYY-MM` 作为稳健的月度归并键，彻底消除"纯靠 date 扫描"的漂移坑。
     2026-08-29 修正：正则放宽至「R 开头且 .md 结尾」（经核验 604 张 R 卡均含合法 frontmatter），
     覆盖全部 ID 式 / 旧式 / 描述式后缀命名。

规范化规则（仅改 frontmatter，绝不碰正文）：
  * `date:` 缺失 → 从 `created:` 派生（取前 10 位 YYYY-MM-DD）；`created:` 也无 → 取文件 mtime。
  * `date:` 非 ISO 日期（如 "2015"、含 T 时间） → 规范为 YYYY-MM-DD。
  * 追加 `created_month: YYYY-MM`（默认开启；已存在则跳过）。

安全设计（遵循 legal-base 六-B 铁律）：
  * 默认 --dry-run，不写盘。
  * --apply 前整目录备份（裁判规则库.bak-<ts>/），仅追加/改写 frontmatter 行，不重建文件。
  * 幂等：字段已合规则跳过，重复运行不堆积、不破坏。
  * 失败可秒级回滚：rm 改造目录，mv 备份目录回原名。

用法：
  python3 normalize_date_field.py                  # dry-run（默认扫描 06-沉淀/裁判规则库）
  python3 normalize_date_field.py --root /path     # 指定根
  python3 normalize_date_field.py --apply          # 真正写盘（先整目录备份）
  python3 normalize_date_field.py --apply --no-created-month   # 不追加 created_month
"""
import argparse
import datetime
import os
import re
import shutil

DEFAULT_ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库"
# 2026-08-29 修正：覆盖全部命名范式
#   - ID 式      ：R-HT-017.md / R-SH-002.md / R-PI-034.md（R-大写字母-数字）
#   - 旧式        ：R005.md（R+数字，无横线）
#   - 描述式后缀：R-SH-027-有限公司股权分期付款转让不适用合同法167条法定解除.md
#                 R030-提供劳务中第三人侵权不真正连带.md（R+数字-描述）
# 经核验，全部 604 张 R*.md 均含合法 frontmatter，放宽至“R 开头且 .md 结尾”安全。
CARD_RE = re.compile(r'^R.*\.md$')
CARD_RE_OLD = CARD_RE  # 兼容主流程（已统一为正则放宽版）
ISO_DATE = re.compile(r'(\d{4}-\d{2}-\d{2})')


def extract_date(val):
    """从任意值中抽取 YYYY-MM-DD；抽不到返回 None。"""
    if not val:
        return None
    m = ISO_DATE.search(val)
    return m.group(1) if m else None


def process_file(path, add_cmonth):
    """返回变更列表（['date'] 等）；无变更返回 None。不写盘。"""
    try:
        text = open(path, encoding="utf-8").read()
    except Exception:
        return None
    if not text.startswith("---"):
        return None  # 无 frontmatter，跳过
    parts = text.split("\n")
    close = None
    for i in range(1, len(parts)):
        if parts[i].strip() == "---":
            close = i
            break
    if close is None:
        return None
    fm = parts[1:close]
    date_idx = created_idx = cmonth_idx = None
    date_val = created_val = None
    for i, l in enumerate(fm):
        s = l.strip()
        if s.startswith("date:"):
            date_idx, date_val = i, s[5:].strip()
        elif s.startswith("created:"):
            created_idx, created_val = i, s[8:].strip()
        elif s.startswith("created_month:"):
            cmonth_idx = i

    # 解析目标 date
    resolved = extract_date(date_val)
    if not resolved and created_val:
        resolved = extract_date(created_val)
    if not resolved:
        resolved = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")

    changes = []
    new_fm = list(fm)
    # 处理 date
    if date_idx is not None:
        new_line = f"date: {resolved}"
        if new_fm[date_idx].strip() != new_line:
            new_fm[date_idx] = new_line
            changes.append("date(rewrite)")
    else:
        ins = f"date: {resolved}"
        if created_idx is not None:
            new_fm.insert(created_idx + 1, ins)
        else:
            new_fm.insert(0, ins)
        changes.append("date(insert)")
    # 处理 created_month
    if add_cmonth and cmonth_idx is None:
        cmonth = resolved[:7]
        di = next((i for i, l in enumerate(new_fm) if l.strip().startswith("date:")), 0)
        new_fm.insert(di + 1, f"created_month: {cmonth}")
        changes.append("created_month(insert)")

    if not changes:
        return None
    new_text = "\n".join(["---"] + new_fm + parts[close:])
    if not new_text.endswith("\n"):
        new_text += "\n"
    return changes, new_text, resolved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--apply", action="store_true", help="真正写盘（默认 dry-run）")
    ap.add_argument("--no-created-month", action="store_true", help="不追加 created_month")
    args = ap.parse_args()
    root = args.root
    add_cmonth = not args.no_created_month

    files = []
    for dp, dn, fn in os.walk(root):
        for f in fn:
            if CARD_RE.match(f):
                files.append(os.path.join(dp, f))
    files.sort()
    print(f"扫描到卡片：{len(files)} 张（root={root}）")
    print(f"模式：{'APPLY(写盘)' if args.apply else 'DRY-RUN'} ｜ 追加 created_month: {'是' if add_cmonth else '否'}")
    print("-" * 60)

    # 六-B 安全前置：--apply 前整目录备份（单一回滚点）
    bak = None
    if args.apply:
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        bak = root + ".bak-" + ts
        i = 2
        while os.path.exists(bak):
            bak = root + ".bak-" + ts + f"-{i}"
            i += 1
        shutil.copytree(root, bak)
        src_n = sum(len(fs) for _, _, fs in os.walk(root))
        bak_n = sum(len(fs) for _, _, fs in os.walk(bak))
        assert src_n == bak_n, "❌ 备份文件数不一致，中止写盘！"
        print(f"📦 已备份整目录：{os.path.basename(bak)}（{bak_n} 个文件，回滚：mv 该目录回原名）")
        print("-" * 60)

    n_date_add = n_date_fix = n_cmonth_add = n_skip = n_nofm = 0
    changed = []
    for p in files:
        res = process_file(p, add_cmonth)
        if res is None:
            n_skip += 1
            continue
        changes, new_text, resolved = res
        if args.apply:
            open(p, "w", encoding="utf-8").write(new_text)
        tagset = set(changes)
        if "date(insert)" in tagset:
            n_date_add += 1
        if "date(rewrite)" in tagset:
            n_date_fix += 1
        if "created_month(insert)" in tagset:
            n_cmonth_add += 1
        rel = os.path.relpath(p, root)
        changed.append((rel, ",".join(changes), resolved))

    print(f"跳过(已合规)：{n_skip} 张")
    print(f"新增 date: {n_date_add} 张 ｜ 改写 date: {n_date_fix} 张 ｜ 新增 created_month: {n_cmonth_add} 张")
    print(f"实际变更文件：{len(changed)} 张")
    if args.apply:
        print("✅ 已写盘。")
        if bak:
            print(f"🔒 回滚点：{bak}（如需撤销：rm -rf {root} && mv {bak} {root}）")
    else:
        print("[dry-run] 未写盘。前 15 条预览：")
        for rel, ch, dt in changed[:15]:
            print(f"   {rel}  <{ch}>  → date={dt}")
    return 0


if __name__ == "__main__":
    main()
