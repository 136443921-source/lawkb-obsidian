---
id: PROJ-SYS-LAWKB
title: LawKB 知识飞轮系统与 AI 工具链运维
type: project-fact
status: active
updated: 2026-09-14
source_ai: workbuddy
scope: project:LawKB
confidence: high
tags:
  - 知识飞轮
  - 运维
  - LawKB
---

# ⚙️ LawKB 知识飞轮 & AI 工具链运维

| 项 | 值 |
|---|---|
| 库路径 | `/Users/chenyouqiang/Documents/LawKB` |
| git 远端 | `lawkb-obsidian.git`（每日自动同步） |
| 知识资产 | 约 205 卡 / 816 规则库条目 / 26 子库 |
| 子目录分工 | `02-提炼` / `06-沉淀` / `04-Log` / `经验卡片` |

## 常驻工具

- **LTI 文本监控器 v4.8.1** —— 五维 QC 门禁
- **IMA 日摄入流水线** —— 5 自有库 × 3 篇/日，单日 ≤15 篇封顶
- **裁判规则库编号治理** —— R-xxx 同号冲突，`next_rule_id.py` 单源取号
- **check_links / build_links.py** —— 链接与编号体检
- **华宇元典 + pkulaw** —— 法条双源核验

## 已完成的 P0

- ✅ P0-2：check_links 假跑疑点已按既有结论推进

## 在办 P0

- [ ] **P0-1**：六-B 安全铁律扩展到所有写入型 automation
- [ ] **P0-3**：`/tmp` 脚本固化迁移到数字分身工具目录
- [ ] **P0-4**：待定号方案表 v1.0 —— 300+ 卡 / 6 组同号冲突（**只改 frontmatter，绝不重命名文件**）
