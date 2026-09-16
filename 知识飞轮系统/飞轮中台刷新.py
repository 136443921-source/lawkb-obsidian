#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 飞轮中台刷新.py
# 扫描知识飞轮六层 + CaseDrop + WorkBuddy 自动化矩阵 + link_audit 断链率 + 摄入管道，
# 重算全部指标，写回 飞轮中台.html 的 const DATA = {...} 块。
# 手动运行：python3 飞轮中台刷新.py
import re, sys, json, subprocess, os
from pathlib import Path
from datetime import date, timedelta, datetime


def atomic_write(dst, content, encoding="utf-8"):
    """原子写：先写临时文件再 os.replace 原子替换，避免读者经 iframe/serve 加载时读到半截/空文件。"""
    dst = Path(dst)
    tmp = dst.with_suffix(dst.suffix + ".tmp_" + datetime.now().strftime("%Y%m%d%H%M%S%f"))
    tmp.write_text(content, encoding=encoding)
    os.replace(tmp, dst)


ROOT = Path("/Users/chenyouqiang/Documents/LawKB/知识飞轮系统")
# 真实文件落在 Desktop（门户/预览直接可读）；LawKB/知识飞轮系统/飞轮中台.html 为指向它的软链接
DASH = Path.home() / "Desktop" / "飞轮中台.html"
CASEDROP = Path("/Users/chenyouqiang/Documents/CaseDrop")
DB = Path.home() / ".workbuddy" / "workbuddy.db"
LINK_AUDIT = ROOT / "运维" / "link_audit.py"

CORE = ["每日知识摄入","飞轮","裁判规则","经验卡片","审判要件","分身系统驾驶舱",
        "LawKB法条一致性","IMA漏窗","知识图谱","索引更新","回灌","短反馈",
        "预判式跨案件","协同效果月报","决策思维月报","分身系统驾驶舱刷新","审判要件卡"]

today = date.today()
now = datetime.now()


def norm_ts(v):
    """统一 last_run_at / next_run_at：接受 epoch(int/ms) 或 ISO 字符串，返回 ('YYYY-MM-DD', datetime|None)。"""
    if v is None:
        return ("—", None)
    if isinstance(v, (int, float)):
        ev = float(v)
        if ev > 1e12:          # 毫秒时间戳
            ev = ev / 1000.0
        try:
            dt = datetime.fromtimestamp(ev)
        except Exception:
            return ("—", None)
        return (dt.strftime("%Y-%m-%d"), dt)
    s = str(v)
    ds = s[:10]
    try:
        dt = datetime.fromisoformat(s.replace("Z", ""))
    except Exception:
        dt = None
    return (ds, dt)


def count_md(d):
    if not d.exists():
        return 0
    return sum(1 for p in d.rglob("*.md") if p.is_file())


def inc_7d(d):
    if not d.exists():
        return 0
    cut = now - timedelta(days=7)
    n = 0
    for p in d.rglob("*.md"):
        try:
            if datetime.fromtimestamp(p.stat().st_mtime) >= cut:
                n += 1
        except Exception:
            pass
    return n


# ---------- 健康 KPI（复用健康仪表盘逻辑）----------
layers = {k: count_md(ROOT / k) for k in
          ["01-采集","02-提炼","03-连接","04-巩固","05-调用","06-沉淀"]}
six_total = sum(layers.values())

cards_dir = ROOT / "02-提炼/经验卡片"
card_files = list(cards_dir.rglob("*.md")) if cards_dir.exists() else []
experience_cards = len(card_files)
sim_cards = sum(1 for p in card_files
                if "is_simulation: true" in p.read_text(encoding="utf-8", errors="ignore"))
real_cards = experience_cards - sim_cards

rules_dir = ROOT / "06-沉淀/裁判规则库"
rule_files = sum(1 for p in rules_dir.rglob("*") if p.is_file()) if rules_dir.exists() else 0

