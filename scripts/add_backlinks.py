#!/usr/bin/env python3
"""
为概念笔记添加反向链接（backlinks）
读取所有笔记中的 [[concept]] 链接，在概念笔记中添加反向链接
"""

import os
import re
from pathlib import Path
from datetime import datetime

VAULT_PATH = Path("/Users/chenyouqiang/Documents/LawKB")

def get_all_md_files(vault_path):
    """获取 vault 内所有 .md 文件"""
    md_files = []
    for root, dirs, files in os.walk(vault_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') or d == '.workbuddy']
        for f in files:
            if f.endswith('.md'):
                fp = os.path.join(root, f)
                if '.workbuddy' not in fp:
                    md_files.append(fp)
    return md_files


def find_all_wikilinks(vault_path):
    """
    扫描所有笔记，找出所有 [[target]] 或 [[target|alias]] 链接
    返回 {target_note: [source_note1, source_note2, ...]}
    """
    link_map = {}  # target -> list of sources
    
    all_files = get_all_md_files(vault_path)
    for fp in all_files:
        source_name = os.path.splitext(os.path.basename(fp))[0]
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            continue
        
        # 查找所有 [[target]] 和 [[target|alias]]
        matches = re.findall(r'\[\[([^|\]]+)(?:\|([^\]]+))?\]\]', content)
        for target, alias in matches:
            target = target.strip()
            if target not in link_map:
                link_map[target] = []
            if source_name not in link_map[target]:
                link_map[target].append(source_name)
    
    return link_map


def add_backlinks_to_concept(concept_path, source_notes):
    """
    在概念笔记的"关联笔记"段落中添加反向链接
    """
    try:
        with open(concept_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return False, str(e)
    
    # 检查是否已有"关联笔记"段落
    section_pattern = r'(## 关联笔记\s*\n)(.*?)(?=\n## |\Z)'
    existing = re.search(section_pattern, content, re.DOTALL)
    
    # 构建反向链接文本
    backlinks_text = ""
    for source in source_notes:
        # 检查是否已存在该反向链接
        if f"[[{source}]]" not in content:
            backlinks_text += f"- [[{source}]]\n"
    
    if not backlinks_text:
        return False, "no new backlinks"
    
    if existing:
        # 在现有段落末尾追加
        section_end = existing.end(1) + len(existing.group(2))
        # 更简单：在 ## 关联笔记 段落末尾追加
        insert_after = existing.group(0)
        new_section = insert_after.rstrip() + "\n" + backlinks_text
        content = content.replace(existing.group(0), new_section)
    else:
        # 在文件末尾追加
        content = content.rstrip() + "\n\n## 关联笔记\n\n" + backlinks_text
    
    try:
        with open(concept_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, None
    except Exception as e:
        return False, str(e)


def main():
    print("🔗 开始添加反向链接...")
    print()
    
    # 1. 找出所有 wikilink 链接关系
    link_map = find_all_wikilinks(VAULT_PATH)
    print(f"📊 找到 {len(link_map)} 个概念有反向链接需求")
    print()
    
    # 2. 为每个概念笔记添加反向链接
    updated_count = 0
    for target_note, source_notes in link_map.items():
        concept_path = VAULT_PATH / f"{target_note}.md"
        if not concept_path.exists():
            continue  # 目标笔记不存在，跳过
        
        success, msg = add_backlinks_to_concept(concept_path, source_notes)
        if success:
            updated_count += 1
            print(f"  ✅ {target_note} ← {len(source_notes)} 个反向链接")
        else:
            if msg != "no new backlinks":
                print(f"  ⚠️ {target_note}：{msg}")
    
    print()
    print(f"📊 更新概念笔记数：{updated_count} 个")
    print(f"✅ 反向链接添加完成")


if __name__ == "__main__":
    main()
