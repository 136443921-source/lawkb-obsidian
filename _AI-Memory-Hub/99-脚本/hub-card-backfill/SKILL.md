---
name: hub-card-backfill
description: Obsidian LawKB 共享记忆中枢「按需补卡」一条龙——读索引→写卡→更新索引→commit/push。当用户说"补卡 XXX"/"把 XXX 补进中枢"/"沉淀一张工作流卡"/"按待沉淀清单补卡"时触发。覆盖 workflow/rule/preference/decision/project-fact 各型，自动取号、更新索引、隐私红线校验、git 推送多设备同步。
agent_created: true
version: 1.0.0

tags:
  - 民事诉讼
  - ##
  - 索引
  - md
  - id
  - WF
---

# 共享记忆中枢 · 按需补卡流水线

## 触发词
补卡 / 补一张卡 / 沉淀到中枢 / 把 XXX 补进中枢 / 按需补卡 / backfill card

## 一句话定位
把一条高价值方法论 / 规则 / 偏好 / 决策快速落成中枢卡片，并自动入索引 + 推送同步，让其它 AI / 设备能召回。

## 前置铁律（不可省略）
1. **隐私红线**：个案卷宗（当事人姓名 / 身份证号 / 银行卡 / 手机号 / 证据原件 / 案号细节）**严禁写入中枢**，只在本地办案系统处理。本流水线卡只沉淀方法论 / 工作流事实。
2. **id 一旦发出终身不变**：同名事实被取代时不得复用旧 id，只能抬 `updated`。
3. **updated 用 `YYYY-MM-DD`** 干净格式（Obsidian 运行态可能补 T 尾巴，脚本层 norm_date 已容错，无需强求）。
4. **只提交 `_AI-Memory-Hub/`**，不碰库内其它改动。

## 标准步骤（一条龙）
### 0. 定位目标目录与索引
- 工作流卡 → `04-Workflows/`；规则 → `00-全局规则/`；偏好 → `01-用户偏好/`；决策 → `03-决策档案/`；项目事实 → `02-当前项目/`。
- 读该目录 `_索引.md`（无则按 Schema 新建）。

### 1. 取号
- **优先复用「待沉淀」**：若 `_索引.md` 的「待沉淀」清单有匹配本次主题的项，直接采用其预留 id（如 WF-023），并随后从清单删除。
- **否则顺延**：扫该目录已有 `XX-NNN-*.md`，取最大序号 +1 作为新 id（如现有最大 WF-022 → 新 WF-023）。

### 2. 写卡
- 文件名：`<id>-<短主题>.md`（中文短主题，需与索引 wikilink 对应）。
- frontmatter 严格按 `00-全局规则/字段-Schema.md`：
  ```yaml
  ---
  id: WF-023
  title: 一句话
  type: workflow
  status: active
  updated: 2026-09-14
  source_ai: workbuddy
  scope: global
  confidence: high
  tags: [标签]
  ---
  ```
- 正文骨架（按类型选，字段以 Schema 模板为准）：
  - **workflow**：`## 适用场景` / `## 标准步骤` / `## 红线` / `## 产出`（可加核心教义 / 阵营映射等）
  - **rule**：`**规则正文**` / `**为什么**` / `**违反时会怎样**`
  - **preference**：`**要**` / **不要** / `**典型场景**`
  - **decision**：`## 考虑了哪些选项` / `## 选了什么&为什么` / `## 什么信号会推翻`
  - **project-fact**：状态表（阶段 / 下一步 / 阻塞点）
- **交叉引用**：若与其它卡强相关（如 WF-001 双轨交付、WF-002 LTI 门禁），正文内用 `[[WF-002]]` 链接形成召回链。
- 内容来源：用户给的方法论 → 读相关 SKILL.md / 本地源文件实地核实 → 起草；**不得凭记忆灌法条**，法条以 pkulaw 主源核验。

### 3. 更新索引 + git 推送（交给脚本，一条龙）
运行本 skill 目录下的 `backfill.py`，自动完成：插「已沉淀」表行 + 删「待沉淀」匹配项 + **精确 `git add` 本次文件（卡+索引）** + commit + push origin main（含 index.lock 安全重试，且不会误带中枢内其它遗留改动）。
```bash
PY=/Users/chenyouqiang/.workbuddy/binaries/python/versions/3.13.12/bin/python3
$PY /Users/chenyouqiang/.workbuddy/skills/hub-card-backfill/backfill.py \
  --card "/Users/chenyouqiang/Documents/LawKB/_AI-Memory-Hub/04-Workflows/WF-023-冒名诉讼程序战方法论.md"
```
脚本自动：① 从卡 frontmatter 取 id/title/scope/updated；② 在该目录 `_索引.md` 的「已沉淀」表末（「待沉淀」节前）追加一行，wikilink 转义 `\|`；③ 若「待沉淀」含该 id/title 的条目则删除，空了则移除该节标题；④ git 提交推送，检测到 `index.lock` 阻塞时确认无真实 git 进程后删除重试。

### 4. 回报
- 报告新卡 id、落点路径、索引已更新、commit hash、push 状态。
- 若 Obsidian 在运行且 `updated` 出现 T 尾巴，提示"功能不受影响，脚本层已容错"。

## 红线速查
- 不写个案隐私 / 不复用旧 id / 不凭记忆灌法条 / 只推 `_AI-Memory-Hub/`。
- 「待沉淀」是待办清单而非已落卡；补完后必须从清单移除。

## 关联
- 取号治理见 `lawkb-rule-id-governance`（R-xxx 规则卡用，与本流水线 WF-xxx 编号空间不同）。
- 双轨交付 WF-001、LTI 门禁 WF-002 为本流水线常用交叉引用目标。
- 中枢元规则：`00-全局规则/共享记忆协议-v1.0.md`、`冲突仲裁规则.md`、`字段-Schema.md`。

## 相关笔记
- [[红队心智模型与训练备忘录-2026-09-14]] (共现关键词: SKILL, 证据)
- [[红队心智模型复盘-2026-09-14]] (共现关键词: ##, SKILL, 证据)
- [[WF-028-知识飞轮卡库接线]] (共现关键词: ##, SKILL, 证据)
- [[DEC-006-蓝队训练记录落位与版本号冻结]] (共现关键词: SKILL, 中枢, md)
- [[字段-Schema]] (共现关键词: ##, updated, 仲裁)
- [[RULE-006-若本目录某个条目与-`_AI-Memory-Hub`-冲突-→-一律以-`_AI]] (共现关键词: updated, 仲裁)
