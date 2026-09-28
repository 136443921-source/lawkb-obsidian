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
- 建卡：`CRT-20260928-01`（③，责任席位 SEAT-07，处置中），接续 [[CRT-20260927-01]]。
- 晋级：断流**中断日**；下一轮再破 26h ⇒ 断流第 2 日，连续 3 日 ⇒ 升 P1。
- 本次零写入（未跑 scan、未改展示层、未动 plist、未 launchctl）。
- watch：下一轮先看 `.9655_scan.log` 是否出现。若仍无 ⇒ 断流第 2 日。
- **下轮复用**：核销只看 `CRT-20260927-01` §四 四条全满足，**禁止单条 `fresh_h` 触发关闭**——单条 fresh_h 只证明"文件被写新了"。
