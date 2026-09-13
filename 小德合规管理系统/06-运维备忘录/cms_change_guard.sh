#!/usr/bin/env bash
# ==========================================================
# cms_change_guard.sh · CMS 变更守卫 v1.0.1
# ----------------------------------------------------------
# 职责：把母本备忘录的「系统一变更 → 备忘录必回写」从纸面协议
#       升级为 **技术强制检测**。
#
# 原理：
#   1) 对 CMS 全部受控文件取 md5 指纹 → .cms_snapshot.tsv
#   2) 同时记录「台账行数 + 母本 version」→ .cms_state.txt
#   3) check 时三态判定：
#        · 无文件变动                → ✅ 无需更新
#        · 有变动 且 台账行数已增加   → ✅ 已回写（提示 mark）
#        · 有变动 且 台账行数未变     → 🔴 未回写，本次迭代【未完成】
#
# 命令：
#   bash cms_change_guard.sh init            初始化 / 重建快照
#   bash cms_change_guard.sh check           检测（默认）
#   bash cms_change_guard.sh mark ["备注"]   回写完成后登记新基线
#   bash cms_change_guard.sh list            列出受控文件清单
#
# 铁律：mark 只能在「台账已追加 + version 已刷新」之后执行。
# 兼容：macOS bash 3.2（避免 local 混合算术赋值、避免变量名紧贴多字节字符）
# ==========================================================

CMS="/Users/chenyouqiang/Documents/LawKB/小德合规管理系统"
MEMO="$CMS/06-运维备忘录"
MASTER="$MEMO/小德合规管理系统-运维手册（五模板版）.md"
SKILL="$HOME/.workbuddy/skills/小德合规管理系统/SKILL.md"
SNAP="$MEMO/.cms_snapshot.tsv"
STATE="$MEMO/.cms_state.txt"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ---------- 受控文件清单（新增系统资产时在此追加）----------
collect() {
  {
    [ -f "$CMS/00-索引-小德合规管理系统制品清单.md" ] && echo "$CMS/00-索引-小德合规管理系统制品清单.md"
    [ -f "$SKILL" ] && echo "$SKILL"
    find "$CMS/01-方案设计" -name '*.md' 2>/dev/null
    find "$CMS/02-落地报告" -name '*.md' 2>/dev/null
    find "$CMS/03-经验卡片" -name '*.md' 2>/dev/null
    find "$CMS/05-系统配置" -name '*.md' 2>/dev/null
    find "$MEMO" -maxdepth 1 -name '*.md' 2>/dev/null
  } | sort -u
}

fingerprint() { md5 -q "$1" 2>/dev/null || echo "ERR"; }

# 台账行数：统计「十八、变更登记台账」段内数据行。
# ⚠️ 历史行存在两种格式（| 2026-… 与 | **2026-…**），正则必须同时兼容，否则漏计。
ledger_n() {
  awk '/^## 十八、变更登记台账/,/^## 附录 A/' "$MASTER" 2>/dev/null \
    | grep -cE '^\|[[:space:]]*\**2026-' | tr -d ' '
}
mver() { grep -m1 '^version:' "$MASTER" 2>/dev/null | sed 's/version:[[:space:]]*//'; }

make_snap() {
  collect | while read -r f; do
    printf '%s\t%s\n' "$(fingerprint "$f")" "$f"
  done
}

write_state() {
  local note="$1"
  {
    echo "LEDGER_N=$(ledger_n)"
    echo "VERSION=$(mver)"
    printf 'MARKED_AT="%s"\n' "$(date '+%Y-%m-%d %H:%M:%S')"
    printf 'NOTE="%s"\n' "$note"
  } > "$STATE"
}

read_state() {
  LEDGER_N=0; VERSION="?"; MARKED_AT="?"; NOTE="?"
  [ -f "$STATE" ] && . "$STATE"
  : "${LEDGER_N:=0}"
}

do_init() {
  make_snap > "$SNAP"
  write_state "init"
  echo "✅ 快照已建立"
  echo "   受控文件: $(wc -l < "$SNAP" | tr -d ' ') 个"
  echo "   台账行数: $(ledger_n)    母本版本: $(mver)"
  echo "   快照: $SNAP  状态: $STATE"
}

do_check() {
  if [ ! -f "$SNAP" ] || [ ! -f "$STATE" ]; then
    echo "⚠️  尚无快照，请先执行: bash $0 init"
    exit 1
  fi
  read_state

  make_snap > "$TMP/now.tsv"

  changed=0; added=0; removed=0

  # 变更 / 新增
  while IFS="$(printf '\t')" read -r h f; do
    [ -z "$f" ] && continue
    old="$(awk -F'\t' -v p="$f" '$2==p{print $1; exit}' "$SNAP")"
    if [ -z "$old" ]; then
      added=$((added + 1)); echo "  ➕ 新增  ${f#$CMS/}"
    elif [ "$old" != "$h" ]; then
      changed=$((changed + 1)); echo "  ✏️  变更  ${f#$CMS/}"
    fi
  done < "$TMP/now.tsv"

  # 删除
  while IFS="$(printf '\t')" read -r h f; do
    [ -z "$f" ] && continue
    if ! grep -qF "	$f" "$TMP/now.tsv"; then
      removed=$((removed + 1)); echo "  ➖ 删除  ${f#$CMS/}"
    fi
  done < "$SNAP"

  total=$((changed + added + removed))
  n_now="$(ledger_n)"
  v_now="$(mver)"
  n_files="$(wc -l < "$TMP/now.tsv" | tr -d ' ')"

  echo "────────────────────────────────────────"
  echo "受控文件: $n_files 个   变动: $total  (改 $changed / 增 $added / 删 $removed)"
  echo "台账行数: $LEDGER_N -> $n_now     母本版本: $VERSION -> $v_now"
  echo "上次登记: $MARKED_AT"
  echo "────────────────────────────────────────"

  if [ "$total" -eq 0 ]; then
    echo "✅ 系统自 $MARKED_AT 以来无变更，备忘录无需更新。"
    exit 0
  fi

  if [ "$n_now" -gt "$LEDGER_N" ]; then
    echo "✅ 检测到变更且台账已追加（+ $((n_now - LEDGER_N)) 行）→ 回写已完成。"
    if [ "$v_now" = "$VERSION" ]; then
      echo "⚠️  但母本 version 未刷新（仍为 $v_now）。若触及基线请同步 version + updated。"
    fi
    echo "👉 确认无误后执行: bash $0 mark \"本次变更摘要\""
    exit 0
  fi

  echo "🔴 未回写！检测到 $total 个文件变更，但台账行数未增加（仍为 $n_now 行）。"
  echo "   按母本铁律：本次迭代视为【未完成】。"
  echo "   请先完成：①追加台账行  ②刷新基线 / version / updated  ③再执行 mark"
  exit 2
}

do_mark() {
  local note="${1:-manual-mark}"
  make_snap > "$SNAP"
  write_state "$note"
  echo "✅ 基线已刷新"
  echo "   台账行数: $(ledger_n)   母本版本: $(mver)   备注: $note"
}

do_list() {
  collect | sed "s|$CMS/||"
  echo "合计: $(collect | wc -l | tr -d ' ') 个"
}

case "${1:-check}" in
  init)  do_init ;;
  check) do_check ;;
  mark)  do_mark "${2:-manual-mark}" ;;
  list)  do_list ;;
  *) echo "用法: bash $0 {init|check|mark [备注]|list}" ;;
esac
