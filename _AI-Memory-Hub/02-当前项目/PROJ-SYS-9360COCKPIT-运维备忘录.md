---
id: PROJ-SYS-9360COCKPIT
title: 9360 小强总驾驶舱运维备忘录（活文档）
type: project-fact
status: active
memo: true
authoritative: true
updated: 2026-09-16
source_ai: workbuddy
scope: project:cockpit
confidence: high
tags:
  - 驾驶舱
  - 运维
  - 9360
  - 活文档
---

# 🖥 9360 小强总驾驶舱 · 运维备忘录（活文档）

> **活文档声明**：本备忘录为 9360 内部操作版驾驶舱的运维唯一参考。凡对 9360 做任何改动
> （`rbac.js` / `scorecard_data.json` / `subapps/` / 自动化 ID·状态 / SOP / 评分基线），
> **必须同步更新本文件**（刷新文首 `updated` 与「数据快照基准」）。改动后建议在 LawKB 内 `git` 提交留痕。
> 本文件与 `xiaoqiang-cockpit-hub` 技能**非同一系统**，二者已分叉（见 §1）。

| 项 | 值 |
|---|---|
| 访问地址 | `http://127.0.0.1:9360/`（本地，令牌登录） |
| 源目录 | `/Users/chenyouqiang/WorkBuddy/2026-09-12-01-29-05/outputs/cockpit-hub-ops/` |
| 当前服务 | 运行中 · PID 见 `.cockpit_ops.pid`（2026-09-16 实测 HTTP 200） |
| **数据快照基准** | 2026-09-16 18:31（scorecard 总评 77.2 / 良好 B；C5/C7 六维已统一为算法驱动；D2 竞态已根治·sync 改原子写；D2·D4 数据 2026-09-16 16:24） |
| 总评（含九计分屏） | **77.2 / 良好 B**（详见 §4；标签与 rescan 阈值(≥70=B)一致 ✅） |
| 敏感级别 | 🔴 **严禁外发**（含真实案号/当事人/额度/评分） |

---

## 1. ⚠️ 与公网门户 / `xiaoqiang-cockpit-hub` 技能的关键分叉

9360 内部版 ≠ 公网门户（`Claw/cockpit-portal-deploy`，即技能描述的版本）。两者已显著分叉：

| 维度 | 公网门户（技能版） | **9360 内部操作版（本备忘录对象）** |
|---|---|---|
| 登录 | OIDC 真 IdP（Auting/Keycloak） | **演示席位工号+密码**（SHA-256 哈希存 rbac.js，明文不落盘）+ 角色精确配屏（见 §2.1） |
| C5 小德合规 | **预留占位**（reserved.html） | **真实系统**（综合合规指数 61，在管主体 8） |
| C7 | 系统卡族看板 | **合同管理中台** |
| 新增屏 | 无 | **D2 知识冲突中台 / D4 心智模型中台** |
| 子屏来源 | 多数敏感屏已撤公网 → offline.html 本地打开 | **全屏本地化** `./subapps/`，内部可用 |
| 编号体系 | C1–C9 + C0（含 subscreens/scorecard） | **C1–C8 + D1(积分) + D2/D3/D4 监控位 + home(C0)** |
| 用途 | 对外/演示（脱敏） | **仅老强本机运维操作** |

> 结论：`xiaoqiang-cockpit-hub` 技能描述的是**公网门户旧架构**，已滞后于 9360 真实现状。
> 运维 9360 请以本备忘录 + 实扫文件为准，不要套用技能里的 C1–C9 口径。

---

## 2. 组件与服务清单

| 组件 | 路径 / 命令 | 说明 |
|---|---|---|
| 门户主页 | `index.html` + `auth.js` + `rbac.js` | RBAC+SSO 骨架（本地令牌版） |
| 评分数据源 | `scorecard_data.json` | 九屏计分真源（由 rescan 生成） |
| 九屏计分板 | `workbench.html` | 九屏 KPI + 六维迷你柱 + 评分总表 |
| 启动脚本 | `./start_cockpit_hub_ops.sh` | setsid 保活本地服务 |
| 刷新评分 | `rescan_scorecard.py` | 重扫→写 `scorecard_data.json`（六-B 铁律：先备份后写） |
| 一键还原 | `build_restore.py` | 从官方源 1:1 拉取并本地化（**破坏性，须 `--force`+自动备份**） |
| 冲突队列同步 | `sync_conflict_queue.py` | D2 知识冲突中台数据同步 |
| 无缓存服务 | `serve_nocache.py` | 2026-09-16 改造：给响应加 `Cache-Control:no-store`，数据改动即时可见 |
| 日志 / PID | `.cockpit_ops.log` / `.cockpit_ops.pid` | 运行留痕 |

