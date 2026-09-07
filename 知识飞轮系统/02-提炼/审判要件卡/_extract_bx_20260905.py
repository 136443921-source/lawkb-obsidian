import fitz, json
pdf="/Users/chenyouqiang/Desktop/贵州法院类案审判要件指南（第二卷）.pdf"
mp=json.load(open("贵州类案指南第二卷-页码映射表.json"))
doc=fitz.open(pdf)
print("total pages:", doc.page_count)
# scan pages 90-160 first 140 chars to locate section boundaries
for i in range(90,161):
    t=doc[i].get_text()
    lines=[l for l in t.splitlines() if l.strip()]
    head=lines[0][:140] if lines else "(empty)"
    bk=mp.get(str(i), "?")
    print(f"PDF{i:>3} 书页{bk:>3} | {head}")
