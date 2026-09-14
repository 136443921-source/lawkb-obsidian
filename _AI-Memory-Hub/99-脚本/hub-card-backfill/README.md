---
created: 2026-09-14
updated: 2026-09-14
---
# hub-card-backfill（多设备同步源）

> 本目录是 `~/.workbuddy/skills/hub-card-backfill/` 的 **git 版本真源**，受 LawKB 仓库管理，用于跨设备复用。

## 架构

- **真源（git）**：`LawKB/_AI-Memory-Hub/99-脚本/hub-card-backfill/`（SKILL.md + backfill.py + index_guard.py）
- **运行时（非 git）**：`~/.workbuddy/skills/hub-card-backfill/`，WorkBuddy 从此加载 skill；`~/.workbuddy` 本身非 git 仓库，故以 LawKB 副本作真源。

## 多设备同步（两步，已闭环）

1. 任意设备 `git pull` LawKB → 取得最新真源
2. 运行 `bash 99-脚本/hub-card-backfill/sync_to_skills.sh` → 一键同步到运行时 skills（自动备份旧版到 /tmp）

## 修改规范

- **改在真源**：在本目录改 SKILL.md / backfill.py / index_guard.py，再 `git add` + commit + push
- **勿直接改运行时**：`~/.workbuddy/skills/` 下的副本由 sync 脚本维护，手动改动会在下次 sync 被覆盖
- 撞号防护机制详见经验卡 `EXP-2026-001`
