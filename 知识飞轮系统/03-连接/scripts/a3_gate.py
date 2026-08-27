#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
a3_gate.py — 每日摄入 A3「标签 + 枢纽挂接」最小门禁（v1.15）

目标：对本次摄入落盘的新笔记（02-提炼/经验卡片/* 与 06-沉淀/裁判规则库/*）
执行最小门禁，确保「领域标签 + 枢纽挂接」在落盘即完成，避免成为阶段3补链前的孤儿。
- 依子目录映射 GROUPS / RULE_MERGE 领域（与 link_cards_rules.py 对齐）
- 补写缺失领域标签（frontmatter tags，不覆盖既有）
- 在独立段「## 关联（A3门禁·领域枢纽挂接」引用对应 连接枢纽-{域}.md
  （枢纽不存在则标 pending_hub，待阶段3补链生成；不与 stage3 的关联段冲突）
- 幂等：已含标签/已引枢纽则跳过；孤儿预检输出统计

用法：
  $PY a3_gate.py                       # 默认扫今天 created/updated 的新笔记
  $PY a3_gate.py --date 2026-08-23     # 指定日期
  $PY a3_gate.py --all                 # 扫全部（评估/兜底，非日常）
  $PY a3_gate.py --dry-run             # 仅统计不落盘
产物：03-连接/scripts/a3_gate_lastrun.json
"""
import os
import re
import json
from datetime import date

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
CARD_DIR = os.path.join(ROOT, "02-提炼", "经验卡片")
RULE_DIR = os.path.join(ROOT, "06-沉淀", "裁判规则库")
HUB_DIR = os.path.join(ROOT, "03-连接")
OUT = os.path.join(HUB_DIR, "scripts", "a3_gate_lastrun.json")

# ---- 领域映射（与 link_cards_rules.py GROUPS 对齐）----
GROUPS = {
    "慈法合规": ("慈法合规", "连接枢纽-慈法合规"),
    "医疗纠纷": ("人伤法", "连接枢纽-人伤法"),
    "合同文书": ("合同风险", "连接枢纽-合同风险"),
    "程序知识": ("通用", "连接枢纽-通用程序"),
    "法条解读": ("通用", "连接枢纽-通用程序"),
    "学习笔记": ("学习笔记", "连接枢纽-学习笔记"),
    "公众号": ("公众号", "连接枢纽-公众号"),
    "案例": ("案例", "连接枢纽-案例"),
    "慈善组织合同纠纷": ("慈善组织合同", "连接枢纽-慈善组织合同纠纷"),
}
RULE_MERGE = {
    "医疗损害责任纠纷": "医疗纠纷",
    "提供劳务者受害责任纠纷": "医疗纠纷",
    "机动车交通事故责任纠纷": "医疗纠纷",
    "生命权健康权身体权纠纷": "医疗纠纷",
    "建设工程": "合同文书",
    "环境公益诉讼": "慈法合规",
    "公司法": "商事纠纷",
    "慈善": "慈法合规",
}

LINK_HEADING = "## 关联（A3门禁·领域枢纽挂接"

TARGET_DATE = None
ALL_MODE = False


def domain_of_card(cat):
    if cat in GROUPS:
        return GROUPS[cat][0], GROUPS[cat][1]
    return cat, f"连接枢纽-{cat}"


def domain_of_rule(rd):
    if rd in RULE_MERGE:
        key = RULE_MERGE[rd]
        if key in GROUPS:
            return GROUPS[key][0], GROUPS[key][1]
        return key, f"连接枢纽-{key}"
    if rd in GROUPS:
        return GROUPS[rd][0], GROUPS[rd][1]
    return rd, f"连接枢纽-{rd}"


def parse_frontmatter(text):
    if not text.startswith("---"):
        return None, text, [], None, None
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return None, text, [], None, None
    fm = m.group(1)
    body = m.group(2)
    tags = []
    created = updated = None
    in_tags = False
    for line in fm.splitlines():
        if re.match(r"^tags:\s*$", line):
            in_tags = True
            continue
        if in_tags:
            tm = re.match(r"^\s*-\s+(.+)$", line)
            if tm:
                tags.append(tm.group(1).strip())
                continue
            else:
                in_tags = False
        cm = re.match(r"^(created|updated):\s*(.+)$", line)
        if cm:
            val = cm.group(2).strip()
            if cm.group(1) == "created":
                created = val
            else:
                updated = val
    return fm, body, tags, created, updated


def hub_exists(hub_name):
    return os.path.exists(os.path.join(HUB_DIR, f"{hub_name}.md"))


def ensure_link_section(body, hub_name):
    lines = body.splitlines()
    idx = None
    for i, ln in enumerate(lines):
        if ln.startswith(LINK_HEADING):
            idx = i
            break
    if idx is not None:
        seg = []
        j = idx + 1
        while j < len(lines) and not (lines[j].startswith("## ") and not lines[j].startswith("## 关联")):
            seg.append(lines[j])
            j += 1
        if any(hub_name in s for s in seg):
            return body, False
        new_lines = lines[:j] + [f"- 领域枢纽：[[{hub_name}]]"] + lines[j:]
        return "\n".join(new_lines), True
    else:
        new_body = body.rstrip() + f"\n\n{LINK_HEADING} · {date.today().isoformat()})\n- 领域枢纽：[[{hub_name}]]\n"
        return new_body, True


def assemble(fm, body):
    if fm is None:
        return body
    return f"---\n{fm}\n---\n{body}"


def process_file(path, dry, stats):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return
    fm, body, tags, created, updated = parse_frontmatter(text)
    if not ALL_MODE:
        hit = (created and created.startswith(TARGET_DATE)) or (updated and updated.startswith(TARGET_DATE))
        if not hit:
            return
    rel = os.path.relpath(path, CARD_DIR if path.startswith(CARD_DIR) else RULE_DIR)
    parts = rel.split(os.sep)
    subdir = parts[0] if len(parts) > 1 else ""
    if path.startswith(CARD_DIR):
        domain, hub_name = domain_of_card(subdir)
    else:
        domain, hub_name = domain_of_rule(subdir)

    changed = False
    # 1) 标签门禁
    if domain not in tags:
        stats["tag_added"] += 1
        changed = True
        if fm is None:
            text = f"---\ntags:\n  - {domain}\n  - {subdir}\n---\n\n" + text
        else:
            if "tags:" in fm:
                fm2 = fm + f"\n  - {domain}"
            else:
                fm2 = fm + f"\ntags:\n  - {domain}"
            text = f"---\n{fm2}\n---\n{body}"
        fm, body, tags, created, updated = parse_frontmatter(text)
    else:
        stats["tag_ok"] += 1

    # 2) 枢纽挂接门禁
    if hub_exists(hub_name):
        new_body, added = ensure_link_section(body, hub_name)
        if added:
            stats["hub_linked"] += 1
            changed = True
            body = new_body
        else:
            stats["hub_ok"] += 1
    else:
        stats["pending_hub"] += 1
        note = f"\n<!-- a3_pending_hub: {hub_name} -->\n"
        if note.strip() not in body:
            body = body.rstrip() + note
            changed = True

    # 3) 孤儿预检
    has_tag = domain in tags
    has_hub = hub_exists(hub_name) and (hub_name in body)
    if not (has_tag and has_hub):
        stats["gate_failed"].append(os.path.relpath(path, ROOT))

    if changed:
        stats["changed"] += 1
        if not dry:
            with open(path, "w", encoding="utf-8") as f:
                f.write(assemble(fm, body))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    global TARGET_DATE, ALL_MODE
    TARGET_DATE = args.date
    ALL_MODE = args.all

    stats = {
        "run_date": args.date, "all_mode": args.all, "dry_run": args.dry_run,
        "scanned": 0, "tag_ok": 0, "tag_added": 0,
        "hub_ok": 0, "hub_linked": 0, "pending_hub": 0,
        "changed": 0, "gate_failed": [],
    }
    for base in (CARD_DIR, RULE_DIR):
        for root, dirs, files in os.walk(base):
            for fn in files:
                if fn.endswith(".md"):
                    stats["scanned"] += 1
                    process_file(os.path.join(root, fn), args.dry_run, stats)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"[A3 门禁] 扫描 {stats['scanned']} 篇 | 标签已OK {stats['tag_ok']} / 补标签 {stats['tag_added']}"
          f" | 枢纽已OK {stats['hub_ok']} / 新挂接 {stats['hub_linked']} / 待枢纽 {stats['pending_hub']}"
          f" | 改写 {stats['changed']} | 门禁未通过 {len(stats['gate_failed'])}"
          f" | {'DRY-RUN' if args.dry_run else '已落盘'}")
    if stats["gate_failed"]:
        print(f"  门禁未通过（待阶段3建枢纽后二次门禁）: {len(stats['gate_failed'])} 篇")


if __name__ == "__main__":
    main()
