#!/bin/bash
# ======================================================================
# start_lti_gate.sh — 9655 单机驾驶舱 · LTI 门禁守护一键启动脚本
# ----------------------------------------------------------------------
# 作用：拉起 com.xiaoqiang.lti-gate（lti-gate-daemon），用于 9360 字节
#       副本子屏评分对齐校验中的门禁守护项。
# 适用：在本机「真实 Terminal / 真实 GUI 登录会话」中运行。
#       注意：在 WorkBuddy 沙箱等隔离命名空间内 launchctl 会报
#       "I/O error 5"，此时请回到本机 Terminal 执行本脚本。
# 无需 sudo：本脚本只操作当前用户的 ~/Library/LaunchAgents 用户域。
# 用法：
#   chmod +x start_lti_gate.sh
#   ./start_lti_gate.sh          # 终端运行
#   open start_lti_gate.sh       # 或将其改名为 .command 后双击
# ======================================================================
set -eu

PLIST="$HOME/Library/LaunchAgents/com.xiaoqiang.lti-gate.plist"
LABEL="com.xiaoqiang.lti-gate"
ERR_LOG="/tmp/lti-gate.err"
SOCK="/tmp/lti-gate.sock"
BS_ERR="/tmp/_lti_bootstrap.err"
LD_ERR="/tmp/_lti_load.err"

echo "=============================================="
echo " LTI 门禁守护 (com.xiaoqiang.lti-gate) 一键启动"
echo "=============================================="

# ---- 0. 前置检查 ----
if [ ! -f "$PLIST" ]; then
  echo "❌ plist 不存在: $PLIST"
  echo "   请确认门禁守护的 LaunchAgent 已安装。"
  exit 1
fi
echo "✅ 找到 plist: $PLIST"

# ---- 1. 已在运行则跳过 ----
if pgrep -fl lti-gate-daemon >/dev/null 2>&1; then
  echo "✅ 门禁守护已在运行，无需重复加载。"
  launchctl list 2>/dev/null | grep -i lti-gate
  exit 0
fi

# ---- 2. 加载（bootstrap 优先，load 回退）----
# 注意：bash 内置 UID 为只读变量，不能用其接收 id -u，改用 uid
uid=$(id -u)
echo "当前用户 UID: $uid"

submit_ok=0
if launchctl bootstrap "gui/$uid" "$PLIST" 2>"$BS_ERR"; then
  submit_ok=1
  echo "ℹ️ 已提交 bootstrap gui/$uid 加载请求"
elif launchctl load "$PLIST" 2>"$LD_ERR"; then
  # launchctl load 在 I/O error 5 时仍可能退出码 0，必须查 stderr 判定
  if grep -qi "load failed" "$LD_ERR" 2>/dev/null; then
    submit_ok=0
  else
    submit_ok=1
    echo "ℹ️ 已提交 launchctl load 加载请求（bootstrap 不可用已回退）"
  fi
fi

if [ "$submit_ok" -ne 1 ]; then
  echo "❌ 两种加载方式均被拒绝。"
  echo "---- bootstrap 错误 ----"; cat "$BS_ERR" 2>/dev/null
  echo "---- load 错误 ----";     cat "$LD_ERR" 2>/dev/null
  echo "提示：若报 I/O error 5，说明当前不在本机真实 GUI 会话中，"
  echo "      请在本机 Terminal（非沙箱/SSH 无会话环境）重新运行本脚本。"
  exit 1
fi

# ---- 3. 等待并核验 ----
sleep 1
echo "----------------------------------------------"
echo "核验："
if launchctl list 2>/dev/null | grep -qi lti-gate; then
  echo "✅ launchctl 已登记 $LABEL"
else
  echo "⚠️ launchctl 未登记（可能不在真实 GUI 会话域）"
fi
if pgrep -fl lti-gate-daemon >/dev/null 2>&1; then
  echo "✅ 守护进程 lti-gate-daemon 已在跑"
else
  echo "⚠️ 守护进程未起来，查看错误日志: $ERR_LOG"
  [ -f "$ERR_LOG" ] && tail -n 20 "$ERR_LOG"
fi
if [ -S "$SOCK" ]; then
  echo "✅ 套接字就绪: $SOCK"
else
  echo "⚠️ 套接字未出现: $SOCK"
fi
echo "=============================================="
echo "完成。下次每日校验门禁项应显示 ✅。"
