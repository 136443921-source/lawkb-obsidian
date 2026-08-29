import os,re,glob
DIRS=["/Users/chenyouqiang/Documents/LawKB/小强律师数字分身系统/案件库/承办案件",
      "/Users/chenyouqiang/Documents/CaseDrop/processed"]
def fm(path):
    t=open(path,encoding="utf-8").read()
    if not t.startswith("---"): return {}
    e=t.find("\n---",3)
    if e<0: return {}
    d={};ck=None
    for ln in t[3:e].splitlines():
        m=re.match(r'^([A-Za-z_0-9\u4e00-\u9fff]+):\s*(.*)$',ln)
        if m: ck=m.group(1); d[ck]=m.group(2).strip()
        elif re.match(r'^\s*-\s+',ln) and ck: d.setdefault(ck+"__l",[]).append(ln.strip()[2:])
    return d
for D in DIRS:
    print("#### ",D)
    for p in sorted(glob.glob(os.path.join(D,"**","*.md"),recursive=True)):
        if ".bak" in p: continue
        f=fm(p)
        cn=f.get("case_no","-"); rs=f.get("result","-")
        ct=f.get("case_type","-") or f.get("案由","-")
        tg=f.get("tags","") or "/".join(f.get("tags__l",[]))
        closed = (rs not in ("-","","进行中") and "进行中" not in rs) and (cn not in ("-","","待补充") and "待补充" not in cn)
        print(f"  [{'CLOSED' if closed else '  open'}] {os.path.basename(p)[:44]:46} ct={ct[:28]:30} case_no={cn[:34]:36} result={rs[:60]}")
        if tg: print(f"           tags={tg[:100]}")
