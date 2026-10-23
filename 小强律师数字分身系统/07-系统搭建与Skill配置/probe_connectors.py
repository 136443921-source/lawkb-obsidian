#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""连接器静态盘点器（9655 驾驶舱 · connectors 段的自动半段）

═══════════ 为什么不是"全自动探测" ═══════════
2026-10-22 复盘发现 `驾驶舱_人工核验.json` 的 connectors 段靠人工填写，漂移 48 天。
第一版尝试用 `settings.json → enabledPlugins` 判定，**实测该字段不可信**：

    实测（2026-10-22 23:5x）：
      enabledPlugins 中 qcc-legal / tencent-docs / yuandian-mcp / pkulaw / ima-mcp
      全部为 **False**；
      而同一时刻会话注入的 connector-status 显示
      qcc-legal / tencent-docs / yuandian-mcp 为 **connected**。

    ⇒ enabledPlugins 布尔值与"连接器当前可用"**已脱钩**。
      用它做判据会造出第二个假仪表盘（比人工更危险，因为看起来"自动"）。

═══════════ 本脚本只做能可靠判定的事 ═══════════
L1 已安装   ：插件缓存目录存在该连接器包           → 可靠
L2 已配置   ：~/.workbuddy/mcp.json 有 server 定义 → 可靠
L3 会话状态 ：**本脚本一律置 null**                 → 只能由运行时 connector-status 注入
L4 实测可用 ：**本脚本不判定**                      → 须真实调用一次工具（亚型B假连接风险）

L3/L4 的真值来源：由小强在会话内把当次注入的 connector-status 写入
`驾驶舱_连接器真值.json`（见 --record 用法），本脚本不猜。

═══════════ 用法 ═══════════
    python3 probe_connectors.py                    # 打印静态盘点 + 更新核验 JSON 的静态段
    python3 probe_connectors.py --dry-run          # 只打印
    python3 probe_connectors.py --json             # 只出 JSON
    python3 probe_connectors.py --record '<json>'  # 记录会话真值（如 {"qcc-legal":"connected"}）

