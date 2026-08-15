#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_ima_connector.py  v1.0  (2026-08-05)

用途：修复 WorkBuddy 连接器 ima-mcp 被置于 userDisabled / 未列入 enabled
      导致 MCP 工具永不加载（ToolSearch 搜不到 mcp__ima-mcp__*）的问题。

根因：~/.workbuddy/connectors/<ws>/connector-states.v3.json
      - enabled      列表决定客户端加载哪些连接器的工具
      - userDisabled 列表为历史禁用标记
      ima-mcp 不在 enabled 且在 userDisabled → 工具永不注册 → 表现为"断线"

安全设计：
  * 默认 --dry-run，不写盘
  * 写盘前自动备份 connector-states.v3.json.bak-<ts>
  * 仅修改 enabled / userDisabled 两个键，其它键原样保留
  * 支持 --rollback <备份文件> 一键还原
  * 不读取、不打印任何 token / 密钥

用法：
  python3 fix_ima_connector.py                 # 只诊断（dry-run）
  python3 fix_ima_connector.py --apply         # 执行修复
  python3 fix_ima_connector.py --rollback <f>  # 回滚
  python3 fix_ima_connector.py --apply --target qq-mail   # 修其它连接器
"""
import argparse
import datetime
import json
import os
import shutil
import sys

CONN_ROOT = os.path.expanduser("~/.workbuddy/connectors")
STATE_NAME = "connector-states.v3.json"


def find_active_ws():
    """活跃 workspace = 目录名为 UUID 且含 connector-states.v3.json 的那个。"""
    cands = []
    if not os.path.isdir(CONN_ROOT):
        return None
    for d in os.listdir(CONN_ROOT):
        p = os.path.join(CONN_ROOT, d)
        if os.path.isdir(p) and os.path.isfile(os.path.join(p, STATE_NAME)):
            mt = os.path.getmtime(os.path.join(p, STATE_NAME))
            cands.append((mt, p))
    if not cands:
        return None
    cands.sort(reverse=True)
    return cands[0][1]


def load_state(ws):
    with open(os.path.join(ws, STATE_NAME), "r", encoding="utf-8") as f:
        return json.load(f)


def _is_user_disabled(user_disabled, target):
    """userDisabled 在不同客户端版本下可能是 list 或 dict，需兼容。
    dict 形态：{'qq-mail': False, 'ima-mcp': True}  → 值为 True 才算禁用
    list 形态：['ima-mcp']                          → 出现即禁用
    """
    if isinstance(user_disabled, dict):
        return bool(user_disabled.get(target, False))
    if isinstance(user_disabled, list):
        return target in user_disabled
    return False


def diagnose(state, target):
    enabled = state.get("enabled", []) or []
    user_disabled = state.get("userDisabled", {})
    ever = state.get("everConnected", []) or []
    headers = state.get("headerOverrides", {}) or {}

    print("=" * 62)
    print("连接器状态诊断")
    print("=" * 62)
    print(f"  目标连接器 : {target}")
    print(f"  enabled({len(enabled)}) : {enabled}")
    print(f"  userDisabled : {user_disabled}   [类型 {type(user_disabled).__name__}]")
    print(f"  everConnected 含目标 : {target in ever}")
    print(f"  headerOverrides 含目标 : {target in headers}  (凭证是否已注入)")
    print("-" * 62)

    problems = []
    if target not in enabled:
        problems.append("NOT_ENABLED   → 不在 enabled，客户端不会加载其 MCP 工具")
    if _is_user_disabled(user_disabled, target):
        problems.append("USER_DISABLED → 被标记为用户手动禁用")
    if target not in ever:
        problems.append("NEVER_CONNECTED → 从未成功连接过，需先在 UI 完成 OAuth 授权")
    if target not in headers:
        problems.append("NO_AUTH_HEADER → 未注入 Authorization，启用后可能 401（需重新授权）")

    if problems:
        print("  发现问题：")
        for p in problems:
            print(f"    ✗ {p}")
    else:
        print("  ✓ 状态正常，无需修复")
    print("=" * 62)
    return problems


def apply_fix(ws, state, target):
    path = os.path.join(ws, STATE_NAME)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = f"{path}.bak-{ts}"
    shutil.copy2(path, bak)
    print(f"  已备份 → {bak}")

    enabled = state.get("enabled", []) or []
    user_disabled = state.get("userDisabled", {})

    changed = []
    if target not in enabled:
        enabled.append(target)
        state["enabled"] = enabled
        changed.append(f"enabled += {target}")

    # 关键：保持 userDisabled 原有数据类型，切勿 dict→list
    if isinstance(user_disabled, dict):
        if user_disabled.get(target, False):
            user_disabled[target] = False          # 与 qq-mail/tencent-docs 同形态
            state["userDisabled"] = user_disabled
            changed.append(f"userDisabled['{target}'] : True → False")
    elif isinstance(user_disabled, list):
        if target in user_disabled:
            state["userDisabled"] = [x for x in user_disabled if x != target]
            changed.append(f"userDisabled -= {target}")

    if not changed:
        print("  无需改动。")
        return bak, []

    # 保证可写
    if not os.access(path, os.W_OK):
        os.chmod(path, 0o600)

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

    print("  已写入改动：")
    for c in changed:
        print(f"    ✓ {c}")
    print(f"  新 enabled({len(enabled)}) : {enabled}")
    return bak, changed


def rollback(ws, bak):
    path = os.path.join(ws, STATE_NAME)
    if not os.path.isfile(bak):
        print(f"  ✗ 备份不存在：{bak}")
        return 1
    if not os.access(path, os.W_OK):
        os.chmod(path, 0o600)
    shutil.copy2(bak, path)
    print(f"  ✓ 已从 {bak} 还原")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="ima-mcp", help="目标连接器 id（默认 ima-mcp）")
    ap.add_argument("--apply", action="store_true", help="真正写盘（默认仅诊断）")
    ap.add_argument("--rollback", metavar="BAK", help="从指定备份还原")
    ap.add_argument("--ws", help="手动指定 workspace 目录")
    args = ap.parse_args()

    ws = args.ws or find_active_ws()
    if not ws:
        print("✗ 未找到活跃 workspace（~/.workbuddy/connectors/<uuid>/）")
        return 2
    print(f"活跃 workspace: {ws}\n")

    if args.rollback:
        return rollback(ws, args.rollback)

    state = load_state(ws)
    problems = diagnose(state, args.target)

    fixable = [p for p in problems if p.startswith(("NOT_ENABLED", "USER_DISABLED"))]
    if not fixable:
        if problems:
            print("\n! 存在问题但本脚本无法自动修复（需在 UI 重新授权）。")
        return 0

    if not args.apply:
        print("\n[dry-run] 加 --apply 执行修复。将执行：")
        for p in fixable:
            print(f"    - 修正 {p.split()[0]}")
        return 0

    print("\n执行修复：")
    apply_fix(ws, state, args.target)
    print("\n" + "=" * 62)
    print("⚠ 必须重启 WorkBuddy（或重新加载连接器）配置才生效！")
    print("  重启后用 ToolSearch 搜 mcp__%s__ 验证工具是否出现。" % args.target.replace("-", "_"))
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
