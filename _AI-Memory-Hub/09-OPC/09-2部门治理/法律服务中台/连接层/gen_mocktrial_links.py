# -*- coding: utf-8 -*-
"""
模拟法庭治理文档小圈层 · 轻量专属连接器 (v1.0)
- 用途：仅对「模拟法庭治理文档小圈层」(白名单) 做自动互链 + 自建专属枢纽，
       与 link_cards_rules.py(v3.2) 主脚本完全独立，不碰法律领域连接层、不污染其图谱。
- 成员：文件名明确含"模拟法庭"的 7 份治理文档（白名单，精确圈定，不扫全目录）。
- 链接约定：Obsidian [[文件名(不含.md)]] wiki 链接。
- 幂等 & 安全：
  * 自动段以稳定前缀 `## 关联（模拟法庭治理连接层自动补链` 写入，重跑整体替换（按前缀切分），
    不破坏既有手工链接（含备忘录 `## 相关笔记` 手工双链段）。
  * frontmatter 完全不动（不剥离 related:、不新增 related_links:）。
  * 仅对 body 按稳定前缀切分后在末尾追加/更新自动段。
- 统计：写 mocktrial_links_lastrun.json（机器可读）；打印 LINK_STAT 单行。
- 用法：python gen_mocktrial_links.py [--dry-run | --apply]
       默认（无参）= dry-run。
"""
import os, re, json, sys, datetime

BASE = "/Users/chenyouqiang/Documents/LawKB/_AI-Memory-Hub/09-OPC/09-2部门治理/法律服务中台"
HERE = os.path.dirname(os.path.abspath(__file__))
DATE = datetime.date.today().strftime("%Y-%m-%d")

DRY = "--dry-run" in sys.argv or (not any(a in sys.argv for a in ("--apply", "--dry-run")))
APPLY = "--apply" in sys.argv

MARK = "## 关联（模拟法庭治理连接层自动补链"
HUB_NAME = "连接枢纽-模拟法庭治理"

# 白名单：模拟法庭治理小圈层（文件名明确含"模拟法庭"的治理文档，精确圈定，不卷其它业务试点）
MEMBERS = [
    "PROJ-模拟法庭科室.md",
    "模拟法庭管理系统备忘录.md",
    "SOP/SOP-BUS-03_模拟法庭红蓝对抗推演.md",
    "SOP/SOP-BUS-04_模拟法庭科室治理.md",
    "SOP/SOP-BUS-09_模拟法庭设备接入.md",
    "SOP/SOP-BUS-10_驾驶舱复盘_模拟法庭.md",
    "模拟法庭设备运行管理制度.md",
]

def base_name(p):
    return os.path.splitext(os.path.basename(p))[0]

def read_file(path):
    with open(path, encoding="utf-8") as f:
        return f.read()

def split_body(raw):
    """按稳定前缀切分：保留前缀之前所有内容（含 frontmatter 与手工段），丢弃旧自动段。"""
    idx = raw.find(MARK)
    if idx != -1:
        line_start = raw.rfind("\n", 0, idx) + 1  # 回到该段行首
        return raw[:line_start].rstrip() + "\n"
    return raw.rstrip() + "\n"

def build_auto_section(hub, others):
    lines = [f"{MARK} · {DATE})"]
    lines.append(f"- 领域枢纽：[[{hub}]]")
    lines.append("- 同域互链：")
    for i in range(0, len(others), 4):
        lines.append("  - " + " · ".join(f"[[{c}]]" for c in others[i:i + 4]))
    return "\n".join(lines) + "\n"

def write_member(path, raw, hub, others):
    body = split_body(raw)
    auto = build_auto_section(hub, others)
    new_raw = body.rstrip() + "\n\n" + auto
    if DRY:
        print(f"  [DRY-RUN] 计划写入: {os.path.relpath(path, BASE)}")
        print("    " + auto.replace("\n", "\n    ").rstrip())
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_raw)

def build_hub_page(member_bases):
    L = ["---", f"title: {HUB_NAME}", "type: 连接枢纽（模拟法庭治理小圈层）",
         f"generated_by: 模拟法庭治理连接层({DATE})", f"created: {DATE}T22:00",
         "tags:", "  - 连接枢纽", "  - 模拟法庭治理", "---", "",
         f"# {HUB_NAME}", "",
         f"> 本页为「模拟法庭治理文档小圈层」专属连接枢纽（MOC），由轻量连接器于 {DATE} 自动生成。",
         f"> 共挂载 {len(member_bases)} 份模拟法庭治理文档，双向链接已自动建立。",
         "> 与法律领域连接层（link_cards_rules.py）完全独立，不污染其图谱。",
         "", "## 小圈层成员", ""]
    for b in member_bases:
        L.append(f"- [[{b}]]")
    L.append("")
    return "\n".join(L)

def main():
    full = [os.path.join(BASE, m) for m in MEMBERS]
    missing = [m for m, p in zip(MEMBERS, full) if not os.path.isfile(p)]
    if missing:
        print(f"[ERROR] 白名单文件缺失，请核对: {missing}")
        sys.exit(1)

    bases = [base_name(p) for p in full]
    mode = "DRY-RUN" if DRY else "APPLY"
    print(f"=== 模拟法庭治理连接层 v1.0 [{mode}] ===")
    print(f"成员数: {len(bases)}")

    for p, b in zip(full, bases):
        others = [x for x in bases if x != b]
        raw = read_file(p)
        write_member(p, raw, HUB_NAME, others)
        print(f"  处理: {b} (互链 {len(others)} 个)")

    hub_raw = build_hub_page(bases)
    hub_path = os.path.join(BASE, HUB_NAME + ".md")
    if DRY:
        print(f"[DRY-RUN] 计划生成枢纽页: {HUB_NAME}.md ({len(bases)} 成员)")
    else:
        with open(hub_path, "w", encoding="utf-8") as f:
            f.write(hub_raw)
        print(f"生成枢纽页: {HUB_NAME}.md")

    stat = {"date": DATE, "mode": "dry-run" if DRY else "apply",
            "members": bases, "hub": HUB_NAME, "member_count": len(bases)}
    if not DRY:
        with open(os.path.join(HERE, "mocktrial_links_lastrun.json"), "w", encoding="utf-8") as f:
            json.dump(stat, f, ensure_ascii=False, indent=1)
    print("LINK_STAT " + json.dumps(stat, ensure_ascii=False))
    if DRY:
        print("⚠️ DRY-RUN：以上为计划，未写入任何文件")

if __name__ == "__main__":
    main()
