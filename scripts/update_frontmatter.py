#!/usr/bin/env python3
"""
LawKB 笔记 frontmatter 批量更新脚本 v1.0
功能：批量更新 LawKB 笔记，添加标准化的 frontmatter 字段
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
REPORT_FILE = os.path.join(LAWKB_ROOT, "知识库/frontmatter批量更新报告.md")

# 知识成熟度推断规则
MATURITY_RULES = {
    "🌱种子": ["初学", "了解", "入门", "基础", "draft"],
    "🌿成长": ["掌握", "熟悉", "熟练", "review"],
    "🌳核心": ["精通", "专家", "完整", "complete", "核心", "重要"],
}

def has_frontmatter(content):
    """检查笔记是否有 frontmatter"""
    pattern = r"^---\s*\n(.*?)\n---"
    match = re.search(pattern, content, re.DOTALL)
    return match is not None

def extract_frontmatter(content):
    """提取笔记的 frontmatter"""
    pattern = r"^---\s*\n(.*?)\n---"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        try:
            return yaml.safe_load(match.group(1))
        except:
            return {}
    return None

def update_frontmatter(content, file_path):
    """更新笔记的 frontmatter"""
    # 提取现有 frontmatter
    existing_fm = extract_frontmatter(content)
    
    # 构建新的 frontmatter
    new_fm = {}
    
    # 保留现有字段
    if existing_fm:
        new_fm = existing_fm.copy()
    
    # 添加/更新必填字段
    file_name = os.path.basename(file_path)
    title = file_name.replace(".md", "")
    
    if "title" not in new_fm:
        new_fm["title"] = title
    
    if "created" not in new_fm:
        # 尝试从文件修改时间推断
        mtime = os.path.getmtime(file_path)
        new_fm["created"] = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    
    if "updated" not in new_fm:
        new_fm["updated"] = datetime.now().strftime("%Y-%m-%d")
    
    if "tags" not in new_fm:
        new_fm["tags"] = infer_tags(file_path, content)
    
    if "maturity" not in new_fm:
        new_fm["maturity"] = infer_maturity(file_path, content)
    
    # 添加可选字段（如果不存在）
    if "source" not in new_fm:
        new_fm["source"] = ""
    
    if "related" not in new_fm:
        new_fm["related"] = []
    
    if "last_review" not in new_fm:
        new_fm["last_review"] = ""
    
    if "review_interval" not in new_fm:
        new_fm["review_interval"] = infer_review_interval(new_fm["maturity"])
    
    if "difficulty" not in new_fm:
        new_fm["difficulty"] = 3
    
    if "importance" not in new_fm:
        new_fm["importance"] = 3
    
    if "status" not in new_fm:
        new_fm["status"] = "draft"
    
    # 生成新的 frontmatter 文本
    new_fm_text = yaml.dump(new_fm, allow_unicode=True, sort_keys=False)
    new_content = f"---\n{new_fm_text}---\n\n"
    
    # 如果原有内容有 frontmatter，替换它
    if has_frontmatter(content):
        pattern = r"^---\s*\n.*?\n---\s*\n"
        content = re.sub(pattern, new_content, content, flags=re.DOTALL)
    else:
        # 如果没有 frontmatter，添加到开头
        content = new_content + content
    
    return content, new_fm

def infer_tags(file_path, content):
    """根据文件路径和内容推断标签"""
    tags = []
    
    # 根据路径推断
    if "法律法规库" in file_path:
        tags.append("法条")
    elif "案例库" in file_path:
        tags.append("案例")
    elif "文书模板库" in file_path:
        tags.append("文书模板")
    elif "执业技能库" in file_path:
        tags.append("实务技巧")
    
    # 根据内容推断
    content_lower = content.lower()
    if "合同" in content:
        tags.append("合同")
    if "诉讼" in content or "庭审" in content:
        tags.append("诉讼")
    if "慈善" in content or "基金会" in content:
        tags.append("慈善组织")
    if "人伤" in content or "工伤" in content or "交通事故" in content:
        tags.append("人伤")
    
    # 过滤掉None值和空字符串
    tags = [str(tag).strip() for tag in tags if tag is not None and str(tag).strip()]
    
    return list(set(tags))  # 去重

def infer_maturity(file_path, content):
    """根据文件路径和内容推断知识成熟度"""
    # 根据路径推断
    if "最佳实践库" in file_path or "核心" in file_path:
        return "🌳核心"
    if "成长" in file_path or "熟练" in file_path:
        return "🌿成长"
    
    # 根据内容推断
    content_lower = content.lower()
    for maturity, keywords in MATURITY_RULES.items():
        for keyword in keywords:
            if keyword in content_lower:
                return maturity
    
    # 默认返回种子
    return "🌱种子"

def infer_review_interval(maturity):
    """根据成熟度推断复习间隔"""
    if maturity == "🌱种子":
        return 7
    elif maturity == "🌿成长":
        return 14
    elif maturity == "🌳核心":
        return 30
    else:
        return 7

def scan_and_update():
    """扫描并更新所有笔记"""
    updated_files = []
    skipped_files = []
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
                    
                    # 更新 frontmatter
                    new_content, new_fm = update_frontmatter(content, file_path)
                    
                    # 写回文件
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    
                    updated_files.append({
                        "file": file_path,
                        "title": new_fm.get("title", ""),
                        "maturity": new_fm.get("maturity", ""),
                        "tags": new_fm.get("tags", []),
                    })
                    
                except Exception as e:
                    error_files.append({
                        "file": file_path,
                        "error": str(e),
                    })
    
    return updated_files, skipped_files, error_files

def generate_report(updated_files, skipped_files, error_files):
    """生成更新报告"""
    report = f"""# LawKB frontmatter 批量更新报告

**更新时间**：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**扫描目录**：{LAWKB_ROOT}

---

## 更新概览

- ✅ 已更新：{len(updated_files)} 个文件
- ⏭️ 已跳过：{len(skipped_files)} 个文件
- ❌ 更新失败：{len(error_files)} 个文件

---

## 已更新文件列表

"""
    
    for item in updated_files:
        # 过滤掉None值，处理tags为None的情况
        if item['tags'] is None:
            tags_str = "（无标签）"
        else:
            tags = [str(tag) for tag in item['tags'] if tag is not None]
            tags_str = ', '.join(tags) if tags else "（无标签）"
        
        report += f"""### {item['title']}
- **文件路径**：{item['file']}
- **知识成熟度**：{item['maturity']}
- **标签**：{tags_str}

"""
    
    if error_files:
        report += "\n---\n\n## 更新失败文件列表\n\n"
        for item in error_files:
            report += f"- **文件路径**：{item['file']}\n  **错误信息**：{item['error']}\n\n"
    
    report += f"\n---\n\n**报告生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    return report

def main():
    """主函数"""
    print("开始扫描 LawKB 笔记...")
    print(f"扫描目录：{LAWKB_ROOT}")
    
    updated_files, skipped_files, error_files = scan_and_update()
    
    print(f"\n更新完成！")
    print(f"✅ 已更新：{len(updated_files)} 个文件")
    print(f"⏭️ 已跳过：{len(skipped_files)} 个文件")
    print(f"❌ 更新失败：{len(error_files)} 个文件")
    
    # 生成报告
    report = generate_report(updated_files, skipped_files, error_files)
    
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"\n📋 更新报告已保存至：{REPORT_FILE}")

if __name__ == "__main__":
    main()
