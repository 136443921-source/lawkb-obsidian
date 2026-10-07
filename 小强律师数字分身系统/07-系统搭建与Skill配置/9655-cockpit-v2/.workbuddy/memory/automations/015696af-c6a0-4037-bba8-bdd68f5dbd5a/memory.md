# 9655 每日数据校齐 · 执行记忆

> 对应《一人公司全面接管单机版与9655驾驶舱监控方案》§5.10.6 落地步骤第4步。
> 真源位（长期资产位）：`07-系统搭建与Skill配置/9655-cockpit-v2`；baseline：`00-系统总览与运维中心/9655_驾驶舱基线快照.json`。

## 固定要点（下轮直接复用，勿重复摸索）

- 只读脚本：`python3 drift_check_9655.py`（退出码 0=对齐 / 1=口径漂移 / 2=仅健康告警）。只读，可放心跑。
- **红线**：严禁跑 `scan_9655.py`；严禁改展示层（HTML/CSS/rbac.js/屏号/title）。
- **心跳必须单列**：单独取真源位 `scorecard_data.json` 的 `generated_at` 算 `fresh_h`，`>26h` ⇒ 判 ③断流并置顶。不可并入 `drift_count`。
- 卡漂移率（A9）**仅周一**跑 `00-系统总览与运维中心/count_rules.py`（写入型，会重写 `card_scale_baseline.json`）；其余日子一律不跑。
- macOS：BSD grep 不支持 `\|`，否定型一律用 `grep -E "A|B"`。
- 写入动作：`cp -p` 备份到 `/tmp/<tag>_$(date +%Y%m%d_%H%M%S)/` 后 dry-run 再执行。

## 执行记录

### 2026-09-26（周六）·判黄（②类新增 1，③④ 各 0）

- `drift_check_9655.py`：退出码 `0`，`baseline_manual_version=v1.5`，`drift_count=0`，`health_count=0`，`aligned=true`；基线与实车均 19 屏 ⇒ 校齐率 100%。
- 心跳：真源位 `generated_at=2026-09-25 19:37:11`，`fresh_h=13.44h`（≤26h，当日绿）。
- **新发现**：`com.xiaoqiang.cockpit9655` 与 `.scan` 两个 LaunchAgent 的四个路径项仍指向旧一次性会话目录 `WorkBuddy/2026-09-17-16-22-53/outputs/9655-cockpit-v2`；且 `launchctl list` 内**无 `.scan` 任务**（漏加载）。长期资产位 scorecard 冻结 vs 旧目录在自刷 ⇒ 明日 `fresh_h` 必破 26h，判 ③断流。
- 建卡：`知识飞轮系统/02-提炼/经验卡片/飞轮运维/经验卡-9655真源位迁移未完成-launchd仍指旧会话目录-20260926.md`。
- 本次零写入（未跑 scan、未改展示层、未动 plist）。 watch：下一轮开跑前先看 plist 是否已修，若已修则真源位 `fresh_h` 应回落。

### 2026-09-27（周日）·判黄（③断流 1，②④ 各 0）

- `drift_check_9655.py`：退出码 `0`，`v1.5`，`drift_count=0`，`aligned=true`，`health_count=0`，19/19 屏 ⇒ 校齐率 100%。
- **心跳破线**：真源位 `generated_at=2026-09-25 19:37:11`，`fresh_h=38.15h` >26h ⇒ **③断流置顶**。昨日预判兑现。
- 根因定位：两个 plist 的 `ProgramArguments` 已改对长期资产位（`plutil -lint` OK、目标 `.py` 存在），但 **launchctl 两任务均未加载**（`launchctl list \| grep -ic cockpit9655` = 0 ⇒ `scan_9655.py` 从未在真源位跑过）。属"改了文件但没上岗"，与 09-26 的"迁目录没迁调度"不同阶段。
- 假绿三重：`drift_count=0` + 服务 `HTTP 200`（端口 9655 探活）+ 19 屏 100%；只有 `fresh_h` 戳穿盲区。
- 建卡：`CRT-20260927-01`（③，责任席位 SEAT-07 IT运维员，处置中）；卡体 `知识飞轮系统/02-提炼/经验卡片/飞轮运维/经验卡-9655心跳断流-fresh_h38h-扫描任务launchd未加载-20260927.md`。
- 修复（待老强确认，本次按红线未执行）：`launchctl load` 两个 plist → 等 `StartInterval=300` 一轮 → 复跑 `fresh_h ≤26` 核销。
- 晋级：断流第 1 日；09-29 仍 >26h ⇒ 连续 3 日 ⇒ 升 P1 进周报红区。
- 本次零写入（未跑 scan、未改展示层、未动 plist、未 load）。周日不跑 `count_rules.py`。
- watch：09-28 先看是否已 load；若已 load，`fresh_h` 应回落至 ≤26h，否则断流第 2 日。

