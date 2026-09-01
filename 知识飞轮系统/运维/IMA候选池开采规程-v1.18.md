---
title: IMA 候选池开采规程 v1.18
type: 运维规程
created: 2026-08-30
applies_to: automation-1783920420205（每日知识摄入 v1.18）
supersedes: 原 SELECT_3 之 S1「首页候选不足 3 且库较大时用 offset 翻页补足」（该条长期未被执行）
tools: 知识飞轮系统/03-连接/scripts/intake_runner.py（is_folder / filter_articles / unseen_articles / should_keep_paging / pending_folders / crawl_report）
tags:
  - 知识飞轮
  - IMA
  - 摄入流水线
  - 翻页铁律
  - P0
updated: 2026-08-30T19:20
aliases:
  - IMA开采规程
  - 候选池开采规程
related_links:
  - - IMA摄入量衰减诊断报告-2026-08-30
  - - 华宇元典MCP评估与优化建议-2026-08-30
  - - 连接枢纽-运维过程
---

# IMA 候选池开采规程 v1.18
> **🗂️ 相关笔记**：[[IMA摄入量衰减诊断报告-2026-08-30|本规程所修复问题的根因诊断]] · [[华宇元典MCP评估与优化建议-2026-08-30|同日志：元典 MCP 评估]] · [[连接枢纽-运维过程|领域枢纽]]


> **为什么要有这份规程**：2026-08-30 实测确认，每日摄入量从 15 篇/日 跌到 3~6 篇/日，
> 主因是**候选池只取首页 50 条、且未摄入不足 3 篇时未翻页**。合同库根目录实测有 1644 篇文章，
> 脚本只看得到第 10~50 条（前 9 条被文件夹占据），**第 51 条之后的 1603 篇从未进入候选池**。
> 本规程把「翻页 + 递归 + 过滤」固化为可执行步骤，杜绝再次退化。

---

## 一、三条铁律（违反即视为流程缺陷）

1. **翻页铁律**：只要「未摄入的真实文章 < 本库配额」且 `is_end=false`，**必须继续翻页**，
   直到凑够配额或翻到末页（上限 20 页）。**严禁只看首页就交差**。
2. **文件夹过滤铁律**：`media_type=99` / 带 `folder_info` / `media_id` 以 `folder_` 开头
   的条目**一律不是候选**，不得进入 `select_3()`。文件夹名（如"合同协议范本""指导性案例"）
   会命中高价值关键词导致评分虚高，混入后必然 `can_fetch_content=false` 取文失败、白占配额。
3. **递归铁律**：根目录候选耗尽（或不足配额）时，**必须展开子文件夹**继续开采；
   大目录优先（`file_number` 降序）。文件夹内文章与根目录文章同等计入选文池。

---

## 二、执行步骤（每库独立执行）

### S1 深度翻页（解锁根目录存量）

```python
import sys
sys.path.insert(0, "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/03-连接/scripts")
from intake_runner import (filter_articles, unseen_articles,
                           should_keep_paging, pending_folders, select_3)

cands, cursor, pages = [], "", 0
while True:
    page = mcp__ima-mcp__get_knowledge_list(
        knowledge_base_id=LIB_ID, limit=50, cursor=cursor,
        sort_type="UPDATE_TS_DESC_SORT_TYPE")
    cands += page["knowledge_list"]
    pages += 1
    dec = should_keep_paging(page["knowledge_list"], INGESTED_SET,
                             quota=3, is_end=page["is_end"], pages_done=pages)
    if not dec["keep"]:
        break                      # 未摄入够配额 / 已到末页 / 达页数上限
    cursor = page["next_cursor"]
    if not cursor:
        break
```

> 每库 `pages` 与剔除的 `folders` 数须记入统计（末步 `crawl_report()` 出表）。

### S2 文件夹递归（解锁目录内存量）

```python
# 根目录翻完后仍未凑够配额 → 展开子文件夹（大目录优先）
visited, expanded = set(), 0
for f in pending_folders(cands, visited=visited):
    if 已凑够配额: break
    visited.add(f["folder_id"])
    sub = 翻页取尽(knowledge_base_id=LIB_ID, folder_id=f["folder_id"])   # 同 S1 的翻页循环
    cands += sub
    expanded += 1
    # 子文件夹内还可能有孙目录 → pending_folders(sub, visited) 继续入队（递归）
```

- 优先展开 `file_number` 大的目录（首批收益最大）。
- 递归深度不限，但单库总调用量控制在 **≤60 次**/天，超限则本轮到此为止、下轮续采。

### S3 过滤 + 选文

```python
chosen, skipped, stat = select_3(cands, INGESTED_SET, LAST_RUN_TS_MS, quota=3)
# select_3 入口已内置 filter_articles，stat["folders_dropped"] 为剔除的文件夹数
```

### S4 留痕（硬要求）

每日报告「IMA 5 库定点摄入」表下方，**必须**新增一块「候选池开采」统计：

```python
from intake_runner import crawl_report
print(crawl_report(stats_by_lib))
# stats_by_lib = {库名: {"pages":翻页数, "expanded":展开目录数,
#                       "folders":剔除文件夹数, "unseen":未摄入候选数, "chosen":实选数}}
```

同时报告须写明：
- 各库**本轮新开采范围**（如"合同库：翻至第 7 页 + 展开'合同协议范本'等 3 个目录"）
- 各库**剩余未开采估算**（`total_size − Σ已摄入`，不得再写"余量充足"这类无依据表述）

---

## 三、停止条件（任一即停）

| 条件 | 处置 |
|---|---|
| 未摄入真实文章 ≥ 配额（3） | 停，进入选文 |
| `is_end=true`（已到末页） | 停，记「本库根目录已采尽」 |
| 翻页 ≥ 20 页 | 停，记「达翻页上限」，下轮从新 cursor 续采 |
| 单库调用 ≥ 60 次 | 停，记「达调用上限」，下轮续采 |

---

## 四、验收标准

- [ ] 修复后首个运行日，5 库合计摄入应**恢复至 12~15 篇**（而非 3~6 篇）
- [ ] 报告中出现「候选池开采」统计块，且各库 `pages ≥ 1`、`folders > 0`
- [ ] 连续 3 日摄入量稳定 ≥12 篇，且**逐日下降趋势消失**（存量充足，不该递减）
- [ ] 医疗事故(331)/工伤工亡(349)/交通事故(220) 三个目录在 7 日内被首次开采

---

## 五、回滚

改动均在 `intake_runner.py`（备份 `03-连接/scripts/_backup/intake_runner.py.bak_20260830-153320`）
与本规程引用。回滚只需 `cp` 备份覆盖，prompt 的 v1.18 段落删除即可，无数据删除风险。

---

## 相关笔记（Obsidian 互链）

| 笔记 | 关系 |
|---|---|
| [[IMA摄入量衰减诊断报告-2026-08-30]] | 本规程所修复问题的根因诊断 |
| [[华宇元典MCP评估与优化建议-2026-08-30]] | 同日志：元典 MCP 评估 |
| [[连接枢纽-运维过程]] | 领域枢纽 |
