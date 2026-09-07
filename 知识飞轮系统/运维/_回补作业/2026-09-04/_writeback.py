import json, sys, datetime, shutil, os

ROOT="/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
STATE=os.path.join(ROOT,"ima_intake_state.json")
SEL=os.path.join(ROOT,"运维/_回补作业/2026-09-04/选文清单.json")
DRY = "--apply" not in sys.argv

d=json.load(open(STATE, encoding="utf-8"))
sel=json.load(open(SEL, encoding="utf-8"))

HG_LIB="7333014572917409"
CF_LIB="7311644304633438"
TARGET_LIBS={HG_LIB, CF_LIB}  # 本任务仅回补 合规库 + 慈善库（18 篇），不碰其他库
EXCLUDE={"R-HG-062"}  # FAIL 220030, never ingested

def norm_id(e):
    return e.get("media_id") if isinstance(e, dict) else e

plan=[]  # (lib_id, entry)
for lib_name, arr in sel.items():
    for it in arr:
        if it["lib_id"] not in TARGET_LIBS:
            continue  # 跳过合同库/律师库/人伤库，超出本任务范围
        rid=it["rule_id"]
        if rid in EXCLUDE:
            continue
        entry={
            "media_id": it["media_id"],
            "title": it["title"],
            "create_time": "",
            "ingested_at": "2026-09-04T11:44",
            "value": 8,
            "rule_id": rid,
            "batch": "backfill-2026-09-04"
        }
        plan.append((it["lib_id"], entry))

added=0
for lib_id, entry in plan:
    lib=d["libraries"][lib_id]
    existing={norm_id(e) for e in lib["ingested"]}
    if entry["media_id"] in existing:
        print("SKIP (dup):", entry["rule_id"], entry["media_id"][:38])
        continue
    if not DRY:
        lib["ingested"].append(entry)
        d["totals"]["libraries"][lib_id]=len(lib["ingested"])
    added+=1
    print("ADD:", entry["rule_id"], entry["media_id"][:38])

# HG-062 -> failed_220030 (idempotent by media_id)
HG062="wechatarticle_62fe55a7567bc291dfbbee29900b27c3_490331c6e27158ee4f5c2201fcdfdef17333014572917409"
if not DRY:
    ef={f.get("media_id") for f in d["failed_220030"]}
    if HG062 not in ef:
        d["failed_220030"].append({
            "media_id": HG062,
            "date": "2026-09-05",
            "reason": "retry 2026-09-05 confirmed PERSISTENT 220030 (ima-mcp channel ok; controls HG-063/CF-101 return full text) -> content-side corruption in IMA; NOT truncation, NOT channel fault. 按摄入中断铁律不写 ingested，需人工至 IMA 客户端核查原文",
            "code": "220030",
            "status": "needs_manual_check"
        })
        print("ADD failed_220030:", HG062[:38])
    else:
        print("SKIP failed_220030 (dup)")

if not DRY:
    # recompute ALL totals.libraries from actual ingested lengths (fixes pre-existing staleness)
    for lid, lib in d["libraries"].items():
        d["totals"]["libraries"][lid]=len(lib["ingested"])
    d["totals"]["ingested_total"]=sum(d["totals"]["libraries"].values())
    d["updated"]="2026-09-05"
    d["last_run_ts_ms"]=int(datetime.datetime.now().timestamp()*1000)
    ts=datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak=STATE+f".bak-{ts}"
    shutil.copy2(STATE, bak)
    json.dump(d, open(STATE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print("WROTE. backup:", bak)
else:
    print(f"DRY-RUN. would add {added} entries. ingested_total {d['totals']['ingested_total']} -> {d['totals']['ingested_total']+added}")
