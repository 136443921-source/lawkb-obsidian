#!/usr/bin/env bash
# =============================================================================
# 律师分身·单机密文版 —— 模板目录实例化脚本（自包含，不依赖律所分身资源）
# 用法：
#   bash bootstrap.sh --dry-run          # 预览，零写入（默认）
#   bash bootstrap.sh --apply            # 真正建目录 + 复制推理配置样本
#   bash bootstrap.sh --apply --root <目标目录>
# 安全：默认 dry-run；建目录用 mkdir -p；复制用 cp -n 防覆盖
# =============================================================================
set -euo pipefail

APPLY=false
# 默认根目录 = 本脚本的上一级（即 律师分身系统（单机密文版）/）
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)   APPLY=true ;;
    --dry-run) APPLY=false ;;
    --root)    ROOT="$2"; shift ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
  shift
done

echo "▶ 目标目录: $ROOT"
DIRS=("01-方案" "02-配置" "03-人格层L1" "04-知识层L2" "05-门禁" "06-部署记录" "logs")
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for d in "${DIRS[@]}"; do
  if $APPLY; then
    mkdir -p "$ROOT/$d" && echo "  + 建目录 $d"
  else
    echo "  · [dry-run] 将建目录 $d"
  fi
done

# 复制推理配置样本（不覆盖已有）
if $APPLY; then
  if [[ -f "$PKG_DIR/inference.A.yaml" && ! -f "$ROOT/02-配置/inference.A.yaml" ]]; then
    cp "$PKG_DIR/inference.A.yaml" "$ROOT/02-配置/inference.A.yaml"
    echo "  + 复制 inference.A.yaml → 02-配置/"
  else
    echo "  · 02-配置/inference.A.yaml 已存在或样本缺失，跳过"
  fi
else
  echo "  · [dry-run] 将复制 inference.A.yaml → 02-配置/"
fi

echo "✅ 完成。下一步：编辑 02-配置/inference.yaml，再跑 crypto-l1.sh 做 L1 加密封装。"
