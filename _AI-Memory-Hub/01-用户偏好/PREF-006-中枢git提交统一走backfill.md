---
id: PREF-006
title: 中枢 git 提交统一走 backfill.py（index.lock 安全重试）
type: preference
status: active
updated: 2026-09-14
source_ai: workbuddy
scope: global
confidence: high
tags:
  - 中枢
  - git
  - 安全通道
  - 提交
  - backfill
---

# 中枢 git 提交统一走 backfill.py（index.lock 安全重试 · 强制）

## 核心规则
- 凡对 Obsidian LawKB 中枢（`_AI-Memory-Hub`）的 git 提交（add / commit / push origin main），一律经由 `99-脚本/hub-card-backfill/backfill.py` 的 `_run_git()` 安全重试通道，**禁止手敲 `git push` 直接操作中枢**。
- `backfill.py` 内置 index.lock 安全重试（`_run_git()`）：捕获 `index.lock` 阻塞后，先 `pgrep -fl git` **精确判定 LawKB 仓库是否有真实 git 进程持有锁**——有则 **ABORT 放弃自动推送（不盲删）**，无持有者才移除残留 `index.lock` 并重试一次。

## 链路分工（务必分清）
- `write_back.py`：只负责**本地落盘 + 索引更新**（无 git push）；
- `backfill.py` 的 `_run_git()`：唯一承担**中枢 git 提交**的通道。
- 故「写回中枢」= `write_back.py` 落盘 + `backfill.py` 安全推送，二者配合、不重叠。

## 背景（事故驱动）
- 2026-09-14 总驾驶舱 C 编号改版排障（script 裸奔修复 + 并发撞号）连续两轮（第 5、6 轮）遭遇 `git index.lock` 僵死残留：手敲 git 报 `Unable to create .../.git/index.lock`（File exists），需 `lsof` 确认无进程持有后清理。backfill.py 把「判定真实进程 → 无持有者才清锁重试」固化进代码，免人工每次重排。

## 不禁止
- 中枢本地文件读写 / 索引更新（`read_hub.py`、`write_back.py` 落盘部分）仍照常；本条只约束 **git 提交通道**。
- 读中枢（`read_hub.py --brief`）不受限。

## 已知坑（2026-09-14 实测）
- `write_back.py` 的 `next_id("PREF", "01-用户偏好")` 在此中枢上返回 `PREF-001`（应为 `PREF-006`），系 `index_guard.next_free_id` 未正确解析 `_索引.md` 中 `[[PREF-00X-...\|PREF-00X]]` wikilink 行编号所致。故经 `write_back.py` 自动取号会撞号被拦；本卡以**手写 PREF-006 + 手动挂索引 + `backfill.py` 的 `git_commit_push`（复用 `_run_git` 安全重试）** 方式落地，规避该 bug。

## 来源
- 2026-09-14 老强设定：「以后中枢提交统一走 backfill.py——它内置了 index.lock 安全重试，比我手敲 git 稳。」
- 跨项目记忆 `~/.workbuddy/MEMORY.md` 同步有同款强制节（并已据此纠正「write_back.py 也走安全通道」的错误假设：write_back.py 不含 git push）。

## 相关笔记
- [[README]] (共现关键词: py, git, backfill)
- [[_索引]] (共现关键词: py, backfill, 中枢)
- [[共享记忆协议-v1.0]] (共现关键词: backfill, 中枢)
- [[DEC-006-蓝队训练记录落位与版本号冻结]] (共现关键词: 中枢, 006)
- [[DEC-2026-003-确立记忆中枢]] (共现关键词: git, 中枢)
- [[EXP-2026-002-暂存校验路径口径误判致静默中止提交]] (共现关键词: git, 提交)
