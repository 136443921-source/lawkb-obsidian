import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from intake_runner import IntakeState, DAILY_CONFIG

st = IntakeState(DAILY_CONFIG.state_path).load()
d = st.data
pw = d.get("pending_windows", [])
wid = "w_2026-10-23_A1B_channel_down"
if not any(w.get("window_id") == wid for w in pw):
    pw.append({
        "window_id": wid, "target": 5, "done": 0, "status": "open",
        "reason": "本会话 ima-mcp 工具 absent（ToolSearch 实查不在工具表），A1/B 5库各1篇定点摄入无法执行；依红线未 --apply 自愈。",
        "opened_at": "2026-10-23T22:33",
        "backfill_log": [{"date": "2026-10-23", "note": "ima-mcp 本会话工具表 absent；A1/B 5篇跳过，登记漏窗待 UI 重授权+重启后回补。"}],
    })
    d["pending_windows"] = pw
cp = d.setdefault("checkpoint", {})
done = cp.setdefault("done", [])
for s in ["A0", "A2", "A2_5", "C", "D"]:
    if s not in done:
        done.append(s)
cp["status"] = "in_progress"
st.save()
open_wins = [w for w in d["pending_windows"] if str(w.get("status","")).lower() not in ("backfilled","closed","done")]
print("pending_windows total:", len(d["pending_windows"]))
print("open windows (consecutive leak):", len(open_wins))
print("checkpoint.done:", d["checkpoint"]["done"])
print("ingested_total:", d["totals"]["ingested_total"])
