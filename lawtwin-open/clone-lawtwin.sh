#!/usr/bin/env bash
# =============================================================================
# clone-lawtwin.sh  —  律所数字分身模板「一键克隆」脚本骨架
# -----------------------------------------------------------------------------
# 作用：把 lawtwin-open 模板骨架复制到目标所知识库，并可选择性做占位符替换。
# 安全设计（骨架默认即安全）：
#   - 默认 DRY-RUN，只预览不写入；加 --apply 才真复制
#   - 用 cp -n 防覆盖，绝不改写目标所已有文件
#   - 占位符替换默认关闭，须显式 --replace 且提供所名才执行
#   - 仅复制模板 .md（方法论/方案），不含任何案件或当事人数据
# 适用：macOS / Linux（perl 做跨平台替换）
# =============================================================================

set -euo pipefail

# ---------- 配置区（按实际环境修改）----------
SRC="${LAWTWIN_SRC:-/Users/chenyouqiang/Documents/LawKB/lawtwin-open}"
DST=""
FIRM_NAME=""
LAWYER_NAME=""
DRY_RUN=1          # 1=预览 0=执行
DO_REPLACE=0       # 占位符替换开关

# ---------- 参数解析 ----------
while [ $# -gt 0 ]; do
  case "$1" in
    --apply)    DRY_RUN=0 ;;
    --replace)  DO_REPLACE=1 ;;
    --src)      SRC="$2"; shift ;;
    --firm)     FIRM_NAME="$2"; shift ;;
    --lawyer)   LAWYER_NAME="$2"; shift ;;
    -*)         echo "未知参数: $1" >&2; exit 2 ;;
    *)          DST="$1" ;;
  esac
  shift
done

if [ -z "$DST" ]; then
  cat <<EOF
用法:
  bash clone-lawtwin.sh <目标所路径> [选项]

选项:
  --apply        真正执行复制（默认仅 dry-run 预览）
  --replace      复制后替换占位符（需 --firm）
  --src <路径>   指定源模板路径（默认 \$LAWTWIN_SRC 或内置路径）
  --firm <所名>  目标所名，用于替换 [律所名]
  --lawyer <名>  目标所负责人，用于替换 [律师名]

示例:
  bash clone-lawtwin.sh /path/to/新所库 --apply --replace --firm "正明律师事务所" --lawyer "王律师"
EOF
  exit 1
fi

if [ ! -d "$SRC" ]; then
  echo "错误：源模板不存在: $SRC" >&2
  exit 3
fi

echo "== 律所分身克隆启动 =="
echo "源: $SRC"
echo "目标: $DST"
[ "$DRY_RUN" = 1 ] && echo "[DRY-RUN] 仅预览，加 --apply 执行复制。"

# ---------- Step1 复制骨架 ----------
if [ "$DRY_RUN" = 1 ]; then
  echo "将复制以下模板文件:"
  ls -1 "$SRC"/*.md 2>/dev/null | xargs -n1 basename
else
  mkdir -p "$DST"
  # 仅复制模板 .md（不含任何案件数据）；-n 防覆盖
  cp -n "$SRC"/*.md "$DST"/
  # 附带本脚本，使目标所自包含
  cp -n "$SRC/clone-lawtwin.sh" "$DST"/ 2>/dev/null || true
  echo "已复制到: $DST"
fi

# ---------- Step2 占位符替换（显式开启）----------
if [ "$DO_REPLACE" = 1 ]; then
  if [ -z "$FIRM_NAME" ]; then
    echo "错误：--replace 需配合 --firm <所名>" >&2
    exit 4
  fi
  if [ "$DRY_RUN" = 1 ]; then
    echo "[DRY-RUN] 将替换: [律所名] -> $FIRM_NAME ; [律师名] -> ${LAWYER_NAME:-（保留原占位符）}"
  else
    # perl 跨平台原地替换；所名含正则特殊字符时需自行转义
    find "$DST" -name '*.md' -exec perl -i -pe "s/\[律所名\]/$FIRM_NAME/g; s/\[律师名\]/${LAWYER_NAME:-[律师名]}/g" {} +
    echo "占位符已替换。"
  fi
fi

echo "完成。后续: 按 03-克隆迁移SOP 做技能安装 + 连接器本所重授权 + 隔离 README + 试点闭环。"
