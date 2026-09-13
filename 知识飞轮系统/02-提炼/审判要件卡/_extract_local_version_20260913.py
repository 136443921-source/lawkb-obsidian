#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地法规库「版本指纹」提取器 —— 版本元数据补标专项（2026-09-13）

背景：qcc 通道余额耗尽，无法逐部远程核验条文。
替代方案：从本地文件正文自带的官方沿革中提取版本指纹，
         与已获取的 qcc 元信息交叉验证。

指纹三件套（全部来自文件正文，不凭记忆、不推断）：
  1. eff_date  —— 末条「本法/本条例自 X 年 X 月 X 日起施行」★最强指纹
  2. enact     —— 开头沿革「X年X月X日…通过/修订/修正」
  3. doc_no    —— 发文字号（主席令/国务院令/法释/部令等）

用法：
  python _extract_local_version_20260913.py            # 输出到 stdout + JSON
"""
import json, os, re, sys

ROOT = "/Users/chenyouqiang/Documents/LawKB"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "本地法规版本指纹-20260913.json")

CN = "零一二三四五六七八九〇两"
DATE = re.compile(r'((?:19|20)\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日')
# 末条施行日期条款：「本法自…起施行」「本条例自…起施行」「本规定自…起施行」
EFF = re.compile(r'本(?:法|条例|规定|办法|解释|细则|制度|规则|决定)\s*(?:自)?\s*'
                 r'((?:19|20)\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*(?:起)?\s*施行')
# 沿革：通过 / 修订 / 修正
ENACT = re.compile(r'((?:19|20)\d{2})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日'
                   r'[^，。；\n]{0,40}?(通过|修订|修正|公布|发布)')
# 发文字号
DOCNO = re.compile(r'(?:中华人民共和国主席令第[^\s，。]+号'
                   r'|中华人民共和国国务院令第[^\s，。]+号'
                   r'|法释〔[^\s，。]+?〕\s*\d+\s*号'
                   r'|法释\[[^\]]+\]\s*\d+\s*号'
                   r'|国务院令第[^\s，。]+号'
                   r'|主席令第[^\s，。]+号'
                   r'|(?:国家|中国)?[^\s，。]{0,10}(?:令|公告)\s*第?\s*[^\s，。]{0,8}号)')


def d2s(y, m, d):
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def body_of(path):
    s = open(path, encoding="utf-8", errors="replace").read()
    if s.startswith("---"):
        e = s.find("\n---", 3)
        if e > 0:
            s = s[e + 4:]
    return s


def fingerprint(path):
    b = body_of(path)
    flat = re.sub(r'\s+', '', b)

    # ① 末条施行日期（取最后一处，附则条款一定在末尾）
    eff = None
    for m in EFF.finditer(flat):
        eff = d2s(m.group(1), m.group(2), m.group(3))

    # ② 沿革：取全部，保留最后一条（最新一次修订）
    enacts = []
    for m in ENACT.finditer(flat[:3000]):
        enacts.append((d2s(m.group(1), m.group(2), m.group(3)), m.group(4)))
    enact = enacts[-1] if enacts else None

    # ③ 发文字号
    doc = None
    m = DOCNO.search(flat[:3000])
    if m:
        doc = m.group(0)

    return {"eff_date": eff, "enact_date": enact[0] if enact else None,
            "enact_act": enact[1] if enact else None, "doc_no": doc}


def main():
    files = json.load(open("/tmp/meta_files_0913.json", encoding="utf-8"))
    out = {}
    for it in files:
        p = os.path.join(ROOT, it["path"])
        if not os.path.exists(p):
            continue
        try:
            fp = fingerprint(p)
        except Exception as e:
            fp = {"err": str(e)}
        fp["qname"] = it["qname"]
        fp["n_arts"] = it["n_arts"]
        fp["last_no"] = it["last_no"]
        out[it["path"]] = fp

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    has_eff = sum(1 for v in out.values() if v.get("eff_date"))
    has_en = sum(1 for v in out.values() if v.get("enact_date"))
    has_doc = sum(1 for v in out.values() if v.get("doc_no"))
    print(f"指纹提取：{len(out)} 文件")
    print(f"  施行日期(最强指纹)  {has_eff}")
    print(f"  制定/修订沿革      {has_en}")
    print(f"  发文字号           {has_doc}")
    print(f"  三无               {sum(1 for v in out.values() if not any([v.get('eff_date'), v.get('enact_date'), v.get('doc_no')]))}")
    print(f"写入 {OUT}")


if __name__ == "__main__":
    main()
