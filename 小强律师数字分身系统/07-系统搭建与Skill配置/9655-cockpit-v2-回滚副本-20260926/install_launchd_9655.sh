#!/bin/bash
#
# install_launchd_9655.sh — 9655 单机运维驾驶舱 launchd 一键脚本（服务保活 + 自动扫描）
#
# 作用：
#   ① com.xiaoqiang.cockpit9655       → 门户服务（RunAtLoad + KeepAlive 崩溃自拉起）
#   ② com.xiaoqiang.cockpit9655.scan  → 实扫管线（每 5 分钟跑 scan_9655.py，刷新 scorecard_data.json + system_registry.json）
#   两者共同实现「系统内数据变化 → 驾驶舱各屏自动更新」的实时骨架。
#
# ⚠️ 此脚本必须在【老强本机】终端执行（WorkBuddy 沙盒内 launchctl load 会报 EIO）。
#    沙盒内只能手动 setsid 起服务，真正的 launchd 保活只能本机落地。
#
# 用法：
#   ./install_launchd_9655.sh          # 默认 = install（装好并验证）
#   ./install_launchd_9655.sh install  # 安装 + 启动 + 验证（服务 + 扫描）
#   ./install_launchd_9655.sh status   # 查看是否已装载 + 服务是否响应
#   ./install_launchd_9655.sh uninstall# 卸载（停止开机自启，不删项目文件）
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# —— 服务 plist（门户常驻）——
SVR_LABEL="com.xiaoqiang.cockpit9655"
SVR_SRC="$SCRIPT_DIR/$SVR_LABEL.plist"
SVR_DST="$HOME/Library/LaunchAgents/$SVR_LABEL.plist"

# —— 扫描 plist（每 5 分钟实扫）——
SCAN_LABEL="com.xiaoqiang.cockpit9655.scan"
SCAN_SRC="$SCRIPT_DIR/$SCAN_LABEL.plist"
SCAN_DST="$HOME/Library/LaunchAgents/$SCAN_LABEL.plist"

PORT=9655
URL="http://127.0.0.1:$PORT/"

is_loaded() { launchctl list 2>/dev/null | awk '{print $3}' | grep -qx "$1"; }
install_one() {
  local label="$1" src="$2" dst="$3" note="$4"
  if [[ ! -f "$src" ]]; then echo "❌ 找不到源 plist：$src" >&2; return 1; fi
  mkdir -p "$HOME/Library/LaunchAgents"
  cp -f "$src" "$dst"
  echo "    ✅ $note 已复制并覆盖旧版"
  if is_loaded "$label"; then launchctl unload "$dst" 2>/dev/null || true; echo "       （先卸载旧实例）"; fi
  launchctl load "$dst"
  if is_loaded "$label"; then echo "    ✅ launchd 已装载：$label"; else echo "    ⚠️ 装载后未出现，请 plutil -lint $dst" >&2; fi
}

do_install() {
  echo "==> [1/2] 门户服务保活"
  install_one "$SVR_LABEL" "$SVR_SRC" "$SVR_DST" "门户服务"
  echo "==> [2/2] 实扫管线（每 5 分钟）"
  install_one "$SCAN_LABEL" "$SCAN_SRC" "$SCAN_DST" "自动扫描"
  sleep 2
  if curl -s -o /dev/null -w "    HTTP %{http_code}\n" "$URL"; then echo "    ✅ 服务已响应 $URL"; else echo "    ⚠️ 服务暂未响应，稍后复查" >&2; fi
  echo
  echo "完成。开机/崩溃后自动拉起服务；每 5 分钟自动重扫刷新驾驶舱数据（无需手动）。"
  echo "手动立即刷新：python3 $SCRIPT_DIR/scan_9655.py"
}

do_status() {
  for label in "$SVR_LABEL" "$SCAN_LABEL"; do
    if is_loaded "$label"; then echo "✅ 已装载：$label"; else echo "❌ 未装载：$label（需 install）"; fi
  done
  if curl -s -o /dev/null -w "HTTP %{http_code}\n" "$URL" 2>/dev/null; then echo "✅ 服务响应正常：$URL"; else echo "⚠️ 服务未响应 $URL"; fi
}

do_uninstall() {
  for label in "$SVR_LABEL" "$SCAN_LABEL"; do
    local dst="$HOME/Library/LaunchAgents/$label.plist"
    if is_loaded "$label"; then launchctl unload "$dst" 2>/dev/null || true; echo "   已 unload：$label"; else echo "   未装载：$label"; fi
    [[ -f "$dst" ]] && rm -f "$dst" && echo "   已删除 $dst"
  done
  echo "完成（项目文件 outputs/9655-cockpit-v2/ 不受影响）。"
}

case "${1:-install}" in
  install)   do_install ;;
  status)    do_status ;;
  uninstall) do_uninstall ;;
  *) echo "用法：$0 [install|status|uninstall]" >&2; exit 1 ;;
esac
