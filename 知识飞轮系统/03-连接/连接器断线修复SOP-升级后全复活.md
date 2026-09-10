---
title: 连接器断线修复标准 SOP（WorkBuddy 升级后全复活）
type: 运维·SOP
created: 2026-09-09
scope: ~/.workbuddy/connectors/<uuid>/connector-states.json
tags:
  - 连接器
  - SOP
  - ima-mcp
  - 元典
  - 断线修复
  - 安全迁移批量清令牌
updated: 2026-09-09T12:30
---

# 连接器断线修复标准 SOP（WorkBuddy 升级后全复活）

> **适用场景**：每次 WorkBuddy 升级 / 重启后，发现 ima-mcp / 华宇元典-mcp / pkulaw / 腾讯公益 等受管 MCP 调用返回 `401` / `Bearer missing` / 工具清单不出现。
>
> **根因记忆（2026-09-09 实测锁定）**：平台级 MCP 安全迁移（connector-states schema **v3→v4**）会**批量清除 `headerOverrides` 的 Bearer 令牌**——落盘标志 `mcpSecurityMigrated` / `headerOverridesBearerStripped` / `staleManagedAuthHeadersPurged` 三 True 为证。受管 MCP 集体掉线，**非单个连接器随机坏**。→ 升级后一律按本 SOP 复验 + 重授权。

---

## 0. 先诊断（只读，绝不写盘）

跑批量探测脚本，对全部受管 MCP 分类：

```bash
/Users/chenyouqiang/.workbuddy/binaries/python/versions/3.13.12/bin/python3 \
  "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/03-连接/scripts/fix_connector_batch.py"
```

判定含义：

| 判定 | 含义 | 对应亚型 | 修法 |
|---|---|---|---|
| `OK` | enabled+bound+令牌 三件套齐 | 健康 | 无需处理 |
| `B` | enabled=true + bound=true，但 `headerOverrides` 无令牌 | 亚型B 假连接（**仅对走 `headerOverrides` 通道的连接器成立，目前实测仅 `ima-mcp`**） | UI「重新授权/信任」补令牌 |
| `C` | `connectors` 映射无该 id（条目完全缺失） | 亚型C 条目缺失 | UI 完整重连注册 |
| `OFF` | 条目在、但 `enabled=false`（卡死残态） | 半残 | **彻底移除重装** |

命中 `B`/`C` 时脚本已自动追加到 `运维/稳定性监测.md`。

> ⚠️ **2026-09-08 实测重大修正（推翻 09-09 初版第 2 节）**：`fix_connector_batch.py` 的 `B` 判定 = `enabled=true 但 headerOverrides 无令牌`。但实测证明 **受管连接器里只有 `ima-mcp` 把令牌存进 `headerOverrides`**；`yuandian-mcp` / `pkulaw` / `gongyi-open-mcp` 三者**走各自原生授权通道**（元典=`yuandian` CLI、pkulaw/公益=平台自有令牌），令牌**永不写入** `headerOverrides`。因此脚本对这三者报的 `B` **全部是假阳性**——已实测 `yuandian_get_user_balance`=512 积分、`pkulaw.get_law_list`=189 条、`gongyi.get_user_and_org_info`=「贵州省厚德公益基金会/陈友强」，**三者均真实可用**。→ 脚本报 `B` 不等于断线，必须以**实测工具调用**为准（见第 2 节）。

---

## 1. ima-mcp（个人版）启用：彻底移除重装 / 解绑→连接

⚠️ **关键教训（2026-09-09 实测）**：ima 个人版卡 `enabled=false`（脚本判 `OFF`，但 bound+令牌都在）时，**「解绑→连接」前两次都没翻 enabled**（写令牌却不翻 enabled），最终成功是在一次**完整 OAuth 弹窗（登录个人版账号 + 点「同意」）真正走完**的连接之后。

- 若连接器提供「市场彻底移除 / 删除」选项：优先走 移除 → 重新添加+连接（最干净）。
- 若**无移除选项**（如华宇元典仅 解绑/连接）：只能反复 解绑→连接，但**每次都必须等 OAuth 弹窗真跳出来、登录并点「同意」**——令牌与 enabled 都是在弹窗完整完成时落盘的，弹窗没完成 = 白连。
- ima 个人版切记登**个人版**账号（厚德 5 库所在），**勿选 `ima-mcp-oa` 司内版**。
- 走完重启 WorkBuddy，复测应 `ima-mcp = OK`。

> **账号混淆坑**：`ima-mcp`（个人版）与 `ima-mcp-oa`（司内版）是两套独立授权账号。登错账号 → 令牌落错 id → 仍断。

---

## 2. ima-mcp 之外的受管连接器：B 是假阳性，勿盲目重授权 ⚠️ 关键

**实测结论（2026-09-08 复验闭环）**：`yuandian-mcp` / `pkulaw` / `gongyi-open-mcp` 三者**走各自原生授权通道**，令牌**不落** `headerOverrides`，故脚本必报 `B`，但**它们全都真实可用**：

