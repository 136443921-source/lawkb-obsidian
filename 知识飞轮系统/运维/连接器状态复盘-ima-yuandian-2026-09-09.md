---
title: ima-mcp / 华宇元典-mcp 状态复盘与根因分析
type: 运维·连接器诊断
created: 2026-09-09
method: 直接读取 connector-states.json（version 4）+ 稳定性监测日志比对
scope: ~/.workbuddy/connectors/<uuid>/connector-states.json
tags:
  - 连接器
  - ima-mcp
  - yuandian-mcp
  - 断线根因
updated: 2026-09-11T19:06
---

# ima-mcp / 华宇元典-mcp 状态复盘与根因分析（2026-09-09）

> 背景：老强反馈"最近几天 ima-mcp 和元典-mcp 老是出问题"。本报告基于**当前落盘真实状态**实测，不凭记忆。

---

## 一、当前真实状态（2026-09-09 10:45 实测）

活跃 config：`~/.workbuddy/connectors/75c7265a-5f11-4420-9e71-be28329d68fd/connector-states.json`（`version: 4`）

**顶层迁移标志（关键）**：
- `mcpSecurityMigrated = True`
- `headerOverridesBearerStripped = True`
- `staleManagedAuthHeadersPurged = True`
- `accountIdentityKey = 75c7265a…||enterprise`

| 连接器 | enabled | bound | headerOverrides 令牌 | 判定 |
|---|---|---|---|---|
| ima-mcp | — | — | 无（条目都不在 connectors 中） | **亚型C（条目缺失）** |
| yuandian-mcp | **true** | true | **无** | **亚型B（假连接）** |
| pkulaw | true | true | 无 | 亚型B（假连接，同批） |
| gongyi-open-mcp | true | true | 无 | 亚型B（假连接，同批） |
| kdocs | false | true | 有 | 已禁用（非问题） |
| github | false | true | 有 | 已禁用（非问题） |
| tencent-docs | false | true | 有 | 已禁用（非问题） |
| qcc-company | false | true | 无 | 已禁用（非问题） |
| qq-mail | false | true | 无 | 已禁用（非问题） |

> 注意：仅有的 3 个**带令牌**的连接器（kdocs/github/tencent-docs）恰好全是 `enabled=false`；而所有 `enabled=true` 的受管 MCP（元典/pkulaw/公益）**令牌全部缺失**。这个分布不是巧合，是迁移的直接后果。

---

## 二、根因（一句话）

**一次平台级 MCP 安全迁移（connector-states schema v3→v4）批量清除了 `headerOverrides` 里的 Bearer 令牌**（`headerOverridesBearerStripped=True` + `staleManagedAuthHeadersPurged=True`）。

- 对 `enabled=true` 的受管 MCP（元典/pkulaw/公益）：条目保留、`enabled` 仍是 true（UI 看着像"已连接"），但**令牌被剥离** → 每次调用缺 Authorization 头 → 401 / "Bearer missing"。即**亚型B 假连接**，**且是批量发生的**。
- 对 ima-mcp：它在迁移前就已是 `enabled=false` 的损坏态（09-04 曾判定根因=enabled=false），迁移时该条目**连同令牌一并被清除**，连 `connectors` 映射里都没有了 → **亚型C 条目缺失**。

**为什么"最近几天老出问题"的时间线**：
- 08-31 ima 曾"自愈待重启"，但复发计数+1；
- 09-03/09-04 确诊 ima 根因=`enabled=false`，需 UI 信任启用；
- 09-05 实测发现元典/pkulaw/公益 三者 `enabled=true` 但令牌缺失（亚型B）——当时已预警"常见同病批次"；
- 09-08 ima 演变为亚型C（条目彻底不在）；
- 09-09（今）落盘实测：v4 迁移标志全部为 True，元典/pkulaw/公益 均为亚型B、ima 为亚型C → **印证安全迁移是批量清令牌的元凶**，而非单个连接器随机坏。

