#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_connector_batch.py — 受管 MCP 连接器 亚型B/C 批量主动探测（只读诊断）

背景：2026-09-09 复盘确认，平台级 MCP 安全迁移（connector-states v3→v4）会批量清除
headerOverrides 的 Bearer 令牌，导致 enabled=true 的受管 MCP 集体沦为 亚型B 假连接
（UI 看着连着、调用 401/Bearer missing），损坏态条目沦为 亚型C 缺失。

v4.0.5 修正（2026-09-08 实测）：`B` 判定**仅对"曾在 headerOverrides 注册过授权"的连接器**
（目前实测仅 ima-mcp 为 enabled 态）生效；`yuandian-mcp` / `pkulaw` / `gongyi-open-mcp` 等
走各自原生授权通道，令牌**永不写入** headerOverrides，其 `B` 恒为假阳性——脚本现判 `OK`，
连通性以实测工具调用为准。

本脚本对监测清单内全部受管 MCP 做只读扫描，逐条判定：
  - C  : id 不在 connectors 映射（条目完全缺失，翻 enabled 无效，须 UI 完整重连）
  - B  : 走 headerOverrides 通道（id 曾在 headerOverrides 注册）且 enabled=true+bound=true 但无令牌（真断，须 UI 重新授权）
  - OK : 健康（headerOverrides 类令牌已注入，或原生授权类 enabled+bound 即视为健康）
  - OFF: 其他（enabled=false 等未启用态，非本次重点，不告警）

铁律：本脚本只读、绝不写盘 connector-states.json、绝不代点 UI 授权。
令牌为 AES-256-GCM 私有加密，AI 无法注入；修复一律交用户在 UI 亲手 OAuth。

用法：
  python3 fix_connector_batch.py                  # 仅打印判定（默认）
  python3 fix_connector_batch.py --report        # 同时把 B/C 命中追加到 稳定性监测.md
  python3 fix_connector_batch.py --watch yuandian-mcp pkulaw gongyi-open-mcp  # 自定义监测清单
"""
import json
import os
import glob
import sys
from datetime import datetime, timezone, timedelta

HOME = os.path.expanduser("~")
DEFAULT_WATCH = ["ima-mcp", "yuandian-mcp", "pkulaw", "gongyi-open-mcp"]
REPORT_PATH = os.path.join(
    HOME, "Documents/LawKB/知识飞轮系统/运维/稳定性监测.md"
)


def find_active_connector_states():
    files = glob.glob(os.path.join(HOME, ".workbuddy/connectors/*/connector-states.json"))
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def classify(cons, ho, cid):
    if cid not in cons:
        return "C"
    c = cons[cid]
    en = c.get("enabled")
    bd = c.get("bound")
    # 是否走 headerOverrides 通用令牌通道：
    # 仅"曾在 headerOverrides 注册过授权"的连接器（目前实测仅 ima-mcp 为 enabled 态）属于此类；
    # 元典/pkulaw/公益 走各自原生授权，令牌永不写入 headerOverrides → 缺省即健康，B 为假阳性。
    ho_based = cid in ho
    tok = False
    h = ho.get(cid)
    if isinstance(h, dict):
        tok = bool(h.get("Authorization"))
    if en and bd:
        if ho_based:
            return "B" if not tok else "OK"
        # 原生授权通道：令牌存于连接器自有通道，不在 headerOverrides
        return "OK"
    return "OFF"


def main():
    report = "--report" in sys.argv
    watch = [a for a in sys.argv[1:] if not a.startswith("--")]
    watch = watch or DEFAULT_WATCH

    path = find_active_connector_states()
    if not path:
        print("✗ 未找到 connector-states.json")
        return 1
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        print("✗ 解析失败:", e)
        return 1

    cons = d.get("connectors", {})
    ho = d.get("headerOverrides", {})
    # 迁移标志（辅助判断根因）
    mig = {k: d.get(k) for k in (
        "mcpSecurityMigrated", "headerOverridesBearerStripped",
        "staleManagedAuthHeadersPurged")}

    results = []
    for cid in watch:
        results.append((cid, classify(cons, ho, cid)))

    b_hits, c_hits = [], []
    print(f"活跃 config: {path}")
    print(f"迁移标志: {mig}")
    print(f"{'连接器':20s} 判定")
    for cid, st in results:
        print(f"  {cid:20s} {st}")
        if st == "B":
            b_hits.append(cid)
        elif st == "C":
            c_hits.append(cid)

    if report and (b_hits or c_hits):
        now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
        lines = []
        for cid in b_hits:
            lines.append(
                f"- [北京时间 {now}] ⚠️ {cid} 假连接(亚型B=enabled=true 但 headerOverrides 无令牌)："
                f"UI 看着连着、调用 401/Bearer missing，须老强在 UI 点「重新授权/信任」把令牌写入 headerOverrides（翻 enabled 无效）"
            )
        for cid in c_hits:
            lines.append(
                f"- [北京时间 {now}] ⚠️ {cid} 断线(亚型C=条目缺失)：connectors 映射无该 id，"
                f"翻 enabled 无效，须老强在 UI 完整「连接/信任/启用」注册（区分个人版/司内版 独立授权账号）"
            )
        try:
            with open(REPORT_PATH, "a", encoding="utf-8") as f:
                f.write("\n" + "\n".join(lines) + "\n")
            print(f"\n已追加 {len(lines)} 条告警到 {REPORT_PATH}")
        except Exception as e:
            print("✗ 追加监测日志失败:", e)

    # 退出码：有 B/C 命中返回 1（便于守卫判定异常），否则 0
    return 1 if (b_hits or c_hits) else 0


if __name__ == "__main__":
    sys.exit(main())
