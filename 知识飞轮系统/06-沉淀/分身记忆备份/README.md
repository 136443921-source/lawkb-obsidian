# 小强律师分身 self.md 双写备份 · 恢复指引

## 恢复（手动）
本脚本仅向前备份，不回写。从某快照恢复：

```bash
SNAP=<快照文件夹名>
SRC_DIR="$HOME/.workbuddy/skills/xiaoqianglvshi"
ROOT=<本目录>
cp "$ROOT/$SNAP/self.md.bak"    "$SRC_DIR/self.md"
cp "$ROOT/$SNAP/persona.md.bak" "$SRC_DIR/persona.md"
cp "$ROOT/$SNAP/SKILL.md.bak"   "$SRC_DIR/SKILL.md"
```

## 校验
- 恢复前比对 `manifest.json` 中 `source_sha256` 与 `shasum -a 256 self.md.bak`。
- 正常 self.md：字节 ≥ 8000、含 `Self Memory`、二级章节 ≥ 6。

## 说明
- 快照内 .md 文件以 `.bak` 后缀存储，是为避免 Obsidian（LawKB 为 vault）对新增
  .md 自动追加 frontmatter 而污染备份；恢复时去掉 `.bak` 即可。
- self.md 头部记载的 combine 工具当前不存在，故快照含 persona.md / SKILL.md 三件套，
  直接复制即可，无需 combine。
- 两处 ROOT 互为冗余：Documents/LawKB/知识飞轮系统/06-沉淀/分身记忆备份
  与 WorkBuddy/Claw/backups/xiaoqiang_self，择一即可。