---

## 三、建议方案

### 3.1 华宇元典-mcp（亚型B·假连接）— 最高频受损
- **根因不是开关，是缺令牌**：`enabled` 已经是 true，翻转 enabled 无效。
- **处置（老强 UI 亲手，AI 不代点）**：连接器管理页 → 元典-mcp → 点「**重新授权 / 连接授权 / 信任**」，由 WorkBuddy 完成真实 OAuth 并把令牌加密写回 `headerOverrides` → **重启 WorkBuddy（或开新会话）**，`mcp__yuandian-mcp__*` 工具才会带上鉴权头。
- **验证**：重启后调用一个轻量工具（如 `yuandian_get_user_balance` 查积分余额），能返回数据而非 401 即修复。

### 3.2 ima-mcp（亚型C·条目缺失）
- **根因是条目从未注册进运行时**，翻 enabled 无效（根本没有开关可翻）。
- **处置（老强 UI 亲手）**：连接器管理页 → 若 ima 不在列表需**先添加/安装**（不是单纯"重新连接"）→ 连接并完成 OAuth（须登录持有厚德 5 库的**个人版**账号，**勿选 ima-mcp-oa 司内版**）→ 点「信任/启用」→ **重启 WorkBuddy**，会话工具清单才会出现 `mcp__ima-mcp__*`。

### 3.3 pkulaw / gongyi-open-mcp（同批亚型B·易被忽略）
- 二者与元典**同一批被迁移清令牌**，目前也是"看着连着、实际调不动"的假连接。
- 建议与元典**一并重新授权**，避免只修了元典、过两天发现 pkulaw/公益 也掉。

### 3.4 系统性建议（防复发）
1. **更新后必做"连接器复验"**：每次 WorkBuddy 升级/重启后，主动核对 `connectors` 各条目 `enabled + bound + headerOverrides 令牌` 三件套；发现 `enabled=true 但无令牌` 立即 UI 重新授权。
2. **守卫增强（建议）**：`automation-1784788482072` step11 目前能识别亚型A（enabled=false）和亚型C（条目缺失），建议增补**亚型B 主动探测**——即 `enabled=true && id ∉ headerOverrides` 时标"假连接·待 UI 重新授权"，在令牌被清的当天就告警，而非等调用失败才发现。
3. **批量重授权 SOP**：把"更新后对所有受管 MCP 统一重新授权"作为标准动作，避免逐个排查。

---

## 四、红线重申
- 令牌密文为 AES-256-GCM 私有加密，AI **无法复现/注入**（`.credentials.v3.json` 的 `mcpOAuth` 经实测全是 3 字节占位值，非真 token）。**任何"代点授权/写令牌"都做不到**，必须由老强在 UI 完成 OAuth。
- 本环境不代点：AI 只做只读诊断 + 备份 + （用户显式授权时）翻 enabled 开关；令牌注入与条目注册一律交 UI。

---

## 五、关联资产
- 诊断技能：`workbuddy-connector-enabled-gate`（v4.0.3，含 A/B/C 三亚型速判）
- 守卫：`automation-1784788482072`（每周摄入稳定性监测守卫）
- 历史日志：`运维/稳定性监测.md`（08-31~09-07 ima 反复记录）

## 相关笔记
- [[案例权威源统一规范]] (共现关键词: 2026, yuandian, ---)
- [[连接器断线修复SOP-升级后全复活]] (共现关键词: yuandian, mcp, ---)
- [[2026-09-02]] (共现关键词: mcp, ima, 2026)
- [[R-LN-059-MCP状态会话级误判为常量]] (共现关键词: yuandian, mcp, ---)
- [[WD-06-核验状态码总览卡]] (共现关键词: ---, 状态)
- [[IMA换源阻断状态-2026-09-03-1123]] (共现关键词: mcp, 状态, ima)
