---
id: RULE-046
title: - **同源坑（前序已记）**：同文件并行 Edit 非原子（后写覆盖先写）→ 批量改同文件一律单进程 Python 脚
type: rule
status: active
updated: 2026-09-24
source_ai: workbuddy
scope: global
confidence: medium
---

# - **同源坑（前序已记）**：同文件并行 Edit 非原子（后写覆盖先写）→ 批量改同文件一律单进程 Python 脚

- **同源坑（前序已记）**：同文件并行 Edit 非原子（后写覆盖先写）→ 批量改同文件一律单进程 Python 脚本（read→多 replace→assert 各匹配 1 次→write）

## 相关笔记
- [[RULE-045---根治：批量改同一文件一律用单进程-Python-脚本（read→多-repl]] (共现关键词: Python, RULE, ---)
- [[R-LN-115-RULE-011二次违反续做交付直接执行的事故教训]] (共现关键词: 前序, RULE)
- [[WF-055---备注：python-脚本原子执行成功，未触发半改]] (共现关键词: ---, 原子)
- [[WF-078-本次用-Python-脚本原子重做-7-行成功（备份-tmpledger_bak]] (共现关键词: ---, Python, 原子)
- [[经验卡-C3知识飞轮中台刷新-生成器非原子写致瞬时空白-20260916]] (共现关键词: ---, 原子)
- [[WF-031-Obsidian监听文件编辑防竞态回验工作流]] (共现关键词: Edit, 文件)
- [[轨迹卡-R-LN-066-同文件静默丢改排查推理链重建-20260917]] (共现关键词: ---, Edit, 文件)
