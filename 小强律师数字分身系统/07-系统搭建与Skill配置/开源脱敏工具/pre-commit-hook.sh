#!/bin/sh
# LawTwin 开源脱敏门禁 —— git pre-commit 钩子
#
# 安装：
#   cp pre-commit-hook.sh /path/to/repo/.git/hooks/pre-commit
#   chmod +x /path/to/repo/.git/hooks/pre-commit
#
# 依赖：把 desensitize_check.py 放到仓库 tools/ 下，或修改下方 CHECKER 路径。
# 姓名名单（可选，本地私有，切勿入库）：
#   默认读取 ~/.lawtwin/names.txt，不存在则跳过姓名检测。

CHECKER="$(git rev-parse --show-toplevel)/tools/desensitize_check.py"
NAMES_FILE="$HOME/.lawtwin/names.txt"

if [ ! -f "$CHECKER" ]; then
    echo "[WARN] 未找到脱敏门禁脚本：$CHECKER"
    echo "       跳过检查（建议尽快补齐，这是开仓库的门票）"
    exit 0
fi

if [ -f "$NAMES_FILE" ]; then
    python3 "$CHECKER" "$(git rev-parse --show-toplevel)" --strict --names-file "$NAMES_FILE"
else
    python3 "$CHECKER" "$(git rev-parse --show-toplevel)" --strict
fi

rc=$?

if [ $rc -ne 0 ]; then
    echo ""
    echo "[BLOCKED] 提交已被脱敏门禁拦截。"
    echo "  处置方式（三选一）："
    echo "    1. 删除或脱敏敏感内容后重新提交"
    echo "    2. 确属样例：在该行末尾或上一行加  desensitize:ignore"
    echo "    3. 整文件豁免：写入 .desensitizeignore"
    echo ""
    echo "  紧急绕过（不推荐，需自行承担泄露风险）：git commit --no-verify"
    exit 1
fi

exit 0
