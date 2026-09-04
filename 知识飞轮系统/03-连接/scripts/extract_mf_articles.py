# -*- coding: utf-8 -*-
"""从本地民法典全文精确抽取指定条文（免费，不走元典）。"""
import re

SRC = "/Users/chenyouqiang/Documents/LawKB/法律法规库/通用实体法/中华人民共和国民法典（全文）.md"

CN = "零一二三四五六七八九"


def num2cn(n):
    """1-9999 -> 中文数字（民法典条文写法）"""
    assert 1 <= n <= 9999
    if n < 10:
        return CN[n]
    if n < 20:
        return ("十" + CN[n % 10]) if n % 10 else "十"
    if n < 100:
        s = CN[n // 10] + "十"
        return s + (CN[n % 10] if n % 10 else "")
    if n < 1000:
        s = CN[n // 100] + "百"
        r = n % 100
        if r == 0:
            return s
        if r < 10:
            return s + "零" + CN[r]
        if r < 20:
            return s + "一十" + (CN[r % 10] if r % 10 else "")
        s += CN[r // 10] + "十"
        return s + (CN[r % 10] if r % 10 else "")
    s = CN[n // 1000] + "千"
    r = n % 1000
    if r == 0:
        return s
    if r < 100:
        s += "零"
    return s + num2cn(r)


lines = open(SRC, encoding="utf-8").read().split("\n")
pat = re.compile(r"^(第[零一二三四五六七八九十百千]+条)([　\s]*)")

idx = {}   # 条号 -> (start_line, end_line_exclusive)
cur = None
for i, ln in enumerate(lines):
    m = pat.match(ln)
    if m:
        if cur:
            idx[cur] = (idx[cur][0], i)
        cur = m.group(1)
        idx[cur] = (i, i + 1)
if cur:
    idx[cur] = (idx[cur][0], len(lines))

WANT = {
    "R-HT-181": [144, 146, 147, 148, 149, 150, 151, 153, 154],
    "R-HT-182": [855, 857],
    "R-HT-183": list(range(762, 770)),
    "R-HT-184": [782, 784, 786, 796],
    "R-HT-186": [401, 428, 538, 539, 540, 541],
}

out = []
miss = []
for card, nums in WANT.items():
    out.append("\n" + "=" * 70)
    out.append("## %s" % card)
    out.append("=" * 70)
    for n in nums:
        key = "第%s条" % num2cn(n)
        if key not in idx:
            miss.append("%s %s" % (card, key))
            out.append("\n【%s】❌ 本地未找到" % key)
            continue
        s, e = idx[key]
        body = "\n".join(lines[s:e]).strip()
        out.append("\n【%s】" % key)
        out.append(body)

print("\n".join(out))
print("\n" + "=" * 70)
print("缺失：", miss or "无 ✅")
open("/tmp/lawkb_mf_extract.txt", "w", encoding="utf-8").write("\n".join(out))
print("已存 /tmp/lawkb_mf_extract.txt")
