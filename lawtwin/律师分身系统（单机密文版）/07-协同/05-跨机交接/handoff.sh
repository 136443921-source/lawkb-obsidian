#!/usr/bin/env bash
# =============================================================================
# 律师分身·单机密文版 —— 跨机加密交接工具 handoff.sh
# 场景：律师助理在自己电脑上完成工作，把成果加密交接给律师(老强)。
#
# 信任模型：
#   助理的电脑 = 外部未授信端点。安全边界 = (加密交接文件) + (律师单机)。
#   交接文件已用「角色密钥」端到端加密，传输通道(USB/微信/邮件/微云)无需保密。
#
# 算法：openssl aes-256-cbc + pbkdf2(iter=600000)  (与 crypto-l1.sh 一致)
# 密钥：macOS 钥匙串 lawtwin-handoff-<role>；非 macOS 用 env LAWTWIN_HANDOFF_PWD
#
# 用法：
#   handoff.sh init-role <role>                 律师侧: 生成角色密钥, 打印一次用于线下转交
#   handoff.sh adopt-role <role> <passphrase>   助理侧: 把律师转交的密钥存入本机钥匙串
#   handoff.sh pack <role> <src_dir> [out_dir]  助理侧: 打包+加密为 *.L1handoff.enc + 明文 meta
#   handoff.sh receive <role> <enc_file> [dest] 律师侧: 解密入待审区 + 可选门禁 + 记台账
#   handoff.sh test                             自测 round-trip
# =============================================================================
set -euo pipefail

# macOS BSD tar 默认会把 xattr/AppleDouble 临时写回源目录, 污染 '.'
# 目录 mtime, 导致两次 tar 的 sha 不一致(round-trip 偶发失败)。
# 关闭它, 让归档确定化。
export COPYFILE_DISABLE=1

SVC="lawtwin-handoff"
ITER=600000

need() { [[ -n "$1" ]] || { echo "❌ 缺少必要参数" >&2; exit 2; } }

key_get() {
  local role="$1"
  if command -v security >/dev/null 2>&1; then
    security find-generic-password -a "$(id -un)" -s "$SVC-$role" -w 2>/dev/null
  elif [[ -n "${LAWTWIN_HANDOFF_PWD:-}" ]]; then
    printf '%s' "$LAWTWIN_HANDOFF_PWD"
  else
    echo "❌ 无法获取角色密钥 $role (无钥匙串且无 LAWTWIN_HANDOFF_PWD)" >&2
    exit 1
  fi
}

key_set() {
  local role="$1" pwd="$2"
  if command -v security >/dev/null 2>&1; then
    security add-generic-password -a "$(id -un)" -s "$SVC-$role" -w "$pwd" -U
  else
    echo "⚠️ 非 macOS 环境: 请设置环境变量 LAWTWIN_HANDOFF_PWD 为该密钥后重试" >&2
    exit 1
  fi
}

init_role() {
  local role="$1"; need "$role"
  local pwd; pwd="$(openssl rand -base64 32)"
  key_set "$role" "$pwd"
  echo "✅ 已生成角色密钥并存入本机钥匙串: $SVC-$role"
  echo "⚠️ 下面这串密钥请仅通过线下可信渠道(当面 / 加密 IM)转交助理, 切勿明文落盘或发公网:"
  echo "    $pwd"
  echo "   助理侧执行: handoff.sh adopt-role $role <上面这串>"
}

adopt_role() {
  local role="$1" pwd="$2"; need "$role"; need "$pwd"
  key_set "$role" "$pwd"
  echo "✅ 已把角色密钥 $role 存入本机钥匙串"
}

pack() {
  local role="$1" src="$2" out="${3:-.}"; need "$role"; need "$src"
  [[ -d "$src" ]] || { echo "❌ 源目录不存在: $src" >&2; exit 1; }
  [[ -f "$src/MANIFEST.md" ]] || { echo "❌ 源目录缺少 MANIFEST.md (请先写交接清单: 作者/日期/关联案号/内容摘要)" >&2; exit 1; }
  local pwd; pwd="$(key_get "$role")"
  export PWD_RAW="$pwd"
  local base; base="$(basename "$src")"; [[ "$base" == "." || -z "$base" ]] && base="handoff"
  local enc="$out/$base.L1handoff.enc"
  mkdir -p "$out"
  # 只归档一次(避免二次 tar 触发 BSD tar 把 xattr/AppleDouble 临时写回源目录、
  # 污染 '.' mtime 导致两次归档 sha 不一致的竞态)。
  # 流程: 归档->加密->解密回比(cmp 字节级)->通过再 mv 为最终 .enc
  local tartmp decmp
  tartmp="$(mktemp)"; decmp="$(mktemp)"
  tar czf "$tartmp" -C "$src" .
  openssl enc -aes-256-cbc -pbkdf2 -iter "$ITER" -in "$tartmp" -out "$enc" -pass env:PWD_RAW
  openssl enc -d -aes-256-cbc -pbkdf2 -iter "$ITER" -in "$enc" -out "$decmp" -pass env:PWD_RAW
  if ! cmp -s "$tartmp" "$decmp"; then
    echo "❌ round-trip 失败 (解密还原与原始归档字节不一致)" >&2
    rm -f "$tartmp" "$decmp"; unset PWD_RAW; exit 1
  fi
  rm -f "$tartmp" "$decmp"
  chmod 600 "$enc"
  # 明文 meta 侧车 (不含任何内容, 仅路由信息, 可随文件发送)
  local nfiles; nfiles="$(find "$src" -type f | wc -l | tr -d ' ')"
  {
    echo "role: $role"
    echo "packed_by: $(id -un)@$(hostname)"
    echo "packed_at: $(date +%Y-%m-%dT%H:%M:%S%z)"
    echo "enc_file: $base.L1handoff.enc"
    echo "enc_sha256: $(sha256sum "$enc" | awk '{print $1}')"
    echo "file_count: $nfiles"
  } > "$out/$base.L1handoff.meta"
  echo "✅ 已打包加密: $enc"
  echo "   明文 meta(可随文件发送, 无内容): $out/$base.L1handoff.meta"
  echo "   传输: 把 .enc + .meta 发给律师即可 (通道无需保密, 文件已加密)"
  unset PWD_RAW
}

