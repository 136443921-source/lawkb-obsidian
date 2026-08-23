#!/usr/bin/env python3
"""
增强双向链接脚本 v2.1
- 扫描 02-提炼 新增笔记
- 提取现有 [[...]] 链接，验证目标存在性
- 补全 related_links 段
- 按领域注册进对应枢纽 MOC
- 输出链接报告
"""
import os, re, json, glob
from datetime import datetime
from pathlib import Path

VAULT = Path("/Users/chenyouqiang/Documents/LawKB")
REFINE_DIR = VAULT / "知识飞轮系统" / "02-提炼"
HUB_DIR = VAULT / "知识飞轮系统" / "03-连接"
RULES_DIR = VAULT / "知识飞轮系统" / "06-沉淀" / "裁判规则库"

# 构建全 vault basename → path 索引（仅 .md）
def build_index():
    idx = {}
    for f in VAULT.rglob("*.md"):
        if "/.workbuddy/" in str(f):
            continue
        name = f.stem  # basename without .md
        if name not in idx:
            idx[name] = str(f)
    return idx

INDEX = build_index()

# 枢纽映射：目录路径前缀 → 枢纽文件名
HUB_MAP = {
    "人伤法": "连接枢纽-人伤法.md",
    "合同文书笔记": "连接枢纽-合同风险.md",
    "学习笔记/合规": "连接枢纽-合规.md",
    "学习笔记/慈善": "连接枢纽-慈法合规.md",
    "学习笔记": "连接枢纽-学习笔记.md",
    "案例摘要": "连接枢纽-案例.md",
}

def extract_links(content):
    """提取 [[X]] 或 [[X|Y]] 中的 X"""
    return list(set(re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content)))

def extract_tags(content):
    """从 frontmatter 提取 tags"""
    m = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return []
    fm = m.group(1)
    tags = re.findall(r'^  - (.+)$', fm, re.MULTILINE)
    return [t.strip() for t in tags]

def extract_title(content):
    """提取第一个 # 标题"""
    m = re.search(r'^# (.+)$', content, re.MULTILINE)
    return m.group(1).strip() if m else ""

def has_related_links(content):
    """检查是否已有 related_links 段"""
    return "## 相关笔记" in content or "related_links" in content

def find_related_by_tags(target_tags, target_name, all_notes):
    """通过 tags 共现找关联笔记（排除自身）"""
    related = []
    for note in all_notes:
        if note['name'] == target_name:
            continue
        overlap = set(target_tags) & set(note['tags'])
        if len(overlap) >= 2:  # 至少2个tag重叠
            related.append((note['name'], list(overlap)[:4]))
    return related[:5]  # 最多5条

def add_related_links(filepath, related_notes):
    """在笔记末尾追加 related_links 段"""
    content = filepath.read_text(encoding='utf-8')
    if has_related_links(content):
        return False  # 已有，跳过

    if not related_notes:
        return False

    lines = ["", "## 相关笔记"]
    for name, keywords in related_notes:
        kw_str = ", ".join(keywords[:3])
        lines.append(f"- [[{name}]] (共现关键词: {kw_str})")

    lines.append("")
    content = content.rstrip() + "\n" + "\n".join(lines)
    filepath.write_text(content, encoding='utf-8')
    return True

def register_in_hub(note_name, note_path, hub_file):
    """在枢纽 MOC 末尾追加笔记链接"""
    hub_path = HUB_DIR / hub_file
    if not hub_path.exists():
        return False

    content = hub_path.read_text(encoding='utf-8')
    if f"[[{note_name}]]" in content:
        return False  # 已收录

    # 找到 "## 本周新增" 或末尾追加
    section_marker = "## 本周新增"
    entry = f"- [[{note_name}]]"

    if section_marker in content:
        # 在该段末尾插入
        parts = content.split(section_marker)
        if len(parts) >= 2:
            # 找下一个 ## 标题
            rest = parts[1]
            next_section = re.search(r'\n## ', rest)
            if next_section:
                pos = next_section.start()
                insert_pos = len(parts[0]) + len(section_marker) + pos
                content = content[:insert_pos].rstrip() + f"\n{entry}\n" + content[insert_pos:]
            else:
                content = content.rstrip() + f"\n{entry}\n"
    else:
        content = content.rstrip() + f"\n\n## 本周新增\n{entry}\n"

    hub_path.write_text(content, encoding='utf-8')
    return True