trace_dir = ROOT / "02-提炼/经验卡片/思维轨迹"
trace_cards = (sum(1 for p in trace_dir.rglob("*.md") if p.name != "README.md")
               if trace_dir.exists() else 0)

processed = CASEDROP / "processed"
case_notes = (sum(1 for p in processed.iterdir()
                  if p.is_dir() and p.name != "README.md" and not p.name.startswith("."))
              if processed.exists() else 0)

# 六层近7日增量
layer_inc = [{"layer": k, "total": layers[k], "inc7d": inc_7d(ROOT / k)}
             for k in ["01-采集","02-提炼","03-连接","04-巩固","05-调用","06-沉淀"]]

# 卡片增长曲线
growth = []
try:
    html0 = DASH.read_text(encoding="utf-8")
    gm = re.search(r"cardGrowth:\s*\[([\s\S]*?)\]", html0)
    if gm:
        for it in re.finditer(r'\{date:"([\d-]+)",\s*cum:(\d+)\}', gm.group(1)):
            growth.append({"date": it.group(1), "cum": int(it.group(2))})
except Exception:
    pass
growth = [g for g in growth if g["date"] != today.isoformat()]
growth.append({"date": today.isoformat(), "cum": experience_cards})
growth.sort(key=lambda g: g["date"])

# ---------- 摄入管道 ----------
report_dir = ROOT / "02-提炼/每日知识摄入报告"
intake_days = 0
intake_7d = 0
latest = None
if report_dir.exists():
    for p in report_dir.glob("每日知识摄入报告-*.md"):
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", p.stem)
        if not m:
            continue
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except Exception:
            continue
        if latest is None or d > latest:
            latest = d
        if d >= today - timedelta(days=7):
            intake_days += 1
            intake_7d += len(re.findall(r"（20\d\d）\S{2,12}民[终初调]?\d+",
                             p.read_text(encoding="utf-8", errors="ignore")))
latest_str = latest.isoformat() if latest else "—"
age = (today - latest).days if latest else 999
if intake_days >= 5 and age <= 2:
    intake_level = "ok"
elif intake_days >= 3:
    intake_level = "watch"
else:
    intake_level = "warn"
if age >= 3:
    intake_level = "warn"

# ---------- 知识图谱快照（03-连接/知识图谱-数据-YYYY-MM.json）----------
kg = {"month": "—", "generated": "—", "total_notes": 0, "total_links": 0,
      "orphan": 0, "linked": 0, "density": 0.0, "dirs": [], "top": []}
try:
    cand = sorted(ROOT.glob("03-连接/知识图谱-数据-*.json"), key=lambda p: p.name)
    if cand:
        kgj = json.loads(cand[-1].read_text(encoding="utf-8"))
        kg["month"] = kgj.get("month", "—")
        kg["generated"] = kgj.get("generated", "—")
        kg["total_notes"] = kgj.get("total_notes", 0)
        kg["total_links"] = kgj.get("total_links", 0)
        kg["orphan"] = kgj.get("orphan_count", 0)
        kg["linked"] = kgj.get("linked_nodes", 0)
        kg["density"] = kgj.get("density", 0.0)
        dc = kgj.get("dir_count", {}) or {}
        kg["dirs"] = [{"name": k, "n": v} for k, v in sorted(dc.items(), key=lambda kv: -kv[1])][:10]
        kg["top"] = [{"title": t.get("title", ""), "refs": t.get("refs", 0)}
                     for t in (kgj.get("top10") or [])][:10]
except Exception as e:
    print("[warn] 知识图谱读取失败:", e)

# ---------- 裁判规则库资产（06-沉淀/裁判规则库）----------
rules = {"cards": experience_cards, "total": 0, "std": 0, "nonstd": 0,
         "compliance": 0.0, "sublibs": [], "nonstdList": []}
