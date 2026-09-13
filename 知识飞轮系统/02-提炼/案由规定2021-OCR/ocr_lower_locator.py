# -*- coding: utf-8 -*-
# 下册 OCR 定位器：粗扫全书，定位「侵权责任纠纷」段所在页序（0-based PDF 页）
import fitz, subprocess, sys, os

PDF="/Users/chenyouqiang/Desktop/最高人民法院新民事案件案由规定理解与适用（下册） 202111 杨万明.pdf"
DPI=200
lang="chi_sim"
doc=fitz.open(PDF)
N=doc.page_count
start=int(sys.argv[1]) if len(sys.argv)>1 else 0
end=int(sys.argv[2]) if len(sys.argv)>2 else N
step=int(sys.argv[3]) if len(sys.argv)>3 else 5

terms=["目录","第八部分","侵权责任纠纷","第十部分","第七部分","第九部分","适用特殊程序","与公司、证券"]
print(f"书总页数={N}，扫描 {start}..{end} step={step}", flush=True)
for pno in range(start, min(end,N), step):
    pg=doc[pno]
    pix=pg.get_pixmap(dpi=DPI)
    r=subprocess.run(["tesseract","stdin","stdout","-l",lang,"--psm","3"],
                     input=pix.tobytes("png"), capture_output=True)
    txt=r.stdout.decode("utf-8","ignore")
    hit=[t for t in terms if t in txt]
    if hit:
        # 取含术语的片段
        snippet=txt.replace("\n"," ")[:160]
        print(f"[命中] PDF页{pno+1}(idx{pno}) terms={hit} :: {snippet}", flush=True)
print("定位扫描结束", flush=True)
