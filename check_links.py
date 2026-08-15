#!/usr/bin/env python3
"""
Obsidian 链接检查工具（修复版 v3）
功能：
1. 识别孤立笔记（没有任何双向链接的笔记）
2. 识别断链（链接到不存在的页面）
3. 识别链接数量过少的笔记
4. 生成链接检查报告

用法:
  python3 check_links.py            # 全量检查（检查所有文件）
  python3 check_links.py -i        # 增量检查（只检查最近7天内修改的文件）
  python3 check_links.py -i -d 3   # 增量检查（检查最近3天内修改的文件）
"""

import os
import re
import sys
import time
import argparse
from datetime import datetime, timedelta

# 知识飞轮系统本体路径（2026-08-02 路径收敛：原 xiaoqianglawkb 镜像库已于 2026-07-14 废弃，
# 此脚本原硬编码扫废弃库会产生失真断链报告；现指向飞轮本体，与 03-连接/ 其余脚本口径一致）
VAULT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"

def get_all_files():
    """获取所有 Markdown 文件"""
    md_files = []
    for root, dirs, files in os.walk(VAULT):
        # 跳过 .obsidian 和 .trash 目录
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if file.endswith('.md'):
                md_files.append(os.path.join(root, file))
    
    return md_files

def get_recent_files(days=7):
    """获取最近 N 天内修改的文件"""
    all_files = get_all_files()
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    
    recent_files = []
    for fp in all_files:
        try:
            mtime = os.path.getmtime(fp)
            if mtime >= cutoff_time:
                recent_files.append(fp)
        except:
            pass
    
    return recent_files

def extract_links(file_path):
    """提取文件中的所有双向链接（修复版 v4）"""
    links = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 方法1：匹配简单的 [[链接]] 或 [[链接|别名]]
            # 使用非贪婪匹配，匹配最内层的链接
            # 先找到所有 [[...]]，然后提取链接名
            pattern = r'\[\[([^\[\]]+?)\]\]'
            matches = re.findall(pattern, content)
            
            for match in matches:
                # 如果有 | 别名，只取 | 前面的部分
                if '|' in match:
                    target = match.split('|')[0].strip()
                else:
                    target = match.strip()
                # 2026-08-13 修复③：剥离表格内转义反斜杠（`[[路径\|别名]]` 写法 → 目标为 `路径`），
                # 避免 `03-连接/知识图谱-2026-07.html\` 带反斜杠误判断链。
                target = target.replace('\\', '').strip()
                
                # 移除 # 开头的标题链接（如 [[页面#标题]]）
                if '#' in target:
                    target = target.split('#')[0].strip()
                
                if target:  # 确保不是空的
                    links.append(target)
    
    except Exception as e:
        print(f"  错误: 无法读取文件 {file_path}: {e}")
    
    return links

def is_placeholder_link(name):
    """判断是否为机器生成噪声/模板占位符链接（2026-08-13 新增，与 kg_scan 脏名护栏对齐）。
    返回 True 表示该链接不应计入知识断链：
    - self.md-YYYYMMDD 快照示意链接（概念页自动生成遗留）
    - 模板占位符：经验卡片-XXX / 裁判规则-Rxxx / ... / x / wikilink / 案件笔记名
    """
    if not name:
        return True
    if re.match(r'^self\.md-\d{8}$', name):
        return True
    PLACEHOLDERS = {'经验卡片-XXX', '裁判规则-Rxxx', '...', 'x', 'wikilink', '案件笔记名'}
    if name in PLACEHOLDERS:
        return True
    if name.endswith('-XXX') or name.endswith('-Rxxx'):
        return True
    return False