**启动 / 重启**：
```bash
cd /Users/chenyouqiang/WorkBuddy/2026-09-12-01-29-05/outputs/cockpit-hub-ops
./start_cockpit_hub_ops.sh            # 已在跑则复用保活
./start_cockpit_hub_ops.sh --restart  # 杀旧进程并重启为受管进程
```

---

### 2.1 演示席位账号与权限矩阵（统一凭据版，2026-09-16 22:52）

> 演示席位为**统一演示账号**：四席位共用工号 `LZ-001` + 密码 `lz001@2026`（SHA-256 哈希存 `rbac.js`，明文不落盘）。`auth.js` 流程：选席位 → 填统一工号密码 → SHA-256 校验 → **按所选席位签发令牌**进对应视图（已去除「工号角色=所选席位」强校验，避免统一工号被拦）。

| 席位（角色） | 统一工号 | 统一密码 | 可见屏（sites） | 权限管理 |
|---|---|---|---|---|
| 律所主任（owner） | `LZ-001` | `lz001@2026` | home + C1–C8 + D1–D4 全部（13 屏） | ✅ 含 manage |
| 执行/执业律师（lawyer） | `LZ-001` | `lz001@2026` | C1–C8 业务驾驶舱 + D1–D4 中台（共 12 屏，不含 home 导航中枢） | ❌ |
| 律师助理（paralegal） | `LZ-001` | `lz001@2026` | 飞轮(C3)/积分(D1)/合同(C7)/案件(C4)/合规(C5)/幻觉冲突(C8) 六屏 | ❌ |
| 当事人（client，只读） | `LZ-001` | `lz001@2026` | 仅脱敏案件大屏（C4 案件管理中台，1 屏） | ❌ |

**实测结论（2026-09-16 22:52 端到端浏览器验证，统一凭据）**：
- ✅ 四席位均用 `LZ-001 / lz001@2026` 登录成功，并各自进入对应视图（owner/lawyer 13 屏、paralegal 6 屏、client 1 屏）。
- ✅ 错误密码被 `demoErr` 拦截；按所选席位精确配屏，徽标正确（律所主任·管理员 / 执业律师 / 律师助理 / 当事人（只读））。
- ✅ `rbac.js` 的 `users` 表已收敛为单一演示账号；`auth.js` 已去除「工号角色=所选席位」强校验。
- **2026-09-16 23:27 复核纠正**：执业律师席位可见屏由「含 home 的 13 屏」调整为 **C1–C8 + D1–D4 共 12 屏（不含 home 导航中枢）**；端到端浏览器实测 `tabCount=12`（C1车机/C2决策/C3飞轮/C4案件/C5合规/C6模拟/C7合同/C8幻觉/D1积分/D2冲突/D3云/D4心智），与矩阵一致。备份 `/tmp/cockpit_lawyer_12screen_20260916-232705/`。

**⚠️ 部署提醒（待办）**：
- 当事人席位指向 `clm`（案件管理中台），**尚未部署「脱敏版案件大屏」独立子应用**——正式给当事人看前需补建脱敏版（屏蔽真实案号/当事人/额度），或切换 `clm` 为脱敏数据源。
- 统一演示密码为静态哈希，生产环境迁移至真实 IdP（Auting/Keycloak）+ 服务端用户目录。
- **会话保持说明**：登录一次后会话存 localStorage，刷新自动以该席位身份进舱、不弹登录框；切换其他席位需先点页面「登出」清会话。

---

## 3. 屏维度总览（12 站点：home + C1–C8 + D1–D4）

`rbac.js` 的 `sites` 为唯一真源。计分屏 = C1–C8 + **D1**(9 屏，权重合计 1.00)；D2/D3/D4 为监控位（`scoring:false`，不纳入加权）。

