---
id: RULE-SCHEMA
title: 字段 Schema 与条目模板
type: rule
status: active
updated: 2026-09-14T18:26
source_ai: workbuddy
scope: global
confidence: high
tags:
  - schema
  - 模板
  - 元规则
created: 2026-09-14
---

# 🧩 字段 Schema（所有条目必须遵守）

## 必填字段

| 字段 | 取值 | 说明 |
|---|---|---|
| `id` | `RULE-001` / `PREF-012` / `PROJ-LAW-001` / `DEC-2026-014` / `WF-007` | 全局唯一；同一事实被取代时**不得复用** |
| `title` | 短句 | 一句话说清这条是什么 |
| `type` | `rule` `preference` `project-fact` `decision` `workflow` `meta` | 决定落盘目录 |
| `status` | `active` `draft` `deprecated` `superseded` | 仲裁第 1 级过滤依据 |
| `updated` | `YYYY-MM-DD` | 仲裁第 2 级依据；**每次修改必须抬新日期** |
| `source_ai` | `human` `obsidian-manual` `workbuddy` `claude` `codex` `gemini` `cursor` `unknown` | 仲裁第 3 级依据 |
| `scope` | `global` / `project:<名>` / `domain:<域>` | 决定这条在多广范围生效 |
| `confidence` | `high` `medium` `low` | 仲裁第 4 级依据 |

## 选填字段

| 字段 | 用途 |
|---|---|
| `supersedes` | 指向被它取代的旧 `id`，形成追溯链 |
| `superseded_by` | 反向指针（由复盘脚本自动补） |
| `deprecated_reason` | 为何作废，防止日后又被捡回来 |
| `expires` | `YYYY-MM-DD`，到期的临时事实（如某案件的临时排期） |
| `tags` | 便于 Obsidian 检索 |
| `evidence` | 支撑该条目的来源文件或会话摘要 |

## 三条不可协商的约束

1. **`id` 一旦发出终身不变**——即使内容改了十次，也只能是同一 id 抬 `updated`，不得改名（改名 = 断链 = 300+ 链接崩）。
2. **`status` 变动必须留痕**——`active → deprecated` 要写 reason，不得直接删。
3. **`updated` 不得倒写**——禁止回填过去日期伪造时效。

---

## 四类条目模板

### 📌 规则（rule）
```yaml
---
id: RULE-XXX
title: 一句话规则
type: rule
status: active
updated: YYYY-MM-DD
source_ai: workbuddy
scope: global
confidence: high
tags: [标签]
---

# 规则标题

**规则正文**：一句话说清必须怎么做。

**为什么**（不写清楚会被后来的 AI 删掉）：
<一句话说明成因>

**违反时会怎样**：
<后果描述>
```

### 💗 偏好（preference）
```yaml
---
id: PREF-XXX
title: 偏好简述
type: preference
status: active
updated: YYYY-MM-DD
source_ai: human
scope: global
confidence: high
---

# 偏好标题

- **要**：…
- **不要**：…
- **典型场景**：…
```

### 🗂 项目事实（project-fact）
```yaml
---
id: PROJ-XXX-001
title: 项目/案件当前状态
type: project-fact
status: active
updated: YYYY-MM-DD
source_ai: workbuddy
scope: project:<项目名>
confidence: high
---

# 项目状态

| 项 | 值 |
|---|---|
| 阶段 | … |
| 下一步 | … |
| 阻塞点 | … |
```

### ⚖️ 决策（decision）
```yaml
---
id: DEC-YYYY-NNN
title: 决策主题
type: decision
status: active
updated: YYYY-MM-DD
source_ai: human
scope: project:<名>
confidence: high
---

# 决策：<主题>

## 考虑了哪些选项
- A：…
- B：…

## 选了什么 & 为什么
选 **A**，因为…

## 否了什么 & 为什么
否决 B，因为…

## 什么信号会推翻这条决策（关键！）
> 当出现 ___X___ 时，本决策作废。
```