def check_links(files):
    """检查链接"""
    # 构建文件名字典（文件名 -> 文件路径）
    filename_to_path = {}
    for fp in get_all_files():
        filename = os.path.splitext(os.path.basename(fp))[0]
        filename_to_path[filename] = fp
    
    # 检查结果
    isolated_notes = []  # 孤立笔记
    broken_links = []    # 断链
    low_links_notes = [] # 链接数量过少的笔记
    
    # meta 报告目录（孤立笔记检测报告、知识库压缩去重报告）内含大量示例/历史断链链接，
    # 不扫描其作为源，避免把报告自身的示例链接误计为本体断链（会造成假断链累积）。
    META_SKIP = {"孤立笔记检测报告", "知识库压缩去重报告"}
    for fp in files:
        if any(meta in fp for meta in META_SKIP):
            continue
        filename = os.path.splitext(os.path.basename(fp))[0]
        links = extract_links(fp)
        
        # 检查是否为孤立笔记
        if len(links) == 0:
            # 检查是否有其他文件链接到它
            is_isolated = True
            for other_fp in get_all_files():
                if other_fp == fp:
                    continue
                # 2026-08-13 修复④：反向链接检查同样跳过 META_SKIP 报告目录——
                # 否则「链接检查报告.md」自身列出的 [[孤立笔记]] 会让孤立笔记被误判为"有人链接"，
                # 导致孤立计数在 0 与真实值之间逐轮交替（自污染）。
                if any(meta in other_fp for meta in META_SKIP):
                    continue
                
                other_links = extract_links(other_fp)
                if filename in other_links:
                    is_isolated = False
                    break
            
            if is_isolated:
                isolated_notes.append((filename, fp))
        
        # 检查链接数量是否过少
        if 0 < len(links) <= 2:
            low_links_notes.append((filename, fp, len(links)))
        
        # 检查断链
        for link in links:
            # Obsidian 允许 [[路径/名称]] 路径式 wikilink，按 basename 解析（与 kg_scan/resolve_broken_links 口径对齐，避免路径式链接误判为断链）
            # 2026-08-13 修复①：改用"仅剥 .md 后缀"而非 splitext——splitext 按最后一个点分割，
            # 会把含版本号/点号的文件名（如 `小强律师数字分身系统 3.0  使用指导手册`、`self.md-20260805`）
            # 中间的点误当扩展名，导致真实存在的文件被误报为断链。
            # 2026-08-13 修复②：对齐 kg_scan 口径——剥 .html/.png 等非 md 扩展名（文件型链接不视为笔记断链）；
            # 跳过机器生成噪声/模板占位符链接（self.md-YYYYMMDD 快照示意链接、XXX/Rxxx/.../x/wikilink/案件笔记名 占位符），
            # 与 kg_scan/resolve_broken_links 的脏名护栏一致，避免将模板示例误计为知识断链。
            norm = os.path.basename(link)
            if norm.endswith('.md'):
                norm = norm[:-3]
            elif norm.endswith(('.html', '.htm', '.png', '.jpg', '.pdf')):
                norm = None  # 文件型链接不计入笔记断链
            if norm is None:
                continue
            if norm not in filename_to_path and not is_placeholder_link(norm):
                broken_links.append((filename, fp, link))
    
    return isolated_notes, broken_links, low_links_notes

