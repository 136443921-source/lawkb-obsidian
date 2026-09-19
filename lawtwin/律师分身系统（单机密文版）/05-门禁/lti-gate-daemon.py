#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTI 门禁 · 独立进程守护程序（G2 交付物）

设计目标
--------
把成熟的 LTI 交付门禁 `lti_gate.py`（小强律师数字分身系统，v4.8.6，131 测试全绿）
从 WorkBuddy skill 上下文里**解耦**出来，变成一个常驻、可独立调用的进程。
任何上游（M1 推理、docx 导出流水线、人工交付前校验）都可以通过本地 Unix
socket 把待交付文档「递」给本进程，拿到结构化的 PASS / REJECT 判定，而不必
关心 LTI 内部 26 个脚本、缓存、元典连线等复杂度。

安全铁律（单机密文版）
----------------------
1. **零外联（airgap）默认开启**：派生子进程执行 lti_gate 时，主动剥离
   `YD_API_KEY` / `YD_API_KEY_REST` 等环境变量，使 `api_key_ready()` 恒为 False，
   从而**不触发元典 REST 自动核验**（LTI 运维手册 §4.2.1 Level3）。案例存在性
   核验（T502）退化为「提取案号 → 比对本地缓存 → 写 pending_verify.json →
   提示会话协办回填」，绝不偷偷连公网。
2. **只校验、不落正文**：门禁本身不写文档正文；pending_verify.json 只存案号
   指纹，符合「审计不落正文」原则。
3. **不修改被封装代码**：lti_gate.py 原样调用（subprocess），本守护进程只是
   一层进程级门面，便于未来 LTI 升级时零改动复用。

协议（Unix socket，行分隔 JSON）
---------------------------------
请求（单行 JSON）：
  {"ping": true}                       → 健康检查
  {"path": "/abs/文书.docx"}           → 跑门禁
  {"path": "...", "timeout": 300}      → 自定义超时（秒）

响应（单行 JSON）：
  {"pong": true, "ts": 169...}
  {"status": "PASS|REJECT|USAGE_ERR|ERROR", "exit": 0|1|2|-1,
   "report": "<lti_gate 标准输出+错误>", "ts": 169..., "elapsed_s": 12.3}

用法
----
  python3 lti-gate-daemon.py                # 前台运行（默认 socket /tmp/lti-gate.sock）
  python3 lti-gate-daemon.py --socket /tmp/x.sock --foreground
  python3 lti-gate-daemon.py --install-plist   # 仅打印 launchd plist 内容供安装

信号：SIGTERM / SIGINT → 优雅退出并清理 socket。
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime

# ---------------------------------------------------------------- 默认配置
DEFAULT_SCRIPT = os.path.expanduser(
    "~/WorkBuddy/2026-08-08-15-48-47/lti_gate.py"
)
DEFAULT_PYTHON = "/usr/bin/python3"
DEFAULT_SOCKET = "/tmp/lti-gate.sock"

# 单机密文版：剥离这些变量 → 门禁不连元典 REST（airgap）
_STRIP_ENV_KEYS = ("YD_API_KEY", "YD_API_KEY_REST", "YUANDIAN_API_KEY")

# 单份文档门禁硬超时（秒），防止卡死拖垮上游
DEFAULT_TIMEOUT = 300


def _ts() -> float:
    return time.time()


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%S")


