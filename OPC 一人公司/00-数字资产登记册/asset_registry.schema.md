---
created: 2026-09-25T20:36
updated: 2026-09-25T20:41
---
# 数字资产登记册 · 字段定义（Schema）

> 单一事实源（SSOT）：`asset_registry.json`
> 维护者：数字资产运维官｜更新须带 `last_verified` 实测日期

## 顶层字段

| 字段 | 含义 |
|---|---|
| `registry_version` | 登记册自身版本 |
| `generated` | 建册日期 |
| `owner_seat` | 负责维护的席位（本席） |
| `categories` | 资产大类（9 类） |
| `assets` | 资产条目数组 |

## assets 条目字段

| 字段 | 必填 | 含义 |
|---|---|---|
| `id` | ✅ | 资产编号（大类前缀：KB 知识库 / RL 规则库 / CA 卡库 / SK 技能 / CN 连接器 / MP 中台面板 / AU 自动化 / MM 心智手册 / RP 规则包） |
| `name` | ✅ | 资产名称 |
| `category` | ✅ | 9 大类之一 |
| `version` | | 资产版本/归库版本 |
| `owner` | ✅ | 资产归属（人 + 席位） |
| `location` | ✅ | 物理路径（绝对或 ~/ 展开） |
| `status` | ✅ | active / draft / deprecated |
| `commercializable` | ✅ | 是否可商业化（true 才可拆规则包） |
| `billing_domain` | | 计费域（如 慈善合规 / 合同风险 / 多域） |
| `last_verified` | ✅ | **实测核验日期**（铁律：记载须可复测） |
| `source_of_truth` | ✅ | 该资产自身的唯一真源路径 |
| `metrics` | | 量化指标（须带「口径」键说明计数单位） |
| `notes` | | 备注（漂移提示、边界、依赖） |

## 铁律（写入即生效）

1. **报数带口径**：`metrics` 中每个数字必须附「口径」键，说明计数单位与来源。
2. **记载须可复测**：`last_verified` 必填；登记册与实测不符即判「文档漂移」，须回写本册。
3. **先备份再改**：改本册前 `cp` 备份至 /tmp 时间戳目录；改后验幂等。
4. **个案卷宗不入册**：当事人隐私/证件号/证据原件绝不进登记册与规则包。
5. **commercializable 红线**：仅 `true` 资产可拆规则包；规则包定价/定位由运营部门负责人核定，本席不代定商务。

## 相关笔记
- [[制度巡检报告_20260924]] (共现关键词: ---, 登记册)
- [[管理制度登记册]] (共现关键词: ---, 登记册)
- [[registry_consistency_report]] (共现关键词: ---, registry, 登记册)
- [[asset_maturity_report]] (共现关键词: ---, asset)
- [[asset_health_report]] (共现关键词: ---, 实测, asset)
- [[R-LN-114-监控驾驶舱僵尸进程与socket残留骗过健康检查的事故教训]] (共现关键词: ---, 复测)
- [[工具事故卡-模板]] (共现关键词: ---, 复测)
- [[RULE-002---动作（铁律）：依约束「通道不可用即中止，不伪造」→-未触碰-state-文件]] (共现关键词: ---, last)
- [[last_run_report]] (共现关键词: ---, last)
