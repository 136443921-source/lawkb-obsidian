---
id: RULE-033
title: - ToolSearch 实查 `mcp__ima-mcp__*` / `mcp__yuandian-mcp__*` *
type: rule
status: active
updated: 2026-09-22
source_ai: workbuddy
scope: global
confidence: medium
---

# - ToolSearch 实查 `mcp__ima-mcp__*` / `mcp__yuandian-mcp__*` *

- ToolSearch 实查 `mcp__ima-mcp__*` / `mcp__yuandian-mcp__*` **全部 absent** → 判**运行态掉线（会话级）**，**未执行 `--apply`**（符合铁律）

## 相关笔记
- [[WF-074---yuandian-mcp-=-运行态掉线（enabled=true-但工具缺]] (共现关键词: mcp, ---, yuandian)
- [[RULE-040---未回写任何-ingested（摄入中断铁律-+-运行态掉线等恢复）]] (共现关键词: ---, 掉线, RULE)
- [[轨迹卡-R-LN-055-MCP误判事故排查推理链重建-20260917]] (共现关键词: mcp, ---, ToolSearch)
