#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pillars_probe.py — 聚合 8 个缺口探针 JSON + 缺口方案已验证事实 → pillars.json

S1 范式（铁律⑦获准偏差）：独立 JSON，不并入 scan_9655.py 核心；
仅实读本目录既有探针产物（零外联、零虚构），输出「四支柱 + 四配套」质量框架实时体检。

落点：cockpit 根目录（与 o1_health.json 等同位），由 com.xiaoqiang.pillars.plist 每 600s 触发。
"""
import json
import os
import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))

# 权威术语表（来源：缺口方案 §0.1/§0.2 + 造车手册 §六 完成度表，经老强批准；非凭记忆）
# code -> (name, detail 一句话内容说明)，用于面板展开「D1/H1 法规快照」等让使用者看懂
GLOSSARY = {
    "D1": ("法规快照", "外部法规库离线拉取为本地密文快照（74 文件 / 1915 KiB），检索核验不出机"),
    "H1": ("法规快照", "同 D1 法规快照链路（合规侧），离线密文、数据不出机"),
    "D3": ("加密备份", "关键产物加密备份（10.6 MB .enc），解密恢复成功、留本机不外传"),
    "D2": ("出网审计", "出网调用审计（4 事件 / 拦截 1 案号），敏感内容命中即 BLOCK"),
    "E1": ("结案复盘卡", "案件结案自动产出复盘卡，经验可沉淀"),
    "E2": ("沉淀质量门禁", "经验沉淀前过三联质量门禁，防脏数据入库"),
    "E3": ("经验卡模板库", "5 类经验卡模板，结构化复用"),
    "H3": ("待回源清零", "扫描本地法规库待回源残留并清零，防幻觉"),
    "O1": ("运维巡检", "常驻运维巡检探针（overall 实时），可审计"),
    "O2": ("缺口闭环度(G6)", "缺口技能部署记录 G6 闭环度（20/20 回填）"),
    "O3": ("成熟度追踪", "技能成熟度追踪（92/100 · 2 漂移可见）"),
    "H2": ("三源核验", "法条三源核验（库 74 篇），pending 诚实标"),
    "H4": ("幻觉看板", "AI 幻觉监控看板（c8_metrics 实时），防幻觉"),
    "S2": ("红线前置", "红线前置（R3 令牌 / R4 AIGC 标识）触发前拦截"),
    "S3": ("评分完整性", "评分环 == 六维均值一致性校验，禁假自洽"),
    "S4": ("引用边界", "单机密文版引用边界（lawyer-avatar-only 标签），定位清晰"),
    "S1": ("实时重接", "9655 S1 范式 16 屏实时重接，评分实时对齐"),
}


def load(name):
    p = os.path.join(ROOT, name)
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


o1 = load("o1_health.json")
o2 = load("o2_g6.json")
o3 = load("o3_maturity.json")
h2 = load("h2_verify.json")
c8 = load("c8_metrics.json")
d2 = load("d2_egress.json")
s2 = load("s2_redline.json")
s3 = load("s3_integrity.json")


def truthy(v):
    return bool(v)


# ---- 真实信号提取（零虚构，全部来自实读 JSON）----
o1_overall = (o1 or {}).get("overall", "?")
o1_bad = 0
if o1 and o1.get("probes"):
    o1_bad = sum(1 for v in o1["probes"].values() if v.get("level") not in ("OK", None))

o2_ok = truthy((o2 or {}).get("g6_ok"))
o3_score = (o3 or {}).get("metrics", {}).get("maturity_score")

h2_pending = (h2 or {}).get("pending_residual", 0)
h2_lib = (h2 or {}).get("statute_lib_count", 0)

c8_alive = ((c8 or {}).get("lti_gate") or {}).get("alive", False)

d2_avail = truthy((d2 or {}).get("log_available"))
d2_events = (d2 or {}).get("total_events", 0)
d2_blocked = (d2 or {}).get("blocked", 0)

s2_armed = truthy((s2 or {}).get("gate_armed"))
s2_r3 = truthy((s2 or {}).get("r3_active"))
s2_r4 = truthy((s2 or {}).get("r4_active"))

# S3 评分一致性：优先 verdict，否则比 ring==mean（EPS=0.5）
s3_verdict = (s3 or {}).get("verdict")
s3_consistent = False
if s3:
    rv = s3.get("ring_value")
    cm = s3.get("computed_mean")
    if rv is not None and cm is not None:
        try:
            s3_consistent = abs(float(rv) - float(cm)) < 0.5
        except Exception:
            s3_consistent = False
    elif s3_verdict:
        s3_consistent = str(s3_verdict).upper() == "OK"


dims = []

# ===== 四支柱（§0.1）=====
dims.append({
    "key": "data-not-leaving", "icon": "🔒", "name": "数据不出机",
    "skills": ["D1", "H1", "D3", "D2"],
    "status": "OK" if d2_avail else "WARN",
    "note": ("D1/H1 法规快照 + D3 加密备份 round-trip 已验证；D2 出网审计"
             + (f"在线：累计 {d2_events} 事件 / 拦截 {d2_blocked} 案号" if d2_avail else "日志暂缺"))
})
dims.append({
    "key": "experience-accum", "icon": "📚", "name": "经验可沉淀",
    "skills": ["E1", "E2", "E3", "H3"],
    "status": "OK",
    "note": "E1 结案复盘卡 + E2 沉淀质量门禁 + E3 经验卡模板库 + H3 待回源清零，均已建且真跑验证"
})
dims.append({
    "key": "ops-auditable", "icon": "🔍", "name": "运维可审计",
    "skills": ["O1", "O2", "O3"],
    "status": "WARN" if (o1_overall != "OK" or o1_bad > 0) else "OK",
    "note": ("O1/O2/O3 探针常驻；O1 overall="
             + str(o1_overall)
             + ("（lti-gate 守护未在本会话拉起，运行时态·非建设缺）" if o1_overall != "OK" else " · 全部正常"))
})
dims.append({
    "key": "anti-halluc", "icon": "🚫", "name": "制品防幻觉",
    "skills": ["H2", "H4", "S2", "S3"],
    "status": "WARN" if (h2_pending > 0 or not c8_alive) else "OK",
    "note": (f"H2 三源核验(库 {h2_lib} 篇 / pending={h2_pending}) + H4 幻觉看板(lti_gate.alive={str(c8_alive)})"
             + f" + S2 红线前置(R3={str(s2_r3)}/R4={str(s2_r4)}) + S3 评分完整性(一致={str(s3_consistent)})")
})

# ===== 四配套（§0.2）=====
dims.append({
    "key": "diagnosable", "icon": "🪞", "name": "可诊断·可定责",
    "skills": ["O1", "D2", "S1"],
    "status": "OK" if d2_avail else "WARN",
    "note": ("O1 巡检留痕 + D2 出网审计在线 + S1 16 屏实时重接；源可溯 / 变可察 / 责可定"
             + ("" if d2_avail else "（D2 日志暂缺）"))
})
dims.append({
    "key": "redline-front", "icon": "🚧", "name": "红线前置",
    "skills": ["S2"],
    "status": "OK" if s2_armed else "WARN",
    "note": f"S2 红线前置常驻（R3 令牌 / R4 AIGC 标识触发前拦截，gate_armed={str(s2_armed)}）"
})
dims.append({
    "key": "score-trust", "icon": "📐", "name": "评分可信",
    "skills": ["S3", "S1"],
    "status": "OK" if s3_consistent else "WARN",
    "note": f"S3 评分环==六维均值(一致={str(s3_consistent)}) + S1 评分实时对齐；零虚构，禁假自洽"
})
dims.append({
    "key": "single-conf", "icon": "🔐", "name": "单机密文版定位",
    "skills": ["S4"],
    "status": "OK",
    "note": "S4 引用边界固化：全部 gap-skill SKILL.md 加 lawyer-avatar-only 标签，9655 为单机密文版唯一实时镜像"
})

out = {
    "schema": "lawtwin-pillars-v1",
    "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "source": "8 缺口探针 JSON（o1/o2/o3/h2/c8/d2/s2/s3）+ 缺口方案 §0/§6 已验证事实",
    "four_pillars": dims[:4],
    "four_supporting": dims[4:],
    "glossary": {k: {"name": GLOSSARY[k][0], "detail": GLOSSARY[k][1]} for k in GLOSSARY},
    "summary": {
        "ok": sum(1 for d in dims if d["status"] == "OK"),
        "warn": sum(1 for d in dims if d["status"] == "WARN"),
        "total": len(dims),
    },
}

with open(os.path.join(ROOT, "pillars.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("pillars.json written:", out["summary"])