### 2026-09-28（周一）·判黄（②新增 0，③新增 0，**但③不予核销**）

- `drift_check_9655.py`：退出码 `0`，`v1.5`，`drift_count=0`，`aligned=true`，`health_count=0`，19/19 屏 ⇒ 校齐率 100%。
- 心跳：`generated_at` 跳变为 `2026-09-28 08:24:50`，`fresh_h=0.07h` ≤26h（由 38.15h 回落）。
- **核销陷阱（本轮核心）**：`fresh_h` 回落**不是调度恢复**。取证四条——
  `launchctl list | grep -c cockpit9655` = **0**；`.9655_scan.log`/`.9655_scan.err` **仍不存在**（`.scan` 今日依然一次没跑）；
  `com.xiaoqiang.cockpit.watch` 未 load（其日志停更于 2026-09-16）；`launchctl list | grep cockpit` 仅 `com.xiaoqiang.cockpit.server`（PID 27487，跑的是 **9360** 端口 cockpit-hub-ops，非本链路）。
  ⇒ 按 [[CRT-20260927-01]] §四 四条件核销，仅满足 3/4，判**不予核销、打回处置态**。
- **来源定位**：本机工作日志载 08:25 `automation-8bcf8ea5` 跑 `sync_flywheel_data.py`（改 `flywheel-data.js`，mtime 08:25:41）；
  同批次 08:24:51 改 `scorecard_data.json` 与根 `index.html`。⇒ 是**并行自动化顺带刷新**制造的新鲜度，与 `.scan` 缺口无关。只报事实，未认定违规。
- 监控盲区补记：`curl 127.0.0.1:9655` = HTTP 200 且进程在，但**服务在 ≠ 数据会自己更新**；端口探活不可作为健康凭据。
- 周一卡漂移率：`count_rules.py` 已跑（写入型，写前备份 `/tmp/count_rules_backup_20260928_082949/`），`drift_status=LOCKED`、10/10 OK；同时产出 `card_scale_drift_report.json`（该报告此前容易被忽略，漂移率要看它，不看 stdout）。

### 2026-09-29（周二）·判绿（②③④ 各 0，无新增卡）

- `drift_check_9655.py`：退出码 `0`，`v1.5`，`drift_count=0`，`aligned=true`，`health_count=0`，19/19 屏 ⇒ 校齐率 100%。
- 心跳：`generated_at=2026-09-29 08:28:15`，`fresh_h=0.01h` ≤26h ⇒ 绿。终态复跑与首跑一致。
- **判据反转（本轮核心，已回写 `CRT-20260927-01`）**：守 400s 做自动重复实证，`scorecard_data.json` mtime **08:18:13 → 08:23:15 → 08:28:16**，间隔 **5分02秒 ≈ StartInterval=300**，无干预 ⇒ **`.scan` 调度确实在跑**，`CRT-20260927-01`/`CRT-20260928-01` 核销**持续有效**，不 reopen。
  - 同期 `.9655_scan.log` **0 字节**、mtime 停在 `09-28 11:25:32` ⇒ 该文件由 launchd 建重定向时创建，此后从未落字节。
  - ⇒ **判据三项排序**（此后复用）：① ✅ `scorecard_data.json` mtime 周期性自跳 ≈StartInterval（唯一可靠）；② ❌ `.9655_scan.log` 存在/mtime 在动（会误报断流）；③ ❌ 「log 不存在⇒没跑」（脆弱，09-27 碰巧成立）。
- **只读性对照实验**：T0 mtime → 跑 drift_check → T1 mtime 不变 ⇒ **确证 drift_check 只读**，可每日放心跑。（真源位 scorecard 08:18:13 那跳来源最终未定位，只报事实。）
- 晋级：无断流 ⇒ **不升 P1**，周报无红区。周二不跑 `count_rules.py`（卡漂移率本周不列）。
- 本次写入 2 处（CRT 卡判据补记 + 工作日志），均先备份 `/tmp/crt_backup_20260929_082855/`；未跑 scan、未改展示层、未动 plist、未 launchctl。
- **下轮复用**：① 直接看 `scorecard_data.json` mtime 是否在 ≈5min 周期自跳，这比看 launchctl/log 都准；② 「全绿」判定维持四要件（校齐率≥95% + drift_count=0 + fresh_h≤26 + **数据侧循环实证**）；③ 若某日 mtime 停止自跳 ⇒ 断流成立，先按 §四 四条件核销，勿单凭 fresh_h 关闭。
- 建卡：`CRT-20260928-01`（③，责任席位 SEAT-07，处置中），接续 [[CRT-20260927-01]]。
- 晋级：断流**中断日**；下一轮再破 26h ⇒ 断流第 2 日，连续 3 日 ⇒ 升 P1。
- 本次零写入（未跑 scan、未改展示层、未动 plist、未 launchctl）。
- watch：下一轮先看 `.9655_scan.log` 是否出现。若仍无 ⇒ 断流第 2 日。
- **下轮复用**：核销只看 `CRT-20260927-01` §四 四条全满足，**禁止单条 `fresh_h` 触发关闭**——单条 fresh_h 只证明"文件被写新了"。

