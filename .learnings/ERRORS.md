# 错误记录 (ERRORS)

## 2026-11-09 · 备份目录已存在时 mkdir(exist_ok=True) 仍抛 FileExistsError

- **命令**：执行文书事实底账端到端 CLI 实跑，连续多次 `execution_fact_gate.py set ...`。
- **错误**：`backup_dir.mkdir(exist_ok=True)` 在第二次修改时由 WorkBuddy 文件代理抛出 `FileExistsError: [Errno 17] EEXIST`，后续字段写入中断，签核链未完整执行。
- **根因**：文件代理对已存在目录的 `mkdir(exist_ok=True)` 未按标准库语义静默放行；首次写入不触发，单测只覆盖一次写入时漏检。
- **处置**：先检查 `is_dir()` 并捕获 `FileExistsError`；备份文件名改为「时间戳 + UUID」，避免同微秒覆盖；补连续两次 `set` 的回归测试。
- **状态**：resolved。补回归后 8 项单测全绿；端到端 CLI 实跑 `PRE_SIGN_EXIT=2`、签核后 `check=PASS`、DOCX/XLSX `audit=PASS`。
