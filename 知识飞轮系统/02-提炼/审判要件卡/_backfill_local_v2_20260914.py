#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地法条源兜底核填器  v2 / 2026-09-14（存量卡质量巡检第 4 轮）

三道闸（缺一不可）：
  ① 坑 46 路径分类 —— 只收真法源，剔除裁判规则卡/案例卡/剪藏（部数不得虚高）
  ② 坑 33 版本门禁 —— frontmatter 有 version / sxx: 现行有效 / source: 元典权威回填 之一才准入；
     三者皆无的旧网页抓取源一律不得回填（宁可少填，不可填错）
  ③ 硬排除黑名单 —— 已知版本幻觉源（红队刑法库 = 1997 原版）

用法：python _backfill_local_v2_20260914.py
输出：本地法源准入门禁-20260914.json + 待回源匹配候选-20260914.json
"""
import os, re, json, glob, io, sys

try:
    import yaml
except ImportError:
    sys.stderr.write("FATAL: 缺 pyyaml，请用 envs/default/bin/python\n")
    sys.exit(2)

ROOT = "/Users/chenyouqiang/Documents/LawKB"
HERE = os.path.dirname(os.path.abspath(__file__))
MIN_SIZE, MIN_ARTICLES = 3000, 8

# ── 坑 46：路径白名单（只有这些才是法源）────────────────────
def is_statute(rel):
    if "/.backup" in rel or "/_隔离_" in rel or "/_archive" in rel:
        return False
    if rel.startswith("法律法规库/"):
        return True
    if "/01-采集/法律法规/" in rel:
        return True
    if "/常用法律法规库/" in rel:
        return True
    if "IMA缓存" in rel and "法律法规" in rel:
        return True
    return False


# ── 坑 33 硬排除黑名单（已知版本幻觉源）──────────────────────
BLACKLIST = {
    "智能体技能库/红队出庭律师/常用法律法规库/中华人民共和国刑法.md":
        "中国人大网 2019 页面所挂 1997 原版（§17 投毒罪、§274 两档无罚金、无 §134之一/§175之一）",
}

D = "零一二三四五六七八九"


def cn2num(s):
    if not s:
        return None
    if s.isdigit():
        return int(s)
    v, cur = 0, 0
    for c in s:
        if c == "零":
            cur = 0
        elif c == "十":
            cur = (cur or 1) * 10; v += cur; cur = 0
        elif c == "百":
            cur = (cur or 1) * 100; v += cur; cur = 0
        elif c == "千":
            cur = (cur or 1) * 1000; v += cur; cur = 0
        else:
            i = D.find(c)
            if i < 0:
                return None
            cur = i + 1
    return v + cur


# 坑 14 第三代 + 🔴 坑 50：本地库排版多样——裸「第X条」/ 加粗「**第X条**」/ 条号后 U+2002 /
# 条号与正文同行。行首锚定即可，**不可限制行尾长度**（否则民法典全条 MISS）。
# 🔴 字符集**绝不能含 \n**：`(?m)^` 已锚行首，若前缀类再含 `\s`（含换行），
#    正则会跨行吞掉上一行行尾，使「第N条」的位置映射到上一条正文 —— 条号整体错位。
#    实证：民法典 1260 条独立成行，`[\s\*　]{0,4}` 令 510/563/620/695 全部指向相邻条，
#    据此回填会制造系统性法条幻觉。改用不含换行的空白集即可修正。
ART = re.compile(r"(?m)^[ \t　\*]{0,4}第([零一二三四五六七八九十百千\d]+)条")


def frontmatter_ok(fm):
    """坑 33 版本门禁：三证居其一才准入"""
    if fm.get("version"):
        return True, f"version={fm.get('version')}"
    sxx = str(fm.get("sxx", ""))
    if "现行有效" in sxx:
        return True, f"sxx={sxx}"
    src = str(fm.get("source", ""))
    if "元典权威回填" in src or "元典" in src and "权威" in src:
        return True, f"source={src[:40]}"
    return False, "无 version / sxx:现行有效 / source:元典权威回填"


def main():
    # ① 扫描法源
    files = [p for p in glob.glob(os.path.join(ROOT, "**/*.md"), recursive=True)
             if is_statute(os.path.relpath(p, ROOT))]
    print(f"路径白名单命中法源文件：{len(files)}")

    admitted, rejected = {}, []
    for p in files:
        rel = os.path.relpath(p, ROOT)
        if rel in BLACKLIST:
            rejected.append({"path": rel, "why": "黑名单：" + BLACKLIST[rel]})
            continue
        try:
            t = io.open(p, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if len(t) < MIN_SIZE:
            continue
        arts = {}
        for m in ART.finditer(t):
            n = cn2num(m.group(1))
            if n:
                arts.setdefault(n, m.start())
        if len(arts) < MIN_ARTICLES:
            continue
        fm = {}
        if t.startswith("---"):
            e = t.find("\n---", 3)
            if e > 0:
                try:
                    fm = yaml.safe_load(t[3:e + 1]) or {}
                except Exception:
                    fm = {}
        ok, why = frontmatter_ok(fm)
        law = os.path.splitext(os.path.basename(p))[0]
        if ok:
            admitted.setdefault(law, []).append(
                {"path": rel, "n_arts": len(arts), "basis": why})
        else:
            rejected.append({"path": rel, "law": law, "n_arts": len(arts), "why": why})

    uniq = sorted({v[0]["path"].rsplit("/", 1)[-1][:-3] for v in admitted.values()})
    print(f"版本门禁准入：{len(admitted)} 个文件 / {len(uniq)} 部唯一法规")
    print(f"版本门禁拒绝：{len(rejected)} 个（宁可少填，不可填错）")

    json.dump({"admitted": {k: v for k, v in admitted.items()},
               "rejected": rejected,
               "blacklist": BLACKLIST},
              io.open(os.path.join(HERE, "本地法源准入门禁-20260914.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # ② 提取 46 张待回源卡的待回源条目
    cards = [p for p in glob.glob(os.path.join(
        ROOT, "知识飞轮系统/06-沉淀/裁判规则库/**/R-*.md"), recursive=True)
        if io.open(p, encoding="utf-8", errors="replace").read(4000).find("statute_text_pending: true") >= 0]
    print(f"\n待回源卡：{len(cards)} 张")

    BOOK = re.compile(r"《([^》]{2,60})》\s*第?\s*([零一二三四五六七八九十百千\d]+)\s*条")
    need = {}
    for p in cards:
        t = io.open(p, encoding="utf-8", errors="replace").read()
        # 只取「待回源」标记附近的行
        for i, ln in enumerate(t.split("\n")):
            if "待回源" not in ln:
                continue
            ctx = "\n".join(t.split("\n")[max(0, i - 2):i + 3])
            for m in BOOK.finditer(ctx):
                law, art = m.group(1), cn2num(m.group(2))
                if art:
                    need.setdefault(law, {}).setdefault(art, set()).add(os.path.basename(p))
    print(f"提取待回源法条：{sum(len(v) for v in need.values())} 条 / {len(need)} 部")

    # ③ 匹配：只在准入法源里找
    # 🔴 坑 50：法规名**不能按固定前 N 字匹配**——「中华人民共和国」是 8 字公共前缀，
    #   用 law[:6] 会把民法典匹配到医师法/刑法/刑诉法（全库假匹配）。
    #   正解：归一化（剥公共前缀与版本后缀）后做**相等或包含**判定。
    def norm_law(s):
        s = re.sub(r"[（(]\s*(?:\d{4}\s*)?(?:修正|修订|修正版|修订版|全文|草案|征求意见稿?)\s*[)）]", "", s)
        s = re.sub(r"^中华人民共和国", "", s)
        return re.sub(r"[\s（）()·、,]", "", s)

    admit_names = {k: v[0]["path"] for k, v in admitted.items()}
    norm2src = {}
    for k in admit_names:
        norm2src.setdefault(norm_law(k), []).append(k)

    # 条号存在性硬校验：必须真的能从源文件里取到第 N 条
    def article_exists(path, n):
        try:
            t = io.open(os.path.join(ROOT, path), encoding="utf-8", errors="replace").read()
        except Exception:
            return None
        for m in ART.finditer(t):
            if cn2num(m.group(1)) == n:
                seg = t[m.end():m.end() + 400].split("\n")[0].strip(" 　*")
                return seg
        return None

    matched, unmatched = [], []
    for law, arts in need.items():
        nl = norm_law(law)
        cands = norm2src.get(nl, [])
        if not cands:
            cands = [s for nn, ss in norm2src.items() if nl and (nl in nn or nn in nl) for s in ss]
        for a in sorted(arts):
            hit = None
            for c in cands:
                txt = article_exists(admit_names[c], a)
                if txt:
                    hit = {"src_name": c, "path": admit_names[c], "text": txt[:160]}
                    break
            if hit:
                matched.append({"law": law, "article": a, **hit, "files": sorted(arts[a])})
            else:
                unmatched.append({"law": law, "article": a,
                                  "cand": cands[:3], "files": sorted(arts[a])})

    print(f"  可匹配且条号实测存在：{len(matched)} 条")
    print(f"  无本地源/条号不存在（须待远程通道）：{len(unmatched)} 条")

    json.dump({"matched": matched, "unmatched": unmatched},
              io.open(os.path.join(HERE, "待回源匹配候选-20260914.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("\n产出：本地法源准入门禁-20260914.json / 待回源匹配候选-20260914.json")


if __name__ == "__main__":
    main()
