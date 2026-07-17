#!/usr/bin/env python3
"""
标签体系自动生成脚本
扫描 LawKB 中所有 .md 文件的 tags 字段，生成标签索引笔记
"""

import os
import re
import yaml
from collections import defaultdict
from datetime import datetime

# 配置
SCAN_DIR = "/Users/chenyouqiang/Documents/LawKB"
OUTPUT_FILE = "/Users/chenyouqiang/Documents/LawKB/03-连接/标签体系/标签索引.md"
MAX_NOTES_PER_TAG = 20
HIGH_FREQ_THRESHOLD = 20
LOW_FREQ_THRESHOLD = 4

def normalize_tags(tags_raw):
    """
    递归规范化 tags 列表：
    - 展平嵌套列表
    - 过滤 None / 空字符串
    - 所有元素转为字符串
    - 过滤掉异常长字符串（>50字符，可能是内容误入标签字段）
    """
    result = []
    for item in tags_raw:
        if item is None:
            continue
        elif isinstance(item, list):
            result.extend(normalize_tags(item))
        elif isinstance(item, (str, int, float)):
            s = str(item).strip()
            if s and len(s) <= 50:
                result.append(s)
    return result


def extract_tags_from_file(filepath):
    """从笔记中提取 tags 字段（支持多种 YAML 格式）"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return []

    # 提取 frontmatter
    if not content.startswith("---"):
        return []

    fm_end = content.find("---", 3)
    if fm_end == -1:
        return []

    fm = content[3:fm_end]

    # 尝试用 yaml.safe_load 解析（更准确）
    try:
        fm_data = yaml.safe_load(fm)
        if isinstance(fm_data, dict) and "tags" in fm_data:
            tags = fm_data["tags"]
            if isinstance(tags, list):
                return normalize_tags(tags)
            elif isinstance(tags, str):
                return [t.strip() for t in tags.split(",") if t.strip() and len(t.strip()) <= 50]
    except Exception:
        pass

    # 正则兜底：匹配 tags: [a, b, c] 格式
    tags_match = re.search(r"^tags:\s*\[(.*?)\]", fm, re.MULTILINE)
    if tags_match:
        tags_str = tags_match.group(1)
        return [t.strip().strip("'\"") for t in tags_str.split(",") if t.strip() and len(t.strip()) <= 50]

    # 正则兜底：匹配 tags:\n  - a\n  - b 格式
    tags_match = re.search(r"^tags:\s*\n((?:\s*-\s*.+\n?)+)", fm, re.MULTILINE)
    if tags_match:
        tags_block = tags_match.group(1)
        return [t.strip().lstrip("- ").strip("'\"")
                for t in tags_block.split("\n") if t.strip() and len(t.strip()) <= 50]

    return []

def scan_all_notes(scan_dir):
    """扫描所有笔记，提取标签统计"""
    tags_stats = defaultdict(int)
    tags_notes = defaultdict(list)
    total_notes = 0
    tagged_notes = 0

    for root, dirs, files in os.walk(scan_dir):
        # 跳过 .workbuddy 目录
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for filename in files:
            if filename.endswith(".md"):
                filepath = os.path.join(root, filename)
                total_notes += 1

                tags = extract_tags_from_file(filepath)
                if tags:
                    tagged_notes += 1

                for tag in tags:
                    if tag:  # 过滤空标签
                        tags_stats[tag] += 1
                        tags_notes[tag].append(filepath)

    return tags_stats, tags_notes, total_notes, tagged_notes

def get_note_title(filepath):
    """获取笔记标题（从文件名或 frontmatter title 字段）"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        # 优先从 frontmatter 取 title
        if content.startswith("---"):
            fm_end = content.find("---", 3)
            if fm_end != -1:
                fm = content[3:fm_end]
                try:
                    fm_data = yaml.safe_load(fm)
                    if isinstance(fm_data, dict) and "title" in fm_data:
                        return str(fm_data["title"])
                except Exception:
                    pass
        # 回退到文件名（去掉 .md）
        return os.path.basename(filepath).replace(".md", "")
    except Exception:
        return os.path.basename(filepath).replace(".md", "")

def get_note_link(filepath):
    """生成 Obsidian 内部链接格式 [[标题]]"""
    title = get_note_title(filepath)
    # Obsidian 内部链接使用标题，这里用文件名作为 fallback
    rel_path = os.path.relpath(filepath, "/Users/chenyouqiang/Documents/LawKB")
    # 去掉 .md 后缀，Obsidian 会自动匹配
    note_name = os.path.basename(filepath).replace(".md", "")
    return f"[[{note_name}]]"

