# -*- coding: utf-8 -*-
"""Check which candidate rawids are NOT yet ingested for a given IMA library.
Usage: python3 _check_cands.py <lib_id> <cands.json>
cands.json: [{"rawid": "...32hex...", "title": "...", "create_time": 123}, ...]
Prints un-ingested candidates sorted by create_time desc.
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ima_intake_state.json")

def main():
    lib_id = sys.argv[1]
    cands = json.load(open(sys.argv[2]))
    d = json.load(open(STATE))
    ing = d["libraries"][lib_id]["ingested"]
    ing_ids = set()
    for x in ing:
        if isinstance(x, dict):
            ing_ids.add(x.get("media_id", ""))
        else:
            ing_ids.add(str(x))
    PREFIX = "wechatarticle_62fe55a7567bc291dfbbee29900b27c3_"
    un = []
    for c in cands:
        full = PREFIX + c["rawid"] + lib_id
        if full not in ing_ids:
            un.append(c)
    un.sort(key=lambda x: x.get("create_time", 0), reverse=True)
    print("TOTAL candidates:", len(cands), "| ingested-known:", len(ing_ids), "| UN-ingested:", len(un))
    for c in un:
        print("  UN %s | %s | ct=%s" % (c["rawid"], c.get("title", "")[:40], c.get("create_time")))

if __name__ == "__main__":
    main()
