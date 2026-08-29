import json, os
ROOT="/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/经验卡片"
d=json.load(open("/Users/chenyouqiang/Documents/LawKB/.workbuddy/tmp_backfill/cards_ranked.json",encoding="utf-8"))
print("count:",len(d))
for i,c in enumerate(d,1):
    fm=c["fm"]
    tags=fm.get("tags","") or " / ".join(fm.get("tags__list",[]))
    print(f"{i:2d}. {c['sk']} conf={fm.get('confidence','-'):>5} dom={fm.get('domain','-')} ctype={fm.get('case_type','-')}")
    print(f"     {os.path.relpath(c['path'],ROOT)}")
    print(f"     tags: {tags[:110]}")
    print(f"     result: {fm.get('result','-')[:150]}")
