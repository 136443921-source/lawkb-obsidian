#!/usr/bin/env python3
"""为被案例摘要引用的新笔记，补回指向案例摘要的反向链接"""
import re
from pathlib import Path

VAULT = Path("/Users/chenyouqiang/Documents/LawKB")
REFINE_DIR = VAULT / "知识飞轮系统" / "02-提炼"

# 案例摘要 → 其引用的新笔记全名
case_to_targets = {
    "吕某诉南海某医院佛山市某医院医疗损害责任案-摘要-2026-08-16.md": ["病历记录完整率-关键诊疗记录缺失风险-2026-08-16"],
    "汤某建诉床具公司股东损害债权人利益案-摘要-2026-08-16.md": ["突破合同相对性的八类法定情形-2026-08-16"],
    "金昌工业气体诉甘肃环保科技加工合同案-摘要-2026-08-16.md": ["合同订立与履行十一问-裁判规则-2026-08-16"],
}

for case_file, targets in case_to_targets.items():
    case_path = REFINE_DIR / "案例摘要" / case_file
    if not case_path.exists():
        print(f"跳过（案例不存在）: {case_file}")
        continue
    case_name = case_path.stem
    
    for tgt_name in targets:
        tgt_path = None
        for f in REFINE_DIR.rglob(f"{tgt_name}.md"):
            tgt_path = f
            break
        if not tgt_path:
            print(f"跳过（目标不存在）: {tgt_name}")
            continue
        
        content = tgt_path.read_text(encoding='utf-8')
        if f"[[{case_name}]]" in content:
            print(f"已存在回链: {tgt_name} → {case_name}")
            continue
        
        # 追加到 ## 相关笔记 段
        if "## 相关笔记" in content:
            parts = content.split("## 相关笔记", 1)
            after = parts[1]
            nh = re.search(r'\n#', after)
            pos = nh.start() if nh else len(after)
            after = after[:pos].rstrip() + f"\n- [[{case_name}]] (共现关键词: 案例印证)" + "\n" + after[pos:]
            new_content = parts[0] + "## 相关笔记" + after
        else:
            new_content = content.rstrip() + f"\n\n## 相关笔记\n- [[{case_name}]] (共现关键词: 案例印证)\n"
        
        tgt_path.write_text(new_content, encoding='utf-8')
        print(f"✅ 补回链: {tgt_name} → [[{case_name}]]")

print("完成案例摘要反向链接补全")
