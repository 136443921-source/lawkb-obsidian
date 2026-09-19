#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTI 门禁 · 客户端 CLI（G2 交付物）

把一份待交付文档递交给 lti-gate-daemon，打印结构化判定。
也可用于健康检查（--ping）。

用法
----
  python3 lti-gate-client.py /abs/文书.docx
  python3 lti-gate-client.py --ping
  python3 lti-gate-client.py --socket /tmp/x.sock /abs/文书.docx

退出码：PASS→0，REJECT→1，ERROR/USAGE_ERR→2，连接失败→3
"""

from __future__ import annotations

import argparse
import json
import socket
import sys

DEFAULT_SOCKET = "/tmp/lti-gate.sock"
_TIMEOUT = 30.0


def _req(sock_path: str, payload: dict) -> dict:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(_TIMEOUT)
    s.connect(sock_path)
    s.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
    buf = b""
    while b"\n" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
    s.close()
    return json.loads(buf.split(b"\n", 1)[0].decode("utf-8", errors="replace"))


def main() -> None:
    ap = argparse.ArgumentParser(description="LTI 门禁客户端")
    ap.add_argument("path", nargs="?", help="待校验 docx 绝对路径")
    ap.add_argument("--socket", default=DEFAULT_SOCKET, help="守护进程 socket 路径")
    ap.add_argument("--ping", action="store_true", help="仅健康检查")
    ap.add_argument("--timeout", type=int, default=300, help="门禁超时（秒，透传）")
    args = ap.parse_args()

    try:
        if args.ping:
            resp = _req(args.socket, {"ping": True})
            print("pong" if resp.get("pong") else "异常: {0}".format(resp))
            sys.exit(0)

        if not args.path:
            print("用法: lti-gate-client.py <docx路径>  (或 --ping)")
            sys.exit(2)

        resp = _req(args.socket, {"path": args.path, "timeout": args.timeout})
    except ConnectionRefusedError:
        print("❌ 无法连接门禁守护进程（socket 未监听）。请先启动 lti-gate-daemon.py")
        sys.exit(3)
    except FileNotFoundError:
        print("❌ socket 文件不存在：{0}。请先启动 lti-gate-daemon.py".format(args.socket))
        sys.exit(3)
    except Exception as exc:
        print("❌ 客户端异常: {0}".format(exc))
        sys.exit(3)

    if "error" in resp:
        print("❌ 门禁返回错误: {0}".format(resp["error"]))
        sys.exit(2)

    status = resp.get("status", "ERROR")
    print("=" * 72)
    print("门禁判定：{0}  （exit={1}, 耗时 {2}s, {3}）".format(
        status, resp.get("exit"), resp.get("elapsed_s"), resp.get("ts")))
    report = resp.get("report", "")
    if report.strip():
        print("-" * 72)
        print(report.rstrip())
    print("=" * 72)

    if status == "PASS":
        sys.exit(0)
    if status == "REJECT":
        sys.exit(1)
    sys.exit(2)


if __name__ == "__main__":
    main()
