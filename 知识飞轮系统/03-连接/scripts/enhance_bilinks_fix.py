#!/usr/bin/env python3
"""
增强双向链接 - 补充修正脚本 v2
1. 对已有 ## 相关笔记 段的笔记：追加新反向链接（去重）
2. 对缺失的笔记：创建 ## 相关笔记 段
3. 识别"断链"中实际是本周新笔记互引的情况（短名→带日期全名匹配）
4. 通过 tag 共现（≥1）推荐关联笔记
"""
import re
from datetime import datetime
from pathlib import Path

VAULT = Path("/Users/chenyouqiang/Documents/LawKB")
REFINE_DIR = VAULT / "知识飞轮系统" / "02-提炼"

def extract_tags(content):
    m = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m: return []
    fm = m.group(1)
    return [t.strip() for t in re.findall(r'^  - (.+)$', fm, re.MULTILINE)]

def extract_links(content):
    return list(set(re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content)))

def build_index():
    idx = {}
    for f in VAULT.rglob("*.md"):
        if "/.workbuddy/" in str(f): continue
        if f.stem not in idx:
            idx[f.stem] = str(f)
    return idx

INDEX = build_index()

new_notes = []
for f in sorted(REFINE_DIR.rglob("*-2026-08-16.md")):
    if "每日知识摄入报告" in f.name: continue
    content = f.read_text(encoding='utf-8')
    new_notes.append({
        'path': f,
        'name': f.stem,
        'short_name': re.sub(r'-2026-08-16$', '', f.stem),
        'tags': extract_tags(content),
        'content': content,
        'links': extract_links(content),
    })

short_to_full = {n['short_name']: n['name'] for n in new_notes}

reverse_added = 0
fixed_cross_refs = 0
report = []

for note in new_notes:
    name = note['name']
    content = note['content']
    existing_section = "## 相关笔记" in content
    existing_links_in_section = set(extract_links(content.split("## 相关笔记", 1)[1])) if existing_section else set()

    # 收集候选关联
    candidates = {}  # name → keywords

    # 方法1: tag共现（≥1）
    for other in new_notes:
        if other['name'] == name: continue
        overlap = set(note['tags']) & set(other['tags'])
        if len(overlap) >= 1:
            candidates[other['name']] = list(overlap)[:3]

    # 方法2: 短名→全名交叉引用修复
    for link in note['links']:
        if link in INDEX: continue  # 已有效
        if link in short_to_full:
            full = short_to_full[link]
            if full != name:
                shared = set(note['tags']) & set(next(n for n in new_notes if n['name'] == full)['tags'])
                candidates.setdefault(full, list(shared)[:3] if shared else ['同源笔记'])
                fixed_cross_refs += 1

    # 过滤已在当前笔记中出现的链接
    new_entries = []
    for rn, kws in candidates.items():
        if rn in existing_links_in_section:
            continue
        # 避免笔记正文中已通过 [[X]] 引用过的（防止重复）
        new_entries.append((rn, kws))

    if not new_entries:
        continue

    new_entries.sort(key=lambda x: -len(x[1]))
    new_entries = new_entries[:5]

    lines = [f"- [[{rn}]] (共现关键词: {', '.join(kws[:3]) if kws else '同源笔记'})" for rn, kws in new_entries]

    if existing_section:
        # 在 ## 相关笔记 段末尾追加
        parts = content.split("## 相关笔记", 1)
        after = parts[1]
        # 找下一个标题或文件末尾
        next_heading = re.search(r'\n#', after)
        insert_at = next_heading.start() if next_heading else len(after)
        # 在该行前插入
        after = after[:insert_at].rstrip() + "\n" + "\n".join(lines) + "\n" + after[insert_at:]
        new_content = parts[0] + "## 相关笔记" + after
    else:
        new_content = content.rstrip() + "\n\n## 相关笔记\n" + "\n".join(lines) + "\n"

    note['path'].write_text(new_content, encoding='utf-8')
    reverse_added += len(new_entries)
    report.append((name, new_entries))

print(f"=== 补充修正完成 v2 ===")
print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"🔗 反向链接（related_links）新增/追加：{reverse_added} 个")
print(f"🔧 短名→全名交叉引用修复：{fixed_cross_refs} 个")
print()
for name, entries in report:
    print(f"--- {name} ---")
    for rn, kws in entries:
        print(f"  + [[{rn}]] (共现: {', '.join(kws[:2])})")
