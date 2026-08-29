---
tags:
  - 08
  - 合同法
  - 医疗纠纷
  - 2026
  - --
  - push
  - git
---

# 自动化任务执行留痕 — obsidian-lawkb 自动备份同步

> 任务ID：automation-1782641923967 ｜ 频率：每3天 22:01 ｜ 范围：/Users/chenyouqiang/Documents/LawKB → GitHub(ssh)

## 根因与修复（2026-08-23）

### 长期"假成功"根因（2026-08-16 起，3048 个变更积压未提交）
1. **分支无 upstream**：本地 `main` 分支未设 `origin/main` 上游，任务执行 `git push` 静默失败（`fatal: The current branch main has no upstream branch`），但任务标记 success → 假成功。
2. **密钥拦截**：知识飞轮系统 `.cache_*` 运行缓存含腾讯云 Secret ID，GitHub secret scanning 拒收（`push declined due to repository rule violations`）→ push 被阻断。

### 2026-08-23 人工修复
- 建立上游并推送成功：`git push --set-upstream origin main` → `be9b9bd..a3d84ba`
- 剔除 `.cache_20260820/` 密钥文件（`git rm --cached`）+ 加入 `.gitignore` 规则 `.cache_*/`、`.cache/`
- 暂扣 12 个纯删除（[[医院法律顾问|医院法律顾问]]10章+2经验卡），保留 remote 副本待用户确认

### 后续建议（写入任务提示词）
- push 改用 `git push --set-upstream origin main`（或先 `git branch --set-upstream-to=origin/main`）
- 运行前 `git status` 确认无 secret/大文件；`.cache_*/` 已 gitignore 应不会再次误提交
- 对纯删除 D 谨慎：勿 `git add -A` 静默删 remote 知识资产，建议逐项确认
- 提交后 `git ls-remote` 或 `git status -sb` 校验远端已更新，避免再次假成功

## 执行留痕

| 时间 | 状态 | 关键指标 | 异常说明 |
|------|------|------|------|
| 2026-08-23 22:35 | ✅成功(人工) | 推送 be9b9bd..a3d84ba，3042变更入库，剔除2密钥文件，加.gitignore | 根因=无upstream+腾讯云Secret拦截；12纯删除暂扣待确认；建议轮换Secret+修任务提示词 |
| 2026-08-27 13:44 | ✅成功 | 推送 a3d84ba..739f9e2，本运行共8提交(首批1391文件+追录~1560文件)，远程已校验一致 | 含引号/空格文件名批处理解析失败已用git add -A补录；提交后检测到后台自动化新增~1560文件改动，已分批追录并push；无冲突，push成功 |
| 2026-08-29 22:45 | ✅成功 | 推送 739f9e2..082425e，8批×500共3974变更(实际入库9338唯一文件)，远端 ls-remote 校验一致 082425e | 提交期间后台自动化又写入~5364文件(06-沉淀3707+.backup2887)被后续批次一并收录，故diff数>提交前status数；57删除项经find同名核验全为目录重组移动、真丢失0；密钥扫描clean；载荷38.7MB/最大1.3MB安全 |

### 2026-08-29 新增强化（已固化到执行流程）
- **批处理改脚本化**：用 `/tmp/lawkb_batch_commit.py`（`git add -A --pathspec-from-file=<nul文件> --pathspec-file-nul`），彻底规避含空格/引号文件名解析失败（08-27 事故复发点）。
- **删除项强制核验**：`git status -z` 取 D 项 → `find -name <basename>` 全库搜同名，确认"已移动"才放行；真丢失>0 则中止推送。
- **同步前四检**：密钥扫描 / 删除核验 / 载荷体检(单文件<100MB) / ping 网络。
- **待治理(P1，不阻塞)**：`知识飞轮系统/.backup/` 已有 3029 个文件被 git 跟踪（本次又入 2887 个），.git 已 86MB，建议加 `.gitignore` 排除 `**/.backup/`；另 06-沉淀 单次涌入 3707 文件，疑为后台批处理产物入库，建议评估是否需排除。

## 相关笔记
- [[案例权威源统一规范]] (共现关键词: 2026, --, 08)
- [[合同风险规则库]] (共现关键词: 2026, --)
- [[LEARNINGS]] (共现关键词: --, git)
