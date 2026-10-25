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
- [[2026-09-19]] (共现关键词: py, 2026, 合同)
- [[2026-09-20]] (共现关键词: py, 共现, 2026)
- [[RULE-056-RULE-AI19-·-AI辅助诉讼材料「核实+说明+负责」强制铁律（法发〔20]] (共现关键词: 基金会, 合同, 提交)
- [[V2常见法律文书错误案例库]] (共现关键词: 共现, 提交, 合同)
- [[2026-10-20-resume-backfill]] (共现关键词: 基金会, backfill)
- [[backfill_plan]] (共现关键词: 合同, backfill)
- [[9655驾驶舱屏台账]] (共现关键词: 合同, index)
- [[WF-123-WF-AI19-·-AI辅助诉讼材料三段式核验作业规程（法发〔2026〕10号第]] (共现关键词: index, py)
- [[WF-079---说明：中央-`03-连接标签体系标签索引.md`-由-`gen_tag_in]] (共现关键词: 合同, 关键词, 共现)
- [[2026-09-26]] (共现关键词: 共现, py)
- [[PROJ-006-QC审判长双模心智训练备忘录]] (共现关键词: 合同, 006)
- [[PREF-007-技能训练记录须回写共享记忆中枢]] (共现关键词: 合同, PREF, 中枢)
- [[2026-09-14-价值复盘]] (共现关键词: 合同, 中枢, 共现)
- [[小德慈善组织合规管理系统_制度清单（慈善版）]] (共现关键词: 基金会, 中枢)
- [[统一知识索引-2026-07]] (共现关键词: 2026, 统一)
- [[统一知识索引-2026-08]] (共现关键词: 2026, 统一)
- [[DEC-2026-025-不设业务运营官_数字员工考核统一归口律所主任]] (共现关键词: 2026, 统一)
- [[RULE-038---T1-落-`法条银行_Schema规范_v1.0.md`（两型统一-fron]] (共现关键词: 共现, 关键词, 统一)
- [[Obsidian配置指南]] (共现关键词: 共现, git)
- [[R-PI-161-医院合规审核应审尽审未经审核不得提交决策涉法事项须报告]] (共现关键词: 2026, 提交)
- [[45-基金会提交虚假财务报告被撤销登记案]] (共现关键词: 共现, 关键词, 提交)
- [[RULE-012---R-PI-161-医院合规审核应审尽审未经审核不得提交决策涉法事项须报告-(]] (共现关键词: 共现, 2026, 提交)
- [[WF-006-AI合同审查搭建思路流程提示词从入门到进阶]] (共现关键词: 006, 关键词)
- [[RULE-006-若本目录某个条目与-`_AI-Memory-Hub`-冲突-→-一律以-`_AI]] (共现关键词: 006, 关键词)
- [[LEARNINGS]] (共现关键词: git, 2026, 共现)
- [[换电脑后WorkBuddy如何迁移]] (共现关键词: git, 共现)
- [[220030回补报告-2026-09-10]] (共现关键词: 重试, ##)
- [[_索引]] (共现关键词: py, backfill, 中枢)
- [[DEC-2026-005-中枢提交规范化四层闭环思维轨迹]] (共现关键词: py, backfill, 中枢)
- [[README]] (共现关键词: py, git, backfill)
- [[_AI-Memory-Hub/01-用户偏好/_索引]] (共现关键词: py, backfill, 中枢)
- [[共享记忆协议-v1.0]] (共现关键词: backfill, 中枢)
- [[DEC-006-蓝队训练记录落位与版本号冻结]] (共现关键词: 中枢, 006)
- [[DEC-2026-003-确立记忆中枢]] (共现关键词: git, 中枢)
- [[EXP-2026-002-暂存校验路径口径误判致静默中止提交]] (共现关键词: git, 提交)
