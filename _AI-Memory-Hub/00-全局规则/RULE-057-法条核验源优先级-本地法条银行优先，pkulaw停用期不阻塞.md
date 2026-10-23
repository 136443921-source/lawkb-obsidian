---
version: v1.0
id: RULE-057
title: 法条核验源优先级 · 本地法条银行优先，在线源逐级降级，pkulaw 停用期不阻塞
type: rule
status: active
updated: 2026-10-22
source_ai: workbuddy
scope: global
confidence: high
supersedes_note: 取代各技能中"pkulaw 主源"的无降级单点表述
tags:
  - 法条核验
  - FR-MAIN
  - pkulaw
  - 连接器
  - 优先级
related:
  - 决策卡-法条唯一主源铁律FR-MAIN-20260927
  - RULE-037
---

# RULE-057 · 法条核验源优先级铁律

## 一、为什么会定这条（实测起因，非推测）

2026-10-22 全系统复盘实测发现一个**结构性错位**：

| 维度 | 原文表述 | 实测事实 | 冲突 |
|---|---|---|---|
| **写入落点**（FR-MAIN 管） | 法条银行 = 唯一主源 ✅ | 决策卡 DEC-2026-FR-MAIN 已生效，铁律六条落盘 | 无冲突 |
| **在线核验源**（技能层管） | 多技能写「**主源** 北大法宝 pkulaw」，**无降级标注** | `connector-status`：**pkulaw = disabled**；同刻 yuandian / qcc-legal = connected | 🔴 **有冲突** |
| **离线权威源** | 多数技能**未提及本地法条银行** | `LawKB/法条银行/` 实存 **156 张**法条卡 | 🔴 **有源不用** |

**病灶**：把「写入落点唯一」与「在线核验源优先级」两个维度混为一谈，
且把一个**会掉线的在线服务写成不可替代的"主源"**——一旦它 disabled，
核验链第一跳就卡死，而流程里没有任何降级指令。

**实测数据**（本会话 connector-status 快照，见 `驾驶舱_连接器真值.json`）：

```
connected : agent-mail / qcc-legal / tencent-docs / yuandian-mcp   (4)
disabled  : pkulaw / gongyi-open-mcp / kdocs / qq-mail / tencent-weiyun / github (6)
not_listed: ima-mcp
```

## 二、铁律正文

### 2.1 两个维度必须分开说

- **写入落点（FR-MAIN）**：一切法条「新建 / 更新 / 版本替换 / 时效性修正」**唯一**写入
  `LawKB/法条银行/`。此条不受任何连接器状态影响。
- **核验源（本条）**：**读取/核对**法条正文时按下列优先级逐级尝试。

> 一句话记法：**FR-MAIN 管"往哪写"，RULE-057 管"从哪读"。**

### 2.2 核验源优先级（五级，逐级降级，不可跳级直取记忆）

| 级 | 源 | 定位 | 当前状态（2026-10-22 实测） |
|---|---|---|---|
| ① | **本地法条银行** `LawKB/法条银行/` | **首选**，离线可用，FR-MAIN 主源 | 🟢 可用（156 张） |
| ② | 华宇元典 `yuandian-mcp`（`rh_ft_search`，`fgmc` 用法规全称） | 在线降级源一 | 🟢 connected |
| ③ | 企查查 `qcc-legal`（`get_legal_article_detail` / `get_legal_citation_verify`） | 在线第三通道 | 🟢 connected |
| ④ | 北大法宝 `pkulaw` | 在线源，**停用期不阻塞**；恢复后回第一顺位 | 🔴 **disabled** |
| ⑤ | 官方源 `flk.npc.gov.cn` / `court.gov.cn` / 部委官网 | 交叉印证与兜底 | 🟢 走 WebFetch |

### 2.3 五级全不可用时

只给**条号 + 条旨**，并显式标注
`⚠️ 条文正文待回填（本轮 法条银行 / 元典 / qcc / pkulaw 均不可用）`，
**严禁**凭记忆写出引号内的"条文原文"。

### 2.4 禁止事项

1. **禁止**在技能/SOP 中把任何**在线服务**写成不可替代的"主源"而不给降级链。
2. **禁止**用 `enabledPlugins` 布尔值判定连接器可用性——2026-10-22 实测该字段与
   实际连接状态**已脱钩**（全部 False 而实有 3 个 connected）。真值只认运行时
   `connector-status`，见 `驾驶舱_连接器真值.json`。
3. **禁止**因 pkulaw 掉线就降级到"凭记忆"——本地法条银行始终是第一顺位。

## 三、落地记录（2026-10-22 已改）

| 落点 | 动作 | 状态 |
|---|---|---|
| `legal-consult-router` SKILL.md 铁律 2 | 原「主源 pkulaw」→ 五级优先级，补入法条银行 | ✅ |
| `hub-card-backfill` SKILL.md | 「pkulaw 主源核验」→ 法条银行 + 逐级降级 | ✅ |
| `seat-orchestrator` SKILL.md §五 第 6 条 | 「本地法律法规库 / pkulaw 主源」→ 法条银行 + 逐级降级 | ✅ |
| `驾驶舱_人工核验.json` connectors 段 | 改由 `probe_connectors.py` 自动半段 + 运行时真值 | ✅ |
| `驾驶舱_连接器真值.json` | 新建，存会话注入真值快照（含 20 条历史） | ✅ |

> **未改**：`lawyer-yourself-skill`（原文已有「断开时降级元典」链路，符合本条精神）；
> `legal-database-search:826`（原已诚实标注「⚠️ 未连接」，知行一致）。

## 四、验证方式

```bash
# 连接器状态（静态 + 运行时真值）
python3 "/Users/chenyouqiang/Documents/LawKB/小强律师数字分身系统/07-系统搭建与Skill配置/probe_connectors.py"

# 埋点活性（含 card_consumption / frontdesk / grill 三处）
python3 "/Users/chenyouqiang/Documents/LawKB/小强律师数字分身系统/07-系统搭建与Skill配置/metrics_watchdog.py"
```

---

*来源：小强律师（WorkBuddy）· 2026-10-22 全系统复盘 P0-2 处置*
*关联：[[决策卡-法条唯一主源铁律FR-MAIN-20260927]] · [[RULE-037]]*