| 连接器 | 原生授权通道 | 实测可用证据 |
|---|---|---|
| `yuandian-mcp` | `yuandian` CLI（`yuandian_authorize_cli`） | `yuandian_get_user_balance` = 512 积分 |
| `pkulaw` | 北大法宝平台自有令牌 | `mcp-law.get_law_list` = 189 条法规 |
| `gongyi-open-mcp` | 腾讯公益平台自有令牌 | `get_user_and_org_info` = 贵州省厚德公益基金会 / 陈友强 |

**操作纪律**：
1. 看到这三者报 `B`，**不要去 UI 重授权**——重授权既无效（令牌不写 headerOverrides，永远还是 `B`）又浪费时间。
2. **唯一可靠的连通性判据 = 实测工具调用**：挑一个该连接器的只读工具跑一次，能返回真实数据即健康。
3. 若实测工具调用**真的 401/超时**，才说明原生令牌本身失效（非 headerOverrides 问题），此时才需去对应平台重授权（元典走第 5 节 CLI；pkulaw/公益走各自平台 UI）。
4. `ima-mcp` 是**唯一**走 `headerOverrides` 的受管连接器，它的 `B` 才是真断（需 UI 重授权补令牌）。

> 该修正已同步到诊断脚本 `fix_connector_batch.py`（v4.0.5）：`B` 判定仅对"曾在 `headerOverrides` 注册过授权"的连接器生效；原生授权类一律判 `OK` 并标注「native-auth，以实测工具调用为准」，不再误报。

## 5. 元典原生授权（yuandian CLI）—— 元典的**唯一**正确修法 ⚠️ 关键

**实测结论（2026-09-09，已验证成功）**：华宇元典-mcp **不走 `headerOverrides` 通用令牌通道**，它用连接器自带的 `yuandian` CLI 原生授权（凭据存于元典自有通道）。因此：
- 无论「解绑→连接」「重新授权」点多少次、OAuth 弹窗多完整，令牌**永远不会**写进 `headerOverrides`，脚本永远判 `B`（这是**假阳性**）；
- 元典 UI 只有「解绑/连接」、无「彻底移除」——那条通路也走不通。

**正确修法（AI 可调工具，用户无需点 UI）**：
1. 调 `mcp__yuandian-mcp__yuandian_prepare_cli` 拿安装指令 → 用官方 `ensure.sh` 安装 `yuandian` CLI（macOS：`tmp=$(mktemp) && curl -fsSL '.../ensure.sh' -o "$tmp" && sh "$tmp" '.../yuandian-cli'`，装到 `~/.local/share/yuandian/yuandian` 并写入 `~/.zshrc` PATH）；
2. 验证：`export PATH="$HOME/.local/share/yuandian:$PATH"` 后 `yuandian version --short`（应 ≥ latest）且 `yuandian version --launcher-protocol` 输出 `1`；
3. 调 `mcp__yuandian-mcp__yuandian_authorize_cli` 拿**一次性授权码 + 登录命令**；
4. 在终端执行该命令（先 `export PATH` 让 `yuandian` 可解析），完成 `yuandian auth login-from-mcp --authorization-code=… --base-url=https://open.chineselaw.com`；
5. 输出「授权成功，有效至 …」即落地；长期凭证本地存储，不回传 MCP。
6. **验证标准**：调 `yuandian_get_user_balance`（返回余额而非 401）= 修复成功。脚本对元典一律判 `OK`（native-auth），**以 `yuandian_*` 工具实际可用为准**。

> ⚠️ 授权码**有时效且一次性**；prepare→install→authorize 三步要连贯。若安装耗时导致码过期，`yuandian_authorize_cli` 重调一次取新码即可（旧码作废无碍）。

---

## 3. 红线（AI 不代做）

- 绝不写盘 `connector-states.json`、不代点 UI 授权。
- 令牌为 **AES-256-GCM 私有加密**，`.credentials.v3.json` 的 `mcpOAuth` 实测全为 3 字节占位值 → AI 无法注入，修复一律交用户在 UI 亲手 OAuth。
- 本环境只做：只读诊断 + 复测。

---

## 4. 复测闭环

全部修复 + 重启后，再跑一次：

```bash
/Users/chenyouqiang/.workbuddy/binaries/python/versions/3.13.12/bin/python3 \
  "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/03-连接/scripts/fix_connector_batch.py"
```

期望输出四个连接器全 `OK`。若仍 `B`/`C`/`OFF`：

- `B` → 重新授权时 OAuth 弹窗没真完成（查账号是否登对、是否点「同意」）
- `C` → UI 完整重连注册没做（区分个人版/司内版）
- `OFF` → ima 走了「解绑→连接」而非「彻底移除重装」，回去重做第 1 步

---

## 关联资产

- 诊断脚本：`03-连接/scripts/fix_connector_batch.py`（只读、不写盘、命中 B/C 自动写 稳定性监测.md）
- 诊断技能：`workbuddy-connector-enabled-gate`（v4.0.4，含 A/B/C 三亚型速判 + 安全迁移批量清令牌根因）
- 复盘报告：`运维/连接器状态复盘-ima-yuandian-2026-09-09.md`
- 守卫：`automation-1784788482072`（每周摄入稳定性监测守卫 v1.6，step 11.5 批量主动探测全受管 MCP，令牌被清当天即告警）
