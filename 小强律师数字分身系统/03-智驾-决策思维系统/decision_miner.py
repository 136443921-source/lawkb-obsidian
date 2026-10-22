#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEC 档案挖掘引擎（P1-2 决策风格 + P2-2 决策树回流）· 2026-10-21
===============================================================
扫描 DEC 决策档案，解析 A/B/C 候选方案与老强拍板选择，产出：
  --style  决策风格画像：A/B/C 被选频次 + 所选方案属性词频（让分身按老强真实偏好排序选项）
  --tree   决策树回流：把散落 DEC 回流为可检索的决策树 JSON 节点（激活决策思维树）
  --list   列出已解析决策及拍板

数据源（实物核实 2026-10-21，两目录均实扫）：
  /Users/chenyouqiang/Documents/LawKB/_AI-Memory-Hub/03-决策档案/   （DEC-2026-* + DEC-006，主档案）
  /Users/chenyouqiang/Documents/LawKB/知识飞轮系统/04-LOG/决策日志/ （DEC-2026-* 思维轨迹 + 决策卡-*，2026-10-21 接入）

解析为启发式（DEC 格式不绝对统一）：
  - 候选方案段提取 A/B/C，支持两种格式：①「A｜desc」分隔式；②「A desc / B desc」空格分隔式；
  - 结论段「选项 X / 拍板 X / ＝A 软入口 / **A 授权** 加粗」等标记所选；
  - **硬闸**：必须解析出 ≥2 个选项 且 至少 1 个被拍板选中，否则视为「分类/枚举/单字母」非真决策，
    自动跳过（用于排除 DEC-026 类「A事实错/B前提不存在/C越界」错误类型分类表、ABC三级核查等）。
