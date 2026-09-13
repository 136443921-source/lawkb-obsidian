#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
待回源项 × 本地法条源索引 匹配器 v2（2026-09-13）
🔴 相比 v1 的两处升级（坑 33 版本校验铁律）：
  1) 源准入门禁：本地源 frontmatter 必须含 `version` / `sxx: 现行有效` /
     `source: 元典权威回填` 之一，三者皆无的旧网页抓取源一律不得回填
  2) 已知雷区硬排除：智能体技能库/红队出庭律师/常用法律法规库/中华人民共和国刑法.md
     系中国人大网 2019 页面所挂 1997 原版（§17「投毒罪」、无 §134之一/§175之一）
只做匹配与报告，不写卡。
"""
import os, re, json, glob
from collections import defaultdict

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
IDX = os.path.join(BASE, "02-提炼/审判要件卡/本地法条源索引-20260912.json")
OUT = os.path.join(BASE, "02-提炼/审判要件卡/待回源匹配报告-20260913.json")

PRIORITY = [
    ("法律法规库/", 100),
    ("知识库/慈法知识库/", 70),
    ("01-采集/法律法规/", 60),
    ("01-采集/IMA缓存/", 50),
    ("02-提炼/", 40),
]
SKIP_DIR = [".backup", ".backup_link", "Backups"]
# 🔴 已知版本幻觉雷区（坑 33）
BLOCK = [
    "智能体技能库/红队出庭律师/常用法律法规库/中华人民共和国刑法.md",
]
# 版本元数据判据
VER_KEYS = ("version", "sxx", "source_verified")


def src_score(rel):
    for k, v in PRIORITY:
        if rel.startswith(k):
            return v
    return None          # 🔴 不在白名单的源不给分（含 90 分的红队库）


def has_version_meta(rel):
    """读真实文件 frontmatter，判有无版本元数据"""
    for root in ("/Users/chenyouqiang/Documents/LawKB", BASE):
        p = os.path.join(root, rel)
        if os.path.exists(p):
            break
    else:
        return False, "文件不存在"
    try:
        s = open(p, encoding="utf-8", errors="replace").read()[:3000]
    except Exception:
        return False, "读取失败"
    if not s.startswith("---"):
        return False, "无 frontmatter"
    e = s.find("\n---", 3)
    fm = s[:e] if e > 0 else s
    if any(re.search(r"(?m)^%s\s*:" % k, fm) for k in VER_KEYS):
        return True, "有版本元数据"
    m = re.search(r"(?m)^source\s*:\s*(.+)$", fm)
    if m and any(x in m.group(1) for x in ("元典", "法宝", "权威回填", "qcc", "企查查")):
        return True, "source 标注权威回填"
    return False, "无版本元数据（旧网页抓取源）"


def norm(s):
    s = re.sub(r"[《》〈〉（）()\[\]【】\s]", "", s)
    s = s.replace("中华人民共和国", "")
    s = re.sub(r"(2023修订|2021修正|2012修正|全文|节选.*?|红队)", "", s)
    return s


def build_lookup():
    idx = json.load(open(IDX, encoding="utf-8"))
    lut = {}
    blocked = []
    for rel, v in idx.items():
        if any(k in rel for k in SKIP_DIR):
            continue
        if any(b in rel for b in BLOCK):
            blocked.append(rel)
            continue
        sc = src_score(rel)
        if sc is None:
            continue
        ok, why = has_version_meta(rel)
        if not ok:
            continue                    # 🔴 坑 33：无版本元数据一律不得回填
        for key in {norm(v["name"]), norm(os.path.basename(rel).replace(".md", ""))}:
            if not key:
                continue
            if key not in lut or sc > lut[key][0]:
                lut[key] = (sc, rel, v["arts"])
    return lut, blocked


PEND_RE = re.compile(r"[>→\-\s]*⚠️\s*待回源[：:]\s*(.+)")
BOOK_RE = re.compile(r"《([^》]+)》")
ART_RE = re.compile(r"第\s*([零一二三四五六七八九十百千]+|\d+)\s*条")
D = "零一二三四五六七八九"


def cn2num(s):
    if s.isdigit():
        return int(s)
    v, cur = 0, 0
    for c in s:
        if c == "十":
            cur = (cur or 1) * 10; v += cur; cur = 0
        elif c == "百":
            cur = (cur or 1) * 100; v += cur; cur = 0
        elif c == "千":
            cur = (cur or 1) * 1000; v += cur; cur = 0
        elif c in D:
            cur = D.index(c)
        else:
            return None
    return v + cur


def main():
    lut, blocked = build_lookup()
    print(f"准入本地源（过坑33版本门禁）：{len(lut)} 部 | 硬排除雷区：{len(blocked)} 个")
    for b in blocked:
        print(f"   🚫 {b}")
    cards = []
    for p in sorted(glob.glob(os.path.join(BASE, "06-沉淀/裁判规则库/**/R-*.md"), recursive=True)):
        t = open(p, encoding="utf-8").read()
        if not re.search(r"(?m)^statute_text_pending: true", t):
            continue
        cards.append((p, t))

    fillable, unmatched = [], []
    for p, t in cards:
        for m in PEND_RE.finditer(t):
            raw = m.group(1).strip()
            le = t.find("\n", m.end())
            seg = t[m.start(): le if le > 0 else len(t)]
            books = BOOK_RE.findall(raw)
            arts = [a for a in (cn2num(x) for x in ART_RE.findall(raw)) if a]
            rec = {"card": os.path.relpath(p, BASE), "raw": raw[:150],
                   "books": books, "arts": arts, "match": None}
            hit = None
            for b in books:
                key = norm(b)
                if key in lut:
                    sc, rel, a = lut[key]
                    got = {n: a[str(n)] for n in arts if str(n) in a}
                    if got or not arts:
                        hit = {"law": b, "src": rel, "score": sc, "arts": got,
                               "n_arts_avail": len(a),
                               "arts_hit": sorted(got.keys(), key=int)}
                        break
            if hit:
                rec["match"] = hit
                fillable.append(rec)
            else:
                unmatched.append(rec)

    json.dump({"fillable": fillable, "unmatched": unmatched, "n_cards": len(cards),
               "n_source_admitted": len(lut), "blocked": blocked},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n_art = sum(len(r["match"]["arts"]) for r in fillable)
    print(f"\n待回源卡：{len(cards)} 张 | 条目：{len(fillable)+len(unmatched)} 条")
    print(f"  ✅ 本地可核填：{len(fillable)} 条（命中条文 {n_art} 条）")
    print(f"  ⚠️  真无源：{len(unmatched)} 条")
    g = defaultdict(list)
    for r in fillable:
        h = r["match"]
        g[r["card"]].append(f'{h["law"]}§{",".join(map(str,h["arts_hit"])) or "全"}'
                            f'  ← {h["src"].split("/")[0]}')
    print("\n=== 可核填（按卡聚合）===")
    for k, v in sorted(g.items()):
        print(f"  {os.path.basename(k)[:56]}")
        for x in v:
            print(f"      - {x}")
    print("\n=== 真无源（前 25）===")
    for r in unmatched[:25]:
        print(f"  [{os.path.basename(r['card'])[:32]}] {r['raw'][:66]}")
    print(f"\n报告 → {OUT}")


if __name__ == "__main__":
    main()
