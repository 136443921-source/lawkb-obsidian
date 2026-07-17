#!/usr/bin/env python3
"""
LawKB 双向链接增强脚本 v2.0
功能：扫描新增笔记，提取关键概念，建立 Obsidian 双向链接
用法：python3 build_bidirectional_links.py
"""

import os
import re
import json
from datetime import datetime, timedelta
from pathlib import Path

# ===== 配置 =====
VAULT_PATH = Path("/Users/chenyouqiang/Documents/LawKB")
OUTPUT_REPORT = VAULT_PATH / ".workbuddy" / "automations" / "automation-1783161437473" / "last_run_report.md"
DAYS_BACK = 7  # 扫描最近7天

# 核心法律概念词表（按优先级排序，用于从笔记中识别关键概念）
# 格式：(概念名称, 别名列表, 目标笔记名称)
CONCEPTS = [
    # 行政法相关
    ("行政许可法", ["《行政许可法》", "行政许可"], "行政许可法"),
    ("行政协议", ["行政协议纠纷", "行政协议案件"], "行政协议"),
    ("信赖利益保护", ["信赖利益", "信赖保护原则"], "信赖利益保护"),
    ("行政补偿", ["行政补偿纠纷", "行政补偿案件"], "行政补偿"),
    ("行政赔偿", ["行政赔偿纠纷", "行政赔偿案件", "行政赔偿司法解释"], "行政赔偿"),
    ("国有资产管理", ["国有资产", "行政单位国有资产"], "国有资产管理"),
    
    # 民法典相关
    ("民法典", ["《民法典》", "中华人民共和国民法典"], "中华人民共和国民法典（全文）"),
    ("保证合同", ["保证责任", "一般保证", "连带责任保证"], "保证合同"),
    ("担保合同", ["担保合同纠纷", "担保合同效力"], "担保合同"),
    ("先诉抗辩权", ["先诉抗辩", "补充责任"], "先诉抗辩权"),
    ("最高额担保", ["最高额抵押", "最高额保证"], "最高额担保"),
    ("抵押权", ["抵押", "抵押权实现", "抵押权人"], "抵押权"),
    ("流质条款", ["流押条款", "流质契约"], "流质条款"),
    ("反担保", ["反担保措施"], "反担保"),
    ("租赁合同", ["房屋租赁合同", "租赁纠纷"], "租赁合同"),
    ("诉讼时效", ["诉讼时效中断", "诉讼时效中止"], "诉讼时效"),
    
    # 程序法
    ("民事诉讼法", ["民诉法", "《民事诉讼法》"], "中华人民共和国民事诉讼法"),
    ("行政诉讼法", ["行政诉讼", "行政诉讼案件"], "行政诉讼法"),
    
    # 慈善法相关
    ("慈善法", ["《慈善法》", "中华人民共和国慈善法"], "中华人民共和国慈善法"),
    ("基金会管理条例", ["基金会管理", "基金会合规"], "基金会管理条例"),
    
    # 证据相关
    ("证据三性", ["证据的三性", "真实性合法性关联性"], "证据三性"),
    ("举证责任", ["举证", "举证责任分配"], "举证责任"),
    
    # 其他重要概念
    ("情势变更", ["情势变更原则", "情势变更制度"], "情势变更"),
    ("违约责任", ["违约", "违约金"], "违约责任"),
    ("合同解除", ["解除合同", "法定解除"], "合同解除"),
    ("不当得利", ["不当得利返还"], "不当得利"),
    ("善意取得", ["善意第三人"], "善意取得"),
    ("表见代理", ["表见代理制度"], "表见代理"),
    ("不可抗力", ["不可抗拒力"], "不可抗力"),
    ("合同效力", ["合同无效", "合同有效", "可撤销合同"], "合同效力"),
    ("扶养义务", ["抚养义务", "赡养义务"], "扶养义务"),
    ("婚内财产协议", ["婚内财产", "夫妻财产约定"], "婚内财产协议"),
    ("离婚纠纷", ["离婚案件", "离婚诉讼"], "离婚纠纷"),
    ("股东知情权", ["股东知情权纠纷", "知情权"], "股东知情权"),
]

# 需要创建的概念笔记模板
CONCEPT_TEMPLATE = """---
created: {timestamp}
updated: {timestamp}
tags: [概念, 法律概念]
aliases: [{aliases}]
---

# {title}

## 概念定义

（待补充）

## 相关法条

（待补充）

## 相关案例

（待补充）

## 关联笔记

（待补充）

## 最后更新

- 创建时间：{timestamp}
- 更新时间：{timestamp}
"""