"""
import os
import re
import sys
import json
import argparse

DEC_DIRS = [
    "/Users/chenyouqiang/Documents/LawKB/_AI-Memory-Hub/03-决策档案",
    "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/04-LOG/决策日志",
]

# 选项段标题关键词（命中即视为"候选/备选"区块）
OPTION_SECTION_KW = ["候选方案", "备选", "候选"]
# 结论段标题关键词
CONCLUSION_SECTION_KW = ["结论", "拍板", "裁决", "落地动作"]

STOPWORDS = set("的 与 和 及 或 在 是 为 对 从 到 该 此 这 那 一 个 不 无 未 已 将 其 中 应 须 需 可 等 并 但 而 若 如 含 含 由 按 据 经 被 把 让 给 同 以 于 也 都 就 还 更 最 上 下 内 外".split())


def iter_dec_files():
    for d in DEC_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.lower().endswith(".md"):
                continue
            if not (fn.startswith("DEC-") or fn.startswith("决策卡-")):
                continue
            yield os.path.join(d, fn), fn


def parse_one(path, fn):
    txt = open(path, encoding="utf-8").read()
    # 取 frontmatter 之后的正文
    m = re.match(r"^---\n.*?\n---\n", txt, re.S)
    body = txt[m.end():] if m else txt

    # 定位选项段 + 结论段
    opt_sec, con_sec = "", ""
    lines = body.splitlines()
    cur = None
    buf = []
    sections = []
    for ln in lines:
        head = re.match(r"^#{1,4}\s*(.*)", ln)
        if head:
            if cur is not None:
                sections.append((cur, "\n".join(buf)))
            cur = head.group(1).strip()
            buf = []
        else:
            buf.append(ln)
    if cur is not None:
        sections.append((cur, "\n".join(buf)))

    for name, sec in sections:
        if any(k in name for k in OPTION_SECTION_KW):
            opt_sec += sec + "\n"
        if any(k in name for k in CONCLUSION_SECTION_KW):
            con_sec += sec + "\n"
    # 兜底：若未分段，整体当选项段
    if not opt_sec:
        opt_sec = body

    # 提取 A/B/C 选项（含 ← 拍板 标记）
    # 格式①「A｜desc」分隔式；格式②「A desc / B desc」空格+分隔式（如「A 软入口 / B 硬钩子」）
    opt_pat = re.compile(r"(?<![A-Za-z0-9])([A-C])\s*[｜|／/、]\s*([^\n（(]{2,40})")
    opt_pat2 = re.compile(r"(?<![A-Za-z0-9])([A-C])\s+([^／/、|｜\n（(]{2,20}?)\s*[／/、|｜]")
    options = []
    seen = set()
    chosen_by_marker = set()
    for pat in (opt_pat, opt_pat2):
        for mm in pat.finditer(opt_sec):
            letter = mm.group(1)
            desc = mm.group(2).strip().strip("*←").rstrip("）。。 ").strip()
            if letter in seen:
                continue
            seen.add(letter)
            is_chosen = "←" in opt_sec[mm.start():mm.start()+60] or "拍板" in opt_sec[mm.start():mm.start()+60]
            options.append({"letter": letter, "desc": desc, "chosen": is_chosen})
            if is_chosen:
                chosen_by_marker.add(letter)

    if not options:
        return None  # 无 A/B/C 结构，跳过
    if len(options) < 2:
        return None  # 单字母误捕（训练轨迹/证据分级等），非真 A/B/C 决策，跳过

    # 结论段提取所选字母（覆盖多表述：选项X / 拍板X / ＝A软入口 / **A授权**加粗 等）
    chosen_by_concl = set()
    concl_pats = [
        r"选项\s*([A-C])",
        r"拍板[：: ]*([A-C])",
        r"裁决[：: ]*([A-C])",
        r"选择\s*([A-C])",
        r"[＝=]\s*([A-C])\s*(?:软|硬|入口|薄壳|中台|落地|授权|静态|判决|撤诉|落定)",
        r"结论[（(]?\s*选项\s*([A-C])",
        r"老强拍板[：: ]*([A-C])",
        r"最终[采用选用决定确定采纳][：: ]*([A-C])",
        r"采用([A-C])\s*方案",
        r"确定([A-C])\s*方案",
        r"\*\*([A-C])\s*(?:授权|软入口|静态|判决|撤诉|落定|采用)",
    ]
    for pat in concl_pats:
        for cm in re.finditer(pat, con_sec + "\n" + body):
            chosen_by_concl.add(cm.group(1))

    chosen = chosen_by_marker | chosen_by_concl
    if not chosen:
        return None  # 硬闸：有 A/B/C 枚举但无「被拍板选中」标记 → 属分类/枚举（如 DEC-026 错误类型分类），非真决策，跳过
    for o in options:
        o["chosen"] = o["letter"] in chosen

    chosen_descs = [o["desc"] for o in options if o["chosen"]]
    # id / title
    fm = {}
    if m:
        for ln in m.group(0).splitlines()[1:-1]:
            if ":" in ln:
                k, v = ln.split(":", 1)
                fm[k.strip()] = v.strip()
    hm = re.search(r"^#\s*(.*)", body)
    title = fm.get("title") or (hm.group(1) if hm else fn) or fn
    did = fm.get("id") or fn

    return {
        "id": did, "title": title, "file": fn,
        "options": options,
        "chosen_letters": sorted(chosen),
        "chosen_descs": chosen_descs,
        "has_explicit_abc": True,
    }


def scan():
    recs = []
    for path, fn in iter_dec_files():
        r = parse_one(path, fn)
        if r:
            recs.append(r)
    return recs


def kw_tally(recs):
    cnt = {}
    for r in recs:
        for d in r["chosen_descs"]:
            toks = re.split(r"[｜|／/、，。；：（）()【】\s]+", d)
            for t in toks:
                t = t.strip().replace("*", "")
                if len(t) < 2 or t in STOPWORDS or t.startswith("←"):
                    continue
                # 取前 4 字作为候选属性短语
                cnt[t[:6]] = cnt.get(t[:6], 0) + 1
    return sorted(cnt.items(), key=lambda x: -x[1])


def cmd_style(recs):
    abc = {"A": 0, "B": 0, "C": 0}
    n = 0
    for r in recs:
        n += 1
        for o in r["options"]:
            if o["chosen"]:
                if o["letter"] in abc:
                    abc[o["letter"]] += 1
    kws = kw_tally(recs)
    print(f"📊 决策风格画像（解析到 {n} 条含 A/B/C 结构的 DEC）")
    print("-" * 50)
    print(f"A 被选次数：{abc['A']} ｜ B 被选次数：{abc['B']} ｜ C 被选次数：{abc['C']}")
    total = sum(abc.values()) or 1
    print(f"字母偏好占比：A {abc['A']/total:.0%} · B {abc['B']/total:.0%} · C {abc['C']/total:.0%}"
          f"（注：仅统计显式 A/B/C 维度的拍板；多维度 DEC 各维度分别计）")
    print("-" * 50)
    # 样本量告警（铁律：不粉饰、不注水——样本薄时明确标注信号强度）
    if n < 10:
        print("⚠️ 样本告警：n<10，以下画像**仅具方向性参考意义，不具统计显著性**，"
              "禁止据此替老强拍板；请继续攒拍板记录（随办案自然累积，不硬凑）。")
    elif n < 30:
        print("ℹ️ 样本提示：n<30，画像可作弱信号参考，统计显著性有限。")
    else:
        print("✅ 样本量达标（n≥30），画像具备统计显著性，可用于选项排序。")
    print("🔑 所选方案高频属性词（让分身给选项时按此排序的倾向信号）：")
    for w, c in kws[:20]:
        print(f"   {w:<10} ×{c}")


def cmd_tree(recs, out=None):
    tree = {
        "generated": True,
        "source": "DEC 决策档案（_AI-Memory-Hub/03-决策档案 + 04-LOG/决策日志）",
        "node_count": len(recs),
        "nodes": [],
    }
    for r in recs:
        tree["nodes"].append({
            "id": r["id"], "title": r["title"], "file": r["file"],
            "options": [{"letter": o["letter"], "desc": o["desc"], "chosen": o["chosen"]} for o in r["options"]],
            "chosen_letters": r["chosen_letters"],
        })
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(tree, f, ensure_ascii=False, indent=2)
        print(f"[OK] 决策树回流 {len(recs)} 节点 → {out}")
    else:
        print(json.dumps(tree, ensure_ascii=False, indent=2))


def cmd_list(recs):
    for r in recs:
        print(f"{r['id']:<40} 选={','.join(r['chosen_letters']) or '—'}  选项={''.join(o['letter'] for o in r['options'])}")


def main():
    ap = argparse.ArgumentParser(description="DEC 档案挖掘引擎")
    ap.add_argument("--style", action="store_true", help="输出决策风格画像")
    ap.add_argument("--tree", action="store_true", help="输出/生成决策树 JSON")
    ap.add_argument("--out", default=None, help="--tree 输出路径")
    ap.add_argument("--list", action="store_true", help="列出已解析决策")
    args = ap.parse_args()

    recs = scan()
    if not recs:
        print("[WARN] 未解析到含 A/B/C 结构的 DEC，请检查 DEC_DIRS 路径。")
        return
    if args.list:
        cmd_list(recs)
    elif args.style:
        cmd_style(recs)
    elif args.tree:
        cmd_tree(recs, args.out)
    else:
        print(f"解析到 {len(recs)} 条含 A/B/C 结构的 DEC。用 --style / --tree / --list。")


if __name__ == "__main__":
    main()
