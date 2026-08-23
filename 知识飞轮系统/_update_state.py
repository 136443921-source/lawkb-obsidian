import json

p = "ima_intake_state.json"
d = json.load(open(p))

lib = "7312048136419112"
new = [
    ("wechatarticle_62fe55a7567bc291dfbbee29900b27c3_a4f92a530276fe3b27e99e18c2bf0edf7312048136419112", "教育培训合同兴趣班版模板", 7),
    ("wechatarticle_62fe55a7567bc291dfbbee29900b27c3_79e4947cef4236217120d2d07bf630ec7312048136419112", "保证合同纠纷实务100问", 8),
    ("wechatarticle_62fe55a7567bc291dfbbee29900b27c3_55921b6aacb0d6e8e08190223895c39c7312048136419112", "建设工程招标代理合同范本", 7),
]

ing = d["libraries"][lib]["ingested"]
added = 0
for mid, title, val in new:
    if mid in ing:
        print("SKIP already:", title)
        continue
    ing[mid] = {"title": title, "ingested_at": "2026-08-19", "value": val, "run": "2026-08-19"}
    added += 1

json.dump(d, open(p, "w"), ensure_ascii=False, indent=2)
d2 = json.load(open(p))
print("added:", added,
      "| contract ingested:", len(d2["libraries"][lib]["ingested"]),
      "| total:", sum(len(v["ingested"]) for v in d2["libraries"].values()))
