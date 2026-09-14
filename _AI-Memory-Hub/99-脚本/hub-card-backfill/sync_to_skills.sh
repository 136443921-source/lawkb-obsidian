#!/usr/bin/env bash
# sync_to_skills.sh — 把 LawKB git 真源同步到 WorkBuddy 运行时 skills 目录
# 用法：bash /Users/chenyouqiang/Documents/LawKB/_AI-Memory-Hub/99-脚本/hub-card-backfill/sync_to_skills.sh
set -e
SRC="/Users/chenyouqiang/Documents/LawKB/_AI-Memory-Hub/99-脚本/hub-card-backfill"
DST="/Users/chenyouqiang/.workbuddy/skills/hub-card-backfill"
mkdir -p "$DST"
BK="/tmp/hub_skill_sync_bak_$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BK"
echo "同步 hub-card-backfill -> $DST"
for f in SKILL.md backfill.py index_guard.py; do
  [ -f "$DST/$f" ] && cp "$DST/$f" "$BK/$f"
  cp "$SRC/$f" "$DST/$f"
  echo "  synced $f"
done
rm -rf "$DST/__pycache__"
echo "done (old backed up at $BK)"
