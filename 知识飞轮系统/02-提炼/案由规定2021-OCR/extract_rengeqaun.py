# -*- coding: utf-8 -*-
import re

path = "案由规定2021-上册-OCR全文.txt"
with open(path, encoding="utf-8") as f:
    lines = f.readlines()

# 收集所有 PAGE 标记：行号 -> PDF页号
page_marks = []  # (lineno, pageno)
for i, ln in enumerate(lines):
    m = re.search(r"<<<\s*PAGE\s+(\d+)\s*>>>", ln)
    if m:
        page_marks.append((i, int(m.group(1))))

def page_of(lineno):
    cur = None
    for pl, pn in page_marks:
        if pl <= lineno:
            cur = pn
        else:
            break
    return cur

# 人格权 11 个三级案由标题（正文部分，行 2918 起）
headings = [
    "1. 生命权、身体权、健康权纠纷",
    "2. 姓名权纠纷",
    "3. 名称权纠纷",
    "4. 肖像权纠纷",
    "5. 声音保护纠纷",
    "6. 名誉权纠纷",
    "7. 荣誉权纠纷",
    "8. 隐私权、个人信息保护纠纷",
    "9. 婚姻自主权纠纷",
    "10. 人身自由权纠纷",
    "11. 一般人格权纠纷",
]

print("=== 人格权三级案由 正文定位（行号 / 最近PDF页）===")
starts = {}
for h in headings:
    for i, ln in enumerate(lines):
        if h in ln and i > 2900:
            starts[h] = i
            print(f"{h:30s} 行 {i:5d}  PDF页 {page_of(i)}")
            break

# 关键横向对比段（discriminator 来源）
print("\n=== 横向对比/鉴别器段（L2 定性分野卡来源）===")
compare_anchors = [
    "荣誉权纠纷还是名誉权纠纷",
    "适用上述案由时需要注意: 对于侵害隐私权引发的纠纷",
    "参照适用肖像权保护的有关规定",
    "笔名、网名、译名、字号、姓名和名称的简称等，参照适用姓名权和名称权",
    "侵害姓名权的纠纷主要有",
    "声音保护的规则适用",
]
for a in compare_anchors:
    for i, ln in enumerate(lines):
        if a in ln and 2900 < i < 3930:
            print(f"[{a[:24]:24s}] 行 {i:5d}  PDF页 {page_of(i)}")
            break

# 管辖权条（民诉法解释第25条 网络侵权管辖）出现位置
print("\n=== 网络侵权管辖锚点（民诉法解释§25）===")
for i, ln in enumerate(lines):
    if "民事诉讼法解释》第 25 条" in ln and 2900 < i < 3930:
        print(f"行 {i:5d}  PDF页 {page_of(i)} : {ln.strip()[:60]}")
