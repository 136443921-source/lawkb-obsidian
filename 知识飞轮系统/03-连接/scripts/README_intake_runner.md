---
created: 2026-08-26T15:34
updated: 2026-08-26T15:59
---
# intake_runner.py 标准运行库 · 使用文档（v1.1）

> 位置：`知识飞轮系统/03-连接/scripts/intake_runner.py`
> 配套：`intake_daily_driver.py`（每日）/ `intake_sunday_driver.py`（周日批）/ `intake_monthly_driver.py`（月度回灌）
> 自检：`python intake_runner.py --selftest`
> 设计目标：根治「每日知识摄入 / 周日批 check_links / 月度回灌」三类写入型自动化共有的 7 大病灶
> （无续跑 / 状态双写不同步 / 失败无升级 / 法条时效靠人工 / 通道判据信面板 / 降级临时补丁 / 交付不可见）。

> **接入状态（2026-08-26）**：三个自动化已全部接入——
> 每日知识摄入 **v1.16**（`DailyRun`）、周日知识维护批处理 **v1.10**（`SundayRun`）、月度回灌 **v2.0**（`MonthlyRun`）。
> 库级增强：`IntakeState(path, libs={})` 支持空库（周日/月度独立状态文件不塞 IMA 5 库骨架）；
> `IntakeConfig.libs` 语义修正（`None`→默认 IMA 5 库，显式 `{}`→空库）；
> `SUNDAY_CONFIG`/`MONTHLY_CONFIG` 的 stages 已对齐各自真实流程（S1~S3/FINAL、M0~M3/FINAL）。

---

## 一、四大模块

| 模块 | 类名 | 职责 | 对应病灶 |
|---|---|---|---|
| 运行态单一真源 | `RunState` / `IntakeState` | 加载/原子写/checkpoint/schema 版本迁移；`totals` 每次写回前由 `ingested` 重算 | ②状态双写不同步 |
| 状态机续跑 | `IntakeMachine` | `resume_plan()` 返回未完成阶段，断点持久化，中断后自动跳过已完成阶段 | ①无 checkpoint/自动续跑 |
| 降级层 | `DegradationLayer` | 220030 截断/持久/通道三类判定；摄入中断铁律；漏窗告警升级阶梯 | ③失败无升级 |
| 法条体检 | `StatuteHealthCheck` | 现行/旧法体检 + exact wording 待核清单 | ④法条时效靠人工 |

附：`SELECT_3` 选文算法（分池/评分/去重/配额，去双重计数）、`make_media_id`（32 位 rawid 构造）、`IntakeConfig`（场景声明）。

---

## 二、每日自动化：如何调用（让"请继续"成为历史）

在自动化 prompt 的运行开头（A0 之前）插入：

```python
from intake_daily_driver import DailyRun
run = DailyRun()                 # 自动 load + new_session + 打印续跑计划
for stage in run.plan:           # run.plan 仅剩未完成阶段；上轮中断则自动跳过已完成
    if stage == "A0":   ... # A0.0/A0.1~A0.3（连接器自检/漏窗）
    elif stage == "A1": ... # SELECT_3 + ima-mcp 取文 + 蓝红蒸馏 + run.ingest(...)
    elif stage == "B":  ... # 4 库同 A1
    elif stage == "A2": ... # 人伤自学习（医疗三类优先）
    elif stage == "A2_5": ... # 省级赔偿标准实时库校验
    elif stage == "C":  ... # 学习资料推荐
    elif stage == "D":  ... # 元典/fasui 案例采集（联动法律检索助手核验法条）
    elif stage == "FINAL": ... # 报告 + 04-LOG + QQ 推送
    run.stage_done(stage)        # 每阶段原子持久化断点（save）
run.finalize()                   # 标记 done
```

**关键变化**：中断（截断/超时）后，下一轮 `DailyRun()` 检测到 `checkpoint.status=='in_progress'` → 自动续跑未完成阶段，**不再需要用户发"请继续"**。

### 单篇 220030 重试（摄入中断铁律）

```python
dec = run.on_fetch_fail(media_id, "220030", channel_ok=True)
# dec['kind']=='persistent_220030' → 已登记 failed_220030，绝不写 ingested
# dec['kind']=='truncation'        → media_id rawid 非 32 位，下轮用 make_media_id 补全长
# dec['kind']=='channel_down'      → 登记 pending_windows 待回补
```

### 法条体检（B/D 阶段）

```python
if run.statute_repealed("公司法", 71):        # True → 旧法，引用即时效错误
    ...
if run.statute_needs_exact("最高法医疗损害解释", 16):  # True → 建议 WebSearch 终核 exact wording
    ...
```

---

## 三、三场景复用（同一套库，已全部接入）

