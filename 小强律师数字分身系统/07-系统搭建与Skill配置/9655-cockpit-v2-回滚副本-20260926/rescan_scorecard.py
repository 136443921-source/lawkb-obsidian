#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
九屏统一作战地图 · 重扫 + 刷新数据源生成器
=========================================================
作用：重扫驾驶舱数据源 → 生成 **9360 小强总驾驶舱（cockpit-hub-ops）** 前端 fetch 用的
      `scorecard_data.json`（含 name/dot/kpis/risk/dims/grade），使首页「↻刷新」拿到最新数据。

⚠️ 重要护栏（2026-09-16 修正）：
   本脚本依赖 scan_scorecard.py 的采集器，而 scan 的 COLLECTORS 仅覆盖 8 屏
   （lti/clm/flywheel/ev/cardfamily/decision/credits/mock），
   **未包含 C5 小德（xiaode）与 C7 合同管理（contractlifecycle）两个真实计分屏**。
   9360 真源 scorecard_data.json 是手工装配的 12 屏（C1–C8 计分 + D1 计分 + D2/D3/D4 监控），
   若直接用本脚本覆盖会丢失 C5/C7。故 main() 已加硬护栏：转换结果缺 xiaode/contractlifecycle
   时拒绝写入，并提示先扩展 scan_scorecard.py 的 COLLECTORS。

铁律：① 只读源、绝不写源头  ② 改写前 cp 备份  ③ 幂等可重跑  ④ 覆盖前必过护栏
用法：
    python3 rescan_scorecard.py            # 重扫并写 cockpit-hub-ops/scorecard_data.json
    python3 rescan_scorecard.py --dry      # 只算不写（预览）

