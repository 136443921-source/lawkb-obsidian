#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_ima_connector.py  v2.1  (2026-09-04 修正：enabled 实为连接门禁)

用途：诊断 / 修复 WorkBuddy 连接器（默认 ima-mcp）的配置态健康，防止"配置翻转 →
      静默断线"。本脚本被「每日摄入稳定性监测守卫」步骤11 调用。

⚠️ schema 修订（2026-09-03 初判，2026-09-04 实测修正）：
  旧 schema（connector-states.v3.json）：
    - 顶层 `enabled` 列表 决定客户端加载哪些连接器工具
    - 顶层 `userDisabled` 为历史禁用标记
    - ima-mcp 不在 enabled 且在 userDisabled → 工具永不注册 → "断线"
  新 schema（connector-states.json，当前生效）：
    - 结构改为 `connectors{id:{enabled, bound}}` 字典 + 顶层 `headerOverrides` 字典（非列表）
    - **2026-09-04 实测修正（推翻 09-03 误判）**：`enabled` 字段**确实是连接门禁**。
      交叉验证：本会话已连接的 3 个 MCP 连接器（gongyi-open-mcp / pkulaw / yuandian-mcp）
      在 config 中均为 `enabled: true`；而所有 `enabled: false` 的（ima-mcp、qq-mail、
      kdocs、github、tencent-docs、qcc-company）均**未**出现在已连接列表。
      → `enabled=True` 才会真正加载并连接；`enabled=False` = 未启用/断开。
    - 真正健康判据 = `enabled=True` + `bound=True` + `id ∈ headerOverrides`(授权已注入)
      + 本会话实测已连接。
    - **本环境不代点规则（老强硬性要求）**：ima-mcp / 元典 类授权状态一律由老强在 UI 侧
      亲手「重新信任/启用」，脚本仅诊断 + 给出 UI 操作指引，**不写盘翻转 enabled**
      （避免越权代点；且令牌过期时翻转无效，仍需 UI 重授权）。

安全设计：
  * 默认 --dry-run，不写盘
  * 写盘前自动备份 <state>.bak-<ts>
  * 新 schema 下 `enabled=False` 是可诊断的真实断线根因，但修复通道是 UI「重新信任/启用」
    （本环境不代点），故脚本对 new schema 仅诊断+告警、不写盘；apply 仅对「旧 schema
    配置态异常」生效
  * 支持 --rollback <备份文件> 一键还原
  * 不读取、不打印任何 token / 密钥

用法：
  python3 fix_ima_connector.py                 # 只诊断（dry-run）
  python3 fix_ima_connector.py --apply         # 执行修复（仅旧 schema 异常有效）
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
# 当前 schema 文件名优先，旧版 .v3.json 向后兼容
STATE_NAMES = ["connector-states.json", "connector-states.v3.json"]


def find_active_ws():
    """活跃 workspace = 目录名为 UUID 且含 connector-states.(json|.v3.json) 的那个（取 mtime 最新）。"""
    cands = []
    if not os.path.isdir(CONN_ROOT):
        return None, None
    for d in os.listdir(CONN_ROOT):
        p = os.path.join(CONN_ROOT, d)
        if not os.path.isdir(p):
            continue
        for name in STATE_NAMES:
            fp = os.path.join(p, name)
            if os.path.isfile(fp):
                mt = os.path.getmtime(fp)
                cands.append((mt, p, name))
                break
    if not cands:
        return None, None
    cands.sort(reverse=True)
    return cands[0][1], cands[0][2]


def load_state(ws, state_name):
    with open(os.path.join(ws, state_name), "r", encoding="utf-8") as f:
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
    """返回 (schema, problems, info)。problems 为可自动修复项（仅旧 schema）。"""
    print("=" * 62)
    print("连接器状态诊断  (目标: %s)" % target)
    print("=" * 62)

    # —— 新 schema 判定 ——
    cons = state.get("connectors")
    if isinstance(cons, dict):
        print("  检测到 schema: 新 (connectors{} 字典 + headerOverrides 字典)")
        entry = cons.get(target)
        if not isinstance(entry, dict):
            print(f"  ✗ connectors 中无 {target} 条目（未配置/未绑定）")
            return "new", ["NOT_BOUND"], {"bound": None, "auth": None, "enabled": None}
        bound = entry.get("bound")
        enabled = entry.get("enabled")
        headers = state.get("headerOverrides", {}) or {}
        auth = target in headers
        print(f"  connectors['{target}'].enabled = {enabled}   (注: enabled=True 才会真正加载并连接，False=未启用/断开)")
        print(f"  connectors['{target}'].bound    = {bound}")
        print(f"  headerOverrides 含 {target}       = {auth}  (授权是否已注入)")
        print("-" * 62)

        problems = []
        if not enabled:
            problems.append("NOT_ENABLED → enabled=False，连接器未启用/不会加载，须老强在 UI 点「连接/信任/启用」翻成 true")
        if not bound:
            problems.append("NOT_BOUND → 连接器未绑定，需 UI 重新授权/配置")
        if not auth:
            problems.append("NO_AUTH_HEADER → headerOverrides 无授权，启用后可能 401，需 UI 重新授权")
        if not problems:
            print("  ✓ 配置态健康（enabled + bound + 授权 均正常；与实测连接交叉验证即可）")
        else:
            print("  发现问题：")
            for p in problems:
                print(f"    ✗ {p}")
            if any(p.startswith("NOT_ENABLED") for p in problems):
                print("  → 本环境不代点（老强硬性规则）：由老强在 UI 点 IMA 知识库卡片「连接/信任/启用」即可，")
                print("    脚本不写盘翻转 enabled。若启用后仍 401/未连，则令牌过期，需 UI 走完整重新授权。")
        print("=" * 62)
        return "new", problems, {"bound": bound, "auth": auth, "enabled": enabled}

    # —— 旧 schema 判定（向后兼容）——
    print("  检测到 schema: 旧 (顶层 enabled/userDisabled)")
    enabled = state.get("enabled", []) or []
    user_disabled = state.get("userDisabled", {})
    ever = state.get("everConnected", []) or []
    headers = state.get("headerOverrides", {}) or {}
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
    return "old", problems, {}