receive() {
  local role="$1" enc="$2" dest="${3:-./待审交付物}"; need "$role"; need "$enc"
  [[ -f "$enc" ]] || { echo "❌ 密文不存在: $enc" >&2; exit 1; }
  local pwd; pwd="$(key_get "$role")"
  export PWD_RAW="$pwd"
  local ts; ts="$(date +%Y%m%d-%H%M%S)"
  local tgt="$dest/$ts"
  mkdir -p "$tgt"
  openssl enc -d -aes-256-cbc -pbkdf2 -iter "$ITER" -in "$enc" -pass env:PWD_RAW | tar xzf - -C "$tgt"
  echo "✅ 已解密到: $tgt"
  if [[ ! -f "$tgt/MANIFEST.md" ]]; then
    echo "⚠️ 解密后未发现 MANIFEST.md, 请人工核对来源" >&2
  else
    echo "--- MANIFEST.md ---"; cat "$tgt/MANIFEST.md"
  fi
  # 可选: 跑 LTI 门禁 (仅律师侧, 需 05-门禁 守护进程运行中)
  local gate_client=""
  for p in "/Users/chenyouqiang/Documents/LawKB/lawtwin/律师分身系统（单机密文版）/05-门禁/lti-gate-client.py" "./05-门禁/lti-gate-client.py"; do
    [[ -f "$p" ]] && gate_client="$p" && break
  done
  local gate_result="skipped"
  if [[ -n "$gate_client" ]] && command -v python3 >/dev/null 2>&1; then
    if python3 "$gate_client" --ping >/dev/null 2>&1; then
      local r=0
      while IFS= read -r docx; do
        if python3 "$gate_client" "$docx" >/dev/null 2>&1; then
          echo "  [门禁 PASS] $docx"
        else
          echo "  [门禁 REJECT] $docx"; r=1
        fi
      done < <(find "$tgt" -name '*.docx')
      gate_result="$( [[ $r -eq 0 ]] && echo PASS || echo REJECT )"
    else
      echo "ℹ️ LTI 门禁守护进程未运行, 跳过门禁 (稍后手动跑 05-门禁)"
    fi
  fi
  # 记台账
  local log="${WORKLOG:-/Users/chenyouqiang/Documents/LawKB/lawtwin/律师分身系统（单机密文版）/07-协同/03-工作台账/worklog.md}"
  [[ -f "$log" ]] || log="./worklog.md"
  {
    echo ""
    echo "## 交接接收 $(date +%Y-%m-%d\ %H:%M)"
    echo ""
    echo "- 来源角色: $role"
    echo "- 密文: $(basename "$enc")"
    echo "- 落地目录: $ts"
    echo "- 门禁: $gate_result"
    echo "- 接收人: $(id -un)"
  } >> "$log"
  echo "📝 已记入台账: $log"
  unset PWD_RAW
}

selftest() {
  local tmp; tmp="$(mktemp -d)"
  local work="$tmp/work"; mkdir -p "$work"
  echo "author: 助理小美" > "$work/MANIFEST.md"
  echo "# 测试草稿" > "$work/draft.md"
  init_role "selftest" >/dev/null 2>&1 || key_set "selftest" "$(openssl rand -base64 32)"
  pack "selftest" "$work" "$tmp/out"
  receive "selftest" "$tmp/out/work.L1handoff.enc" "$tmp/in"
  # 清掉测试钥匙串条目
  security delete-generic-password -a "$(id -un)" -s "$SVC-selftest" >/dev/null 2>&1 || true
  rm -rf "$tmp"
  echo "✅ handoff.sh 自测通过"
}

case "${1:-test}" in
  init-role) init_role "${2:-}" ;;
  adopt-role) adopt_role "${2:-}" "${3:-}" ;;
  pack) pack "${2:-}" "${3:-}" "${4:-.}" ;;
  receive) receive "${2:-}" "${3:-}" "${4:-./待审交付物}" ;;
  test|selftest) selftest ;;
  *) echo "用法: handoff.sh [init-role|adopt-role|pack|receive|test] ..." >&2; exit 2 ;;
esac
