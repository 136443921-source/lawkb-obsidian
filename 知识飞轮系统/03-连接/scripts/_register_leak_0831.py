# -*- coding: utf-8 -*-
"""08-31 运行态掉线漏窗登记（幂等：已存在同 window_id 则跳过）。"""
import json, os, sys, datetime

STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     "ima_intake_state.json")

WINDOW_ID = "w_2026-08-31_A1B_channel_down"
LIB_NAMES = {
    "7312048136419112": "合同文书AI助手",
    "7312042960642489": "律师AI助手",
    "7312035322822509": "人伤法律实务助手",
    "7333014572917409": "合规与政府监管AI助手",
    "7311644304633438": "慈善组织合规AI助手",
}

def now_iso():
    return datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")

def main():
    d = json.load(open(STATE, encoding="utf-8"))
    wins = d.setdefault("pending_windows", [])
    if any(w.get("window_id") == WINDOW_ID for w in wins):
        print("ALREADY_REGISTERED:", WINDOW_ID)
        return
    window = {
        "window_id": WINDOW_ID,
        "start": "2026-08-31T08:30",
        "end": now_iso(),
        "reason": ("ima-mcp 运行态掉线：配置健康（enabled 含 ima-mcp、userDisabled=false、everConnected 含）"
                   "但工具不在 deferred 索引（ToolSearch 实查 absent）；按规范属会话级掉线，不执行 --apply，登记漏窗待通道恢复后回补。"),
        "selfhealed": False,
        "registered_at": now_iso(),
        "targets": [
            {"stage": "A1", "lib": LIB_NAMES[k], "target": 3, "done": 0}
            for k in ("7312048136419112",)
        ] + [
            {"stage": "B", "lib": LIB_NAMES[k], "target": 3, "done": 0}
            for k in ("7312042960642489", "7312035322822509", "7333014572917409", "7311644304633438")
        ],
        "total_target": 15,
        "total_done": 0,
        "backfill_log": [],
        "status": "pending",
    }
    wins.append(window)
    # 更新 updated 时间戳
    d["updated"] = now_iso()
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE)
    print("REGISTERED:", WINDOW_ID, "targets=15, status=pending")
    # 校验写回
    d2 = json.load(open(STATE, encoding="utf-8"))
    assert any(w.get("window_id") == WINDOW_ID for w in d2["pending_windows"])
    print("VERIFY_OK")

if __name__ == "__main__":
    main()
