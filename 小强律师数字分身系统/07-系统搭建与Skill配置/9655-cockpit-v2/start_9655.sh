#!/usr/bin/env bash
# ============================================================
# 9655 单机驾驶舱 — 本地预览一键启动
# 位置: outputs/9655-cockpit-v2/start_9655.sh (与 index.html 同目录)
#
# 用法:
#   ./start_9655.sh           # 若端口已在跑则复用(保活)，否则启动
#   ./start_9655.sh --restart # 杀掉旧进程后重启为受管进程(pidfile+日志)
#
# 访问: http://127.0.0.1:9655/   (令牌登录 / 演示席位, 账号见 README.md)
#
# 安全: 仅绑定 127.0.0.1（单机密文版，不外暴露网络）。
# 说明: 用 os.setsid() 让 http.server 脱离启动它的 shell 进程组,
#       避免被父 shell 退出时回收, 实现真正"保活"。
# ============================================================
set -u

PORT=9655
HOST=127.0.0.1
DIR="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$DIR/.9655.pid"
LOGFILE="$DIR/.9655.log"
# 钉死受管 python，避免依赖系统 python3 解释器差异
PY="/Users/chenyouqiang/.workbuddy/binaries/python/versions/3.13.12/bin/python3"

# 自检: 根路径是否返回 200
is_up() {
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://$HOST:$PORT/" 2>/dev/null)
  [ "$code" = "200" ]
}

# 取占用端口的 PID
port_pid() {
  lsof -ti tcp:"$PORT" 2>/dev/null | head -1
}

# 以全新会话启动 无缓存 http 服务 (serve_nocache.py，彻底脱离父 shell, 实现保活)
start_server() {
  nohup python3 -c "
import os, sys
os.setsid()
sys.exit(os.execvp('python3', ['python3', '$DIR/serve_nocache.py', '$PORT', '$HOST', '$DIR']))
" > "$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"
}

restart=0
[ "${1:-}" = "--restart" ] && restart=1

if [ "$restart" = "1" ]; then
  old=$(port_pid)
  if [ -n "$old" ]; then
    kill "$old" 2>/dev/null && echo "🛑 已停止旧进程 PID $old"
    sleep 1
  fi
  rm -f "$PIDFILE"
fi

# 已在运行 -> 直接保活复用, 不打断当前浏览
if is_up; then
  echo "✅ 服务已在运行: http://$HOST:$PORT/ (PID $(port_pid))"
  exit 0
fi

echo "▶ 启动 9655 单机驾驶舱本地预览 (端口 $PORT, setsid 保活) ..."
cd "$DIR" || exit 1
start_server
sleep 2

if is_up; then
  echo "✅ 启动成功: http://$HOST:$PORT/ (PID $(cat "$PIDFILE"), 日志 $LOGFILE, pidfile $PIDFILE)"
else
  echo "❌ 启动失败, 请查看 $LOGFILE"
  exit 1
fi
