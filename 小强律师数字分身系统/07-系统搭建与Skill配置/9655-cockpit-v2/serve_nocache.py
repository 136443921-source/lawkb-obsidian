#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
serve_nocache.py · 9360 驾驶舱 · 无缓存本地服务
========================================================
替代裸 `python3 -m http.server`，仅增加 `Cache-Control: no-store` 等响应头，
其余行为完全一致（同目录、同端口、同绑定）。

用途：让数据驱动屏（C1-C9）在 refresh_8139.py / watch_cockpit.py 重算后，
浏览器刷新即见最新数据，不再被 http.server 的默认缓存拖住。
这是「系统内改数据 → 同步到 C1-C9」的根因修复：一招覆盖全部子资源
(index.html / flywheel-data.js / mind_panels_data.js / *.json 等)。

配合 start_cockpit_hub_ops.sh 使用（其内已改为 exec 本脚本）。
落点铁律：仅位于 cockpit-hub-ops 目录内，不触碰其它项目目录。
"""
import sys
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9360
    host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    directory = sys.argv[3] if len(sys.argv) > 3 else os.path.dirname(os.path.abspath(__file__))

    class NoCacheHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)

        def end_headers(self):
            # 关键：禁止一切缓存，保证数据屏刷新即时可见
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            super().end_headers()

        def log_message(self, *args, **kwargs):
            pass  # 静默访问日志，避免刷屏

    httpd = ThreadingHTTPServer((host, port), NoCacheHandler)
    print(f"[serve_nocache] serving {directory} @ http://{host}:{port}/ (Cache-Control: no-store)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[serve_nocache] 收到中断，退出。")


if __name__ == "__main__":
    main()
