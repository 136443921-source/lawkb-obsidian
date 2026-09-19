#!/usr/bin/env bash
# =============================================================================
# 律师分身·单机密文版 —— L1 人格层加密封装工具
# 算法：openssl aes-256-cbc + pbkdf2(iter=600000)
# 密钥：仅存 macOS 钥匙串（security），绝不明文落盘、不在日志/对话打印
# 验收：加密后 round-trip 解密，sha256 一致才放行；密文权限 600
#
# 用法：
#   crypto-l1.sh encrypt <staging_dir> [name]   # 加密某目录为 <name>.L1.tar.gz.enc
#   crypto-l1.sh decrypt <enc_file>   [name]    # 解密到当前目录
#   crypto-l1.sh test                              # 自测（临时目录 round-trip）
# =============================================================================
set -euo pipefail
KEYCHAIN_SVC="lawtwin-l1-lawyer"

encrypt() {
  local src="$1" name="${2:-lawyer-l1}"
  [[ -d "$src" ]] || { echo "❌ 目录不存在: $src" >&2; exit 1; }
  local pwd_raw; pwd_raw="$(openssl rand -base64 32)"
  # 口令只进钥匙串，绝不明文落盘
  security add-generic-password -a "$(id -un)" -s "$KEYCHAIN_SVC-$name" -w "$pwd_raw" -U
  export PWD_RAW="$pwd_raw"
  local tmpout; tmpout="$(mktemp)"
  tar czf - -C "$src" . | openssl enc -aes-256-cbc -pbkdf2 -iter 600000 \
      -out "$tmpout" -pass env:PWD_RAW
  local orig_sha dec_sha
  orig_sha="$(tar czf - -C "$src" . | sha256sum | awk '{print $1}')"
  dec_sha="$(openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \
      -in "$tmpout" -pass env:PWD_RAW | sha256sum | awk '{print $1}')"
  if [[ "$orig_sha" == "$dec_sha" ]]; then
    mv "$tmpout" "$name.L1.tar.gz.enc"
    chmod 600 "$name.L1.tar.gz.enc"
    echo "✅ round-trip 验证通过 (sha256 一致): $dec_sha"
    echo "🔐 密文: $name.L1.tar.gz.enc | 密码已存钥匙串: $KEYCHAIN_SVC-$name"
  else
    rm -f "$tmpout"
    echo "❌ round-trip 失败，已清理" >&2; exit 1
  fi
  unset PWD_RAW
}

decrypt() {
  local encfile="$1" name="${2:-lawyer-l1}"
  [[ -f "$encfile" ]] || { echo "❌ 密文不存在: $encfile" >&2; exit 1; }
  local pwd_raw
  pwd_raw="$(security find-generic-password -a "$(id -un)" -s "$KEYCHAIN_SVC-$name" -w 2>/dev/null)" \
    || { echo "❌ 钥匙串无密码: $KEYCHAIN_SVC-$name" >&2; exit 1; }
  export PWD_RAW="$pwd_raw"
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -in "$encfile" -pass env:PWD_RAW | tar xzf - -C "."
  echo "✅ 已解密到当前目录"
  unset PWD_RAW
}

selftest() {
  local tmp; tmp="$(mktemp -d)"
  echo "display_name: 测试律师" > "$tmp/profile.yaml"
  echo "# 测试人格" > "$tmp/self.md"
  echo "▶ 自测：加密临时目录并 round-trip ..."
  ( cd "$tmp" && encrypt "." "selftest" )
  echo "▶ 自测：解密回临时目录 ..."
  ( cd "$tmp" && decrypt "selftest.L1.tar.gz.enc" "selftest" )
  rm -rf "$tmp"
  echo "✅ crypto-l1.sh 自测通过"
}

case "${1:-test}" in
  encrypt) encrypt "${2:-}" "${3:-lawyer-l1}" ;;
  decrypt) decrypt "${2:-}" "${3:-lawyer-l1}" ;;
  test|selftest) selftest ;;
  *) echo "用法: crypto-l1.sh [encrypt <dir> [name]|decrypt <enc> [name]|test]" >&2; exit 2 ;;
esac