| 编号 | key | 名称 | 计分 | 屏级分 | flag | 关键风险（2026-09-16） |
|---|---|---|---|---|---|---|
| C0 | home | 九屏维度（首页） | — | — | — | 本地视图，不加载 iframe |
| **C1** | ev | 车机驾驶舱 | ✅ | **86.2** | false | 等级 L3/支柱5/卡片24/桩位8/告警1（已较旧值 68.5 大幅提升） |
| **C2** | decision | 决策思维舱 | ✅ | **88.3** | false | 卡片388/域17/规则链1734/唯一629 |
| **C3** | flywheel | 知识飞轮舱 | ✅ | **91.8** | false | 卡片408/规则1516/链接33840/孤儿108/规范率97.6% |
| **C4** | clm | 案件管理中台 | ✅ | **66.5** | 🔴 true | 在册2/门禁通过8/预警1/gate_todo2；**产出52 短板** |
| **C5** | xiaode | 小德·合规管理中台 | ✅ | **61.0** | 🔴 true | 综合合规指数61；**R2 审计约定书缺失触发 G8 硬挡、R6 航合表态稿逾期** |
| **C6** | mock | 模拟庭审中台 | ✅ | **62.0** | 🔴 true | 剧本1/**已开庭0**；**产出15 短板** |
| **C7** | contractlifecycle | 合同管理中台 | ✅ | **71.0** | 🔴 true | CG2 合规门禁预警（R-CF 合同域实体卡=0）；CG6 王德明担保高风险敞口 |
| **C8** | lti | AI 幻觉监控舱 | ✅ | **85.1** | false | 累计调用15650/通过率94.57%/拦截2.52%/零命中29/事故卡7 |
| **D1** | credits | 积分监测中台 | ✅ | **78.1** | 🔴 true | **剩余 -2095.05 / 消耗 112.30% / health=29 🔴 超额度** |
| D2 | conflict | 知识冲突中台 | ❌ | null | false | 冲突303/AI裁决96.7%/待复核10；「有人管」闭环 |
| D3 | cloud | 云服务中台 | ❌ | null | false | 云能力4/4/模型29/应用1/**DB 0 表/端用户 0（已开通未启用）**；快照 09-12 未接刷新 |
| D4 | mindmodel | 心智模型中台 | ❌ | null | false | 席位4/ACTIVE 4/最高~98/平均~85/配置v1.4.5 |

> 注：C5/C7 的 `risk` 文案现由 rescan 按采集器**具体风险名**自动生成（含 R2/R6/R8 风险标题、CG2/CG3/CG6 门禁名、6 争议案名，详见 SOP-02）；六维评分已统一为 `scan_scorecard.py` 的**算法驱动**（替代原硬编码基线）。上表为屏级分 / flag / 关键结构的静态快照，动态值以 scorecard 实际为准。

---

## 4. 六维评分基线（scorecard_data.json；基线 09-14 快照，2026-09-16 18:10 经 rescan 统一六维算法刷新）

| 维度 | 值 | 备注 |
|---|---|---|
| 数据新鲜度 fresh | 91.9 | 强 |
| 覆盖完备度 coverage | 89.4 | 强 |
| 运行健康度 health | **72.6** | 中等（被 D1/C5/C6 拖低） |
| 产出有效性 output | 79.0 | 中 |
| 安全合规度 compliance | 78.9 | 中 |
| 自动化程度 automation | 74.6 | 中 |
| **总维度** | **77.2 / 良好 B** | 九屏加权；标签与 rescan 阈值(≥70=B)一致 ✅ |

---

## 5. 事件分级（运维 SLA）

| 级 | 触发 | 响应 |
|---|---|---|
| **P0** | 服务不可访问（非 200）/ 评分 NaN / 数据源全缺失 | 立即，<30min 恢复 |
| **P1** | 单屏 404 / flag 风险未治理（尤其 D1 超额度、C5 合规硬挡） | <2h |
| **P2** | 新鲜度超标 / 评分显著下滑 / 已知缺口（D3 未接刷新、C6 推演未跑） | 当日内 |
| **P3** | 标签色缺失 / 文案笔误 / 编号标签不一致 | 周例行 |

---

## 6. SOP（运维标准动作）

**SOP-01 启动/重启服务**：见 §2 启动命令（`--restart` 才杀旧进程）。
**SOP-02 刷新评分数据源**：
```bash
cd /Users/chenyouqiang/WorkBuddy/2026-09-12-01-29-05/outputs/cockpit-hub-ops
python3 rescan_scorecard.py --dry   # 先预览
python3 rescan_scorecard.py         # 备份旧 json 后写入（六-B 铁律）
```
> 注意：rescan 依赖 `scan_scorecard.py`（位于 `outputs/cockpit-scorecard/`），须**本机运行**（沙箱访问不到本地 LawKB/桌面）。
**SOP-03 新增分屏**：`rbac.js` 的 `sites` 加条目（按 C1→C8→D1/D3/D4 排序）→ `auth.js`/`index.html` 补 `.dot.<字母>` 配色（防无色）→ 若纳入评分须在 `scorecard_data.json` 加屏（含 cno/key/name/six/kpis/weight）→ 跑 `rescan_scorecard.py` 校验权重合计=1.00。
**SOP-04 还原**：`build_restore.py` 会 1:1 覆盖 `index/rbac/auth/scorecard/workbench` 五文件，**默认拒绝执行**；须 `--force` 且会自动备份到 `/tmp/cockpit_hub_ops_restore_backup_<ts>/`。**切勿未备份加 --force**。
**SOP-05 回滚**：从 `/tmp/<名>_<时间戳>` 取最近备份 `cp -n` 还原 → 重启服务。

---

## 7. 🔴 红线（写入型动作必守）

1. **严禁外发**：含真实案号/当事人/额度/评分，与脱敏演示版 `cockpit-hub-demo.app.workbuddy.host` 严格区分。
2. **数据不出所**：本地令牌版不接公网 IdP；敏感屏不部署外网。
3. **改造前必备份**：任何 `rbac.js`/`scorecard_data.json`/`subapps/` 改动前先 `cp -n` 到 `/tmp` 时间戳目录（六-B 铁律）。
4. **旧 `.link` 后端哈希链接不可经工具改写**：已冻结死链（curl 恒 404），一律走可管理活链。
5. **评分真源唯一**：以 `scorecard_data.json` 实扫值为准，禁止凭记忆回填六维。
6. **绝不终端明文打印**：真实案号、当事人姓名、元典余额。

---

## 8. 当前在办 / 待治理（flag 风险清单）

| # | 优先级 | 屏 | 问题 | 处置建议 |
|---|---|---|---|---|
| 1 | **P0/P1** | D1 积分监测 | **剩余 -2095.05、消耗 112.30%、health=29** 已超额度 | 核查元典额度/套餐，必要时充值或限流；定位超额调用源 |
| 2 | P1 | C5 小德合规 | R2 审计约定书主体缺失触发 G8 硬挡、R6 航合表态稿逾期 | 补审计约定书、催办航合表态稿；降 amber→green |
| 3 | P1 | C6 模拟法庭 | 产出15、已开庭0 | 至少跑一轮红蓝推演验证座舱可用 |
| 4 | P2 | C4 CLM | 产出52、gate_warn=1 | 清理门禁预警、补齐产出项 |
| 5 | P2 | C7 合同管理 | CG2 合规门禁预警（R-CF 合同域实体卡=0）、CG6 王德明担保敞口 | 补实体卡或固化人工审查替代说明；跟踪王德明案 |
| 6 | P3 | D3 云监控 | 快照 09-12 未接定时刷新、DB 0 表/端用户 0 | 接入定时刷新或标注「已开通未启用」 |

**技术债 / 数据质量（2026-09-16 17:55 复核，多数已闭环）**：
- ✅ 总评标签已统一为「良好 B」（`grade_of()` 自动计算，≥70=B），不再手工误标。
- ✅ `xiaoqiang-cockpit-hub` 技能已同步至 v1.1.13（分叉对照+备忘录指针），描述滞后问题已解决。
- ✅ **C5/C7 采集器已补建**：`scan_scorecard.py` 新增 `collect_xiaode`/`collect_contractlifecycle`（实扫 `subapps/xiaode/compliance-state.json` 与 `subapps/contract-lifecycle/contract-state.json`）；`rescan` 改为**骨架模式**（以 9360 真源为权威，仅用采集器 raw 刷新 updated/kpis/risk/flag），一键刷新已跑通，C5/C7 动态追新、权重/六维/评分基线稳定。
- ✅ **C5/C7 六维已统一为算法驱动（2026-09-16 18:10）**：`collect_xiaode`/`collect_contractlifecycle` 的六维从硬编码常量改为调用 `scan_scorecard.py` 统一的 `six_*` 六维子函数（fresh/coverage/output/automation/health/compliance 由 JSON 真实数据算出，参数已调校贴合原手工基线：C5 score≈61 / C7 score≈71）；`rescan` 的 `convert()` 对 C5/C7 优先采用采集器算法 scores，彻底消除「硬编码兜底」。`_risk_text()` 已拼出含具体风险名的文案（R2 审计约定书主体缺失 / R6 航合表态稿 / R8 众志救援 / CG2·CG3·CG6 门禁 / 雅菲·道真百益等 6 争议案）。其余 7 屏 six 仍沿用 9360 真源手工基线（不在本轮范围）。
- ✅ **D2 知识冲突中台数据源（2026-09-16 18:24 复核闭环 + 18:31 P3 根治）**：原 18:10 报 `queue.json` line 201 损坏，经 18:23 复测文件已**合法可解析**（413KB，顶层 `count=303`/`resolved_count=293`）——判定为「冲突仲裁 sync 进程并发改写该文件、rescan 读到半截」的**瞬时写入竞态**，非数据损坏；D2 实时数据已恢复（冲突303 / AI裁决96.7% / 待复核10 / 跨卡型291，`updated=2026-09-16 18:24`）。`build_conflict_screen()`/`build_mind_screen()` 的 JSON 解析异常保护**保留为常驻防御**（未来 sync 再竞态时 rescan 不崩、仅降级用骨架值）。✅ **P3 根治已完成（2026-09-16 18:31）**：`sync_conflict_queue.py` 已新增 `atomic_write_json()`（写同目录隐藏临时文件 + `f.flush()`/`os.fsync()` 落盘 + `os.replace` 原子覆盖），`main()` 以原子写替代原 `open(OUT,'w')` 截断写；**跨进程压力测试实证**：旧截断写 3000 次读中半截失败 **2138** 次，新原子写 **0** 次（APFS rename 原子性保证读方永远拿到完整旧版或完整新版）。备份 `/tmp/sync_repair_20260916-182741/`。
- ℹ️ `rescan` 的 `KEY_MAP` 仍列 `cardfamily`（旧 C7 残留映射），但 `convert()` 已显式跳过 cardfamily（9360 无此屏），不污染现网；属无害遗留，可择期清理。

---

## 9. 变更日志

| 日期 | 变更 |
|---|---|
| 2026-09-16 22:52 | **演示席位统一凭据改造**：四席位共用主任凭据（工号 `LZ-001` / 密码 `lz001@2026`）。`rbac.js` 的 `users` 表收敛为单一演示账号；`auth.js` 去除「工号角色=所选席位」强校验、改按所选席位签发令牌。浏览器端到端实测四席位均用统一凭据登录并各自进入对应视图（owner/lawyer 13 屏、paralegal 6 屏、client 1 屏）。备份 `/tmp/cockpit_unify_seat_20260916-225606/`。 |
| 2026-09-16 23:27 | **执业律师席位配屏纠正为 12 屏**：执业律师可见屏由含 home 的 13 屏调整为 C1–C8 业务驾驶舱 + D1–D4 中台共 12 屏（不含 home 导航中枢）。`rbac.js` 的 `lawyer.sites` 去除 `home`；`index.html` 的 `rbac.js` 缓存参数 bump 至 `?v=20260916c`。端到端浏览器实测 `tabCount=12`（C1车机/C2决策/C3飞轮/C4案件/C5合规/C6模拟/C7合同/C8幻觉/D1积分/D2冲突/D3云/D4心智）。备份 `/tmp/cockpit_lawyer_12screen_20260916-232705/`。 |
| 2026-09-16 22:39 | **演示席位认证改造（工号密码 + 角色精确配屏）**：`index.html` 登录浮层改工号密码表单 + `auth.js` 选席位→SHA-256 校验→签发令牌 + `rbac.js` 新增 `users` 账号表（工号+密码哈希）并精确配屏（主任全屏+manage / 律师 C0–C9 / 助理六屏 C3·C4·C5·C7·C8·D1 / 当事人仅 C4 脱敏大屏）。前端只存 SHA-256 哈希不存明文；浏览器端到端实测四席位登录 + 角色隔离全部通过。备份 `/tmp/cockpit_seat_auth_20260916-222654/`、中枢 `/tmp/cockpit_memo_backup_20260916-224057/`。 |
| 2026-09-16 18:31 | **P3 根治：sync_conflict_queue.py 改原子写消除 D2 竞态**：新增 `atomic_write_json()`（写同目录隐藏临时文件 + `f.flush()`/`os.fsync()` 落盘 + `os.replace` 原子覆盖），`main()` 以原子写替代原 `open(OUT,'w')` 截断写；**跨进程压力测试实证**：旧截断写 3000 次读中半截失败 **2138** 次、新原子写 **0** 次（APFS rename 原子性保证读方永远拿到完整旧版或完整新版）。D2 数据源竞态从「瞬时竞态 + 异常保护降级」升级为「写入侧根因消除」。备份 `/tmp/sync_repair_20260916-182741/`。 |
| 2026-09-16 18:10 | **增强 C5/C7 风险名自动显示 + 统一六维评分算法**：① `scan_scorecard.py` 新增 `six_health/six_coverage/six_output/six_compliance/six_automation` 统一六维子函数（合规/合同类标准口径）；② `collect_xiaode`/`collect_contractlifecycle` 六维从硬编码常量改为算法驱动（参数调校贴合原基线：C5 score≈61 / C7 score≈71），并从 JSON 提取 redRiskNames/orangeRiskNames/warnGateNames/disputeNames 风险名；③ `rescan` 的 `convert()` 对 C5/C7 优先采用算法 scores，`_risk_text()` 拼出含具体风险名的文案（R2审计约定书主体缺失、R6航合表态稿、R8众志救援、CG2/CG3/CG6 门禁、雅菲/道真百益等6争议案）；④ 给 `build_conflict_screen`/`build_mind_screen` 加 JSON 解析异常保护（修复 D2 `queue.json` 损坏引发的崩溃）；⑤ 实跑验证：12 屏、总评 77.2/良好 B、C5/C7 动态六维+风险名生效、其余7屏 six 不变；⑥ 备份 `/tmp/unify_six_backup_20260916-181039/`。 |
| 2026-09-16 17:55 | **C5/C7 采集器补建 + rescan 骨架模式 + 一键刷新跑通**：① `scan_scorecard.py` 新增 `collect_xiaode`/`collect_contractlifecycle`（实扫 `subapps/xiaode/compliance-state.json` 与 `contract-lifecycle/contract-state.json`，WEIGHTS 置 0 不影响旧门户总评）；② `rescan_scorecard.py` 的 `convert()` 改为**骨架模式**（以 9360 真源为权威，保留手工权重/六维/评分基线，仅用采集器 raw 刷新 updated/kpis/risk/flag，显式跳过 cardfamily）；③ 护栏由「缺屏 exit 5」放宽为「骨架兜底+警告」；④ 实跑验证：12 屏齐全、总评稳定 77.2/良好 B、C5/C7 动态追新、cardfamily 不污染；⑤ 备份 `/tmp/collector_backup_20260916-175006/`。 |
| 2026-09-16 | **评分标签统一 + 技能同步 + 脚本护栏**：① 修正 9360 `scorecard_data.json` 的 grade 标签 77.2「合格 C」→「良好 B」（符合 `grade_of()` 阈值，原误标）；② 修 `rescan_scorecard.py` 的 `PORTAL_DIR` 错位（原指旧门户，现指 cockpit-hub-ops）+ 加硬护栏（缺 xiaode/contractlifecycle 拒绝写入 exit 5）；③ 定位 `scan_scorecard.py` 的 `COLLECTORS` 仅 8 屏、缺 C5/C7 采集器，故该管线暂不能覆盖 9360；④ 同步 `xiaoqiang-cockpit-hub` 技能至 v1.1.13（分叉对照+备忘录指针+管线缺口）；⑤ 备份至 `/tmp/scorecard_backup_20260916-173434/`。 |
| 2026-09-16 | 建活文档备忘录（首版）。全量复盘确认：9360 已分叉为公网门户之外独立系统；新增 D2 知识冲突 / D4 心智模型两屏；C5 小德合规已成真实系统；D1 积分监测超额度(-2095/112.3%)为头号风险；总评 77.2（标签与阈值存疑，本日已修正）。服务在线 PID 37597。 |