```python
from intake_runner import (IntakeState, IntakeMachine, DegradationLayer,
                           StatuteHealthCheck, DAILY_CONFIG, SUNDAY_CONFIG, MONTHLY_CONFIG)

# 每日摄入：状态文件 ima_intake_state.json，5 库 × 3 篇
st, m, plan = DAILY_CONFIG  # 见 intake_daily_driver.DailyRun

# 周日批 check_links：独立状态文件 check_links_state.json（空库 libs={}，不塞 IMA 骨架）
from intake_sunday_driver import SundayRun
run = SundayRun()                    # plan = ['S1_scan','S2_check_links','S2_5_fix_broken','S3_relink_graph','FINAL']
run.stage_done("S2_5_fix_broken")    # 每阶段原子持久化断点
run.record_fail("S3_relink_graph", "link_cards_rules 异常")  # 失败留痕 → QQ 告警
run.finalize()

# 月度回灌：独立状态文件 monthly_backfill_state.json（空库 libs={}）
from intake_monthly_driver import MonthlyRun
run = MonthlyRun()                   # plan = ['M0_backup','M1_scan','M2_append','M3_log','FINAL']
run.record_backup("/Users/.../self_backup_.../self.md.bak")  # M0 备份留痕（秒级回滚依据）
run.stage_done("M2_append")
run.finalize()
```

三场景共用 `IntakeState`/`IntakeMachine`/`DegradationLayer`/`StatuteHealthCheck`；各自状态文件互不污染
（周日/月度传 `libs={}` 空库，状态文件无 IMA 5 库骨架）。新增场景只需声明一个
`IntakeConfig(name, stages, state_path, quota, libs)` 并镜像 driver 结构。

---

## 四、已固化的历史 bug（写库时顺手修掉，自检锁死）

1. **`score_article` 双重计数**：「要点」同时落在高价值/深度两表 → 被算 +3；已合并去重（同词只计一次，高价值权重优先）。
2. **220030 截断误判**：旧正则 `_[0-9a-f]{32}_` 会错配 media_id **前缀自身尾部 32 位** → 任何含前缀的 id 都被判 rawid 正常；改为 prefix 感知切分（`_rawid_segment_ok`），只校验 rawid 段。
3. **`checkpoint:null` 必崩**：历史文件 `checkpoint` 为 `null`，`setdefault` 不替换 None，后续 `None.setdefault` 崩溃；`_migrate` 改为 isinstance 守卫，遇 null/非预期类型强制重建。
4. **`totals` 双写不同步**：旧流程 list 与 totals 分两处写，曾出现 264 vs 真实 269；`IntakeState.save()` 每次强制 `_recompute_totals()`，`totals` 永远由 `ingested` 重算。
5. **`ingested` dict/str 混排**：旧写回脚本对裸字符串调 `.get` 崩溃；`mid_in`/`_mid_of` 全兼容两种形态。

---

## 五、v1.16 自动化 prompt 补丁（copy-ready，待用户确认后写入）

在 automation-1783920420205 的 prompt **开头**（变更记录之后、「任务目标」之前）插入本段，并把版本行改为 v1.16：

```markdown
> - **v1.16（2026-08-26）运行态工程化**：摄入流水线抽出标准库
>   `知识飞轮系统/03-连接/scripts/intake_runner.py`（IntakeState 单一真源 + 原子写 +
>   schema 版本迁移 / IntakeMachine checkpoint 续跑 / DegradationLayer 220030 判定与告警升级 /
>   StatuteHealthCheck 法条时效体检）+ `intake_daily_driver.py`（每日运行态管理器）。
>   运行开头一律 `from intake_daily_driver import DailyRun; run = DailyRun()`，仅执行
>   `run.plan` 中未完成阶段，每阶段 `run.stage_done(stage)` 持久化断点；中断后下一轮自动续跑，
>   不再需人工"请继续"。220030 失败统一经 `run.on_fetch_fail` 判定（持久失败绝不写 ingested）；
>   法条引用经 `run.statute_*` 体检（旧法/ exact wording 待核）。
>   周日批 check_links、月度回灌复用同一套库（各自独立状态文件）。

## 运行态管理（intake_runner 集成 · v1.16 新增，最先执行）

- 每次运行**第一句**：`from intake_daily_driver import DailyRun; run = DailyRun()`。
  - 若打印 `检测到上轮中断(in_progress)` → 进入**自动续跑**：`run.plan` 仅含未完成阶段，已完阶段跳过。
  - 若打印 `全新运行` → 从 A0 起跑。
- A1/B 每摄入一篇成功：`run.ingest(lib_id, media_id, title, create_time, value)`（幂等）。
- A1/B 单篇取文失败：`dec = run.on_fetch_fail(media_id, code, channel_ok)`；据 `dec['kind']` 处置
  （persistent_220030 → 登记不摄入；truncation → 下轮补全长 rawid；channel_down → 登记漏窗）。
- B/D 引用法条前：`run.statute(law, article)` / `run.statute_repealed(...)` / `run.statute_needs_exact(...)`；
  命中旧法或 exact 待核 → 联动法律检索助手核验，禁止直接落"现行"。
- 每阶段结束：`run.stage_done(stage)`（原子写回断点）。
- 末步结束：`run.finalize()`。
- QQ 推送失败：除响应正文输出外，调用 `run.escalation()` 取告警等级，按阶梯写主题前缀。
```

> ⚠️ 该补丁会改写运行中的每日自动化 prompt。建议用户确认后由 `automation_update(mode=update)` 写入（需附完整新 prompt，已在本文件留存要点）。