def calculate_hhi(tags_stats):
    """计算赫芬达尔指数（HHI）—— 衡量标签分布均匀度"""
    total = sum(tags_stats.values())
    if total == 0:
        return 0
    return sum((count / total) ** 2 for count in tags_stats.values())

def extract_prior_update_log(existing_content):
    """从已有标签索引中提取「四、更新日志」历史，用于追加而非覆盖"""
    if not existing_content:
        return []
    marker = "## 四、更新日志"
    idx = existing_content.find(marker)
    if idx == -1:
        return []
    block = existing_content[idx:]
    # 去掉 tip 行
    tip_idx = block.find("> [!tip]")
    if tip_idx != -1:
        block = block[:tip_idx]
    entries = []
    for line in block.splitlines():
        if line.strip().startswith("- **") or line.strip().startswith("- "):
            entries.append(line.strip())
    return entries


def generate_tag_index(tags_stats, tags_notes, total_notes, tagged_notes, prior_log=None):
    """生成标签索引笔记内容"""
    today = datetime.now().strftime("%Y-%m-%d")
    total_tags = len(tags_stats)
    untagged_notes = total_notes - tagged_notes
    tagged_percent = round(tagged_notes / total_notes * 100, 1) if total_notes else 0
    untagged_percent = round(untagged_notes / total_notes * 100, 1) if total_notes else 0

    # 按使用次数降序排序
    sorted_tags = sorted(tags_stats.items(), key=lambda x: x[1], reverse=True)

    # 分类标签
    high_freq = [(t, c) for t, c in sorted_tags if c >= HIGH_FREQ_THRESHOLD]
    mid_freq = [(t, c) for t, c in sorted_tags if LOW_FREQ_THRESHOLD < c < HIGH_FREQ_THRESHOLD]
    low_freq = [(t, c) for t, c in sorted_tags if c <= LOW_FREQ_THRESHOLD]

    # 计算 HHI
    hhi = calculate_hhi(tags_stats)
    hhi_desc = "不均匀（少数标签占据大部分使用）" if hhi > 0.15 else "较均匀"

    # 覆盖率分析
    coverage_desc = "高（≥80%）" if tagged_percent >= 80 else \
                    "中（50%-80%）" if tagged_percent >= 50 else "低（<50%）"

    # 生成 Markdown
    lines = []
    lines.append("---")
    lines.append("title: 标签索引")
    lines.append(f"date: {today}")
    lines.append("tags: [标签体系, 知识管理]")
    lines.append("---\n")
    lines.append("# 标签索引\n")
    lines.append(f"> 本文档由 AI 自动生成（{today}），统计 obsidian-lawkb-知识飞轮系统 中所有笔记的标签使用情况。\n")
    lines.append("---\n")

    # 一、标签使用统计表
    lines.append("## 一、标签使用统计（按使用次数降序）\n")
    lines.append("| 排名 | 标签 | 使用次数 | 占比（估算） |")
    lines.append("|------|------|---------|------------|")

    top_n = min(len(sorted_tags), 30)  # 显示前30个
    for i, (tag, count) in enumerate(sorted_tags[:top_n], 1):
        pct = round(count / sum(tags_stats.values()) * 100, 1)
        lines.append(f"| {i} | {tag} | {count} | {pct}% |")

    if len(sorted_tags) > 30:
        lines.append(f"\n> 共 {len(sorted_tags)} 个标签，仅显示前 30 个。完整列表见下方「标签详情」部分。\n")

    lines.append("\n**统计说明：**\n")
    lines.append(f"- 总笔记数：{total_notes}")
    lines.append(f"- 有标签的笔记数：{tagged_notes}")
    lines.append(f"- 无标签的笔记数：{untagged_notes}")
    lines.append(f"- 标签总数：{total_tags}\n")
    lines.append("---\n")

    # 二、标签详情
    lines.append("## 二、标签详情\n")

    # A. 高频标签
    if high_freq:
        lines.append(f"### A. 高频标签（使用次数 ≥ {HIGH_FREQ_THRESHOLD}）\n")
        for tag, count in high_freq:
            lines.append(f"#### A.{high_freq.index((tag, count)) + 1} {tag}（{count} 篇笔记）\n")
            lines.append("**相关笔记**（最多显示 20 篇）：\n")
            notes = tags_notes[tag][:MAX_NOTES_PER_TAG]
            for note_path in notes:
                link = get_note_link(note_path)
                lines.append(f"- {link}")
            if len(tags_notes[tag]) > MAX_NOTES_PER_TAG:
                lines.append(f"- ……（还有 {len(tags_notes[tag]) - MAX_NOTES_PER_TAG} 篇未显示）")
            lines.append("")

    # B. 中频标签
    if mid_freq:
        lines.append(f"### B. 中频标签（使用次数 {LOW_FREQ_THRESHOLD + 1}～{HIGH_FREQ_THRESHOLD - 1}）\n")
        for tag, count in mid_freq:
            lines.append(f"- **{tag}**（{count} 篇）")
        lines.append("")

    # C. 低频标签
    if low_freq:
        lines.append(f"### C. 低频标签（使用次数 ≤ {LOW_FREQ_THRESHOLD}）\n")
        for tag, count in low_freq:
            lines.append(f"- {tag}（{count} 篇）")
        lines.append("")

    lines.append("---\n")

    # 三、标签体系分析
    lines.append("## 三、标签体系分析\n")
    lines.append("### 3.1 标签覆盖率\n")
    lines.append(f"- **有标签笔记占比**：{tagged_percent}%")
    lines.append(f"- **无标签笔记占比**：{untagged_percent}%")
    lines.append(f"- **分析**：标签覆盖率**{coverage_desc}**\n")

    lines.append("### 3.2 标签分布均匀度\n")
    lines.append(f"- **赫芬达尔指数（HHI）**：{round(hhi, 4)}（0-1，越接近1表示分布越不均匀）")
    lines.append(f"- **分析**：标签分布**{hhi_desc}**\n")

    lines.append("### 3.3 建议与推荐\n")
    lines.append("> 以下笔记未打标签或标签较少，建议补充：\n")

    # 找出无标签的笔记（最多10篇）
    untagged_list = []
    for root, dirs, files in os.walk(SCAN_DIR):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in files:
            if filename.endswith(".md"):
                filepath = os.path.join(root, filename)
                tags = extract_tags_from_file(filepath)
                if not tags:
                    untagged_list.append(filepath)
                if len(untagged_list) >= 10:
                    break
        if len(untagged_list) >= 10:
            break

    if untagged_list:
        for note_path in untagged_list[:10]:
            link = get_note_link(note_path)
            lines.append(f"- {link} —— 建议补充标签")
    else:
        lines.append("- 当前所有笔记均已打标签，请继续保持！")

    lines.append("\n---\n")

    # 四、更新日志（保留历史，最新在前）
    lines.append("## 四、更新日志\n")
    lines.append(f"- **{today}**：自动生成标签索引（扫描 {total_notes} 篇笔记，发现 {total_tags} 个标签）\n")
    if prior_log:
        for entry in prior_log:
            # 避免重复今天已写入的条目
            if today not in entry:
                lines.append(f"{entry}\n")

    lines.append("> [!tip] 使用提示")
    lines.append("> 本文档自动生成，每周日 23:00 更新。如需手动更新，运行「标签体系自动生成」自动化任务。")

    return "\n".join(lines)

def main():
    print("开始扫描笔记标签……")
    tags_stats, tags_notes, total_notes, tagged_notes = scan_all_notes(SCAN_DIR)

    print(f"扫描完成：共 {total_notes} 篇笔记，其中 {tagged_notes} 篇有标签，发现 {len(tags_stats)} 个标签")

    # 读取已有更新日志历史
    prior_log = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                prior_log = extract_prior_update_log(f.read())
        except Exception:
            prior_log = []

    # 生成标签索引内容
    content = generate_tag_index(tags_stats, tags_notes, total_notes, tagged_notes, prior_log=prior_log)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    # 写入文件
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"标签索引已写入：{OUTPUT_FILE}")

    # 输出 TOP 5 标签（用于企微通知）
    sorted_tags = sorted(tags_stats.items(), key=lambda x: x[1], reverse=True)
    print("\n📊 高频标签 TOP 5：")
    for i, (tag, count) in enumerate(sorted_tags[:5], 1):
        print(f"  {i}. {tag}（{count} 篇）")

    return tags_stats, total_notes, tagged_notes

if __name__ == "__main__":
    main()
