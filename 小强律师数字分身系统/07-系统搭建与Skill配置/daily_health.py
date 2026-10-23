#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""系统健康日报（唯一一条 · 只报 6 个数）

═══════════ 设计铁律：指标不超 6 个 ═══════════
2026-10-22 复盘结论：仪表盘不是指标越多越好，是**少到每天都真看**才有用。
故本日报**硬编码只报 6 项**，新增指标须先删一个（常量 MAX_METRICS 校验）。

    ① 技能数            —— 资产规模（对比昨日增量）
    ② 自动化 ACTIVE 数   —— 调度负载（对比昨日增量）
    ③ 埋点 24h 新增      —— 三处埋点合计（断链第一信号）
    ④ 卡片挂载率         —— 知识"挂了但没被调用"的度量
    ⑤ 门禁拦截数(24h)    —— 防幻觉闸门是否在工作
    ⑥ 自动化失败数(24h)  —— 真正跑挂了几个

═══════════ 数据源（全部实地可算，零编造）═══════════
① ls ~/.workbuddy/skills/*/SKILL.md
②③ ~/.workbuddy/workbuddy.db → automations 表（**只读模式打开**）
④ 三处 metrics/*.jsonl 的 24h 新增
⑤ 知识飞轮卡片 × 消费方语料 引用扫描
⑥ grill_hook_violations.jsonl

⚠️ 数据库一律 `file:...?mode=ro` 只读打开，物理上不能写。改自动化只走 automation_update。

═══════════ 埋点死亡告警 ═══════════
任一埋点连续 3 天 0 新增 → 该项标 🔴 并输出「埋点可能已断」+ 上游发射点定位。
（与 metrics_watchdog.py 同源逻辑，直接复用其 scan_one，不重写）

═══════════ 用法 ═══════════
    python3 daily_health.py              # 人读日报
    python3 daily_health.py --json       # 机器读
    python3 daily_health.py --no-mount   # 跳过挂载率（跳过大扫描，秒出）
    python3 daily_health.py --quiet      # 只在有 🔴 时输出（供 automation 判断）
退出码：0=全绿/黄；1=有 🔴
"""
import os
import re
import sys
import json
import time
import glob
import sqlite3
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from metrics_watchdog import scan_one, TARGETS as WATCH_TARGETS  # 复用，不重写

HOME = os.path.expanduser("~")
SKILLS = os.path.join(HOME, ".workbuddy", "skills")
DB = os.path.join(HOME, ".workbuddy", "workbuddy.db")
METRICS = os.path.join(HOME, ".workbuddy", "metrics")
LAWKB = os.path.join(HOME, "Documents", "LawKB")
FLYWHEEL = os.path.join(LAWKB, "知识飞轮系统")
HUB = os.path.join(LAWKB, "_AI-Memory-Hub")
STATE = os.path.join(HOME, "Documents", "LawKB", "小强律师数字分身系统",
                     "00-系统总览与运维中心", "_健康日报_历史.jsonl")

MAX_METRICS = 6  # 硬上限，超了必须删一个


# ────────────────────── ① 技能数 ──────────────────────
def metric_skills():
    """技能数：必须报「启用数」，不能报「目录数」。

    2026-10-23 纠偏：早期版本只数 `<skills>/*/SKILL.md` 得 192，把这件事
    报成「192 个技能、元数据常驻 2.7 万 tokens」。实测 `~/.workbuddy/settings.json`
    的 `skillOverrides` 才是真正的开关——221 条里 161 条 off，**真正注入的只有
    54~60 个**，元数据合计 1.0 万字符（≈5 千 tokens），不到原估的 1/5。
    报 192 会让人误以为系统臃肿到需要削，实际上分层早就做完了。
    """
    import json as _json
    import re as _re

    dirs = 0
    enabled = 0
    meta_chars = 0
    try:
        overrides = _json.load(
            open(os.path.join(HOME, ".workbuddy", "settings.json"), encoding="utf-8")
        ).get("skillOverrides", {})
    except Exception:
        overrides = {}
    for d in sorted(os.listdir(SKILLS)):
        f = os.path.join(SKILLS, d, "SKILL.md")
        if not os.path.isdir(os.path.join(SKILLS, d)) or not os.path.exists(f):
            continue
        dirs += 1
        try:
            txt = open(f, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        m = _re.match(r"^---\s*\n(.*?)\n---", txt, _re.S)
        fm = m.group(1) if m else ""
        nm = _re.search(r"^name:\s*(.+)$", fm, _re.M)
        ds = _re.search(r"^description:\s*(.+)$", fm, _re.M)
        nm = nm.group(1).strip().strip("\"'") if nm else d
        ds = ds.group(1).strip() if ds else ""
        state = overrides.get(d) or overrides.get(nm)
        if state in ("on", "user-invocable-only"):
            enabled += 1
            meta_chars += len(nm) + len(ds)

    pct = (enabled / dirs * 100) if dirs else 0
    return {
        "key": "skills", "label": "技能启用数", "value": enabled, "unit": "个",
        "level": "info",
        "hint": "目录 %d 个，未启用 %d 个（%.0f%% 已启用）；"
                "启用集元数据 %d 字符 ≈ %.0f tokens"
                % (dirs, dirs - enabled, pct, meta_chars, meta_chars / 2),
        "extra": {"dirs": dirs, "enabled": enabled, "meta_chars": meta_chars},
    }


# ────────────────────── ②⑥ 自动化（只读 DB）──────────────────────
def _db():
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


def metric_automations():
    try:
        con = _db()
        cur = con.cursor()
        cur.execute("SELECT status, COUNT(*) FROM automations WHERE deleted_at IS NULL GROUP BY status")
        dist = dict(cur.fetchall())
        con.close()
        active = dist.get("ACTIVE", 0)
        paused = dist.get("PAUSED", 0)
        level = "warn" if active > 80 else "ok"
        return {
            "key": "automations_active", "label": "自动化 ACTIVE", "value": active, "unit": "条",
            "level": level, "hint": f"暂停 {paused} 条，在跑 {active} 条",
            "extra": {"paused": paused},
        }
    except Exception as e:
        return {"key": "automations_active", "label": "自动化 ACTIVE", "value": None,
                "unit": "条", "level": "unknown", "hint": f"读库失败：{e}"}


def metric_automation_failures(hours=24):
    try:
        con = _db()
        cur = con.cursor()
        since = int((time.time() - hours * 3600) * 1000)
        cur.execute("SELECT COUNT(*) FROM automation_runs WHERE created_at >= ?", (since,))
        total = cur.fetchone()[0]

        # 区分「真失败」与「重启/中断」——后者是环境事件，不是自动化本身坏了。
        # 2026-10-22 实测：24h 内 3 条 result_success=0，其中 2 条是 restart_interrupted / interrupted。
        # 若不加区分，日报会把"机器重启"误报成"两个自动化坏了"，属典型指标失真。
        INTERRUPT_CODES = ("restart_interrupted", "interrupted", "cancelled", "aborted")
        ph = ",".join("?" * len(INTERRUPT_CODES))
        cur.execute(f"""SELECT COUNT(*) FROM automation_runs
                        WHERE created_at >= ? AND result_success = 0
                          AND (reason_code IS NULL OR reason_code NOT IN ({ph}))""",
                    (since, *INTERRUPT_CODES))
        real_fail = cur.fetchone()[0]
        cur.execute("""SELECT COUNT(*) FROM automation_runs
                       WHERE created_at >= ? AND result_success = 0
                         AND reason_code IN ('restart_interrupted','interrupted')""", (since,))
        interrupted = cur.fetchone()[0]

        cur.execute(f"""SELECT COALESCE(a.name,'(未知)'), COALESCE(r.failure_code,'(无码)'),
                               COALESCE(r.reason_code,'(无因)')
                        FROM automation_runs r LEFT JOIN automations a ON a.id = r.automation_id
                        WHERE r.created_at >= ? AND r.result_success = 0
                          AND (r.reason_code IS NULL OR r.reason_code NOT IN ({ph}))
                        ORDER BY r.created_at DESC LIMIT 3""", (since, *INTERRUPT_CODES))
        detail = [f"{n}／{fc}" for n, fc, rc in cur.fetchall()]
        con.close()

        level = "ok" if real_fail == 0 else ("warn" if real_fail <= 2 else "bad")
        hint = f"近{hours}h 运行 {total} 次"
        if interrupted:
            hint += f"，其中 {interrupted} 次为重启/中断（不计真失败）"
        if detail:
            hint += f"；真失败：{'、'.join(detail)}"
        return {"key": "automation_failures", "label": f"自动化失败({hours}h)", "value": real_fail,
                "unit": "次", "level": level, "hint": hint,
                "extra": {"total_runs": total, "interrupted": interrupted, "detail": detail}}
    except Exception as e:
        return {"key": "automation_failures", "label": "自动化失败(24h)", "value": None,
                "unit": "次", "level": "unknown", "hint": f"读库失败：{e}"}


# ────────────────────── ③ 埋点 24h 新增 ──────────────────────
def metric_metrics24h():
    rows = []
    total = 0
    dead = []
    for t in WATCH_TARGETS:
        r = scan_one(t, days=1)
        rows.append({"key": r["key"], "recent": r["recent_count"], "status": r["status"],
                     "silent_days": r["silent_days"]})
        total += r["recent_count"]
        # 死亡告警：连续 3 天 0 新增
        r3 = scan_one(t, days=3)
        if r3["recent_count"] == 0:
            dead.append({"key": r["key"], "silent_days": r["silent_days"],
                         "emitter": r["emitter"], "fix": r["fix_hint"]})

    if dead:
        # 分级：连续 3 天 0 新增即报「可能已断」（老强 2026-10-23 指令）；
        # 静默 ≥30 天升级为 🔴 判定已断。区分是为了不把低频埋点（如 grill）天天报红。
        hard = [d for d in dead if d["silent_days"] >= 30]
        level = "bad" if hard else "warn"
        mark = "🔴 判定已断" if hard else "🟡 可能已断"
        hint = mark + "：" + "、".join(
            f"{d['key']}（静默{d['silent_days']}天）" for d in dead)
    elif total == 0:
        level = "warn"
        hint = "24h 三处埋点全 0 新增"
    else:
        level = "ok"
        hint = " / ".join(f"{r['key'][:8]}={r['recent']}" for r in rows)

    return {"key": "metrics_24h", "label": "埋点 24h 新增", "value": total, "unit": "条",
            "level": level, "hint": hint, "extra": {"detail": rows, "dead": dead}}


# ────────────────────── ④ 卡片挂载率 ──────────────────────
CARD_GLOBS = [
    os.path.join(FLYWHEEL, "06-沉淀", "**", "*.md"),
    os.path.join(FLYWHEEL, "02-提炼", "**", "*.md"),  # 补：审判要件卡体量主要在 02-提炼（447 张）
]

# ⚠️ 口径必须对齐 2026-10-06 普查（结论 40.6% = 998/2456），否则数字会虚高。
# 第一版实现把「整个中枢 432 个 md」都算消费方，连卡族总索引、每日日志、调用记录一起算进去，
# 得出 93.9%（2425/2583）——**索引里提到 ≠ 被挂载到技能/心智模型**，属典型指标失真。
# 现按普查口径收敛：只认「智能体 SKILL.md + 心智资产 + 训练备忘录 + 席位/中台人格」。
CONSUMER_GLOBS = [
    os.path.join(SKILLS, "*", "SKILL.md"),
    os.path.join(HUB, "08-心智资产", "**", "*.md"),
    os.path.join(HUB, "05-调用", "**", "*备忘录*.md"),
]
CONSUMER_EXTRA_DIRS = [
    os.path.join(LAWKB, "小强律师数字分身系统", "09-席位与心智资产"),
    os.path.join(LAWKB, "小强律师数字分身系统", "10-律所数字分身中台"),
]
# 明显不属于「挂载声明」的噪声文件（索引/日志/台账/清单/备份）
CONSUMER_EXCLUDE = ("索引", "总索引", "日志", "台账", "清单", "备份", "归档", "报告")

RULE_ID_RE = re.compile(r"R-[A-Z]{2,4}-\d{2,4}")
MOUNT_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_挂载率缓存.json")
MOUNT_TTL_DAYS = 7  # 挂载率是慢变量，不必每天重扫（全量扫描约 40-55 秒）


def _load_json(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {}


def _consumer_files():
    files = []
    for g in CONSUMER_GLOBS:
        files.extend(glob.glob(g, recursive=True))
    for d in CONSUMER_EXTRA_DIRS:
        if os.path.isdir(d):
            for ext in ("*.md", "*.yaml", "*.yml"):
                files.extend(glob.glob(os.path.join(d, "**", ext), recursive=True))
    out = []
    for f in files:
        base = os.path.basename(f)
        if any(x in base for x in CONSUMER_EXCLUDE):
            continue
        out.append(f)
    return out


def _compute_mount_rate():
    universe = set()
    for g in CARD_GLOBS:
        for f in glob.glob(g, recursive=True):
            base = os.path.basename(f)
            if base.startswith((".", "_")):
                continue
            try:
                head = open(f, encoding="utf-8", errors="ignore").read(1200)
            except Exception:
                continue
            m = re.search(r"^rule_id:\s*['\"]?([A-Za-z0-9\-]+)", head, re.M)
            if m:
                universe.add(m.group(1).upper())

    referenced = set()
    cons = _consumer_files()
    for f in cons:
        try:
            txt = open(f, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        referenced.update(x.upper() for x in RULE_ID_RE.findall(txt))

    hit = len(universe & referenced)
    return {
        "universe": len(universe),
        "hit": hit,
        "consumer_files": len(cons),
        "computed_at": datetime.date.today().isoformat(),
    }


def metric_mount_rate(force=False):
    cache = _load_json(MOUNT_CACHE)
    fresh = False
    age = None
    if cache.get("computed_at"):
        try:
            d = datetime.date.fromisoformat(cache["computed_at"])
            age = (datetime.date.today() - d).days
            fresh = age < MOUNT_TTL_DAYS
        except Exception:
            fresh = False

    if fresh and not force:
        data = cache
        note = f"（缓存，算于 {cache['computed_at']}，{MOUNT_TTL_DAYS} 天一算）"
    else:
        data = _compute_mount_rate()
        note = "（本次实算）"
        try:
            json.dump(data, open(MOUNT_CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        except Exception:
            pass

    u, h = data.get("universe", 0), data.get("hit", 0)
    if not u:
        return {"key": "mount_rate", "label": "卡片挂载率", "value": None, "unit": "%",
                "level": "unknown", "hint": "未扫到含 rule_id 的卡（检查路径）"}
    rate = h / u * 100
    level = "ok" if rate >= 60 else ("warn" if rate >= 40 else "bad")
    return {"key": "mount_rate", "label": "卡片挂载率", "value": round(rate, 1), "unit": "%",
            "level": level,
            "hint": f"{h}/{u} 张被引用，未挂载 {u-h}{note}｜静态接线口径，真实调用看埋点",
            "caveat": "⚠️ 挂载≠会调用：2026-10-23 抽样实测，案由路由卡 15/15 全被同 3 个技能"
                      "（模拟法庭主控/法律检索助手/案由路由专项）引用，属「清单式批量接线」。"
                      "真实调用率须看埋点 card_consumption，本指标只反映静态接线覆盖。",
            "extra": {"universe": u, "hit": h, "cache_age_days": age,
                      "consumer_files": data.get("consumer_files")}}


# ────────────────────── ⑤ 门禁拦截数 ──────────────────────
def metric_gate_blocks(hours=24):
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)
    p = os.path.join(METRICS, "grill_hook_violations.jsonl")
    n = 0
    if os.path.exists(p):
        for line in open(p, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if not line:
                continue
            try:
                ts = json.loads(line).get("ts", "")
                if ts and datetime.datetime.fromisoformat(ts) >= cutoff:
                    n += 1
            except Exception:
                continue
    return {"key": "gate_blocks", "label": f"门禁拦截({hours}h)", "value": n, "unit": "次",
            "level": "info",
            "hint": "0 也正常（未触发）；持续为 0 且确在写法律文书时需查钩子"}


# ────────────────────── 历史对比 ──────────────────────
def load_prev():
    if not os.path.exists(STATE):
        return None
    last = None
    for line in open(STATE, encoding="utf-8", errors="ignore"):
        line = line.strip()
        if line:
            try:
                last = json.loads(line)
            except Exception:
                pass
    return last


def save_today(payload):
    """幂等写入：同一天重复运行 → 覆盖当日记录，不追加。

    2026-10-23 实测：初版是纯 append，一次 test 里连跑两次就留下 2 条同日记录
    （generated_at 差 4 秒）。日报的意义是"每天一条"，重跑应覆盖，否则历史会虚胖、
    周对比也会算错。
    """
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    kept = []
    today = payload.get("date")
    if os.path.exists(STATE):
        for line in open(STATE, encoding="utf-8", errors="ignore"):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("date") != today:
                kept.append(line)
    kept.append(json.dumps(payload, ensure_ascii=False))
    with open(STATE, "w", encoding="utf-8") as f:
        f.write("\n".join(kept) + "\n")


ICON = {"ok": "🟢", "warn": "🟡", "bad": "🔴", "info": "·", "unknown": "❔"}


def main():
    argv = sys.argv[1:]
    metrics = [metric_skills(), metric_automations(), metric_metrics24h()]
    if "--no-mount" not in argv:
        metrics.append(metric_mount_rate(force="--force-mount" in argv))
    metrics.append(metric_gate_blocks())
    metrics.append(metric_automation_failures())

    assert len(metrics) <= MAX_METRICS, f"指标数 {len(metrics)} 超过硬上限 {MAX_METRICS}"

    prev = load_prev()
    prev_list = (prev or {}).get("metrics", [])
    prev_map = {m["key"]: m.get("value") for m in prev_list}
    prev_full = {m["key"]: m for m in prev_list}

    bad = [m for m in metrics if m["level"] == "bad"]
    warn = [m for m in metrics if m["level"] == "warn"]
    overall = "bad" if bad else ("warn" if warn else "ok")

    payload = {
        "date": datetime.date.today().isoformat(),
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "overall": overall,
        "metrics": metrics,
        "counts": {"bad": len(bad), "warn": len(warn)},
    }

    if "--json" in argv:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
        if "--dry-run" not in argv:
            save_today(payload)
        sys.exit(1 if bad else 0)

    if "--quiet" in argv and not bad:
        sys.exit(0)

    # ── 人读输出（刻意做短，一屏内看完）──
    print(f"════ 系统健康日报 · {payload['date']} ════")
    for m in metrics:
        icon = ICON.get(m["level"], "·")
        v = "—" if m["value"] is None else m["value"]
        delta = ""
        pv = prev_map.get(m["key"])
        # 🔴 口径变更保护：技能数 2026-10-23 从「目录数」改为「启用数」，
        # 与旧记录的 192 相比会算出 -138 这种毫无意义的差值，必须屏蔽。
        # 判据：上一条记录若有 extra.enabled，说明已是新口径，才可比。
        changed_schema = (m["key"] == "skills"
                          and prev_full.get("skills", {}).get("extra", {}).get("enabled") is None)
        if pv is not None and m["value"] is not None and not changed_schema \
                and m["key"] in ("skills", "automations_active"):
            d = m["value"] - pv
            delta = f"（{'+' if d>0 else ''}{d}）" if d else "（＝）"
        print(f"  {icon} {m['label']:16} {str(v):>6}{m['unit']}{delta}")
        print(f"       └ {m['hint']}")

    # 埋点死亡告警单独提行，避免淹没在 hint 里；图标跟随分级（warn/bad）
    mm = next((m for m in metrics if m["key"] == "metrics_24h"), None)
    if mm and mm.get("extra", {}).get("dead"):
        deads = mm["extra"]["dead"]
        hard = [d for d in deads if d["silent_days"] >= 30]
        head_icon = "🔴" if hard else "🟡"
        head_txt = "判定已断（静默≥30天）" if hard else "可能已断（连续3天0新增）"
        print(f"\n  {head_icon} 埋点死亡告警 · {head_txt}")
        for d in deads:
            mark = "🔴" if d["silent_days"] >= 30 else "🟡"
            print(f"     {mark} {d['key']}：静默 {d['silent_days']} 天｜发射点 {d['emitter']}")
            print(f"        处置：{d['fix']}")

    verdict = {"ok": "🟢 全项正常", "warn": f"🟡 {len(warn)} 项需关注",
               "bad": f"🔴 {len(bad)} 项告警"}[overall]
    print(f"\n════ {verdict} ════")

    if "--dry-run" not in argv:
        save_today(payload)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
