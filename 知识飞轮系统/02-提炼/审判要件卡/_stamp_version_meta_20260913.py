#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地法律法规库「版本元数据补标」写入器 —— 版本元数据补标专项（2026-09-13）

三级判定（严守坑 33：宁可少填，不可填错）：
  A 级 · 可标现行有效
      判据：本地末条施行日期 == qcc 现行版施行日期  ★双证一致
      写入：version / sxx: 现行有效 / source / version_basis
  B 级 · 版本存疑，禁止据以回填
      判据：本地施行日期 != qcc 现行版（旧版）或 条数显著偏少（节选）
      写入：version_local / sxx: 版本存疑·待核验 / version_mismatch: true / version_note
  C 级 · 无远程核验，仅做沿革结构化
      判据：无 qcc 数据，或无施行日期指纹
      写入：version_local / sxx: 待远程核验 / version_basis
      ★ 不标现行有效

用法：
  python _stamp_version_meta_20260913.py            # dry-run
  python _stamp_version_meta_20260913.py --apply    # 写入
"""
import json, os, re, sys, shutil

ROOT = "/Users/chenyouqiang/Documents/LawKB"
HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = "2026-09-13"
APPLY = "--apply" in sys.argv

FP = json.load(open(os.path.join(HERE, "本地法规版本指纹-20260913.json"), encoding="utf-8"))
QA = json.load(open(os.path.join(HERE, "_meta_probe_A_20260913.json"), encoding="utf-8"))
FILES = json.load(open("/tmp/meta_files_0913.json", encoding="utf-8"))
BK = open("/tmp/bk_meta_0913.txt").read().split("=", 1)[1].strip()

# ---- 已知版本不符（本地指纹 vs qcc 现行版），由交叉验证得出 ----
MISMATCH = {
    "精神卫生法": ("2013-05-01", "2018-04-27", "本地为 2012 通过版，qcc 现行版为 2018 修正"),
    "境外非政府组织境内活动管理法": ("2017-01-01", "2017-11-05", "本地为 2016 通过版，qcc 现行版为 2017 修正"),
    "工伤保险条例": ("2004-01-01", "2011-01-01", "本地末条仍记 2004-01-01 施行，qcc 现行版为 2010 修订"),
    "药品管理法": ("2001-12-01", "2019-12-01", "本地末条仍记 2001-12-01 施行，qcc 现行版为 2019 修订"),
    "慈善法": ("2016-09-01", "2024-09-05", "本副本为 2016 原版（已被 2023 年修正取代），另有同名副本为现行版"),
    "民事诉讼法": (None, "2024-01-01", "本地仅 121 条，远少于现行 2023 修正版，疑为节选或旧版"),
}


def yq(v):
    """YAML 安全标量：一律单引号包裹，内部单引号转义"""
    if v is None:
        return "''"
    s = str(v).replace("\n", " ").strip()
    return "'" + s.replace("'", "''") + "'"


def split_fm(text):
    if not text.startswith("---"):
        return None, text
    e = text.find("\n---", 3)
    if e < 0:
        return None, text
    return text[3:e], text[e + 4:]


def fix_wikilink_title(fm):
    """修复 title: [[...]] 未加引号导致 YAML 判为流样式序列（坑 44 同根因，历史遗留）"""
    def repl(m):
        val = m.group(1).strip()
        if val.startswith("'") and val.endswith("'"):
            return m.group(0)
        return "title: " + yq(val)
    return re.sub(r"(?m)^title:\s*(\[\[.*)$", repl, fm)


def upsert(fm, pairs):
    """在 frontmatter 中插入/替换字段（一次原子重建）"""
    fm = fix_wikilink_title(fm)
    lines = fm.split("\n")
    out, done = [], set()
    for ln in lines:
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):", ln)
        if m and m.group(1) in pairs:
            k = m.group(1)
            out.append(f"{k}: {yq(pairs[k])}")
            done.add(k)
        else:
            out.append(ln)
    for k, v in pairs.items():
        if k not in done:
            out.append(f"{k}: {yq(v)}")
    return "\n".join(out)


def decide(path, it):
    """返回 (级别, 字段字典, 说明)"""
    fp = FP.get(path, {})
    q = QA.get(path)
    key = it["key"]
    eff = fp.get("eff_date")
    enact = fp.get("enact_date")
    n = fp.get("n_arts")

    # 本地沿革串（B/C 级用）
    bits = []
    if enact:
        bits.append(f"{enact}通过/修订")
    if eff:
        bits.append(f"末条载明{eff}施行")
    local_ver = "；".join(bits) if bits else None

    # ---- B 级：已知版本不符 ----
    if key in MISMATCH:
        ml, mq, why = MISMATCH[key]
        # 若本地指纹与"疑似旧版"的日期不符，说明这份不是旧版那一份 → 不套用
        if ml is None or eff == ml:
            return "B", {
                "version_local": local_ver,
                "sxx": "⚠️ 版本存疑·待核验",
                "version_mismatch": "true",
                "version_note": f"本地施行日期{eff or '缺'}，qcc 现行版为{mq}；{why}。禁止据以回填。",
                "version_source": "本地正文沿革（本地指纹，未经远程一致性校验）",
            }, why

    # ---- A 级：qcc 命中 且 施行日期一致 ----
    if q and q.get("found"):
        qeff = q.get("施行日期")
        if eff and qeff and eff == qeff and q.get("时效性") == "现行有效":
            return "A", {
                "version": q.get("matched_name"),
                "sxx": "现行有效",
                "source": f"企查查·法律数据核填·{TODAY}",
                "version_verify": f"本地末条施行日期 {eff} 与企查查现行版一致",
                "version_basis": "企查查·法律数据元信息 + 本地末条施行日期 双证一致",
                "version_doc_no": q.get("发文字号"),
                "version_effect_rank": q.get("效力级别"),
                "version_org": q.get("制定机关"),
                "version_effective_date": qeff,
                "version_ref": q.get("引用链接"),
            }, f"双证一致（{eff}）"

    # ---- C 级：其余，仅沿革结构化 ----
    basis = "本地正文制定/修订沿革提取，未经远程核验" if local_ver else "本地正文无版本线索"
    return "C", {
        "version_local": local_ver,
        "sxx": "待远程核验",
        "version_basis": basis,
    }, "无远程核验，仅结构化本地沿革"


def main():
    # ---- 第一遍：逐份独立判定 ----
    stat = {"A": 0, "B": 0, "C": 0}
    detail = {}
    for it in FILES:
        path = it["path"]
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            continue
        lvl, pairs, why = decide(path, it)
        detail[path] = {"level": lvl, "fields": pairs, "why": why, "key": it["key"]}

    # ---- 第二遍：同指纹副本传播 ----
    # 同一法规的镜像副本（eff_date 相同）应继承已核验成员的结论，
    # 否则主库判 A、采集副本判 C，等于把可用面白白砍掉一半。
    import collections
    groups = collections.defaultdict(list)
    for path, v in detail.items():
        groups[v["key"]].append(path)
    for key, paths in groups.items():
        tmpl = next((p for p in paths if detail[p]["level"] == "A"), None)
        if not tmpl:
            continue
        t_eff = FP.get(tmpl, {}).get("eff_date")
        for p in paths:
            if detail[p]["level"] != "C":
                continue
            if not t_eff or FP.get(p, {}).get("eff_date") != t_eff:
                continue  # 指纹不同 → 不传播（如慈善法 2016 原版 vs 2023 修正）
            f = dict(detail[tmpl]["fields"])
            f["version_verify"] = f["version_verify"] + "（同指纹副本继承）"
            detail[p] = {"level": "A", "fields": f,
                         "why": "同指纹镜像副本，继承已核验结论", "key": key}

    # ---- 写入 ----
    for path, v in detail.items():
        stat[v["level"]] += 1
        if not APPLY:
            continue
        full = os.path.join(ROOT, path)
        pairs = v["fields"]
        text = open(full, encoding="utf-8").read()
        fm, body = split_fm(text)
        if fm is None:
            print("  ⚠️ 无 frontmatter，跳过:", path)
            stat[v["level"]] -= 1
            continue
        new_fm = upsert(fm, pairs)
        open(full, "w", encoding="utf-8").write("---\n" + new_fm + "\n---" + body)
        if not APPLY:
            continue
        text = open(full, encoding="utf-8").read()
        fm, body = split_fm(text)
        if fm is None:
            print("  ⚠️ 无 frontmatter，跳过:", path)
            stat[lvl] -= 1
            continue
        new_fm = upsert(fm, pairs)
        open(full, "w", encoding="utf-8").write("---\n" + new_fm + "\n---" + body)

    json.dump(detail, open(os.path.join(HERE, "版本元数据补标明细-20260913.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"{'APPLY' if APPLY else 'DRY-RUN'}  A级(可标现行有效) {stat['A']}  "
          f"B级(版本存疑·禁止回填) {stat['B']}  C级(待远程核验) {stat['C']}")
    print(f"明细 -> 版本元数据补标明细-20260913.json | 备份 {BK}")


if __name__ == "__main__":
    main()