try:
    rules_dir = ROOT / "06-沉淀/裁判规则库"
    if rules_dir.exists():
        std_pat = re.compile(r'^R-[A-Z]{2,3}-\d+')
        total = 0
        for p in rules_dir.rglob('*'):
            if not p.is_file():
                continue
            total += 1
            rel = str(p.relative_to(rules_dir))
            if std_pat.match(p.stem):
                rules["std"] += 1
            else:
                if len(rules["nonstdList"]) < 80:
                    rules["nonstdList"].append(rel)
        rules["total"] = total
        rules["nonstd"] = total - rules["std"]
        rules["compliance"] = round(rules["std"] / total * 100, 1) if total else 0.0
        for sd in rules_dir.iterdir():
            if sd.is_dir():
                cnt = sum(1 for _ in sd.rglob('*') if _.is_file())
                rules["sublibs"].append({"name": sd.name, "n": cnt})
        rules["sublibs"].sort(key=lambda x: -x["n"])
except Exception as e:
    print("[warn] 裁判规则库读取失败:", e)

# ---------- 自动化矩阵 ----------
autos = []
try:
    import sqlite3
    con = sqlite3.connect(str(DB))
    cur = con.cursor()
    rows = cur.execute("select id,name,status,cwds,last_run_at,next_run_at from automations").fetchall()
    sel = []
    for id_, name, status, cwds, lra, nra in rows:
        cwds = cwds or ""
        if "知识飞轮系统" in cwds:
            sel.append((id_, name, status, lra, nra)); continue
        if any(k in name for k in CORE):
            sel.append((id_, name, status, lra, nra))
    for id_, name, status, lra, nra in sel:
        run = cur.execute(
            "select result_success,runs_json from automation_runs where automation_id=? order by updated_at desc limit 1",
            (id_,)).fetchone()
        last_ok = None
        run_ts = None   # 以 automation_runs 的真实运行时间为准（last_run_at 列常为空）
        if run:
            rj = run[1] or ""
            try:
                arr = json.loads(rj)
                if isinstance(arr, list) and arr and isinstance(arr[0], dict):
                    last_ok = bool(arr[0].get("success"))
                    fa = arr[0].get("finishedAt") or arr[0].get("startedAt")
                    if isinstance(fa, (int, float)):
                        ev = fa / 1000.0 if fa > 1e12 else float(fa)
                        try:
                            run_ts = datetime.fromtimestamp(ev)
                        except Exception:
                            run_ts = None
            except Exception:
                pass
            if last_ok is None:
                try:
                    last_ok = (run[0] == 1)
                except Exception:
                    last_ok = None
        # 状态判定：优先用真实运行时间，回退到 last_run_at 列
        if run_ts is None and lra is not None:
            _, run_ts = norm_ts(lra)
        lastRun = run_ts.strftime("%Y-%m-%d") if run_ts else (norm_ts(lra)[0] if lra else "—")
        nextRun, _ = norm_ts(nra)
        if status != "ACTIVE":
            state = "paused"
        elif run_ts is None:
            state = "none"
        elif last_ok is False:
            state = "fail"
        else:
            state = "ok" if (now - run_ts).days <= 7 else "warn"
        res_txt = {True: "成功", False: "失败", None: "无记录"}[last_ok]
        autos.append({
            "name": name,
            "state": state,
            "lastRun": lastRun,
            "result": res_txt,
            "nextRun": nextRun,
        })
    con.close()
except Exception as e:
    import traceback
    traceback.print_exc()
    print("[warn] 自动化矩阵读取失败:", e)

# ---------- 断链率（link_audit 实时）----------
link_rate = None
link_ok = True
try:
    out = subprocess.run([sys.executable, str(LINK_AUDIT), "--quiet"],
                         capture_output=True, text=True, timeout=120).stdout
    mm = re.search(r"断链率\s+([\d.]+)%", out)
    if mm:
        link_rate = float(mm.group(1))
        link_ok = link_rate <= 0.5
except Exception as e:
    print("[warn] link_audit 执行失败:", e)

