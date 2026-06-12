#!/bin/bash
# ============================================================
# LawKB 日常同步脚本
# 用途：提交本地变更并推送到 GitHub
# 运行方式：bash ~/Documents/LawKB/scripts/git-sync.sh
# ============================================================

set -e

LOCAL_DIR="$HOME/Documents/LawKB"
BRANCH="main"

cd "$LOCAL_DIR"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${YELLOW}📚 LawKB 日常同步${NC}"
echo ""

# 检查是否有变更
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    echo -e "${GREEN}✓ 没有需要提交的变更${NC}"
    exit 0
fi

# 显示变更摘要
echo -e "${YELLOW}变更文件：${NC}"
git status --short
echo ""

# 提交信息
MSG="${1:-weekly backup $(date +%Y-%m-%d)}"

# 添加并提交
git add -A
git commit -m "$MSG"
echo -e "${GREEN}✓ 已提交: $MSG${NC}"

# 推送
git push origin "$BRANCH"
echo -e "${GREEN}✓ 已推送到 GitHub${NC}"
echo ""
