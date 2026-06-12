#!/bin/bash
# ============================================================
# LawKB GitHub 远程仓库一键配置脚本
# 用途：认证 GitHub CLI → 创建私有仓库 → 添加远程 → 推送
# 运行方式：bash ~/Documents/LawKB/scripts/setup-github-remote.sh
# ============================================================

set -e

REPO_NAME="obsidian-lawkb"
REPO_DESC="法律知识库 Obsidian Vault — 法规、案例、合规手册、案件档案"
LOCAL_DIR="$HOME/Documents/LawKB"
BRANCH=$(cd "$LOCAL_DIR" && git branch --show-current 2>/dev/null || echo "main")

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "══════════════════════════════════════════════════════"
echo "  📚 LawKB GitHub 远程仓库配置"
echo "══════════════════════════════════════════════════════"
echo ""

# ---- Step 1: 检查 gh CLI ----
echo -e "${YELLOW}[1/5] 检查 GitHub CLI...${NC}"
if ! command -v gh &>/dev/null; then
    echo -e "${RED}gh CLI 未安装，正在安装...${NC}"
    brew install gh
fi
echo -e "${GREEN}✓ gh CLI 已就绪${NC}"
echo ""

# ---- Step 2: 认证 GitHub ----
echo -e "${YELLOW}[2/5] 认证 GitHub 账号...${NC}"
if gh auth status &>/dev/null; then
    echo -e "${GREEN}✓ 已认证 GitHub 账号${NC}"
    gh auth status
else
    echo "即将打开浏览器完成 GitHub 授权，请在浏览器中确认。"
    echo "如果浏览器未自动打开，请复制终端中显示的代码到 https://github.com/login/device"
    echo ""
    gh auth login --hostname github.com --git-protocol https --scopes repo,workflow -p https
    echo ""
    echo -e "${GREEN}✓ GitHub 认证成功${NC}"
fi
echo ""

# ---- Step 3: 创建远程仓库 ----
echo -e "${YELLOW}[3/5] 创建 GitHub 远程仓库 ${REPO_NAME}...${NC}"
cd "$LOCAL_DIR"

# 检查仓库是否已存在
if gh repo view "$REPO_NAME" &>/dev/null; then
    echo -e "${GREEN}✓ 仓库已存在: $(gh repo view "$REPO_NAME" --json url -q '.url')${NC}"
else
    gh repo create "$REPO_NAME" \
        --private \
        --description "$REPO_DESC" \
        --source=. \
        --push=false
    echo -e "${GREEN}✓ 私有仓库创建成功${NC}"
fi
echo ""

# ---- Step 4: 配置 remote ----
echo -e "${YELLOW}[4/5] 配置 git remote...${NC}"
USERNAME=$(gh api user --jq '.login')
REMOTE_URL="https://github.com/${USERNAME}/${REPO_NAME}.git"

if git remote get-url origin &>/dev/null; then
    EXISTING_URL=$(git remote get-url origin)
    if [ "$EXISTING_URL" = "$REMOTE_URL" ]; then
        echo -e "${GREEN}✓ origin 已指向 ${REMOTE_URL}${NC}"
    else
        echo "更新 origin: ${EXISTING_URL} → ${REMOTE_URL}"
        git remote set-url origin "$REMOTE_URL"
        echo -e "${GREEN}✓ origin 已更新${NC}"
    fi
else
    git remote add origin "$REMOTE_URL"
    echo -e "${GREEN}✓ origin 已添加: ${REMOTE_URL}${NC}"
fi
echo ""

# ---- Step 5: 推送到远程 ----
echo -e "${YELLOW}[5/5] 推送代码到 GitHub...${NC}"
echo "当前分支: ${BRANCH}"
echo "正在推送所有提交和分支..."
git push -u origin "$BRANCH"
echo ""
echo -e "${GREEN}✓ 推送完成${NC}"
echo ""

# ---- 完成 ----
echo "══════════════════════════════════════════════════════"
echo -e "  ${GREEN}🎉 配置完成！${NC}"
echo "══════════════════════════════════════════════════════"
echo ""
echo "  📦 仓库地址: https://github.com/${USERNAME}/${REPO_NAME}"
echo "  🔒 仓库类型: 私有（Private）"
echo "  📂 本地路径: ${LOCAL_DIR}"
echo "  🌿 当前分支: ${BRANCH}"
echo ""
echo "  后续日常推送："
echo "    cd ~/Documents/LawKB && git add -A && git commit -m 'update' && git push"
echo ""
