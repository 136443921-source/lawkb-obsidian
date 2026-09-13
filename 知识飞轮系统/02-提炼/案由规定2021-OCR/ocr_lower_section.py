# -*- coding: utf-8 -*-
# 下册「侵权责任纠纷」段 OCR：逐页渲染+tesseract chi_sim，输出带 <<<PAGE N>>> 标记的全文
import fitz, subprocess, os, sys

PDF="/Users/chenyouqiang/Desktop/最高人民法院新民事案件案由规定理解与适用（下册） 202111 杨万明.pdf"
BASE="/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/案由规定2021-OCR"
OUT=os.path.join(BASE,"案由规定2021-下册-侵权责任段-OCR全文.txt")
PAGEDIR=os.path.join(BASE,"pages_lower")
os.makedirs(PAGEDIR, exist_ok=True)
DPI=200; lang="chi_sim"
doc=fitz.open(PDF)
start=int(sys.argv[1]); end=int(sys.argv[2])
print(f"SECTION OCR: {start}..{end} (共{end-start}页)", flush=True)
with open(OUT,"w",encoding="utf-8") as fo:
    for pno in range(start, min(end, doc.page_count)):
        pg=doc[pno]
        pix=pg.get_pixmap(dpi=DPI)
        r=subprocess.run(["tesseract","stdin","stdout","-l",lang,"--psm","3"],
                         input=pix.tobytes("png"), capture_output=True)
        txt=r.stdout.decode("utf-8","ignore")
        fo.write(f"\n<<<PAGE {pno}>>>\n")
        fo.write(txt)
        with open(os.path.join(PAGEDIR,f"p{pno:04d}.txt"),"w",encoding="utf-8") as fp:
            fp.write(txt)
        print(f"page {pno} done (len={len(txt)})", flush=True)
print("SECTION OCR DONE", flush=True)