def get_all_md_files(vault_path):
    """获取 vault 内所有 .md 文件（排除 .workbuddy 和 .git）"""
    md_files = []
    for root, dirs, files in os.walk(vault_path):
        # 排除隐藏目录和特定目录
        dirs[:] = [d for d in dirs if not d.startswith('.') or d == '.workbuddy']
        for f in files:
            if f.endswith('.md'):
                full_path = os.path.join(root, f)
                # 排除 .workbuddy 目录下的文件
                if '.workbuddy' not in full_path:
                    md_files.append(full_path)
    return md_files


def get_recent_files(vault_path, days_back=7):
    """获取最近 N 天修改的 .md 文件"""
    cutoff = datetime.now() - timedelta(days=days_back)
    recent = []
    all_files = get_all_md_files(vault_path)
    for fp in all_files:
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(fp))
            if mtime >= cutoff:
                recent.append((fp, mtime))
        except OSError:
            continue
    recent.sort(key=lambda x: x[1], reverse=True)
    return recent


def get_existing_notes(vault_path):
    """获取 vault 内所有笔记的名称（不含扩展名），用于检查目标是否存在"""
    note_names = set()
    all_files = get_all_md_files(vault_path)
    for fp in all_files:
        fname = os.path.splitext(os.path.basename(fp))[0]
        note_names.add(fname)
    return note_names


def extract_concepts_from_text(text, concepts_list):
    """从文本中提取匹配的关键概念，返回 (概念名称, 目标笔记名称) 列表"""
    found = []
    for concept_name, aliases, target_note in concepts_list:
        # 检查概念名称和所有别名
        search_terms = [concept_name] + aliases
        for term in search_terms:
            # 使用正则匹配，避免部分匹配
            pattern = r'(' + re.escape(term) + r')'
            if re.search(pattern, text):
                found.append((concept_name, target_note))
                break  # 找到一个匹配即可
    return list(set(found))  # 去重


def has_wikilink(text, target_note):
    """检查文本中是否已存在指向目标笔记的 wikilink"""
    # 检查 [[target_note]] 或 [[target_note|alias]]
    pattern = r'\[\[' + re.escape(target_note) + r'(\||\]\])'
    if re.search(pattern, text):
        return True
    # 检查 [[alias|target_note]] 
    pattern2 = r'\[\[[^|\]]*\|' + re.escape(target_note) + r'\]\]'
    if re.search(pattern2, text):
        return True
    return False