═══════════ 安全 ═══════════
- 写回前自动备份 <原名>.bak-YYYYmmdd-HHMMSS
- 只改 connectors / connector_probe / connector_checked_at 三个键
- 不读取、不输出任何令牌明文
"""
import os
import sys
import json
import glob
import shutil
import datetime

HOME = os.path.expanduser("~")
SETTINGS = os.path.join(HOME, ".workbuddy", "settings.json")
MCP_JSON = os.path.join(HOME, ".workbuddy", "mcp.json")
PLUGIN_CACHE = os.path.join(HOME, ".workbuddy", "plugins", "cache",
                            "workbuddy-connector-plugins-official")
DASH_DIR = os.path.join(HOME, "Documents", "LawKB", "知识飞轮系统")
TARGET = os.path.join(DASH_DIR, "驾驶舱_人工核验.json")
TRUTH = os.path.join(DASH_DIR, "驾驶舱_连接器真值.json")

# 业务上关心的连接器（静态盘点范围）
WATCH = [
    "agent-mail", "qcc-legal", "tencent-docs", "yuandian-mcp",
    "pkulaw", "ima-mcp", "gongyi-open-mcp", "kdocs", "qq-mail",
    "tencent-weiyun", "github",
]


def load_json(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {} if default is None else default


def installed_set():
    return {os.path.basename(p) for p in glob.glob(os.path.join(PLUGIN_CACHE, "*"))
            if os.path.isdir(p)}


def configured_set():
    return set((load_json(MCP_JSON).get("mcpServers") or {}).keys())


def load_truth():
    """读取最近一次由会话注入记录的真值（connector-status 快照）"""
    d = load_json(TRUTH)
    return d if isinstance(d, dict) else {}


def static_probe():
    inst = installed_set()
    conf = configured_set()
    truth = load_truth()
    truth_map = truth.get("status", {}) if isinstance(truth.get("status"), dict) else {}
    truth_at = truth.get("recorded_at", "")

    rows = []
    for name in WATCH:
        is_inst = name in inst
        is_conf = name in conf
        session = truth_map.get(name)  # 可能为 None

        if not is_inst and not is_conf:
            static = "absent"
        elif is_conf and not is_inst:
            static = "configured_only"
        else:
            static = "installed"

        rows.append({
            "name": name,
            "static": static,                 # L1/L2 可判定部分
            "installed": is_inst,
            "mcp_configured": is_conf,
            "session_status": session,        # L3：仅来自运行时真值
            "session_status_at": truth_at if session else None,
            "probe_level": "L1+L2 (static); L3 from runtime truth only",
            "note": {
                "absent": "未安装、未在 mcp.json 配置",
                "configured_only": "仅 mcp.json 有定义，插件包不在缓存目录",
                "installed": "插件包已安装（**不代表已连接**，须看 session_status 或实测调用）",
            }[static],
        })

    return {
        "static_probed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "script": "probe_connectors.py",
        "judgement_policy": (
            "L1 已安装/L2 已配置=可静态判定；L3 会话连接状态只取运行时真值（本脚本不猜）；"
            "L4 实测可用不判定。**禁止用 enabledPlugins 判定可用性**——2026-10-22 实测该字段与"
            "实际连接状态脱钩（全 False 而实有 3 个 connected）。"
        ),
        "counts": {
            "installed": sum(1 for r in rows if r["static"] == "installed"),
            "configured_only": sum(1 for r in rows if r["static"] == "configured_only"),
            "absent": sum(1 for r in rows if r["static"] == "absent"),
            "session_connected": sum(1 for r in rows if r["session_status"] == "connected"),
            "session_absent": sum(1 for r in rows if r["session_status"] not in (None, "connected")),
            "session_unknown": sum(1 for r in rows if r["session_status"] is None),
        },
        "connectors": rows,
    }


def record_session_truth(status_map, note=""):
    """记录会话注入的 connector-status 真值（由小强在会话内调用）"""
    old = load_truth()
    hist = old.get("history", [])
    payload = {
        "recorded_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": "会话注入 connector-status 快照（运行时真值）",
        "status": status_map,
        "note": note,
        "history": (hist + [{
            "at": old.get("recorded_at", ""),
            "status": old.get("status", {}),
        }])[-20:],
    }
    with open(TRUTH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(f"✅ 会话真值已记录 → {TRUTH}")
    print(f"   连接数：{sum(1 for v in status_map.values() if v == 'connected')}"
          f" / 共 {len(status_map)}")
    return payload


def write_back(payload, dry_run=False):
    if not os.path.exists(TARGET):
        print(f"⚠️ 目标核验文件不存在，跳过写回：{TARGET}")
        return False
    data = load_json(TARGET)
    if not data:
        print("⚠️ 目标文件无法解析，拒绝写入（防覆盖）")
        return False

    old = data.get("connectors", [])
    data["connectors"] = payload["connectors"]
    data["connector_probe"] = {
        "static_probed_at": payload["static_probed_at"],
        "script": payload["script"],
        "counts": payload["counts"],
        "judgement_policy": payload["judgement_policy"],
        "note": "connectors 段由 probe_connectors.py 自动生成，人工勿手改；判据改脚本。",
    }
    data["connector_checked_at"] = payload["static_probed_at"]

    # ── 分项新鲜度：让仪表盘能看出"哪段是旧数据"，而不是用一个 checked_at 掩盖漂移 ──
    now = payload["static_probed_at"]
    fresh = data.get("_freshness") or {}
    if not isinstance(fresh, dict):
        fresh = {}
    legacy_at = data.get("checked_at", "")
    # connectors 恒为本次自动时间
    fresh["connectors"] = {
        "at": now,
        "mode": "auto+runtime_truth",
        "stale": False,
        "by": "probe_connectors.py",
    }
    # 其余人工段：没有记录过的，一律以旧 checked_at 兜底并标 stale
    for seg in ("lti", "maturity", "system_level", "ev"):
        if seg not in fresh:
            fresh[seg] = {
                "at": legacy_at,
                "mode": "manual",
                "stale": True,
                "by": data.get("checked_by", ""),
                "todo": "本次未重跑，须实地复核后更新（见 _freshness_todo）",
            }
    data["_freshness"] = fresh
    data["_freshness_todo"] = (
        "lti：跑一次 LTI 五维回归（REJECT 数须为 0）后再改 lti.at；"
        "maturity：按花名册 v1.7 复核席位成熟度；"
        "system_level / ev：按运维手册 EV 版实地探针。"
        "**未重跑就不许把 stale 改成 false**——那正是 09-04 漂移 48 天的成因。"
    )
    # checked_at 保持"全量人工核验"语义不被污染，另设 overall 提示
    data["checked_at_note"] = (
        f"全量人工核验时间仍为 {legacy_at}（含 lti/maturity/system_level/ev 四段，均已标 stale）；"
        f"connectors 段已于 {now} 由脚本+运行时真值接管。二者不可混为一谈。"
    )

    if dry_run:
        print("=== DRY-RUN（不写文件）===")
        print(f"旧 connectors 条数 {len(old)} → 新 {len(payload['connectors'])}")
        print(f"counts: {json.dumps(payload['counts'], ensure_ascii=False)}")
        return True

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = f"{TARGET}.bak-{ts}"
    shutil.copy2(TARGET, bak)

    with open(TARGET, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"✅ 已写回 {TARGET}")
    print(f"   备份：{bak}")
    print(f"   counts：{json.dumps(payload['counts'], ensure_ascii=False)}")
    return True


def main():
    argv = sys.argv[1:]

    if "--record" in argv:
        i = argv.index("--record")
        raw = argv[i + 1] if len(argv) > i + 1 else "{}"
        try:
            smap = json.loads(raw)
        except Exception as e:
            print(f"❌ --record 需传合法 JSON：{e}")
            sys.exit(2)
        note = argv[i + 2] if len(argv) > i + 2 else ""
        record_session_truth(smap, note)
        payload = static_probe()
    else:
        payload = static_probe()

    if "--json" in argv:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        return

    write_back(payload, dry_run=("--dry-run" in argv))

    print("\n=== 明细（静态段 + 会话真值）===")
    for r in payload["connectors"]:
        s = r["session_status"]
        flag = {"connected": "🟢", "disabled": "⚪", "disconnected": "🔴",
                "reconnect": "🟡", None: "❔"}.get(s, "·")
        sess = s if s else "未记录"
        print(f"  {flag} {r['name']:18} 静态={r['static']:16} 会话={sess}")


if __name__ == "__main__":
    main()
