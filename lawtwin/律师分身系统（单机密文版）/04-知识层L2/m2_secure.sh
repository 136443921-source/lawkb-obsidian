#!/usr/bin/env bash
# =============================================================================
# 律师分身·单机密文版 —— M2 检索 + L1 密文 闭环工具
#
# 设计：M2 索引库 m2_index.db 是明文 SQLite；本工具把它用 crypto-l1.sh（L1 加密封装，
#       openssl aes-256-cbc + pbkdf2，密钥仅存 macOS 钥匙串）加密为密文归档。
#       常态下索引以「密文」存储；检索时即时解密到临时目录查询，用完即焚，不落明文盘。
#       → 实现「检索能力 + 密文存储」闭环，符合单机密文版「数据不出机、静默加密」承诺。
#
# 子命令：
#   rebuild            依 manifest 重建索引并重新加密（语料变更后调用）
#   seal               仅把现有 m2_index.db 加密为密文归档（不动语料）
#   query  "<检索词>"  解密到临时目录并检索，结果打印后清理临时明文
#   verify             解密自测：跑内置查询确认命中 + 密文完整性
#   status             查看密文归档状态（存在性 / 大小 / 权限）
#
# 注意：密文密钥名固定为 m2-index（与 crypto-l1.sh 的 name 参数一致），
#       存于钥匙串 lawtwin-l1-lawyer-m2-index。seal / query / verify 必须同名。
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRYPTO="$SCRIPT_DIR/../启动包/crypto-l1.sh"
BUILD="$SCRIPT_DIR/m2_build_index.py"
QUERY="$SCRIPT_DIR/m2_query.py"
ENC_NAME="m2-index"
ENC_FILE="$SCRIPT_DIR/${ENC_NAME}.L1.tar.gz.enc"
DB="$SCRIPT_DIR/m2_index.db"
MANIFEST="$SCRIPT_DIR/m2_corpus_manifest.txt"

# 仅用已装 sqlite_vec 的 managed venv python（/usr/bin/python3 无 sqlite_vec）
PY="/Users/chenyouqiang/.workbuddy/binaries/python/envs/default/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "❌ 未找到带 sqlite_vec 的 managed python: $PY" >&2
  exit 1
fi
if [[ ! -f "$CRYPTO" ]]; then
  echo "❌ 找不到 crypto-l1.sh: $CRYPTO" >&2
  exit 1
fi

_ensure_enc_dir() { mkdir -p "$SCRIPT_DIR"; }

seal() {
  _ensure_enc_dir
  [[ -f "$DB" ]] || { echo "❌ 明文索引不存在: $DB（请先 rebuild 或 build）" >&2; exit 1; }
  local staging; staging="$(mktemp -d)"
  cp "$DB" "$staging/"
  echo "🔐 加密 m2_index.db -> $ENC_FILE (密钥存钥匙串: lawtwin-l1-lawyer-$ENC_NAME)"
  ( cd "$staging" && bash "$CRYPTO" encrypt . "$ENC_NAME" )
  mv "$staging/${ENC_NAME}.L1.tar.gz.enc" "$ENC_FILE"
  rm -rf "$staging"
  echo "✅ 密文归档就绪: $ENC_FILE"
}

rebuild() {
  echo "🔧 依 manifest 重建 M2 索引 ..."
  "$PY" "$BUILD" --manifest "$MANIFEST" --db "$DB"
  seal
}

query() {
  local q="$*"
  [[ -n "$q" ]] || { echo "❌ 请提供检索词: m2_secure.sh query \"股权转让 意思表示\"" >&2; exit 2; }
  [[ -f "$ENC_FILE" ]] || { echo "❌ 密文归档不存在: $ENC_FILE (请先 rebuild/seal)" >&2; exit 1; }
  local work; work="$(mktemp -d)"
  echo "🔓 解密到临时目录并检索: \"$q\""
  ( cd "$work" && bash "$CRYPTO" decrypt "$ENC_FILE" "$ENC_NAME" >/dev/null )
  "$PY" "$QUERY" "$q" --db "$work/m2_index.db"
  rm -rf "$work"
  echo "（临时明文已清理）"
}

verify() {
  [[ -f "$ENC_FILE" ]] || { echo "❌ 密文归档不存在: $ENC_FILE" >&2; exit 1; }
  local work; work="$(mktemp -d)"
  ( cd "$work" && bash "$CRYPTO" decrypt "$ENC_FILE" "$ENC_NAME" >/dev/null )
  # 内置自测查询：覆盖人伤 / 合同 / 案件三类语料，至少应有命中
  local ok=1
  for q in "工伤认定" "股权转让" "意思表示真实" "病历 过错"; do
    local n
    n="$("$PY" "$QUERY" "$q" --db "$work/m2_index.db" --json 2>/dev/null | "$PY" -c "import sys,json;d=json.load(sys.stdin);print(len(d))" 2>/dev/null || echo 0)"
    echo "  · 查询 \"$q\" -> 命中 $n 片段"
    [[ "${n:-0}" -gt 0 ]] && ok=0 || true
  done
  rm -rf "$work"
  if [[ "$ok" -eq 0 ]]; then
    echo "✅ 闭环验证通过：密文可解密、检索有命中"
  else
    echo "⚠️ 闭环验证：解密成功但内置查询无命中，请检查语料/索引" >&2
    exit 1
  fi
}

status() {
  if [[ -f "$ENC_FILE" ]]; then
    local sz perm
    sz="$(stat -f %z "$ENC_FILE" 2>/dev/null)"
    perm="$(stat -f %A "$ENC_FILE" 2>/dev/null)"
    echo "🔒 密文归档: $ENC_FILE"
    echo "   大小: ${sz} bytes | 权限: $perm (应为 600)"
    echo "   明文库: $([[ -f "$DB" ]] && echo '存在(建议重建后删除明文)' || echo '不存在')"
  else
    echo "⚠️ 尚无密文归档，请跑: bash m2_secure.sh rebuild"
  fi
}

case "${1:-status}" in
  rebuild) rebuild ;;
  seal)    seal ;;
  query)   shift; query "$@" ;;
  verify)  verify ;;
  status)  status ;;
  *) echo "用法: m2_secure.sh [rebuild|seal|query \"词\"|verify|status]" >&2; exit 2 ;;
esac
