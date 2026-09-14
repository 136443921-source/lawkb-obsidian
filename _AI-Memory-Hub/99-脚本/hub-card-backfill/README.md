# hub-card-backfill（镜像副本）

> ⚠️ 本目录是 `~/.workbuddy/skills/hub-card-backfill/` 的**镜像副本**，用于跨设备复用。

- **运行时位置**：仍为 `~/.workbuddy/skills/hub-card-backfill/`（WorkBuddy 从 skills 目录加载 skill，`~/.workbuddy` 非 git 仓库，故无法直接纳入版本控制）。
- **本副本用途**：中枢 git 仓库（LawKB）受 git 管理，任意设备 `git pull` 即可取得最新版，再手动 `cp -r` 回 `~/.workbuddy/skills/` 即生效——这是当前唯一的多设备同步通道。
- **修改以源为准**：改脚本请改 `~/.workbuddy/skills/hub-card-backfill/`，改完手动 `cp` SKILL.md + backfill.py 回本目录并重提交，保持镜像与源同步。
- **当前版本含撞号防护**：`parse_index_ids()` 解析 `{id: 文件名}`；`update_index()` 仅当 id 指向**同文件**才幂等跳过，**异文件占同一 id 则 `[ABORT] 撞号` 中止、不写不提交**（严禁覆盖他人卡片）。详见经验卡 `EXP-2026-001`。
