#!/usr/bin/env python3
"""
修复 LawKB 笔记 frontmatter 中的空标签 v1.0
功能：移除 frontmatter 中的空字符串标签
作者：小强律师数字分身
日期：2026-06-27
"""

import os
import re
from datetime import datetime
from pathlib import Path
import yaml

# 配置
LAWKB_ROOT = "/Users/chenyouqiang/Documents/LawKB"

def fix_empty_tags(content):
    """修复 frontmatter 中的空标签"""
    pattern = r"^---\s*\n(.*?)\n---"
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        return content, False
    
    fm_text = match.group(1)
    
    try:
        fm = yaml.safe_load(fm_text)
    except:
        return content, False
    
    if not fm or "tags" not in fm:
        return content, False
    
    # 修复空标签
    if fm["tags"]:
        original_count = len(fm["tags"])
        # 过滤掉空字符串和None
        fm["tags"] = [tag for tag in fm["tags"] if tag and str(tag).strip()]
        new_count = len(fm["tags"])
        
        if original_count!= new_count:
            # 重新生成 frontmatter
            new_fm_text = yaml.dump(fm, allow_unicode=True, sort_keys=False)
            new_content = f"---\n{new_fm_text}---\n"
            
            # 替换原有 frontmatter
            content = re.sub(pattern, new_content, content, flags=re.DOTALL)
            
            return content, True
    
    return content, False

def scan_and_fix():
    """扫描并修复所有笔记"""
    fixed_files = []
    error_files = []
    
    # 扫描所有 .md 文件
    for root, dirs, files in os.walk(LAWKB_ROOT):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                
                try:
                    # 读取文件内容
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # 修复空标签
                    new_content, fixed = fix_empty_tags(content)
                    
                    if fixed:
                        # 写回文件
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        
                        fixed_files.append(file_path)
                    
                except Exception as e:
                    error_files.append({
                        "file": file_path,
                        "error": str(e),
                    })
    
    return fixed_files, error_files

def main():
    """主函数"""
    print("开始修复 LawKB 笔记中的空标签...")
    print(f"扫描目录：{LAWKB_ROOT}")
    
    fixed_files, error_files = scan_and_fix()
    
    print(f"\n修复完成！")
    print(f"✅ 已修复：{len(fixed_files)} 个文件")
    print(f"❌ 修复失败：{len(error_files)} 个文件")
    
    if fixed_files:
        print(f"\n已修复文件列表：")
        for file in fixed_files[:10]:  # 只显示前10个
            print(f"  - {file}")
        if len(fixed_files) > 10:
            print(f"  ... 还有 {len(fixed_files) - 10} 个文件")
    
    if error_files:
        print(f"\n修复失败文件列表：")
        for item in error_files:
            print(f"  - {item['file']}")
            print(f"    错误：{item['error']}")

if __name__ == "__main__":
    main()
