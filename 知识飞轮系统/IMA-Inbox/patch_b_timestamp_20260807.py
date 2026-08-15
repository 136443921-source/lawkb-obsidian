import json

path = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/ima_intake_state.json"
with open(path, encoding="utf-8") as f:
    data = json.load(f)

TS = "2026-08-07T12:53"

# fix top-level
data["updated"] = TS
data["ima_status"] = "runtime_healthy_backfilled_B36_2026-08-07"
data["note"] = "2026-08-07 12:53 B 库补录 10 篇（律师3+人伤2+合规2+慈善3）全部 IMA 真源摄入，B_done 26→36（36/36 达标）；四库各 9 篇。occupies_new_quota=false。"

# fix the 10 just-appended records (they carry create_time_approx=True and ingested_at 2026-08-07T08:45)
fixed = 0
for kb_id, lib in data["libraries"].items():
    for rec in lib["ingested"]:
        if rec.get("ingested_at") == "2026-08-07T08:45" and rec.get("create_time_approx"):
            rec["ingested_at"] = TS
            fixed += 1

# fix last consumed_windows entry
cw = data["consumed_windows"]
if cw and cw[-1].get("consumed_by", "").startswith("automation-1783920420205 v1.13 续跑（B 库达标补录）"):
    cw[-1]["consumed_at"] = TS

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("patched ingested_at records:", fixed, "| top updated:", data["updated"], "| B_done:", data["totals"]["B_done"])
