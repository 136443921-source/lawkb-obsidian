#!/usr/bin/env python3
"""为18张新裁判规则卡补回链：找到引用它们的02-提炼笔记，添加反向链接"""
import re
from pathlib import Path

VAULT = Path("/Users/chenyouqiang/Documents/LawKB")
REFINE_DIR = VAULT / "知识飞轮系统" / "02-提炼"
RULES_DIR = VAULT / "知识飞轮系统" / "06-沉淀" / "裁判规则库"

# 18张新规则卡
new_rules = [
    "R-PI-122", "R-PI-123", "R-PI-124", "R-PI-125",
    "R-HT-067", "R-HT-068", "R-HT-069",
    "R-HG-023", "R-HG-024", "R-HG-025",
    "R-SH-023",
    "R-LN-006", "R-LN-007", "R-LN-008",
    "R-CF-061", "R-CF-062", "R-CF-063",
    "R-CS-006",
]

# 索引所有02-提炼笔记
refine_notes = {}
for f in REFINE_DIR.rglob("*.md"):
    if "每日知识摄入报告" in f.name: continue
    content = f.read_text(encoding='utf-8')
    links = set(re.findall(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', content))
    refine_notes[f.stem] = {'path': f, 'links': links}

total_added = 0
report = []

for rule_id in new_rules:
    # 找规则卡文件
    rule_path = None
    for f in RULES_DIR.rglob(f"{rule_id}.md"):
        rule_path = f
        break
    if not rule_path:
        print(f"⚠️ 规则卡不存在: {rule_id}")
        continue
    
    # 找引用该规则的笔记
    referencing = []
    for name, info in refine_notes.items():
        if rule_id in info['links']:
            referencing.append(name)
    
    if not referencing:
        print(f"⚠️ {rule_id} 未被任何笔记引用，跳过")
        continue
    
    content = rule_path.read_text(encoding='utf-8')
    
    # 去重：检查是否已包含这些回链
    existing = set(re.findall(r'\[\[([^\]|]+)\]\]', content))
    new_refs = [r for r in referencing if r not in existing]
    
    if not new_refs:
        continue
    
    lines = []
    if "## 相关笔记" in content:
        parts = content.split("## 相关笔记", 1)
        after = parts[1]
        nh = re.search(r'\n#', after)
        pos = nh.start() if nh else len(after)
        after = after[:pos].rstrip() + "\n" + "\n".join([f"- [[{r}]] (共现关键词: 引用来源)" for r in new_refs]) + "\n" + after[pos:]
        new_content = parts[0] + "## 相关笔记" + after
    else:
        new_content = content.rstrip() + f"\n\n## 相关笔记\n" + "\n".join([f"- [[{r}]] (共现关键词: 引用来源)" for r in new_refs]) + "\n"
    
    rule_path.write_text(new_content, encoding='utf-8')
    total_added += len(new_refs)
    report.append((rule_id, new_refs))

print(f"=== 规则卡反向链接补全 ===")
print(f"🔗 规则卡反向链接新增：{total_added} 个")
print()
for rule_id, refs in report:
    print(f"--- {rule_id} ---")
    for r in refs:
        print(f"  ← [[{r}]]")