### 2026-09-30（周三）·判绿（②③④ 各 0，无新增卡）

- `drift_check_9655.py`：退出码 `0`，`v1.5`，`drift_count=0`，`aligned=true`，`health_count=0`，19/19 屏 ⇒ 校齐率 100%。
- 心跳：`generated_at=2026-09-30 08:22:04`，`fresh_h=0.01h` ≤26h ⇒ 绿。
- **心跳实证（守 320s 双采样）**：scorecard_data.json mtime `08:22:05 → 08:27:06`，delta = **301.2s ≈ StartInterval=300**，无干预 ⇒ `.scan` 调度确在跑，排除 09-28 假绿陷阱（并行自动化刷新 scorecard 致 fresh_h 回落但 scan 未跑）。
- launchctl 双任务已加载：`com.xiaoqiang.cockpit9655`（PID 1334，服务）+ `com.xiaoqiang.cockpit9655.scan`（周期调度）。
- 闭环：`CRT-20260927-01` / `CRT-20260928-01` 核销**持续有效**，不 reopen、不计时。
- 周三：未跑 `count_rules.py`（卡漂移率仅周一，写入型红线）；未跑 `scan_9655.py`；未改展示层；零建卡。
- 本次写入 2 处（工作日志 `2026-09-30.md` + 本记忆），automation memory 改前已备份 `/tmp/cockpit9655_automem_backup_20260930_082800/`。
- **下轮复用**：① 全绿四要件已连续多日成立（校齐率100% + drift=0 + fresh≤26 + mtime 周期自跳≈300s）；② 任何一天 mtime 停止自跳 ⇒ 断流成立，先按 §四 四条件核销；③ 红线不变：禁跑 scan_9655.py、禁改展示层、卡漂移率仅周一。

### 2026-10-06（周二）·判绿（②③④ 各 0，无新增卡，**补跑**）

- **补跑背景**：距上次（09-30 周三）缺 6 天（10-01~10-05 无记忆记录）。按 fresh_h 实测判活，**不按日历天数判断流**。
- `drift_check_9655.py`：退出码 `0`，`v1.5`，`drift_count=0`，`drift=[]`，`health_count=0`，`aligned=true`；基线 19 屏 ↔ 实车 19 屏 ⇒ **校齐率 100%**。
- 心跳：`generated_at=2026-10-06 11:42:32`，`fresh_h=0.01h` ≤26h ⇒ 绿。
- **数据侧实证（守 400s）**：mtime 无干预自跳 `11:42:35 → 11:47:17`，间隔 **282s ≈ StartInterval=300** ⇒ `.scan` 在跑。复跑 drift_check 结果一致 ⇒ 只读性再复证。
- launchctl 现状：`com.xiaoqiang.cockpit9655`(PID 1334)、`.scan`(已 load，09-27 时为 0 匹配)、`com.xiaoqiang.cockpit.watch`(PID 1333，**已 load**)、`com.xiaoqiang.cockpit.server`(PID 1310)。
- **本轮两条新发现（只报事实，未建卡）**：
  ① `cockpit.watch` 现已 load（09-28 记录其未 load、日志停更 09-16）——属**修复恢复**，不建 ④ 卡。
  ② 采样出现 **23s 双跳**（11:47:17 → 11:47:40），除 `.scan` 周期外另有写源动 `scorecard_data.json`，与今日 00:17/11:48 飞轮同步记录中"9655 并发 job 11:47 刷新"吻合。多写源并发，**不属 ②③④ 任一档 ⇒ 不建卡**，列观察项。
- **迁移收口**：旧 `WorkBuddy/2026-09-17-16-22-53/outputs/9655-cockpit-v2/scorecard_data.json` 停于 **09-26 06:50:45，已停止自刷** ⇒ 真源位迁移彻底完成，旧目录抢写风险消除。
- 闭环：`CRT-20260927-01` / `CRT-20260928-01` 核销**持续有效**，不 reopen、不计时。无断流 ⇒ 不升 P1，周报无红区。
- 周二：未跑 `count_rules.py`（卡漂移率仅周一）；未跑 `scan_9655.py`；未改展示层；未动 plist；未 launchctl。
- 本次写入 2 处（工作日志 `2026-10-06.md` + 本记忆），写前备份 `/tmp/cockpit9655_backup_20261006_115005/`。
- **下轮复用**：① 判绿四要件（校齐率≥95% + drift=0 + fresh≤26 + 400s 自跳实证）继续照做；② `cockpit.watch` 已上岗，若后续 watch 再写 scorecard，**要分清是 watch 造的新鲜度还是 `.scan` 的自跳**——判据仍是 mtime 周期（≈300s）而非单次 fresh_h；③ 红线不变。
