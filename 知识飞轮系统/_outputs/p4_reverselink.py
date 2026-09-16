# -*- coding: utf-8 -*-
import re, glob, os, sys
DIR="/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库/慈法合规"
os.chdir(DIR)
DRY = "--apply" not in sys.argv

rid2stem={}
for f in glob.glob("R-CF-*.md"):
    m=re.match(r"(R-CF-\d+)", f[:-3])
    if m: rid2stem[m.group(1)]=f[:-3]

# 目标C卡 -> 需补的判准卡(rid)
ADD = {
 159:[174,175],
 163:[175],
 164:[175],
}

def add_to_block(txt, new_stems):
    lines=txt.split("\n")
    # 找 判准↔操作 头 与 领域枢纽 行
    hdr=None; hub=None
    for i,l in enumerate(lines):
        if "判准↔操作 双向对应" in l and hdr is None:
            hdr=i
        if l.strip().startswith("- 领域枢纽") and hub is None and hdr is not None:
            hub=i; break
    if hdr is None or hub is None:
        return txt, False
    # 已存在检查
    block="\n".join(lines[hdr:hub])
    added=[]
    for s in new_stems:
        if s not in block:
            added.append("  - [[%s]]"%s)
    if not added:
        return txt, False
    new_lines = lines[:hub] + added + lines[hub:]
    return "\n".join(new_lines), True

for tgt, judges in ADD.items():
    f=[x for x in glob.glob("R-CF-%d-*.md"%tgt)]
    if not f:
        print("[跳过·无文件]", tgt); continue
    fn=f[0]
    txt=open(fn,encoding="utf-8").read()
    new_stems=[rid2stem["R-CF-%d"%j] for j in judges if "R-CF-%d"%j in rid2stem]
    out, changed = add_to_block(txt, new_stems)
    if DRY:
        print("="*50); print(fn, "变更" if changed else "无变更")
        if changed:
            print(out[out.index("判准↔操作"):out.index("领域枢纽")+20])
    else:
        if changed:
            open(fn,"w",encoding="utf-8").write(out)
            print("[已写]", fn)
        else:
            print("[无变更]", fn)
print("\n=== DRY=", DRY, "===")
