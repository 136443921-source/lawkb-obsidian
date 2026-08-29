---
tags:
  - add
  - status
  - ...
  - --
  - git
---

# 学习记录 (LEARNINGS)

## 2026-08-27 · git 批量提交特殊文件名解析坑

**现象**：用 `git status --porcelain | sed 's/^...//'` 提取路径后逐文件 `git add -- "$f"`，含空格/中文/书名号的文件名被 git status 加引号包裹（如 `"Clippings/权威发布 - ...md"`），导致 `git add` 把引号当作路径一部分 → `pathspec did not match` 失败。

**正确做法**：
- 优先用 `git add -A`（git 自己解析路径，不受引号影响）。
- 若必须逐文件处理，用 `git status --porcelain -z` 取出 NUL 分隔的原始路径，或 `git diff --cached --name-only -z | xargs -0 ...`。
- 分批提交用 `git diff --cached --name-only -z | xargs -0 -n 500 -J % git commit -m "..." -- %`（注意 `-m` 必须在 `--` 之前，否则被当成 pathspec）。

**教训**：自动化 git 备份脚本不要手动解析 porcelain 文本，直接用 `git add -A` + `git commit`。本任务最终因此补录了 4 批。

## 相关笔记
- [[memory]] (共现关键词: --, git)