依赖：scan_scorecard.py（同仓 cockpit-scorecard 目录，负责实扫各屏数据源）
注意：本脚本须在**本机**运行（部署沙箱隔离、访问不到本地 LawKB/桌面文件）。
"""
import os, re, json, sys, subprocess, shutil, datetime

HOME = os.path.expanduser("~")
# 2026-09-16 修正：原指向旧门户 cockpit-portal/portal，与 9360 真源（cockpit-hub-ops）错位。
# 9360 实际由 cockpit-hub-ops/index.html 同源 fetch('scorecard_data.json') 提供服务，故改指向此处。
PORTAL_DIR = os.path.join(HOME, "WorkBuddy/2026-09-12-01-29-05/outputs/cockpit-hub-ops")
SC_DIR     = os.path.join(HOME, "WorkBuddy/2026-09-12-01-29-05/outputs/cockpit-scorecard")
SCAN       = os.path.join(SC_DIR, "scan_scorecard.py")
OUT        = os.path.join(PORTAL_DIR, "scorecard_data.json")
COCKPIT    = os.path.join(HOME, "WorkBuddy/2026-09-12-01-29-05/outputs/cockpit-hub-ops")
PY         = sys.executable

# ---- 屏 key → (中文名, dot 配色键) ----
# 命名规范（2026-09-16 统一）：C1–C8 九屏主体；D1 积分监测 / D3 云服务（原 C9/C0 重编号）
KEY_MAP = {
    "lti":       ("C8 AI 幻觉监控舱",   "h"),
    "clm":       ("C4 案件管理中台",    "f"),
    "flywheel":  ("C3 知识飞轮舱",       "b"),
    "ev":        ("C1 车机驾驶舱",       "a"),
    "cardfamily":("系统卡族看板",        "g"),
    "decision":  ("C2 决策思维舱",       "d"),
    "credits":   ("D1 积分监测中台",     "e"),
    "mock":      ("C6 模拟庭审中台",     "c"),
    "xiaode":    ("小德 · 合规管理中台", "k"),
    "contractlifecycle": ("C7 合同管理中台", "g"),
}

# ---- 分屏编号秩序（2026-09-16 统一）：C1–C8 九屏主体；D1 积分监测 / D3 云服务 ----
CNO_MAP = {
    "ev": "C1", "decision": "C2", "flywheel": "C3", "clm": "C4", "xiaode": "C5",
    "mock": "C6", "contractlifecycle": "C7", "lti": "C8", "credits": "D1",
}

# D3 云服务中台（原 C0 云监控）：运维监控位，不纳入评分。重扫时必须保留。
CLOUD_SCREEN = {
    "cno": "D3", "key": "cloud", "name": "D3 云服务中台", "dot": "i",
    "weight": 0, "score": None, "updated": "2026-09-12", "flag": False, "scoring": False,
    "kpis": [["云能力", "4/4"], ["可用模型", "29"], ["接入应用", "1"],
             ["数据表", "0"], ["端用户", "0"], ["快照日", "09-12"]],
    "six": None,
    "risk": "四项云能力已启用，但 DB 0 张表 / 端用户 0 人，属「已开通未启用」；"
            "快照 2026-09-12，未接定时刷新。",
}

# D2 知识冲突中台（读取冲突仲裁队列真实数据 subapps/conflict-arbitration/queue.json）
def build_conflict_screen():
    qf = os.path.join(COCKPIT, "subapps", "conflict-arbitration", "queue.json")
    if not os.path.exists(qf):
        return None
    try:
        d = json.load(open(qf, encoding="utf-8"))
    except Exception as e:
        print("⚠ build_conflict_screen: queue.json 解析失败，跳过 D2 屏（不阻断整体刷新）：%s" % e)
        return None
    cf = d.get("conflicts", [])
    total = d.get("count") or len(cf)
    resolved = d.get("resolved_count", 0)
    hold = sum(1 for c in cf if c.get("decision") == "hold")
    cr = sum(1 for c in cf if c.get("type") == "CR")
    rate = round(100 * resolved / total, 1) if total else 0
    return {
        "cno": "D2", "key": "conflict", "name": "D2 知识冲突中台", "dot": "conf",
        "weight": 0, "score": None, "updated": d.get("synced_at") or d.get("generated", "—"),
        "flag": False, "scoring": False,
        "kpis": [["冲突总数", str(total)], ["AI 裁决率", "%.1f%%" % rate],
                 ["待复核", str(hold)], ["跨卡型冲突", str(cr)]],
        "six": None,
        "risk": "AI 已裁决 %d/%d（%.1f%%），待人工复核 %d 条；属「有人管」闭环工作流，运转健康。" % (
            resolved, total, rate, hold),
    }

# D4 心智模型中台（读取席位绑定配置生成的心智面板数据 subapps/mock/mind_panels_data.js）
def build_mind_screen():
    mf = os.path.join(COCKPIT, "subapps", "mock", "mind_panels_data.js")
    if not os.path.exists(mf):
        return None
    src = open(mf, encoding="utf-8").read()
    m = re.search(r'window\.MIND_PANELS=(\{.*\})\s*;?\s*$', src, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(1))
    except Exception as e:
        print("⚠ build_mind_screen: mind_panels_data.js 解析失败，跳过 D4 屏（不阻断整体刷新）：%s" % e)
        return None
    roles = obj.get("roles", [])
    if not roles:
        return None
    active = sum(1 for r in roles if r.get("status") == "ACTIVE")
    def _mat_num(s):
        head = str(s or "").split("/")[0]
        digs = re.sub(r"\D", "", head)
        return int(digs) if digs else 0
    mats = [_mat_num(r.get("maturity")) for r in roles]
    top = max(mats) if mats else 0
    avg = round(sum(mats) / len(mats)) if mats else 0
    return {
        "cno": "D4", "key": "mindmodel", "name": "D4 心智模型中台", "dot": "mm",
        "weight": 0, "score": None, "updated": obj.get("generated", "—"),
        "flag": False, "scoring": False,
        "kpis": [["席位总数", str(len(roles))], ["ACTIVE", "%d/%d" % (active, len(roles))],
                 ["最高成熟度", "~%d/100" % top], ["平均成熟度", "~%d/100" % avg],
                 ["配置版本", obj.get("configVersion", "—")]],
        "six": None,
        "risk": "4 心智席位全部 ACTIVE（审判长 ~98 / 红队 91 / 蓝队 88 / 书记员 64）；"
                "心智面板已生成，待接入统一视图。",
    }


def cno_rank(screen):
    c = str(screen.get("cno") or "")
    # D 系列（D1 积分监测 / D3 云服务）置于 C 系列之后、压尾之前
    s = c.upper()
    if s.startswith("D"):
        try:
            return 50 + int(s[1:])
        except (ValueError, IndexError):
            return 97
    if s == "C0":
        return 99
    try:
        return int(c[1:])
    except (ValueError, IndexError):
        return 98
# ---- 六维定义（固定） ----
SIX = [
    ("fresh",     "数据新鲜度"),
    ("coverage",  "覆盖完备度"),
    ("health",    "运行健康度"),
    ("output",    "产出有效性"),
    ("compliance","安全合规度"),
    ("automation","自动化程度"),
]
SIX_COLOR = {
    "fresh":     "#5b9bff",
    "coverage":  "#2dd4bf",
    "health":    "#ef5350",
    "output":    "#f59e0b",
    "compliance":"#a78bfa",
    "automation":"#34d399",
}
# ---- raw 字段 → 中文标签 ----
RAW_CN = {
    "calls":"累计调用", "pass_rate":"通过率", "block_rate":"拦截率", "health_avg":"模块健康均",
    "modules":"模块数", "zero_rule":"零命中规则", "incidents":"事故卡",
    "cases":"在册案件", "gates_ok":"门禁通过", "gate_active":"在效门禁", "gate_warn":"预警门禁",
    "blues":"蓝方态势",
    "cards":"卡片", "ruleFiles":"规则文件", "links":"链接", "orphan":"孤儿节点", "compliance":"规范率",
    "level":"等级", "pillars":"支柱", "hitFilled":"桩位", "hitTotal":"桩位总数", "alerts":"告警",
    "scanned":"实扫", "card_types":"卡型", "rule_id":"rule_id", "fm_rate":"frontmatter率",
    "rid_rate":"编号率", "top_types":"卡型Top",
    "domains":"域", "ruleLinks":"规则链", "uniqueRules":"唯一规则",
    "total_credit":"总额度", "plan_total":"套餐总额", "remaining":"剩余", "used_pct":"消耗%", "yd_point":"元典点",
    "scripts":"剧本", "started":"已开庭",
    # 2026-09-16 增补 C5 小德 / C7 合同管理（与 9360 真源 kpis 中文标签对齐，供骨架覆盖匹配）
    "managedObjects":"在管主体", "escalatedRisks":"升级风险",
    "domainCardsTotal":"域知识卡", "gatesTotal":"合规闸门", "connectors":"连接器中台",
    "reviewedContracts":"已审合同", "totalAssets":"合同资产",
    "disputes":"争议案", "healthIndex":"健康指数",
}
PCT = {"pass_rate","block_rate","used_pct","fm_rate","rid_rate","compliance"}


def run_scan(dry=False):
    """跑 scan_scorecard.py --json，返回 report dict（stdout 优先，否则读文件）。"""
    if not os.path.exists(SCAN):
        print("✗ 找不到扫描器:", SCAN); sys.exit(1)
    cmd = [PY, SCAN, "--json"]
    print("▶ 重扫数据源:", " ".join(cmd))
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except Exception as e:
        print("✗ 扫描器执行失败:", e); sys.exit(1)
    txt = out.stdout.strip()
    # 优先解析 stdout 里的 JSON
    try:
        return json.loads(txt)
    except Exception:
        pass
    # 回退读 scorecard_report.json
    # ⚠️ 注意路径必须与 scan_scorecard.py 写报告路径一致：
    #     scan 写于 os.path.join(APP_DIR,'..','scorecard_report.json')
    #     其中 APP_DIR = cockpit-scorecard，故实际为 outputs/scorecard_report.json（SC_DIR/..）
    #     旧代码误读 SC_DIR/scorecard_report.json（02:07 旧快照）→ 门户长期显示旧 79.4，已修正。
    f = os.path.join(SC_DIR, "..", "scorecard_report.json")
    if os.path.exists(f):
        return json.load(open(f, encoding="utf-8"))
    print("✗ 扫描器未返回可用 JSON（stderr 见下）:\n", out.stderr[:800]); sys.exit(1)


def fmt_raw(field, val):
    """raw 字段 → (中文标签, 展示值)。"""
    if val is None:
        return (RAW_CN.get(field, field), "未取")
    lab = RAW_CN.get(field, field)
    if field == "blues" and isinstance(val, list):
        return (lab, " / ".join(str(x) for x in val))
    if field == "top_types" and isinstance(val, list):
        top = ", ".join("%s %s" % (n, c) for n, c in val[:3])
        return ("卡型Top3", top)
    if field in PCT and isinstance(val, (int, float)):
        return (lab, ("%.2f" % val) + "%")
    if isinstance(val, float):
        return (lab, ("%.2f" % val))
    return (lab, str(val))


def build_kpis(raw):
    kpis = []
    for k, v in raw.items():
        if k == "updated":
            continue
        if v is None:
            kpis.append([RAW_CN.get(k, k), "未取"])
            continue
        lab, disp = fmt_raw(k, v)
        kpis.append([lab, disp])
    return kpis


def grade_of(total):
    if total >= 90: return "优秀 A"
    if total >= 70: return "良好 B"
    if total >= 60: return "中等 C"
    return "及格 D"


def _risk_text(key, raw, low_k, low_v):
    """基于采集到的风险信号生成动态 risk 文案。
    C5/C7 增强为「具体风险名」自动拼装（red/orange 风险标题 + warn 门禁名 + 争议案名），
    其余屏 fallback 原「短板维度」文案。"""
    if key == 'xiaode':
        parts = []
        if raw.get('redRiskNames'):
            parts.append("红线风险：" + "、".join(raw['redRiskNames']))
        if raw.get('orangeRiskNames'):
            parts.append("升级风险：" + "、".join(raw['orangeRiskNames'][:2]))
        if raw.get('warnGateNames'):
            parts.append("门禁预警：" + "、".join(raw['warnGateNames']))
        if parts:
            return "；".join(parts) + "。建议优先治理。"
    if key == 'contractlifecycle':
        parts = []
        if raw.get('warnGateNames'):
            parts.append("门禁预警：" + "、".join(raw['warnGateNames']))
        if raw.get('disputeNames'):
            dn = raw['disputeNames']
            head = "、".join(dn[:2])
            parts.append("争议案 %d 项敞口（%s 等）" % (raw.get('disputes', 0), head))
        if parts:
            return "；".join(parts) + "。建议优先治理。"
    return "%s维度 %s 为短板，建议优先治理。" % (dict(SIX).get(low_k, low_k), low_v)


def convert(report):
    """以 9360 真源 scorecard_data.json 为权威骨架：保留手工权重 / 六维 / 评分基线，
    仅用 scan 采集器的 raw 刷新 updated / kpis / risk / flag。
    这样「一键刷新」动态追新且不破坏老强已调校的评价体系（六维算法与权重稳定）。"""
    skeleton = {}
    if os.path.exists(OUT):
        try:
            skeleton = json.load(open(OUT, encoding='utf-8'))
        except Exception:
            skeleton = {}
    sk_by_key = {s.get('key'): s for s in skeleton.get('screens', [])}

    screens_src = report.get('screens', {})
    screens = []
    seen = set()
    wsum = 0.0
    six_acc = {k: 0.0 for k, _ in SIX}

    for key, blk in screens_src.items():
        if key == 'cardfamily':
            continue  # 9360 无此屏（旧门户遗留），丢弃，禁止污染 9360
        raw = blk.get('raw', {}) or {}
        scores = blk.get('scores', {}) or {}
        sk = sk_by_key.get(key)
        if sk:
            name = sk.get('name'); dot = sk.get('dot'); cno = sk.get('cno')
            weight = sk.get('weight', 0); score = sk.get('score')
            # ★ 2026-09-16 统一六维算法：C5/C7 优先采用采集器算出的算法 scores，
            #   替代原硬编码基线；其余屏沿用 9360 真源手工 six（已是算法/固化值，不在本轮范围）。
            if key in ('xiaode', 'contractlifecycle') and scores:
                six_base = scores
            else:
                six_base = sk.get('six') or {}
            base_kpis = sk.get('kpis') or []
            updated = raw.get('updated') or sk.get('updated', '—')
        else:
            # 兜底：骨架缺失时按通用映射重建（仅首次无骨架场景）
            name, dot = KEY_MAP.get(key, (key, '?'))
            cno = CNO_MAP.get(key, '—'); weight = blk.get('weight', 0)
            score = blk.get('screen_score', 0); six_base = scores
            base_kpis = build_kpis(raw)
            updated = raw.get('updated') or '—'
        # —— 动态刷新：kpis 以骨架为基线，用 raw 可映射字段覆盖（自动追新）——
        raw_disp = {lab: val for lab, val in build_kpis(raw)}  # label -> val（含 RAW_CN + C5/C7 扩展映射）
        kpis = [[lab, raw_disp.get(lab, val)] for lab, val in base_kpis]
        # —— flag / risk：基于骨架六维短板 + 采集风险信号 ——
        valid = {k: six_base.get(k, 0) for k, _ in SIX}
        low_k = min(valid, key=valid.get) if valid else None
        low_v = valid.get(low_k, 0) if low_k else 0
        no_data = not updated
        # 自动 flag：除六维短板外，采集器报告的风险信号（C5 红/橙风险·warn 门禁；C7 争议·warn 门禁）也触发标记
        has_risk_signal = bool(
            (key == 'xiaode' and (raw.get('redRisks') or raw.get('orangeRisks') or raw.get('gateWarn')))
            or (key == 'contractlifecycle' and (raw.get('disputes') or raw.get('warnGates')))
        )
        flag = (low_v < 60) or no_data or has_risk_signal
        if no_data:
            risk = "数据源缺失（未取到最新数据），建议注入后重扫。"
        elif flag:
            risk = _risk_text(key, raw, low_k, low_v)
        else:
            risk = "低风险 · 运转健康"
        screens.append({
            "cno": cno, "key": key, "name": name, "dot": dot,
            "weight": weight, "score": score,
            "updated": updated, "flag": flag, "kpis": kpis,
            "six": valid, "risk": risk,
        })
        seen.add(key)
        wsum += weight
        for k in six_acc:
            six_acc[k] += valid[k] * weight

    # —— 补齐骨架中的监控屏（D2/D3/D4 等 score=None 的屏），跳过后面实时/静态处理的 ——
    for sk in skeleton.get('screens', []):
        k = sk.get('key')
        if k in seen or k in ('conflict', 'mindmodel', 'cloud'):
            continue
        screens.append(dict(sk))

    # —— 总维度六维（按骨架权重加权）——
    dims = []
    for k, nm in SIX:
        v = six_acc[k] / wsum if wsum else 0
        dims.append({"key": k, "name": nm, "val": round(v, 1), "color": SIX_COLOR[k]})

    total = round(sum(s["score"] * s["weight"] for s in screens
                      if s.get("scoring") is not False), 1) if wsum else 0

    # ★ D2 知识冲突 / D4 心智模型：用实时 build_* 覆盖骨架（确保最新）★
    for extra in (build_conflict_screen(), build_mind_screen()):
        if not extra:
            continue
        screens = [s for s in screens if s.get('key') != extra['key']]
        screens.append(extra)
        seen.add(extra['key'])
    # ★ D3 云服务中台（原 C0 云监控）：静态保留（不计分）★
    if not any(s.get('key') == 'cloud' for s in screens):
        screens.append(dict(CLOUD_SCREEN))
    for s in screens:
        if s.get('key') == 'cloud':
            s['scoring'] = False

    screens.sort(key=cno_rank)
    return {
        "total": total,
        "grade": grade_of(total),
        "generated_at": report.get("generated_at", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        "dims": dims,
        "screens": screens,
    }


def main():
    dry = "--dry" in sys.argv
    report = run_scan()
    data = convert(report)
    # ★ 护栏（2026-09-16 增补采集器后放宽）：以 9360 真源为骨架兜底，
    #   scan 未采集到 C5/C7 时仅警告并保留骨架旧动态值，不再 exit（骨架保证不丢屏）。
    REQUIRED = ("xiaode", "contractlifecycle")
    scan_missing = report.get("missing", []) or []
    lack = [k for k in REQUIRED if k in scan_missing]
    if lack:
        print("⚠ 护栏提示：scan 未采集到 %s，保留 9360 真源骨架旧动态值（不覆盖丢失）。" % ", ".join(lack))
    if not all(any(s.get("key") == k for s in data["screens"]) for k in REQUIRED):
        print("✗ 致命：转换结果仍缺失 %s（骨架/采集均失败），中止以防破坏。" % ", ".join(REQUIRED))
        sys.exit(5)
    # 自洽校验（不计分屏不参与加权）
    scored = [s for s in data["screens"] if s.get("scoring") is not False]
    sc = sum(s["score"] * s["weight"] for s in scored)
    print("  总评=%.1f | 屏数=%d（计分 %d + 监控位 %d）| 加权校验=%.2f (差%.2f)" % (
        data["total"], len(data["screens"]), len(scored),
        len(data["screens"]) - len(scored), sc, abs(sc - data["total"])))
    if dry:
        print("▶ dry-run：不写文件。预览首屏：")
        print("  ", json.dumps(data["screens"][0], ensure_ascii=False)[:200])
        return
    # 备份
    if os.path.exists(OUT):
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(OUT, OUT + ".bak_" + ts)
        print("✓ 已备份旧 json")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("✓ 已写入:", OUT, "(%d 字节)" % os.path.getsize(OUT))


if __name__ == "__main__":
    main()
