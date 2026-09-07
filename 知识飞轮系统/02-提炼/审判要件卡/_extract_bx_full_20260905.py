import fitz, json
pdf="/Users/chenyouqiang/Desktop/贵州法院类案审判要件指南（第二卷）.pdf"
mp=json.load(open("贵州类案指南第二卷-页码映射表.json"))
doc=fitz.open(pdf)
out=[]
total_chars=0
for i in range(98,154):  # PDF 98..153 inclusive
    t=doc[i].get_text()
    bk=mp.get(str(i), "?")
    out.append(f"\n\n========== PDF页{i}（书页{bk}）==========\n")
    out.append(t)
    total_chars+=len(t)
open("贵州类案指南第二卷-保险合同-提取文本.md","w").write("".join(out))
print("saved, total chars:", total_chars)
