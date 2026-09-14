---
id: WF-031
title: Obsidian 监听文件编辑防竞态·改后必 READ 回验
type: workflow
status: active
updated: 2026-09-14
source_ai: workbuddy
scope: global
confidence: high
tags:
  - Obsidian
  - 并发竞态
  - 编辑安全
  - 回验
  - 中枢
---

# WF-031 · Obsidian 监听文件编辑防竞态·改后必 READ 回验

> 适用场景 C（技术踩坑 / 排障方法论）。与 PREF-006、共享记忆协议第六条同源互引。

## 适用场景

- 编辑 **Obsidian 实时监听 / 自动保存** 的中枢 `.md` 文件（frontmatter 的 `updated` 时间戳会被 Obsidian 自动改写，例如 `18:29 → 18:43`）。
- 对 `_AI-Memory-Hub/` 下任何会被 Obsidian 监听的文件做 `Edit`（`00-全局规则/`、`01-用户偏好/`、`02-当前项目/`、`03-决策档案/`、`04-Workflows/`、`04-每日日志/` 及其各目录 `_索引.md`）。
- 提交 / 推送前需要确认"正文真的落盘了"，而非只信工具返回"成功"。

## 标准步骤（单文件串行）

1. **编辑前先 Read 确认真实文本**：尤其 `updated`、`tags`、修订日志行——Obsidian 可能已自动改写，old_string 必须以"当前磁盘真实内容"为准，不能凭上一轮记忆。
2. **单条 Edit，绝不同消息并发多 Edit 同一文件**：把一个文件的多个改动拆成"先后多条消息"，每条一个 Edit。同一消息并发 ≥2 个 Edit 到同一 Obsidian 文件会与其自动保存抢写，导致部分写入竞态失效（见事故背景）。
3. **改后立刻 READ 回验正文真在**：不要只信 Edit 工具返回的"ok"或"已替换"。Read 回目标区段，肉眼确认正文、编号、标签都在；尤其核对"插入的正文段落"是否真的落盘。
4. **若回验发现缺失 / 竞态**：重新 Read 取最新全文 → 单条 Edit 补回缺失段 → 再 Read 回验，循环到稳。
5. **推送走安全通道**：确认正文齐备后，用 `backfill.py --files <路径>`（非卡片通用提交）或 `--card`（补卡）经 `_run_git()` 安全重试通道推送（受 PREF-006 / 协议第六条约束，**禁止手敲 git push**）。

## 红线

- ❌ **同消息并发多个 Edit 到同一 Obsidian 监听文件**（最大雷区，实测会导致正文竞态丢失）。
- ❌ 改完不 Read 回验就直接推送——"Edit 返回成功 ≠ 磁盘正文在"。
- ❌ 以"提交信息写了 XX"或"上一轮以为写过了"代替 Read 回验。
- ❌ 对 `_AI-Memory-Hub/` 提交手敲 `git add/commit/push`（一律 backfill.py，见 PREF-006）。

## 事故背景（为什么有这张卡）

2026-09-14 第 8 轮：给 `共享记忆协议-v1.0.md` 新增第六条，同一条消息并发 3 个 Edit（frontmatter / 正文 / 修订日志），恰逢 Obsidian 自动改写 `updated` 时间戳与之抢写，导致**第六条正文整段竞态丢失**——但 frontmatter tags、修订日志"新增第六条"行生效了，于是把"谎称有第六条"的残缺版推上 origin/main。第 9 轮 Read 回验才发现正文缺失，被迫补回并重推。根因即"同消息并发 Edit + 未回验"。

## 关联

- PREF-006（01-用户偏好/）：中枢 git 提交统一走 backfill.py 安全通道。
- 共享记忆协议第六条（00-全局规则/）：禁手敲 git、链路分工、`--files` / `--card` 双模式。
- 本目录 `_索引.md` 挂行本身也是 Obsidian 文件——挂行同样遵守"单条 Edit + 回验"。
