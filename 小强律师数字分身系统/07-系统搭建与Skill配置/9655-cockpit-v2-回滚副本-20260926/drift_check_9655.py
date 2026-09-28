#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
9655 驾驶舱 · 手册口径漂移比对器（运维"活文档"守护）
================================================================
比对对象：
  A. 基线快照（手册 v1.1 的机器可读口径）  -> 9655_驾驶舱基线快照.json
  B. 实车真源：
       - rbac.js             (导航/权限注册表，D7/D8 检测)
       - scorecard_data.json (C0 实际渲染的评分/权重/flag)
       - scan_9655.py        (评分逻辑源：律所静态分、评级阈值、屏定义)
输出：
  - 口径漂移清单（=> 需修订《9655 驾驶舱运维手册》）
  - 运行健康清单（=> 运维处置，不强制改手册）
  - 退出码：0=对齐 / 1=口径漂移(需改手册) / 2=仅健康告警
守护原则：只读，不修改任何文件。
"""
import json
import re
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# 路径支持环境变量覆盖（便于隔离测试与迁移）
BASELINE = os.environ.get(
    "DC_BASELINE",
    "/Users/chenyouqiang/Documents/LawKB/小强律师数字分身系统/00-系统总览与运维中心/9655_驾驶舱基线快照.json",
)
SCORECARD = os.environ.get("DC_SCORECARD", os.path.join(HERE, "scorecard_data.json"))
RBAC = os.environ.get("DC_RBAC", os.path.join(HERE, "rbac.js"))
SCAN = os.environ.get("DC_SCAN", os.path.join(HERE, "scan_9655.py"))


def load_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def load_text(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def parse_rbac_sites(txt):
    """从 rbac.js 抽取 sites 注册表 -> {key: {cno, lawFirm}}
    注意：roles.*.sites 用的是数组(sites: [...])，必须只匹配顶层对象(sites: {...})。"""
    mm = re.search(r'^\s*sites:\s*\{', txt, re.M)
    if not mm:
        return {}
    i = mm.start()
    j = txt.index("{", i)
    depth = 0
    k = j
    n = len(txt)
    block = ""
    while k < n:
        c = txt[k]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                block = txt[j + 1:k]
                break
        k += 1

    sites = {}
    i2 = 0
    while i2 < len(block):
        m = re.match(r"\s*([A-Za-z_][\w]*)\s*:\s*\{", block[i2:])
        if not m:
            nl = block.find("\n", i2)
            i2 = nl + 1 if nl >= 0 else len(block)
            continue
        key = m.group(1)
        start = i2 + m.end() - 1
        depth = 0
        kk = start
        while kk < len(block):
            c = block[kk]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    entry = block[start + 1:kk]
                    props = {}
                    for pm in re.finditer(r"(\w+)\s*:\s*([^,\n]+)", entry):
                        props[pm.group(1)] = pm.group(2).strip().rstrip(",").strip()
                    cno = props.get("cno", "").strip().strip('"')
                    law = props.get("lawFirm", "false").strip().lower() == "true"
                    sites[key] = {"cno": cno, "lawFirm": law}
                    i2 = kk + 1
                    break
            kk += 1
        else:
            break
    return sites


def extract_lawfirm_scores(scan_txt):
    """从 scan_9655.py 抽取 LAWFIRM_9360_SCORE -> {key: score}"""
    m = re.search(r"LAWFIRM_9360_SCORE\s*=\s*\{(.*?)\}", scan_txt, re.S)
    if not m:
        return {}
    d = {}
    for km in re.finditer(r'"([\w]+)"\s*:\s*([\d.]+)', m.group(1)):
        d[km.group(1)] = float(km.group(2))
    return d


def extract_grade_thresholds(scan_txt):
    """从 grade_of() 抽取阈值 -> {A,B,C,D}"""
    d = {}
    m = re.search(r"def grade_of\(v\):(.*?)return", scan_txt, re.S)
    if not m:
        return d
    body = m.group(1)
    for letter in ["A", "B", "C", "D"]:
        mm = re.search(r'if v >= (\d+): return "' + letter, body)
        if mm:
            d[letter] = int(mm.group(1))
    return d


def main():
    base = load_json(BASELINE)
    sc = load_json(SCORECARD)
    rbac_txt = load_text(RBAC)
    scan_txt = load_text(SCAN)

    exp = base["expected_screens"]
    expected_keys = set(exp.keys())
    drift = []
    health = []

    # ---- 1. rbac.js 屏注册表 ----
    rbac_sites = parse_rbac_sites(rbac_txt)
    rbac_keys = set(rbac_sites.keys())
    forbidden = base.get("forbidden_cno", [])
    for key, info in rbac_sites.items():
        if info["cno"] in forbidden:
            drift.append("⛔ rbac.js 出现禁用屏 {cno}（{key}），手册口径为 15 屏且无 D7/D8".format(cno=info["cno"], key=key))
    for k in expected_keys - rbac_keys:
        drift.append("🔻 rbac.js 缺失预期屏：{k}（{cno} {name}）".format(k=k, cno=exp[k]["cno"], name=exp[k]["name"]))
    for k in rbac_keys - expected_keys:
        drift.append("🔺 rbac.js 多出非预期屏：{k}（cno={cno}）".format(k=k, cno=rbac_sites[k]["cno"]))
    for cno in forbidden:
        if re.search(r'"' + re.escape(cno) + r'"', rbac_txt) or re.search(r'\b' + re.escape(cno.lower()) + r'\b', rbac_txt):
            if not any(info["cno"] == cno for info in rbac_sites.values()):
                drift.append("⛔ rbac.js 文本中出现禁用编号 {cno}".format(cno=cno))

    # ---- 2. scorecard_data.json 屏渲染 ----
    sc_screens = {s["key"]: s for s in sc["screens"]}
    sc_keys = set(sc_screens.keys())
    for k in expected_keys - sc_keys:
        drift.append("🔻 scorecard_data.json 缺失预期屏：{k}".format(k=k))
    for k in sc_keys - expected_keys:
        drift.append("🔺 scorecard_data.json 多出非预期屏：{k}（cno={cno}）".format(k=k, cno=sc_screens[k].get("cno")))
    for cno in forbidden:
        if any(s.get("cno") == cno for s in sc["screens"]):
            drift.append("⛔ scorecard_data.json 出现禁用屏 {cno}".format(cno=cno))
    # 逐屏属性
    tol = float(base.get("score_tolerance", 0.05))
    for k, e in exp.items():
        if k not in sc_screens:
            continue
        s = sc_screens[k]
        if s.get("cno") != e["cno"]:
            drift.append("🔻 屏 {k} cno 不符：手册 {ec} vs 实车 {sc}".format(k=k, ec=e["cno"], sc=s.get("cno")))
        if bool(s.get("lawFirm")) != bool(e["lawFirm"]):
            drift.append("🔻 屏 {k} lawFirm 标记不符：手册 {ec} vs 实车 {sc}".format(k=k, ec=e["lawFirm"], sc=s.get("lawFirm")))
        if abs(float(s.get("weight", 0)) - float(e["weight"])) > 1e-6:
            drift.append("🔻 屏 {k} 权重不符：手册 {ec} vs 实车 {sc}".format(k=k, ec=e["weight"], sc=s.get("weight")))
        if bool(s.get("scoring")) != bool(e["scoring"]):
            drift.append("🔻 屏 {k} scoring 标记不符：手册 {ec} vs 实车 {sc}".format(k=k, ec=e["scoring"], sc=s.get("scoring")))
    # 律所静态分比对（cno -> key 映射）
    cno2key = {e["cno"]: k for k, e in exp.items()}
    lf = base.get("law_firm_static_scores", {})
    for cno, anchor in lf.items():
        k = cno2key.get(cno)
        if not k or k not in sc_screens:
            continue
        s = sc_screens[k]
        sc_score = s.get("score")
        if sc_score is None:
            drift.append("🔻 律所屏 {cno}({k}) 评分为空，手册口径为静态 {a}".format(cno=cno, k=k, a=anchor))
        elif abs(float(sc_score) - float(anchor)) > tol:
            drift.append("🔻 律所屏 {cno}({k}) 评分漂移：手册静态 {a} vs 实车 {s}（超容差 {t}）".format(cno=cno, k=k, a=anchor, s=sc_score, t=tol))
    # 非评分位
    for cno in base.get("non_scored_cno", []):
        k = cno2key.get(cno)
        if k and k in sc_screens and sc_screens[k].get("scoring") is True:
            drift.append("🔻 非评分位 {cno}({k}) 被设为纳入评分，手册口径为不评分监控位".format(cno=cno, k=k))

    # ---- 3. scan_9655.py 逻辑源 ----
    lf_src = extract_lawfirm_scores(scan_txt)
    for cno, anchor in lf.items():
        k = cno2key.get(cno)
        if k and k in lf_src and abs(lf_src[k] - anchor) > tol:
            drift.append("🔻 scan_9655.py 律所静态分逻辑变更：{k} 现为 {v}（手册口径 {a}）".format(k=k, v=lf_src[k], a=anchor))
    th = extract_grade_thresholds(scan_txt)
    bt = base.get("grade_thresholds", {})
    for letter in ["A", "B", "C", "D"]:
        if letter in bt and letter in th and th[letter] != bt[letter]:
            drift.append("🔻 评级阈值变更：{l} 现为 {v}（手册口径 {a}）".format(l=letter, v=th[letter], a=bt[letter]))

    # ---- 4. 运行健康（非手册修订触发） ----
    total = sc.get("total")
    grade = sc.get("grade", "")
    floor = base.get("total_grade_floor", "C 合格")
    floor_letter = floor[0] if floor else "C"
    if grade and grade[0] != floor_letter and grade[0] not in ("A", "B"):
        health.append("🔴 环形总评跌至 {g}（手册口径底线 {f}），需排查六维回落原因".format(g=grade, f=floor))
    for s in sc["screens"]:
        if s.get("scoring") and s.get("score") is None:
            health.append("🟠 评分屏 {cno}({k}) 评分为空，存在数据缺口".format(cno=s.get("cno"), k=s.get("key")))

    # ---- 输出 ----
    report = {
        "checked_at": sc.get("generated_at"),
        "baseline_manual_version": base.get("manual_version"),
        "drift_count": len(drift),
        "drift": drift,
        "health_count": len(health),
        "health": health,
        "aligned": len(drift) == 0,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("")
    print("==== 9655 驾驶舱 · 手册口径漂移比对 ====")
    print("基线手册版本：{v}".format(v=base.get("manual_version")))
    print("实车评分生成时间：{t}".format(t=sc.get("generated_at")))
    if drift:
        print("❌ 发现 {n} 项口径漂移（需修订《9655 驾驶舱运维手册》）".format(n=len(drift)))
        for d in drift:
            print("   " + d)
    else:
        print("✅ 手册口径与实车一致，无漂移")
    if health:
        print("⚠️ 运行健康提示 {n} 项（运维处置，不强制改手册）".format(n=len(health)))
        for h in health:
            print("   " + h)
    sys.exit(1 if drift else (2 if health else 0))


if __name__ == "__main__":
    main()