def generate_report(isolated_notes, broken_links, low_links_notes, output_path):
    """生成链接检查报告"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("---\n")
        f.write(f"created: {datetime.now().strftime('%Y-%m-%dT%H:%M')}\n")
        f.write("---\n\n")
        
        f.write("# 链接检查报告\n\n")
        f.write(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## 检查结果概览\n\n")
        f.write(f"- 孤立笔记数量: {len(isolated_notes)}\n")
        f.write(f"- 断链数量: {len(broken_links)}\n")
        f.write(f"- 链接数量过少的笔记数量: {len(low_links_notes)}\n\n")
        
        # 孤立笔记
        f.write("## 孤立笔记（没有任何双向链接的笔记）\n\n")
        if len(isolated_notes) == 0:
            f.write("✅ 无孤立笔记\n\n")
        else:
            for filename, fp in isolated_notes[:50]:  # 只显示前50个
                rel_path = os.path.relpath(fp, VAULT)
                f.write(f"- [[{filename}]] (`{rel_path}`)\n")
            
            if len(isolated_notes) > 50:
                f.write(f"\n... 还有 {len(isolated_notes) - 50} 个孤立笔记未显示\n\n")
        
        f.write("\n")
        
        # 断链
        f.write("## 断链（链接到不存在的页面）\n\n")
        if len(broken_links) == 0:
            f.write("✅ 无断链\n\n")
        else:
            # 按源文件分组
            broken_by_source = {}
            for source_filename, source_fp, target in broken_links:
                if source_filename not in broken_by_source:
                    broken_by_source[source_filename] = []
                broken_by_source[source_filename].append(target)
            
            for source_filename, targets in list(broken_by_source.items())[:50]:  # 只显示前50个
                f.write(f"### {source_filename}\n\n")
                for target in targets:
                    f.write(f"- [[{target}]] (不存在)\n")
                f.write("\n")
            
            if len(broken_by_source) > 50:
                f.write(f"... 还有 {len(broken_by_source) - 50} 个源文件的断链未显示\n\n")
        
        # 链接数量过少的笔记
        f.write("## 链接数量过少的笔记（1-2个链接）\n\n")
        if len(low_links_notes) == 0:
            f.write("✅ 无链接数量过少的笔记\n\n")
        else:
            for filename, fp, link_count in low_links_notes[:50]:  # 只显示前50个
                rel_path = os.path.relpath(fp, VAULT)
                f.write(f"- [[{filename}]] ({link_count} 个链接) (`{rel_path}`)\n")
            
            if len(low_links_notes) > 50:
                f.write(f"\n... 还有 {len(low_links_notes) - 50} 个笔记未显示\n\n")
        
        f.write("\n")
        
        # 修复建议
        f.write("## 修复建议\n\n")
        
        if len(isolated_notes) > 0:
            f.write("### 孤立笔记修复建议\n\n")
            f.write("1. 为孤立笔记添加相关链接（链接到相关概念、案例、法条）\n")
            f.write("2. 在相关笔记中添加指向孤立笔记的链接\n")
            f.write("3. 如果孤立笔记不再需要，考虑删除或归档\n\n")
        
        if len(broken_links) > 0:
            f.write("### 断链修复建议\n\n")
            f.write("1. 检查断链是否拼写错误，修正链接目标\n")
            f.write("2. 如果链接目标已删除，移除或更新链接\n")
            f.write("3. 如果链接目标尚未创建，考虑创建该页面\n\n")
        
        if len(low_links_notes) > 0:
            f.write("### 链接数量过少的笔记修复建议\n\n")
            f.write("1. 为笔记添加更多相关链接（至少3-5个）\n")
            f.write("2. 在相关笔记中添加指向该笔记的链接\n")
            f.write("3. 考虑是否需要扩展笔记内容，增加知识点\n\n")

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Obsidian 链接检查工具')
    parser.add_argument('-i', '--incremental', action='store_true', help='增量检查（只检查最近修改的文件）')
    parser.add_argument('-d', '--days', type=int, default=7, help='增量检查的天数（默认7天）')
    args = parser.parse_args()
    
    print("=" * 60)
    print("Obsidian 链接检查工具（修复版 v3）")
    if args.incremental:
        print(f"模式：增量检查（检查最近 {args.days} 天内修改的文件）")
    else:
        print("模式：全量检查（检查所有文件）")
    print("=" * 60)
    
    # 1. 获取文件列表
    print("\n[1/3] 获取文件列表...")
    if args.incremental:
        files = get_recent_files(args.days)
        print(f"  ✓ 找到 {len(files)} 个最近 {args.days} 天内修改的文件")
    else:
        files = get_all_files()
        print(f"  ✓ 找到 {len(files)} 个文件")
    
    # 2. 检查链接
    print("\n[2/3] 检查链接...")
    isolated_notes, broken_links, low_links_notes = check_links(files)
    print(f"  ✓ 发现 {len(isolated_notes)} 个孤立笔记")
    print(f"  ✓ 发现 {len(broken_links)} 个断链")
    print(f"  ✓ 发现 {len(low_links_notes)} 个链接数量过少的笔记")
    
    # 3. 生成报告（输出至 03-连接/孤立笔记检测报告/ 与历史报告同目录，避免污染本体根）
    print("\n[3/3] 生成链接检查报告...")
    report_dir = os.path.join(VAULT, "03-连接", "孤立笔记检测报告")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "链接检查报告.md")
    generate_report(isolated_notes, broken_links, low_links_notes, report_path)
    print(f"  ✓ 报告已生成: {report_path}")
    
    # 4. 输出摘要
    print("\n" + "=" * 60)
    print("✅ 检查完成！")
    print(f"  - 孤立笔记: {len(isolated_notes)} 个")
    print(f"  - 断链: {len(broken_links)} 个")
    print(f"  - 链接数量过少的笔记: {len(low_links_notes)} 个")
    print(f"📝 报告: {report_path}")
    print("=" * 60)

if __name__ == "__main__":
    main()
