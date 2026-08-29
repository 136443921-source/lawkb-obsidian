import json,os,re
ROOT="/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/经验卡片"
d=json.load(open("/Users/chenyouqiang/Documents/LawKB/.workbuddy/tmp_backfill/cards_ranked.json",encoding="utf-8"))
withcase=[c for c in d if c["fm"].get("case_no","").strip() not in ("","-")]
print("含 frontmatter case_no 的个案蒸馏型卡：",len(withcase))
for c in withcase:
    fm=c["fm"]
    print(f"  - {os.path.relpath(c['path'],ROOT)}")
    print(f"      case_type={fm.get('case_type','-')} | conf={fm.get('confidence','-')}")
print()
print("规则锚定型（无 case_no，按规范跳过）：",len(d)-len(withcase))
