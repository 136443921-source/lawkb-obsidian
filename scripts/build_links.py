#!/usr/bin/env python3
"""
Obsidian 双向链接自动建立工具 - 正确版
用法: python3 build_links.py
"""

import os
import re
from pathlib import Path

VAULT = "/Users/chenyouqiang/Documents/LawKB"
EXCLUDE_DIRS = {'.obsidian', '.git', '.trash', 'node_modules'}

# 黑名单：排除无意义标题
BLACKLIST = {
    '证据清单', '法律意见书', '代理词', '质证意见', '庭审提纲',
    '民事判决书', '民事裁定书', '法律检索报告', '案件模板',
    '使用说明', '配置指南', '操作指南', '详细计划',
    '学习笔记', '工作笔记', '其他笔记', '知识库', '规则库',
    '第一部分', '第二部分', '第三部分', '第四部分', '第五部分',
    '第六部分', '第七部分', '第八部分', '第九部分', '第十部分',
    '总览', '索引', '目录', '模板', '报告', '分析', '总结',
    '详细记录', '处理结果', '详细步骤', '处理结果', '详细情况'
}

# 白名单：优先链接的重要关键词
PRIORITY = {
    '民法典', '民事诉讼法', '刑事诉讼法', '行政诉讼法',
    '慈善法', '基金会管理条例', '工伤保险条例', '医疗事故处理条例',
    '交通事故', '工伤', '医疗事故', '医疗损害',
    '担保合同', '借款合同', '劳动合同', '服务合同',
    '厚德基金会', '百益服务中心', '王德明', '罗江辉', '陈长卫'
}

def get_all_files():
    """获取所有 markdown 文件"""
    files = []
    for root, dirs, files_list in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files_list:
            if f.endswith('.md'):
                files.append(os.path.join(root, f))
    return sorted(files)

def get_title(fp):
    """从文件提取标题"""
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()
        # 找第一个 # 标题
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            title = match.group(1).strip()
            # 清理可能的残留
            title = title.replace('[[', '').replace(']]', '')
            return title
        # 否则用文件名
        return os.path.splitext(os.path.basename(fp))[0]
    except:
        return os.path.splitext(os.path.basename(fp))[0]

def build_db(files):
    """构建链接数据库：文件名 -> 标题"""
    db = {}  # filename -> {'title': ..., 'path': ...}
    for fp in files:
        filename = os.path.splitext(os.path.basename(fp))[0]
        title = get_title(fp)
        # 只保留高质量标题
        if len(title) >= 6 and title not in BLACKLIST and not title.startswith('202'):
            db[filename] = {'title': title, 'path': fp}
    return db

def add_links_to_file(fp, db):
    """给单个文件添加双向链接"""
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            content = f.read()
        
        filename = os.path.splitext(os.path.basename(fp))[0]
        modifications = []
        
        # 按标题长度排序（长标题优先，更精确）
        targets = sorted(db.items(), 
                        key=lambda x: (-len(x[1]['title']), -int(any(k in x[1]['title'] for k in PRIORITY))))
        
        # 记录已替换的位置，避免重叠
        replaced_positions = []
        
        for target_fn, info in targets:
            if target_fn == filename:
                continue  # 跳过自己
            
            title = info['title']
            
            # 在内容中查找标题
            idx = 0
            while True:
                pos = content.find(title, idx)
                if pos == -1:
                    break
                
                # 检查这个位置是否已经被替换过
                overlap = False
                for (start, end) in replaced_positions:
                    if start <= pos < end or start < pos + len(title) <= end:
                        overlap = True
                        break
                
                if overlap:
                    idx = pos + 1
                    continue
                
                # 检查前后字符，避免替换已有链接或代码
                before = content[max(0, pos-2):pos]
                after = content[pos+len(title):min(len(content), pos+len(title)+2)]
                
                # 如果前面有 [[ 或后面有 ]]，说明已经在链接中
                if '[[' in before or ']]' in after:
                    idx = pos + 1
                    continue
                
                # 替换
                link_text = f'[[{target_fn}|{title}]]'
                content = content[:pos] + link_text + content[pos+len(title):]
                
                # 记录替换位置（考虑链接长度）
                new_end = pos + len(link_text)
                replaced_positions.append((pos, new_end))
                
                modifications.append((title, target_fn))
                
                # 只替换第一次出现
                break
        
        if modifications:
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return modifications
        
    except Exception as e:
        print(f"  错误: {fp}: {e}")
        return []

def main():
    print("=" * 60)
    print("Obsidian 双向链接自动建立工具")
    print("=" * 60)
    
    # 1. 扫描文件
    print("\n[1/3] 扫描文件...")
    files = get_all_files()
    print(f"  ✓ 找到 {len(files)} 个文件")
    
    # 2. 构建数据库
    print("\n[2/3] 构建链接数据库...")
    db = build_db(files)
    print(f"  ✓ 构建了 {len(db)} 个链接目标")
    
    # 3. 添加链接
    print("\n[3/3] 添加双向链接...")
    total = 0
    log_entries = []
    
    for i, fp in enumerate(files):
        if i % 50 == 0:
            print(f"  进度: {i}/{len(files)}")
        
        filename = os.path.splitext(os.path.basename(fp))[0]
        mods = add_links_to_file(fp, db)
        
        if mods:
            total += len(mods)
            log_entries.append((filename, mods))
            if len(log_entries) <= 10:
                print(f"  ✓ {filename}: {len(mods)} 个链接")
    
    # 4. 写日志
    log_path = os.path.join(VAULT, "双向链接建立日志.md")
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write("---\n")
        f.write("created: 2026-06-26T22:10\n")
        f.write("---\n\n")
        f.write("# 双向链接建立日志\n\n")
        f.write(f"处理时间: {os.popen('date').read().strip()}\n\n")
        f.write(f"共处理: {len(files)} 个文件\n")
        f.write(f"共添加: {total} 个链接\n\n")
        f.write("## 详细记录（前50个文件）\n\n")
        for fn, mods in log_entries[:50]:
            f.write(f"### {fn}\n\n")
            for title, target in mods:
                f.write(f"- {title} → [[{target}]]\n")
            f.write("\n")
    
    print("\n" + "=" * 60)
    print(f"✅ 完成！共添加 {total} 个双向链接")
    print(f"📝 日志: {log_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