def apply_fix(ws, state_name, state, target):
    path = os.path.join(ws, state_name)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = f"{path}.bak-{ts}"
    shutil.copy2(path, bak)
    print(f"  已备份 → {bak}")

    schema = "new" if isinstance(state.get("connectors"), dict) else "old"
    changed = []

    if schema == "old":
        enabled = state.get("enabled", []) or []
        user_disabled = state.get("userDisabled", {})
        if target not in enabled:
            enabled.append(target)
            state["enabled"] = enabled
            changed.append(f"enabled += {target}")
        if isinstance(user_disabled, dict):
            if user_disabled.get(target, False):
                user_disabled[target] = False
                state["userDisabled"] = user_disabled
                changed.append(f"userDisabled['{target}'] : True → False")
        elif isinstance(user_disabled, list):
            if target in user_disabled:
                state["userDisabled"] = [x for x in user_disabled if x != target]
                changed.append(f"userDisabled -= {target}")
    else:
        # 新 schema：enabled 确为连接门禁，但「重新信任/启用」须由老强在 UI 亲手操作
        # （本环境不代点规则），脚本不写盘翻转 enabled。
        print("  新 schema：enabled 为连接门禁，但「重新信任/启用」须由老强在 UI 亲手操作（本环境不代点），")
        print("  脚本不写盘翻转 enabled。请在连接器 UI 点目标卡片「连接/信任/启用」，必要时走完整重新授权。")

    if not changed:
        print("  无需改动。")
        return bak, []
    # 新 schema 不会走到这里（changed 为空即返回）

    if not os.access(path, os.W_OK):
        os.chmod(path, 0o600)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

    print("  已写入改动：")
    for c in changed:
        print(f"    ✓ {c}")
    return bak, changed


def rollback(ws, state_name, bak):
    path = os.path.join(ws, state_name)
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

    ws, state_name = (args.ws, None) if args.ws else (None, None)
    if not ws:
        ws, state_name = find_active_ws()
    if not ws:
        print("✗ 未找到活跃 workspace（~/.workbuddy/connectors/<uuid>/）")
        return 2
    if not state_name:
        # 手动指定 ws 时推断文件名
        for n in STATE_NAMES:
            if os.path.isfile(os.path.join(ws, n)):
                state_name = n
                break
    if not state_name:
        print("✗ workspace 内无 connector-states 文件")
        return 2
    print(f"活跃 workspace: {ws}")
    print(f"状态文件: {state_name}\n")

    if args.rollback:
        return rollback(ws, state_name, args.rollback)

    state = load_state(ws, state_name)
    schema, problems, info = diagnose(state, args.target)

    # 新 schema：问题均需在 UI 处理（本环境不代点），不自动写盘
    if schema == "new":
        if problems:
            print("\n! 新 schema 下检测到配置异常（详见上方）。其中 enabled=False 即断线根因，")
            print("  须由老强在 UI 点目标卡片「连接/信任/启用」翻成 true（本环境不代点，脚本不写盘）。")
            print("  若启用后仍 401/未连，则令牌过期，需 UI 走完整重新授权。")
        else:
            print("\n✓ 连接器配置态健康（enabled + bound + 授权均正常），无需任何操作。")
        return 0

    # 旧 schema
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
    apply_fix(ws, state_name, state, args.target)
    print("\n" + "=" * 62)
    print("⚠ 必须重启 WorkBuddy（或重新加载连接器）配置才生效！")
    print("  重启后用 ToolSearch 搜 mcp__%s__ 验证工具是否出现。" % args.target.replace("-", "_"))
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