def add_wikilinks_to_note(note_path, concepts_found):
    """
    在笔记中为正文第一段后添加关键概念链接
    返回实际添加的链接数
    """
    try:
        with open(note_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return 0, str(e)
    
    original_content = content
    added_links = []
    
    # 在笔记末尾的 "---" 前或文件末尾添加概念链接区
    # 先检查是否已有 "## 关联概念" 或类似段落
    concept_section_pattern = r'(## .*?概念.*?\n)(.*?)(?=\n## |\Z)'
    existing_section = re.search(concept_section_pattern, content, re.DOTALL | re.IGNORECASE)
    
    links_to_add = []
    for concept_name, target_note in concepts_found:
        if not has_wikilink(content, target_note):
            links_to_add.append((concept_name, target_note))
    
    if not links_to_add:
        return 0, "no new links needed"
    
    # 构建链接文本
    links_text = "\n## 关联概念\n\n"
    for concept_name, target_note in links_to_add:
        links_text += f"- [[{target_note}|{concept_name}]]\n"
    links_text += "\n"
    
    if existing_section:
        # 在现有概念段落中追加
        # 找到段落结束位置
        section_start = existing_section.start()
        section_content = existing_section.group(0)
        # 在段落末尾（下一个 ## 或文件末尾）前插入
        insert_pos = section_start + len(section_content.strip())
        # 更简单的做法：替换整个段落
        new_section = existing_section.group(1) + links_text
        content = content[:section_start] + new_section + content[section_start + len(existing_section.group(0)):]
    else:
        # 在文件末尾（ before last --- if exists）或文件末尾添加
        # 查找文件末尾的 --- （某些 Obsidian 模板用 --- 分隔）
        frontmatter_end = content.find("---", 3)
        if frontmatter_end > 0 and content[:frontmatter_end].count("---") == 1:
            # 有 frontmatter，在正文末尾添加
            content = content.rstrip() + "\n\n" + links_text
        else:
            content = content.rstrip() + "\n\n" + links_text
    
    # 写回文件
    try:
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return len(links_to_add), None
    except Exception as e:
        return 0, str(e)


def create_concept_note(vault_path, concept_name, target_note, aliases):
    """为目标概念创建笔记（如果不存在）"""
    note_path = vault_path / f"{target_note}.md"
    if note_path.exists():
        return False, "already exists"
    
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")
    aliases_str = ", ".join([f'"{a}"' for a in aliases] + [f'"{concept_name}"'])
    
    content = CONCEPT_TEMPLATE.format(
        timestamp=timestamp,
        aliases=aliases_str,
        title=concept_name
    )
    
    try:
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, None
    except Exception as e:
        return False, str(e)


def main():
    print(f"🔍 开始扫描 LawKB 新增笔记...")
    print(f"📅 扫描范围：最近 {DAYS_BACK} 天")
    print(f"📂 扫描目录：{VAULT_PATH}")
    print()
    
    # 1. 获取最近修改的文件
    recent_files = get_recent_files(VAULT_PATH, DAYS_BACK)
    print(f"📝 找到 {len(recent_files)} 个最近修改的笔记")
    print()
    
    if not recent_files:
        print("✅ 没有新增笔记需要处理。")
        return
    
    # 2. 获取现有笔记名称
    existing_notes = get_existing_notes(VAULT_PATH)
    print(f"📚 Vault 中共有 {len(existing_notes)} 个笔记")
    print()
    
    # 3. 处理每个最近修改的文件
    total_links_added = 0
    total_notes_updated = 0
    total_concepts_created = 0
    link_details = []  # (note_name, concept_name, target_note)
    
    for note_path, mtime in recent_files:
        note_name = os.path.splitext(os.path.basename(note_path))[0]
        print(f"  处理：{note_name}")
        
        try:
            with open(note_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"    ⚠️ 读取失败：{e}")
            continue
        
        # 提取关键概念
        concepts_found = extract_concepts_from_text(text, CONCEPTS)
        
        if not concepts_found:
            print(f"    ℹ️ 未识别到关键概念")
            continue
        
        print(f"    🔎 识别到 {len(concepts_found)} 个关键概念：{', '.join([c[0] for c in concepts_found])}")
        
        # 检查目标笔记是否存在，不存在则创建
        for concept_name, target_note in concepts_found:
            if target_note not in existing_notes:
                # 查找对应的别名
                aliases = []
                for c in CONCEPTS:
                    if c[1] == concept_name or c[2] == target_note:
                        aliases = c[1]
                        break
                created, msg = create_concept_note(VAULT_PATH, concept_name, target_note, aliases if isinstance(aliases, list) else [])
                if created:
                    total_concepts_created += 1
                    existing_notes.add(target_note)
                    print(f"    ✅ 创建概念笔记：{target_note}")
                else:
                    print(f"    ⚠️ 创建概念笔记失败：{msg}")
        
        # 添加 wikilink
        added_count, msg = add_wikilinks_to_note(note_path, concepts_found)
        if added_count > 0:
            total_links_added += added_count
            total_notes_updated += 1
            for concept_name, target_note in concepts_found:
                link_details.append((note_name, concept_name, target_note))
            print(f"    ✅ 添加 {added_count} 个双向链接")
        else:
            print(f"    ℹ️ {msg}")
        print()
    
    # 4. 生成报告
    print("=" * 60)
    print("📊 增强双向链接任务完成报告")
    print("=" * 60)
    print(f"⏰ 执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📚 扫描目录：{VAULT_PATH}")
    print(f"📝 新增/修改笔记数：{len(recent_files)} 个")
    print(f"🔗 建立链接数：{total_links_added} 个")
    print(f"📄 更新笔记数：{total_notes_updated} 个")
    print(f"📊 创建概念笔记数：{total_concepts_created} 个")
    print()
    
    if link_details:
        print("🔗 主要链接关系：")
        for note_name, concept_name, target_note in link_details[:20]:  # 最多显示20条
            print(f"  - [[{note_name}]] → [[{target_note}|{concept_name}]]")
        if len(link_details) > 20:
            print(f"  ...（共 {len(link_details)} 条，显示前20条）")
    print()
    print(f"✅ 任务状态：{'成功' if total_links_added > 0 else '无新增链接'}")
    print("=" * 60)
    
    # 5. 保存报告
    report_content = f"""# 增强双向链接任务报告

**执行时间**：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**扫描目录**：`{VAULT_PATH}`  
**扫描范围**：最近 {DAYS_BACK} 天

---

## 执行摘要

| 指标 | 数值 |
|------|------|
| 新增/修改笔记数 | {len(recent_files)} 个 |
| 建立链接数 | {total_links_added} 个 |
| 更新笔记数 | {total_notes_updated} 个 |
| 创建概念笔记数 | {total_concepts_created} 个 |

---

## 主要链接关系

"""
    for note_name, concept_name, target_note in link_details:
        report_content += f"- [[{note_name}]] → [[{target_note}|{concept_name}]]\n"
    
    report_content += f"\n---\n\n✅ **任务状态**：成功\n"
    
    # 保存报告
    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"\n📄 报告已保存：{OUTPUT_REPORT}")
    except Exception as e:
        print(f"\n⚠️ 报告保存失败：{e}")


if __name__ == "__main__":
    main()