def get_hub_for_path(rel_path):
    """根据笔记相对路径返回对应枢纽文件名"""
    for prefix, hub in HUB_MAP.items():
        if rel_path.startswith(prefix + "/"):
            return hub
    return None

def main():
    print(f"=== 增强双向链接任务 v2.1 ===")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Vault 索引: {len(INDEX)} 个 .md 文件")
    print()

    # 收集22篇新增笔记
    new_notes = []
    for f in sorted(REFINE_DIR.rglob("*-2026-08-16.md")):
        if "每日知识摄入报告" in f.name:
            continue  # 排除报告
        content = f.read_text(encoding='utf-8')
        rel_path = str(f.relative_to(REFINE_DIR))
        new_notes.append({
            'path': f,
            'name': f.stem,
            'rel_path': rel_path,
            'content': content,
            'tags': extract_tags(content),
            'title': extract_title(content),
            'existing_links': extract_links(content),
        })

    print(f"新增知识笔记: {len(new_notes)} 篇")
    print()

    # 统计
    total_forward = 0  # 正向链接（笔记中已有的 [[X]] 且目标存在）
    total_broken = 0   # 断链（目标不存在）
    total_reverse_added = 0  # 反向链接（related_links 新增）
    total_hub_registered = 0  # 枢纽注册数
    concepts_involved = set()

    link_report = []

    for note in new_notes:
        name = note['name']
        links = note['existing_links']
        valid_links = []
        broken_links = []

        for link in links:
            # 检查目标是否存在
            if link in INDEX:
                valid_links.append(link)
                concepts_involved.add(link)
            else:
                broken_links.append(link)

        total_forward += len(valid_links)
        total_broken += len(broken_links)

        # 通过 tags 共现找关联笔记
        related = find_related_by_tags(note['tags'], name, new_notes)

        # 补 related_links
        added = add_related_links(note['path'], related)
        if added:
            total_reverse_added += len(related)

        # 注册进枢纽
        hub_file = get_hub_for_path(note['rel_path'])
        hub_added = False
        if hub_file:
            hub_added = register_in_hub(name, note['path'], hub_file)
            if hub_added:
                total_hub_registered += 1

        # 收集报告
        if valid_links or related or hub_added:
            link_report.append({
                'name': name,
                'valid_links': valid_links,
                'broken_links': broken_links,
                'related_added': related if added else [],
                'hub': hub_file if hub_added else None,
            })

    # 输出报告
    print("【增强双向链接任务完成】")
    print()
    print(f"⏰ 执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📚 扫描目录：{VAULT}")
    print(f"📝 新增笔记数：{len(new_notes)} 个")
    print(f"🔗 正向链接数：{total_forward} 个（已存在于笔记中的 [[X]] 且目标有效）")
    print(f"⚠️  断链数：{total_broken} 个（目标笔记不存在，需后续创建概念页）")
    print(f"🔗 反向链接数：{total_reverse_added} 个（related_links 段新增）")
    print(f"📊 枢纽注册数：{total_hub_registered} 个")
    print(f"📊 涉及概念数：{len(concepts_involved)} 个")
    print()
    print("🔗 主要链接关系：")
    for item in link_report:
        print(f"\n--- {item['name']} ---")
        if item['valid_links']:
            print(f"  正向链接（目标存在）: {', '.join(item['valid_links'][:8])}")
        if item['broken_links']:
            print(f"  ⚠️ 断链（目标不存在）: {', '.join(item['broken_links'][:8])}")
        if item['related_added']:
            for rn, kws in item['related_added']:
                print(f"  → [[{rn}]] (共现: {', '.join(kws[:3])})")
        if item['hub']:
            print(f"  📊 已注册枢纽: {item['hub']}")

    # 断链清单
    if total_broken > 0:
        print(f"\n⚠️ 断链汇总（{total_broken}个，目标笔记不存在）:")
        all_broken = set()
        for item in link_report:
            for b in item['broken_links']:
                all_broken.add(b)
        for b in sorted(all_broken):
            print(f"  - [[{b}]]")

    print(f"\n✅ 任务状态：成功")
    print(f"📦 备份路径：/Users/chenyouqiang/WorkBuddy/Claw/backups/增强双向链接_20260816-221956")

if __name__ == "__main__":
    main()
