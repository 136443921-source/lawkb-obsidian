#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, sys, shutil, os

STATE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/ima_intake_state.json"
DRY = "--dry-run" in sys.argv

def main():
    with open(STATE, encoding="utf-8") as f:
        data = json.load(f)

    before_total = data["totals"]["ingested_total"]
    libs_before = dict(data["totals"]["libraries"])

    # 1) failed_220030: collapse to only needs_manual_check (idempotent)
    f220 = data.get("failed_220030", [])
    keep = [e for e in f220 if e.get("status") == "needs_manual_check"]
    removed = [e["media_id"][:20] for e in f220 if e.get("status") != "needs_manual_check"]
    data["failed_220030"] = keep

    # 2) window w_2026-09-07_A1B_channel_down -> backfilled (match siblings)
    win = None
    for w in data.get("pending_windows", []) + data.get("consumed_windows", []):
        if isinstance(w, dict) and w.get("window_id") == "w_2026-09-07_A1B_channel_down":
            win = w
            break
    was_open = bool(win and win.get("status") == "open")
    if win:
        for t in win.get("targets", []):
            t["done"] = 3
        win["total_done"] = 15
        win["status"] = "backfilled"
        win["closed_at"] = "2026-09-07T08:30"

    # 3) totals: +15 only if window was still open (idempotent)
    if was_open:
        data["totals"]["ingested_total"] = before_total + 15
        for k in data["totals"]["libraries"]:
            data["totals"]["libraries"][k] += 3

    after_total = data["totals"]["ingested_total"]
    libs_after = data["totals"]["libraries"]

    print("=== DRY-RUN ===" if DRY else "=== APPLY ===")
    print(f"failed_220030: {len(f220)} -> {len(keep)} (removed {len(removed)}: {removed})")
    print(f"window was_open={was_open}; now status={win.get('status') if win else None}, done={win.get('total_done') if win else None}")
    print(f"ingested_total: {before_total} -> {after_total}")
    print(f"libraries: {libs_before} -> {libs_after}")
    print(f"sum after = {sum(libs_after.values())} (should equal {after_total})")

    if not DRY:
        bak = STATE + ".bak-20260907-0830"
        if not os.path.exists(bak):
            shutil.copy2(STATE, bak)
        with open(STATE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"BACKUP -> {bak}")
        print("WROTE state file OK")

if __name__ == "__main__":
    main()
