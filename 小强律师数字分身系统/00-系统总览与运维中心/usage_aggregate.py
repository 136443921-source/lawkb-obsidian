#!/usr/bin/env python3
# 步5：usage_count / last_used 聚合（05-调用 → 注册表）
# 扫描 05-调用 目录下所有 md，统计每张卡被引用次数（usage_count）与最近引用时间（last_used）。
# 无结构化用量数据时诚实置 0，不臆造。六-B：写前 cp -n 备份。幂等：同输入同输出。
import os, re, json, shutil, datetime

FLY="/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
CALL=os.path.join(FLY,"05-调用")
HERE=os.path.dirname(os.path.abspath(__file__))
REG=os.path.join(HERE,"card_route_registry.yaml")
TS=datetime.datetime.now().strftime("%Y-%m-%d")

if not os.path.isdir(CALL):
    print(f"[usage] 05-调用 目录不存在：{CALL}，无可聚合用量数据，usage_count 保持 0"); raise SystemExit(0)

# 注册表全部 rid
reg=open(REG,encoding="utf-8").read()
rids=re.findall(r'(?m)^  - rule_id: (\S+)',reg)
# 扫描 05-调用
usage={r:0 for r in rids}
last={r:None for r in rids}
for root,_,files in os.walk(CALL):
    for f in files:
        if not f.endswith(".md"): continue
        p=os.path.join(root,f)
        try: t=open(p,encoding="utf-8",errors="ignore").read()
        except: continue
        mt=datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d")
        for r in rids:
            c=t.count(r)
            if c:
                usage[r]+=c
                if last[r] is None or mt>last[r]: last[r]=mt

# 回写注册表 usage_count / last_used（原位替换，保留其余字段）
out=[]; cur=None
for line in reg.split("\n"):
    m=re.match(r'  - rule_id: (\S+)',line)
    if m: cur=m.group(1)
    if line.strip().startswith("usage_count:") and cur:
        out.append(f"    usage_count: {usage[cur]}"); continue
    if line.strip().startswith("last_used:") and cur:
        out.append(f"    last_used: {last[cur]}"); continue
    out.append(line)
newtxt="\n".join(out)
bak=REG+".bak-usage-"+datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy2(REG,bak)
open(REG,"w",encoding="utf-8").write(newtxt)
n_used=sum(1 for r in rids if usage[r]>0)
print(f"[usage] 聚合完成：{n_used}/{len(rids)} 张卡在 05-调用 有引用记录；备份 {bak}")
print(f"[usage] 注册表 usage_count/last_used 已回写（无引用记录者诚实置 0）")
