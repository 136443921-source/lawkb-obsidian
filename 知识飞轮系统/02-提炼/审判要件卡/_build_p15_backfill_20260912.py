#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第十五批补拆（三撤程序分流 + 婚姻债务与抚养）法条回填库建造器
2026-09-12
🔴 通道状态（实测，带时间戳）：
   北大法宝 / 华宇元典 —— 2026-09-12 09:5x 实测：connector-states.json 均 enabled=True/bound=True，
   但 ToolSearch 精确查 + DeferExecuteTool 真调用均返回 "not found in the deferred tools index"
   （工具未注册进本会话工具表）。→ 按 SKILL §5.0 第三顺位 + 坑 31 走**本地法律法规库**兜底，
   并复用历史批次中「北大法宝/华宇元典/最高法院官网」已核填的条文（属已在库权威文本）。
   本地与历史库均未收的，据实标「待回源」，绝不虚标。
"""
import json, re, os

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
LAW = "/Users/chenyouqiang/Documents/LawKB/法律法规库"
OUT = f"{BASE}/02-提炼/审判要件卡/贵州类案指南第二卷-第十五批补拆-法条回填库.json"

LOCAL = "本地法律法规库核填"
PENDING = "待回源（2026-09-12 法宝/元典未注册进本会话工具表，本地库未收）"

lib = {}


def add(key, law, article, text, source, timeliness="现行有效", note="", gid=""):
    lib[key] = {"law": law, "article": article, "text": text.strip(),
                "source": source, "timeliness": timeliness, "note": note, "gid": gid}


# ---------- 1) 本地《民事诉讼法（2023）》：加粗体 **第N条** ----------
MS = f"{LAW}/程序法/中华人民共和国民事诉讼法（2023）.md"
ms_txt = open(MS, encoding="utf-8").read()
ms_arts = {}
for m in re.finditer(r"(?m)^\*\*第(\d+)条\*\*[ 　]*([^\n]*)", ms_txt):
    ms_arts[m.group(1)] = m.group(2).strip()
assert len(ms_arts) > 250, f"民诉法条文提取异常：{len(ms_arts)}"
for n, desc in [("59", "第三人撤销之诉的起诉条件与期间"),
                ("238", "案外人执行异议、申请再审与执行异议之诉"),
                ("127", "起诉的分别处理（含第七项新情况新理由）")]:
    add(f"民诉法(2023)§{n}", "中华人民共和国民事诉讼法（2023）", f"第{n}条",
        ms_arts[n], f"{LOCAL}：《中华人民共和国民事诉讼法（2023）》",
        note=desc)

# ---------- 2) 本地《民法典（全文）》：裸 第N条 ----------
MFD = f"{LAW}/通用实体法/中华人民共和国民法典（全文）.md"
mf_txt = open(MFD, encoding="utf-8").read()


def cn_art(n):
    """阿拉伯数字 → 中文条号（民法典用中文）"""
    D = "零一二三四五六七八九"
    n = int(n)
    if n < 10:
        return D[n]
    if n < 20:
        return "十" + (D[n % 10] if n % 10 else "")
    if n < 100:
        return D[n // 10] + "十" + (D[n % 10] if n % 10 else "")
    q, r = divmod(n, 1000)
    h, r2 = divmod(r, 100)
    t, o = divmod(r2, 10)
    s = D[q] + "千"
    if h:
        s += D[h] + "百"
    elif t or o:
        s += "零"
    if t:
        s += (D[t] if t > 1 or q or h else "") + "十"
    elif o:
        s += "零"
    if o:
        s += D[o]
    return s


def get_mf(n):
    cn = cn_art(n)
    # 🔴 民法典正文用 U+2002(EN SPACE) 而非普通空格/全角空格（呼应坑 14「排版不一致」）
    m = re.search(rf"(?m)^第{cn}条[^\S\n]*([^\n]*(?:\n(?!第[零一二三四五六七八九十百千]+条)[^\n]*)*)", mf_txt)
    if not m:
        return None
    return re.sub(r"\n{2,}", "\n", m.group(1)).strip()


for n, desc in [(1064, "夫妻共同债务的认定"), (1067, "父母的抚养义务与子女的抚养费请求权"),
                (1084, "离婚后子女直接抚养的确定"), (1085, "离婚后抚养费的负担"),
                (1086, "探望权"), (1043, "家庭文明建设与夫妻互相忠实互相尊重")]:
    t = get_mf(n)
    if t:
        add(f"民法典§{n}", "中华人民共和国民法典", f"第{n}条", t,
            f"{LOCAL}：《中华人民共和国民法典（全文）》", note=desc)
    else:
        add(f"民法典§{n}", "中华人民共和国民法典", f"第{n}条", "", PENDING,
            timeliness="待核", note=desc)

# ---------- 3) 本地《九民会议纪要》 ----------
JJ = f"{LAW}/司法解释/全国法院民商事审判工作会议纪要（九民会议纪要）.md"
jj_txt = open(JJ, encoding="utf-8").read()
m = re.search(r"122\.【程序启动后案外人不享有程序选择权】([^\n]*)", jj_txt)
if m:
    add("九民纪要§122", "全国法院民商事审判工作会议纪要（九民会议纪要）", "第122条",
        m.group(1).strip().replace("　", ""),
        f"{LOCAL}：《全国法院民商事审判工作会议纪要》",
        note="🔴 坑24 条号位移：原文援引「民事诉讼法司法解释第303条」「《民事诉讼法》第227条」均为**旧版条号**；"
             "《民事诉讼法》2023 修正后「第227条」已位移为**第238条**；司法解释条号待回源核（贵州指南 2025 版引为第301条）")

# ---------- 4) 复用历史批次已核填条文（法宝/元典/最高法院官网） ----------
HIST = {
    "婚姻家庭-法条回填库.json": [("反家庭暴力法", "第二十三条"), ("反家庭暴力法", "第二十六条"),
                                 ("反家庭暴力法", "第二十七条"), ("反家庭暴力法", "第二十八条"),
                                 ("反家庭暴力法", "第二十九条"), ("反家庭暴力法", "第三十条"),
                                 ("反家庭暴力法", "第三十一条"), ("民诉法解释", "第一百零八条"),
                                 ("婚姻家庭编解释一", "第四十七条"), ("婚姻家庭编解释一", "第四十八条"),
                                 ("婚姻家庭编解释一", "第五十六条")],
    "抚养纠纷-法条回填库.json": [("婚姻家庭编解释一", "第四十条"), ("婚姻家庭编解释一", "第四十三条"),
                                 ("婚姻家庭编解释二", "第十四条"), ("婚姻家庭编解释二", "第十八条"),
                                 ("婚姻家庭编解释二", "第十九条")],
}
for fn, pairs in HIST.items():
    p = f"{BASE}/02-提炼/审判要件卡/贵州类案指南第二卷-{fn}"
    if not os.path.exists(p):
        print("⚠️ 缺失历史库", fn); continue
    d = json.load(open(p, encoding="utf-8"))
    items = d if isinstance(d, list) else list(d.values())
    for v in items:
        if not isinstance(v, dict):
            continue
        if (v.get("law"), v.get("article")) in pairs:
            law = v["law"]
            k = f"{law}§{v['article']}"
            src = v.get("source", "")
            add(k, law, v["article"], v.get("text", ""), src,
                timeliness=v.get("timeliness", "现行有效"),
                note=v.get("note", "") or "复用历史批次已核填条文（属已在库权威文本）",
                gid=v.get("gid", ""))

# ---------- 5) 待回源条目（本地与历史库均未收） ----------
for k, law, art, note in [
    ("民诉法解释§299", "最高人民法院关于适用《中华人民共和国民事诉讼法》的解释（2022修正）", "第299条",
     "第三人撤销之诉审理期间原裁判被裁定再审时的程序吸收规则及例外"),
    ("民诉法解释§301", "最高人民法院关于适用《中华人民共和国民事诉讼法》的解释（2022修正）", "第301条",
     "案外人救济程序选择权限制规则；⚠️《贵州指南》第二卷引为第301条，九民纪要(2019)引为第303条，内容一致——疑为2022修正后条号位移，引用前须核现行条号"),
    ("反家庭暴力法§32", "中华人民共和国反家庭暴力法", "第32条", "人身安全保护令的执行主体与协助执行"),
    ("反家庭暴力法§34", "中华人民共和国反家庭暴力法", "第34条", "违反人身安全保护令的法律责任"),
    ("家庭教育促进法§49", "中华人民共和国家庭教育促进法", "第49条", "责令接受家庭教育指导"),
]:
    add(k, law, art, "", PENDING, timeliness="待核", note=note)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(lib, f, ensure_ascii=False, indent=2)

ok = sum(1 for v in lib.values() if v["text"])
pend = sum(1 for v in lib.values() if not v["text"])
print(f"✅ 法条回填库：{OUT}")
print(f"   条目 {len(lib)}｜已核填 {ok}｜待回源 {pend}")
for k, v in lib.items():
    flag = "✅" if v["text"] else "⏳"
    print(f"   {flag} {k}  [{v['source'][:28]}]")
