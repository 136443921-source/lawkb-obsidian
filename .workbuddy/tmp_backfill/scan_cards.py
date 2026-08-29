import os, re, json, glob

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/经验卡片"

def parse_fm(path):
    try:
        txt = open(path, encoding="utf-8").read()
    except Exception as e:
        return None, str(e)
    if not txt.startswith("---"):
        return {}, txt
    end = txt.find("\n---", 3)
    if end == -1:
        return {}, txt
    fm_raw = txt[3:end]
    body = txt[end+4:]
    fm = {}
    cur_key = None
    for line in fm_raw.splitlines():
        if re.match(r'^\s*-\s+', line) and cur_key:
            fm.setdefault(cur_key+"__list", []).append(line.strip()[2:].strip())
            continue
        m = re.match(r'^([A-Za-z_0-9\u4e00-\u9fff]+):\s*(.*)$', line)
        if m:
            cur_key = m.group(1)
            fm[cur_key] = m.group(2).strip()
    return fm, body

cards = []
for p in glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True):
    if ".bak" in p or "/.trash" in p:
        continue
    fm, body = parse_fm(p)
    if fm is None:
        continue
    cards.append({"path": p, "fm": fm, "body_len": len(body or "")})

print("total md (excl .bak):", len(cards))
sim = [c for c in cards if str(c["fm"].get("is_simulation","")).lower().startswith("true")]
print("is_simulation:true ->", len(sim))
for c in sim: print("   SKIP:", c["path"])

real = [c for c in cards if c not in sim]
withres = [c for c in real if c["fm"].get("result","").strip() not in ("", "null", "None")]
print("real cards:", len(real), "| with result field:", len(withres))

def sortkey(c):
    fm = c["fm"]
    d = fm.get("created","") or fm.get("review_date","") or ""
    d = re.sub(r'[^\d\-]', '', d)[:10]
    return d
withres.sort(key=sortkey, reverse=True)
print("\n=== TOP 12 by created/review_date ===")
for c in withres[:12]:
    fm=c["fm"]
    print(f"{sortkey(c)} | conf={fm.get('confidence','-')} | domain={fm.get('domain','-')} | case_no={fm.get('case_no','-')} | {os.path.relpath(c['path'],ROOT)}")

json.dump([{"path":c["path"],"fm":c["fm"],"sk":sortkey(c)} for c in withres],
          open("/Users/chenyouqiang/Documents/LawKB/.workbuddy/tmp_backfill/cards_ranked.json","w",encoding="utf-8"),
          ensure_ascii=False, indent=1)
