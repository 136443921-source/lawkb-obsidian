#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_rules_monthly.py  v1.0  (2026-08-13)

用途：月度「裁判规则对账」的合并步骤——把当月新增裁判规则卡（R-*.md）的索引
     合并进主文件（裁判规则库.md / 合同风险规则库.md），保持主库新鲜度。

背景：06-沉淀/裁判规则库/ 已全面卡片化（08 月新增 200+ 张 R-*.md 独立卡），
     而主文件「裁判规则库.md」「合同风险规则库.md」为早期表格式汇编，停更于 07-28。
     卡片与主文件格式异构，不能直接内容合并 → 采用「月度索引段」增量合并：
     在主文件尾部追加「## 月度新增裁判规则卡索引（YYYY-MM）」段，
     列出当月新增卡的 rule_id / title / 相对路径链接，重复运行幂等不堆积。

安全设计：
  * 默认 --dry-run，不写盘
  * 写盘前自动备份主文件（.bak-<ts>）
  * 按月份段标记幂等：已存在该月段则跳过
  * 仅追加不覆盖，不修改主文件原有内容

用法：
  python3 merge_rules_monthly.py                  # dry-run（默认当月）
  python3 merge_rules_monthly.py --month 2026-08  # 指定月份
  python3 merge_rules_monthly.py --apply          # 真正写盘
  python3 merge_rules_monthly.py --apply --month 2026-08
"""
import argparse
import datetime
import os
import re
import shutil

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库"
MAIN_MASTER = os.path.join(ROOT, "裁判规则库.md")          # 全领域主文件
HT_MASTER = os.path.join(ROOT, "合同风险规则库.md")        # 合同风险主文件


def scan_cards(month):
    """扫描指定月份（YYYY-MM）新增的 R-*.md 卡片，返回 [(rule_id, title, rel_path), ...]"""
    cards = []
    for dp, dn, fn in os.walk(ROOT):
        for f in fn:
            if not (re.match(r'R-[A-Z]+-\d+\.md$', f) or re.match(r'R\d+\.md$', f)):
                continue
            p = os.path.join(dp, f)
            try:
                with open(p, encoding="utf-8") as fh:
                    content = fh.read()
            except Exception:
                continue
            m_rid = re.search(r'rule_id:\s*(\S+)', content)
            m_title = re.search(r'title:\s*(.+)', content)
            m_cmonth = re.search(r'created_month:\s*(\S+)', content)
            m_date = re.search(r'date:\s*(\S+)', content)
            m_created = re.search(r'created:\s*(\S+)', content)
            # 归属月份：优先 created_month（卡片创建月，规范化后全量覆盖），
            # 其次 date 前缀，再次 created 前缀（兜底）。
            # 说明：案例卡的 date: 常是「裁判日期」而非创建月，故不能单凭 date: 判定当月新卡。
            month_field = None
            if m_cmonth:
                month_field = m_cmonth.group(1)[:7]
            elif m_date:
                month_field = m_date.group(1)[:7]
            elif m_created:
                month_field = m_created.group(1)[:7]
            if not m_rid or not month_field:
                continue
            if not month_field.startswith(month):
                continue
            rid = m_rid.group(1)
            title = m_title.group(1).strip().strip('"\'') if m_title else f
            rel = os.path.relpath(p, ROOT)
            cards.append((rid, title, rel))
    cards.sort(key=lambda x: x[0])
    return cards


def month_section(month, cards):
    """生成月度索引段（Markdown）"""
    lines = [
        "",
        f"## 月度新增裁判规则卡索引（{month}）",
        "",
        f"> 由 merge_rules_monthly.py 合并（{datetime.date.today().isoformat()}）。当月新增卡片 {len(cards)} 张，索引如下（卡片为权威详情，主文件仅作导航）：",
        "",
        "| rule_id | 标题 | 卡片路径 |",
        "|---------|------|----------|",
    ]
    for rid, title, rel in cards:
        safe_title = title.replace("|", "／")[:60]
        lines.append(f"| {rid} | {safe_title} | `{rel}` |")
    return "\n".join(lines) + "\n"


def append_if_missing(master_path, month, section, apply):
    """幂等追加：主文件已含该月段则跳过"""
    if not os.path.isfile(master_path):
        print(f"  ⚠️ 主文件不存在：{master_path}")
        return False
    with open(master_path, encoding="utf-8") as f:
        content = f.read()
    marker = f"月度新增裁判规则卡索引（{month}）"
    if marker in content:
        print(f"  ⏭️  已含 {month} 索引段，跳过：{os.path.basename(master_path)}")
        return False
    if not content.endswith("\n"):
        content += "\n"
    new_content = content + section
    if not apply:
        n = section.count("| R-")
        print(f"  [dry-run] 将追加 {n} 条索引到：{os.path.basename(master_path)}")
        return False
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = f"{master_path}.bak-{ts}"
    shutil.copy2(master_path, bak)
    if not os.access(master_path, os.W_OK):
        os.chmod(master_path, 0o600)
    tmp = master_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(new_content)
    os.replace(tmp, master_path)
    n = section.count("| R-")
    print(f"  ✅ 已追加 {n} 条到：{os.path.basename(master_path)}（备份 {os.path.basename(bak)}）")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", default=datetime.date.today().strftime("%Y-%m"), help="目标月份 YYYY-MM（默认当月）")
    ap.add_argument("--apply", action="store_true", help="真正写盘（默认 dry-run）")
    args = ap.parse_args()
    month = args.month

    print(f"扫描 {month} 新增裁判规则卡...")
    cards = scan_cards(month)
    print(f"  当月新增卡片：{len(cards)} 张")
    if not cards:
        print("  无新增卡片，无需合并。")
        return 0

    ht_cards = [c for c in cards if c[0].startswith("R-HT-")]
    other_cards = [c for c in cards if not c[0].startswith("R-HT-")]

    print(f"  → 合同风险主文件应合并 R-HT 卡 {len(ht_cards)} 张")
    print(f"  → 全领域主文件应合并其余卡 {len(other_cards)} 张")
    print()

    # 全领域主文件：合并全部当月新卡（或至少 R-HT 之外）
    section_all = month_section(month, cards)
    append_if_missing(MAIN_MASTER, month, section_all, args.apply)

    # 合同风险主文件：合并 R-HT 卡
    if ht_cards:
        section_ht = month_section(month, ht_cards)
        append_if_missing(HT_MASTER, month, section_ht, args.apply)
    else:
        print(f"  ⏭️  当月无 R-HT 卡，合同风险主文件跳过。")

    print("\n完成。")
    return 0


if __name__ == "__main__":
    main()
