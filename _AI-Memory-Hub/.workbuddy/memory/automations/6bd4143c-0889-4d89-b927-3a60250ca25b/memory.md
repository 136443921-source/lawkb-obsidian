---
tags:
  - 20
  - 2026
  - 候选
  - legacy
  - 09
---

# 自动化执行记录：遗留资产只读盘点

## 2026-09-27 20:00 执行（首次运行，无历史）

### 执行动作
- 跑 `99-脚本/scan_legacy.py --auto-ingest --include-jsonl --max-ingest 20`
- 复现 top-20 候选并逐条以 `write_back --dry-run` 探测冲突既有 id（探针写 /tmp，未改任何源）
- 读取报告 `04-每日日志/legacy-scan-2026-09-27.md`
- 向 `/Users/chenyouqiang/WorkBuddy/2026-09-14-12-50-52/.workbuddy/memory/2026-09-27.md` 追加高层摘要（新建文件）
- present_files 展示报告

### 结果（高层）
- 扫描：旧库 md 224 命中 / projects jsonl 1437 命中
- 漏斗：原始 840 → 去重 613 → 净化候选 606
- 写回：尝试 20，实际写入 **0**（全部被 0.85 门禁拦截）
- 类型分布：workflow 339 / rule 198 / preference 59 / decision 10
- 20 条 top 候选 = 中枢既有 WF-003~WF-022 完全重复（相似度 1.00，均 2026-09-14 入库）

### 红线核验
- ✅ 只读：源文件零修改
- ✅ 隐私：隐私过滤生效，无个案卷宗入中枢
- ✅ 无静默覆盖：冲突走仲裁拦截，全部挂起未写
- ✅ 幂等：write_back 相似度拦截 + /tmp 备份兜底，无条目被改写

### 后续
- 冲突清单（20 候选 ↔ WF-003~022）已列给老强拍板，默认不重复写入
- 若某源材料有更新，由老强确认后走 `--supersedes` 显式覆盖

### 备注
- scan_legacy 的 do_ingest 在 write_back 返回 exit 2（被拦）时仍 `n+=1`，导致终端打印「自动写回 20 条」为误报；实际 0 写入。属展示文案瑕疵，不影响安全（写回本就被拦）。

## 2026-10-18 20:00 执行（第 2 次运行）

### 执行动作
- 跑 `99-脚本/scan_legacy.py --auto-ingest --include-jsonl --max-ingest 20`（4m5s，只读）
- 读取报告 `04-每日日志/legacy-scan-2026-10-18.md`
- 幂等探针：对 WF-103 重跑 `write_back --dry-run` → 触发"被重复检测拦截" ✅
- 向 `/Users/chenyouqiang/WorkBuddy/2026-09-14-12-50-52/.workbuddy/memory/2026-10-18.md` 创建并写入高层摘要
- present_files 展示报告

### 结果（高层）
- 扫描：旧库 md **0 命中**（600 md 在，但 source_ok 白名单/SUPER 信号未命中）/ projects jsonl **1893 命中**
- 漏斗：原始 909 → 去重 705 → 净化 705
- 写回：**20 条实际写入**（WF-103~WF-122，全部 workflow 类；本次不同于 09-27 全拦截，本次相似度门禁放行）
- 1 条候选（3b4c9071）因 write_back 60s 超时丢弃（无损坏）
- 类型分布：workflow 351 / rule 253 / preference 79 / decision 22
- 无 --supersedes / 冲突提示

### 红线核验
- ✅ 只读：源文件零修改
- ✅ 隐私：PRIV 过滤生效
- ✅ 无静默覆盖：20 条全新建 ID，未改既有条目
- ✅ 幂等：write_back 0.85 门禁 + /tmp 备份 + 重跑探针确认拦截

### 待老强拍板 / 关注
- ⚠️ **内容质量**：20 条 WF 实为原始会话片段/状态报告/系统注入文本，非提炼方法论（例：WF-103 正文是 automation system-reminder 注入；WF-122 是"巡检完成 IN_SYNC"状态报告）。建议目视复核后再定 canonical。
- ⚠️ 旧库收尾落空：xiaoqianglawkb 600 md 命中 0，旧库方法论仍待提炼（scan_legacy 旧库 source_ok 过严）。
- write_back 60s 超时致首条候选丢弃，建议脚本加超时/重试。

## 相关笔记
- [[legacy-scan-2026-09-14]] (共现关键词: 仲裁, legacy, 2026)
- [[legacy-scan-2026-09-27]] (共现关键词: 2026, legacy, 仲裁)
- [[PROJ-模拟法官心智成熟度备忘录]] (共现关键词: 候选, 2026)
- [[2026-09-25]] (共现关键词: 仲裁, 候选, 09)
- [[2026-09-24]] (共现关键词: 候选, 09, 2026)