# ---------- 写回 DATA 块 ----------
metrics = [
    {"name":"协同效果命中率", "value":"待采集", "desc":"分身问答埋点日志积累中，每月28日协同效果月报将出首值"},
    {"name":"经验卡片（真实/演练）", "value":"%d/%d" % (real_cards, experience_cards),
     "desc":"2026-08-28 实测：真实 %d 张 / 演练 %d 张" % (real_cards, sim_cards)},
    {"name":"裁判规则库规模", "value":"🌳成长中", "desc":"2026-09-05 实测：%d 文件 / 26 子库，编号体系 R-领域-序号，规范率详见「规则库资产」卡" % rule_files},
    {"name":"案件-卡片-规则三维索引", "value":"已建", "desc":"%d 归档案件 / %d 经验卡 / %d 规则文件 三维互联" % (case_notes, experience_cards, rule_files)},
    {"name":"思维轨迹卡", "value":"%d 张" % trace_cards, "desc":"2026-08-31 起：反复咨询→四维+三问沉淀"},
    {"name":"摄入5槽位·近7日采集", "value":"%d 例 / %d 天" % (intake_7d, intake_days), "desc":"D 阶段合同/慈善/医疗/工伤/交通靶向采集，v1.23 生效"},
]

def jq(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

lines = []
lines.append("const DATA = {")
lines.append('  updated: "%s",' % today.isoformat())
lines.append("  kpi: { experienceCards:%d, ruleFiles:%d, sixLayerTotal:%d, caseNotes:%d, automations:%d, ongoingCases:0 },"
             % (experience_cards, rule_files, six_total, case_notes, len(autos)))
lines.append("  cardGrowth: [")
for g in growth:
    lines.append('    {date:"%s", cum:%d},' % (g["date"], g["cum"]))
lines.append("  ],")
lines.append("  metrics: [")
for m in metrics:
    lines.append('    {name:"%s", value:"%s", desc:"%s"},' % (jq(m["name"]), jq(m["value"]), jq(m["desc"])))
lines.append("  ],")
lines.append("  layerInc: [")
for l in layer_inc:
    lines.append('    {layer:"%s", total:%d, inc7d:%d},' % (l["layer"], l["total"], l["inc7d"]))
lines.append("  ],")
lines.append("  kg: " + json.dumps(kg, ensure_ascii=False) + ",")
lines.append("  rules: " + json.dumps(rules, ensure_ascii=False) + ",")
lines.append("  autos: [")
for a in autos:
    lines.append('    {name:"%s", state:"%s", lastRun:"%s", result:"%s", nextRun:"%s"},'
                 % (jq(a["name"]), a["state"], a["lastRun"], a["result"], a["nextRun"]))
lines.append("  ],")
lines.append('  intake: { days7:%d, cases7:%d, level:"%s", latest:"%s" },'
             % (intake_days, intake_7d, intake_level, latest_str))
lines.append("  alerts: {")
lines.append("    linkRate:%s, linkOk:%s," % ("%.3f" % link_rate if link_rate is not None else "null",
                                              "true" if link_ok else "false"))
lines.append('    lti:"在线 · 缓存 100 条高频法条 · 三轮终评检出 80.6% / 误报 0%",')
lines.append("    ltiCache:100")
lines.append("  }")
lines.append("};")
new_block = "\n".join(lines)

html = DASH.read_text(encoding="utf-8")
m = re.search(r"const DATA = \{[\s\S]*?\n\s*\};", html)
if not m:
    raise SystemExit("未找到 DATA 块")
html = html[: m.start()] + new_block + html[m.end():]
atomic_write(DASH, html, "utf-8")

print("[飞轮中台] %s 经验卡=%d(真实%d) 规则库=%d 六层=%d 自动化=%d 断链率=%s 摄入=%d例/%d天(%s)"
      % (today.isoformat(), experience_cards, real_cards, rule_files, six_total, len(autos),
         ("%.3f%%" % link_rate if link_rate is not None else "未知"), intake_7d, intake_days, intake_level))
