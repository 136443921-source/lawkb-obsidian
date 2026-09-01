#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段1 知识盲区扫描量化：按 W31 口径测算各领域覆盖度。
笔记质量 = frontmatter0.2 + 双向链接0.2 + 标签0.1 + 90天更新0.2 + 长度0.3
覆盖度 = 匹配笔记该加权分均值。"""
import os, re, json, datetime

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
VAULT = ROOT
EXCLUDE = {"IMA-Inbox", "03-连接/运维过程", "scripts", ".workbuddy"}
NOW = datetime.datetime(2026, 8, 30)
RECENT = NOW - datetime.timedelta(days=90)

DOMAINS = {
    "合同纠纷": ["合同", "协议", "买卖", "违约", "解除", "履行"],
    "股东知情权/公司法": ["股东", "知情权", "公司法", "决议", "出资"],
    "婚姻家庭": ["婚姻", "离婚", "抚养", "家事", "财产分割", "抚养权"],
    "担保/商事": ["担保", "保证", "抵押", "质押", "商事"],
    "人伤/劳务": ["人伤", "劳务", "损害", "医疗", "工伤", "侵权"],
    "慈法合规": ["慈善", "基金会", "公益", "慈法", "捐赠", "合规"],
}

link_re = re.compile(r"\[\[([^\]]+)\]\]")

def has_frontmatter(text):
    return text.startswith("---")

def count_links(text):
    return len(link_re.findall(text))

def count_tags(text):
    m = re.search(r"^tags:\s*$", text, re.M)
    # count "- xxx" under tags
    tags = re.findall(r"^tags:\s*$", text, re.M)
    # simpler: find tags block
    mt = re.search(r"tags:\s*\n((?:\s*-\s*.+\n)+)", text)
    if not mt:
        # inline tags: tags: [a, b]
        mi = re.search(r"tags:\s*\[(.+)\]", text)
        return len([x for x in mi.group(1).split(",") if x.strip()]) if mi else 0
    return len([l for l in mt.group(1).splitlines() if l.strip().startswith("-")])

def score_note(path):
    try:
        text = open(path, encoding="utf-8", errors="ignore").read()
    except Exception:
        return None
    fm = 1.0 if has_frontmatter(text) else 0.3
    nlinks = count_links(text)
    link_s = min(nlinks / 5.0, 1.5)
    ntags = count_tags(text)
    tag_s = min(ntags / 3.0, 1.3) if ntags > 0 else 0.0
    # update recency
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path))
    if mtime >= RECENT:
        upd_s = 1.0 + 0.5 * ((mtime - RECENT) / datetime.timedelta(days=90))
    else:
        age = (NOW - mtime).days
        upd_s = max(0.2, 1.0 - age / 365.0)
    length = len(text)
    len_s = min(length / 2000.0, 1.5)
    quality = 0.2*fm + 0.2*link_s + 0.1*tag_s + 0.2*upd_s + 0.3*len_s
    return quality

def domain_match(path, text, kws):
    base = os.path.basename(path)
    hay = base + "\n" + text[:4000]
    return any(k in hay for k in kws)

results = {}
notes_all = []
for dp, _, fns in os.walk(VAULT):
    rel = os.path.relpath(dp, ROOT)
    if any(rel.startswith(e) or ("/" + e) in ("/" + rel) for e in EXCLUDE):
        continue
    if any(e in rel.split(os.sep) for e in ["IMA-Inbox"]):
        continue
    for fn in fns:
        if not fn.endswith(".md"):
            continue
        full = os.path.join(dp, fn)
        results.setdefault("_files", 0)
        results["_files"] += 1

for dp, _, fns in os.walk(VAULT):
    rel = os.path.relpath(dp, ROOT)
    parts = rel.split(os.sep)
    if "IMA-Inbox" in parts:
        continue
    if rel.startswith("03-连接/运维过程") or rel.startswith("scripts"):
        continue
    for fn in fns:
        if not fn.endswith(".md"):
            continue
        full = os.path.join(dp, fn)
        try:
            text = open(full, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        for dom, kws in DOMAINS.items():
            if domain_match(full, text, kws):
                q = score_note(full)
                if q is None:
                    continue
                results.setdefault(dom, {"n": 0, "sum": 0.0})
                results[dom]["n"] += 1
                results[dom]["sum"] += q

print("扫描文件总数:", results.get("_files"))
for dom in DOMAINS:
    d = results.get(dom)
    if d and d["n"]:
        cov = d["sum"] / d["n"]
        print(f"{dom}\t匹配={d['n']}\t量化覆盖度={cov:.3f}\t判定={'严重' if cov<0.5 else ('中度' if cov<1.0 else '良好')}")
    else:
        print(f"{dom}\t匹配=0\t量化覆盖度=N/A")
