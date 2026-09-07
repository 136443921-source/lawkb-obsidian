import fitz
SRC="/Users/chenyouqiang/Desktop/贵州法院类案审判要件指南（第二卷）.pdf"
doc=fitz.open(SRC)
out=[]
for i in range(214,254):  # PDF页 215-253
    t=doc[i].get_text()
    out.append(f"\n===== PDF页 {i+1} =====\n{t}")
txt="".join(out)
open("贵州类案指南第二卷-新就业形态-提取文本.md","w").write(txt)
print("字符数",len(txt))