def run_gate(script: str, python: str, path: str, timeout: int) -> dict:
    """通过 subprocess 调用 lti_gate.py，返回结构化判定。"""
    if not os.path.isfile(path):
        return {
            "status": "ERROR",
            "exit": -1,
            "report": "文件不存在: {0}".format(path),
            "ts": _iso(_ts()),
            "elapsed_s": 0.0,
        }
    if not os.path.isfile(script):
        return {
            "status": "ERROR",
            "exit": -1,
            "report": "门禁脚本不存在: {0}".format(script),
            "ts": _iso(_ts()),
            "elapsed_s": 0.0,
        }

    # airgap：剥离外联密钥，确保门禁不触发元典 REST
    env = dict(os.environ)
    for k in _STRIP_ENV_KEYS:
        env.pop(k, None)
    # 显式声明 airgap 形态（供 lti_gate 内部 Level3 判定，双保险）
    env["LAWTWIN_DEPLOY_MODE"] = "A_ciphertext_single"

    started = _ts()
    try:
        proc = subprocess.run(
            [python, script, path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        exit_code = proc.returncode
        report = (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return {
            "status": "ERROR",
            "exit": -1,
            "report": "门禁执行超时（>{0}s），已中止".format(timeout),
            "ts": _iso(_ts()),
            "elapsed_s": round(_ts() - started, 3),
        }
    except Exception as exc:  # pragma: no cover
        return {
            "status": "ERROR",
            "exit": -1,
            "report": "门禁调用异常: {0}".format(exc),
            "ts": _iso(_ts()),
            "elapsed_s": round(_ts() - started, 3),
        }

    if exit_code == 0:
        status = "PASS"
    elif exit_code == 1:
        status = "REJECT"
    else:
        status = "USAGE_ERR"
    return {
        "status": status,
        "exit": exit_code,
        "report": report,
        "ts": _iso(_ts()),
        "elapsed_s": round(_ts() - started, 3),
    }


class _ConnHandler(threading.Thread):
    """每个连接一个线程，读取一行 JSON 请求并回写一行 JSON 响应。"""

    def __init__(self, conn: socket.socket, script: str, python: str, timeout: int):
        super().__init__(daemon=True)
        self.conn = conn
        self.script = script
        self.python = python
        self.timeout = timeout

    def run(self) -> None:
        try:
            self.conn.settimeout(10.0)
            raw = b""
            while b"\n" not in raw:
                chunk = self.conn.recv(4096)
                if not chunk:
                    break
                raw += chunk
            line = raw.split(b"\n", 1)[0].strip()
            if not line:
                self._send({"error": "空请求"})
                return
            try:
                req = json.loads(line.decode("utf-8", errors="replace"))
            except ValueError:
                self._send({"error": "JSON 解析失败"})
                return

            if req.get("ping"):
                self._send({"pong": True, "ts": _iso(_ts())})
                return

            path = req.get("path")
            if not path:
                self._send({"error": "缺少 path 字段"})
                return
            to = int(req.get("timeout") or self.timeout)
            result = run_gate(self.script, self.python, path, to)
            self._send(result)
        except socket.timeout:
            self._send({"error": "读取请求超时"})
        except Exception as exc:  # pragma: no cover
            try:
                self._send({"error": "处理异常: {0}".format(exc)})
            except Exception:
                pass
        finally:
            try:
                self.conn.close()
            except Exception:
                pass

    def _send(self, obj: dict) -> None:
        payload = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
        self.conn.sendall(payload)


def _print_plist(socket_path: str, script: str, python: str) -> None:
    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.xiaoqiang.lti-gate</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>{script}</string>
        <string>--socket</string>
        <string>{socket_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>{os.path.dirname(script)}</string>
    <key>StandardOutPath</key>
    <string>/tmp/lti-gate.out</string>
    <key>StandardErrorPath</key>
    <string>/tmp/lti-gate.err</string>
    <key>ProcessType</key>
    <string>Standard</string>
</dict>
</plist>
"""
    sys.stdout.write(plist)


def main() -> None:
    ap = argparse.ArgumentParser(description="LTI 门禁独立进程守护程序")
    ap.add_argument("--socket", default=DEFAULT_SOCKET, help="Unix socket 路径")
    ap.add_argument("--script", default=DEFAULT_SCRIPT, help="lti_gate.py 绝对路径")
    ap.add_argument("--python", default=DEFAULT_PYTHON, help="运行 lti_gate 的 python 解释器")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="单份文档门禁超时（秒）")
    ap.add_argument("--foreground", action="store_true", help="前台运行（默认即前台，便于 launchd 托管）")
    ap.add_argument("--install-plist", action="store_true", help="仅打印 launchd plist 内容后退出")
    args = ap.parse_args()

    if args.install_plist:
        _print_plist(args.socket, os.path.abspath(args.script), args.python)
        return

    sock_path = args.socket
    if os.path.exists(sock_path):
        # 上次异常退出残留，清理后重建
        try:
            os.unlink(sock_path)
        except OSError:
            pass

    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path)
    srv.listen(8)
    print("[lti-gate] 监听 {0} | 门禁脚本 {1} | airgap=on".format(sock_path, args.script), flush=True)

    _alive = {"run": True}

    def _stop(signum, frame):  # pragma: no cover
        print("[lti-gate] 收到信号 {0}，优雅退出".format(signum), flush=True)
        _alive["run"] = False
        try:
            srv.close()
        except Exception:
            pass
        try:
            os.unlink(sock_path)
        except OSError:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    while _alive["run"]:
        try:
            conn, _ = srv.accept()
        except OSError:
            break
        _ConnHandler(conn, args.script, args.python, args.timeout).start()


if __name__ == "__main__":
    main()
