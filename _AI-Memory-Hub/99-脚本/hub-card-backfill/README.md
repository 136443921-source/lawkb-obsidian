---
created: 2026-09-14
updated: 2026-09-14

tags:
  - hub
  - backfill
  - 共现
  - 医疗纠纷
  - git
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

## 相关笔记
- [[DEC-2026-003-确立记忆中枢]] (共现关键词: 关键词, git, 共现)
- [[LEARNINGS]] (共现关键词: 关键词, git, 共现)
- [[AI工具WorkBuddy篇8换电脑后数据如何迁移]] (共现关键词: 关键词, workbuddy, 医疗)
- [[WF-085---脚本：`Userschenyouqiang.workbuddyskills_]] (共现关键词: workbuddy, skills)
- [[换电脑后WorkBuddy如何迁移]] (共现关键词: 关键词, git, 共现)
- [[02-skills-manifest]] (共现关键词: skills, 共现)
- [[WF-049-部署前先侦查目标app生命周期避免误推退役app]] (共现关键词: 2026, 关键词, 真源)
- [[经验卡-C3知识飞轮中台刷新事故-部分同步与双份漂移-20260914]] (共现关键词: 2026, 真源)
- [[经验卡-规范清单硬编码必漂移-单一真源教训]] (共现关键词: 2026, 真源, 共现)
- [[共享记忆协议-v1.0]] (共现关键词: 2026, backfill, git)
- [[DEC-2026-005-中枢提交规范化四层闭环思维轨迹]] (共现关键词: 2026, backfill, git)
- [[_索引]] (共现关键词: hub, backfill, card)
- [[2026-09-19]] (共现关键词: hub, 2026)
- [[20260915-规则库归库P0-单一真源建设]] (共现关键词: 2026, 真源)
- [[R-PI-381-医疗纠纷新形势与预防裁判规则]] (共现关键词: 2026, card)
- [[R-PI-383-医院法治建设嵌入三路径裁判规则]] (共现关键词: 2026, card)
- [[2026-09-17-慈法合规hub补索引]] (共现关键词: 2026, hub, git)
- [[EXP-2026-001-补卡并发撞号事故与防护]] (共现关键词: 2026, backfill)
- [[PREF-006-中枢git提交统一走backfill]] (共现关键词: py, git, backfill)
- [[一定要尽早用这个AI工具workbuddy的100条实操攻略]] (共现关键词: 2026, workbuddy)
- [[模拟法庭系统运维手册-v2-2026-09-06]] (共现关键词: 2026, workbuddy)
