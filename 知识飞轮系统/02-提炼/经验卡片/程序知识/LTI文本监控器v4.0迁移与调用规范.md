---
title: LTI文本监控器v4.0迁移与调用规范（经验卡片）
type: 经验卡片
category: 程序知识
trigger: 维护/迁移法律智能体技能、在 SKILL.md 中写入 LTI 调用示例、将监控器版本从旧版升级到 v4.0 时
domain: 程序知识
source: 2026-08-10 LTI v4.0 迁移实操复盘
original_source: 小强律师分身与知识飞轮日常维护
review_date: 2026-11-10
importance: 4
generated_by: 经验总结与知识沉淀增量提炼（2026-08-10）
created: 2026-08-10T17:49
updated: 2026-08-21T18:55
tags:
  - 经验卡片
  - 程序知识
  - LTI文本监控器
  - 知识工程
related_links:
  - 连接枢纽-通用程序
  - R-PR-023
  - R-PR-017
  - R-PR-025
  - R-PR-024
  - R-PR-016
  - R-PR-037
  - 通用
---
# LTI文本监控器v4.0迁移与调用规范（经验卡片）

> 提炼自 2026-08-10 LTI 文本监控器从旧版（v2.9.1/v2.0，含 AUTO_FIX、格式检查）批量迁移至 v4.0 三模块（法条校验 / 法理逻辑 / 金额·名称一致性）的实操复盘。

## 触发场景（trigger）
维护或迁移法律智能体技能、在 SKILL.md 中写入 LTI 调用示例、将监控器版本从旧版升级到 v4.0 时。

## 应当做（do）
- v4.0 仅两种阻断级（REJECT）：R101 条号越界/伪造、C301 金额硬矛盾；其余（已废止法 R001、虚构法律名 R105、逻辑矛盾 L201-L204、名称错写 C302、案号不一致 C304）**只提示不阻断，且绝不改写原文**。
- Python 调用**必须**先 `sys.path.insert(0, ".../LTI文本监控器/references")` 再 `from main import wrap_output, LTIRejectError`；裸 `from main import` 会 `ModuleNotFoundError`。
- 批量升级旧模板时，用脚本按「整段精确字符串替换」（标题 / 核心原则 / INFO 示例 / AUTO_FIX 段 / REJECT 示例 / QA / 页脚版本标）幂等替换，避免逐文件手改。
- 同步修复破损 import（如旧 `from lti_v2.integration import ...`，v4.0 已无此模块）→ 统一改为 `from main import wrap_output, LTIRejectError`。
- 经验总结 / 知识沉淀产出的资产（经验卡片、裁判规则）入库前也须过 LTI（沉淀入口校验），防错误法条污染飞轮。
- 验证链路时用真实 `wrap_output` 跑：伪造条号应 R101 REJECT，正常文本应 PASS 且页脚标注「三模块法律文本监控器 v4.0」。

## 不应当做（dont）
- 不要在文档示例里留裸 `from main import` 而缺 `sys.path`（复制即跑不通）。
- 不要沿用旧版 AUTO_FIX 描述（v4.0 已删除自动修正、格式/术语/标点检查 R002-R024）。
- 不要把结果三分法写成 `PASS/AUTO_FIX/REJECT`（v4.0 实为 `PASS/WARNING/REJECT`）。
- 不要把 LTI 称作「防火墙式拦截」误导为全阻断——它只阻断 R101/C301。
- 不要把 LTI 自带 SKILL.md 变更日志里对 AUTO_FIX/lti_v2 的历史性提及当作「待清理错误」删掉（那是正确历史记录）。

## 规则要点（裁判规则维度）
- 核心规则：法律智能体 LTI 调用规范。适用见「裁判规则库 / 程序知识」。
- 适用要点：所有继承 legal-base 的活跃子技能，其 LTI 调用示例必须含 `sys.path.insert`；迁移/升级须幂等、可回滚、实测验证。

## 原文索引
- 复盘源：2026-08-10 会话（LTI v4.0 迁移 + 22 个 legal-base 子技能 sys.path 补齐 + 端到端实测）

## 关联（知识飞轮连接层自动补链 · 2026-08-23)
- 领域枢纽：[[连接枢纽-通用程序]]
- 同域语义关联：
  - [[R-PR-023]] · [[R-PR-017]] · [[R-PR-025]] · [[R-PR-024]]
  - [[R-PR-016]] · [[R-PR-037]]

## 关联（A3门禁·领域枢纽挂接 · 2026-08-23)
- 领域枢纽：[[连接枢纽-通用程序]]
