# -*- coding: utf-8 -*-
"""周日批处理统一编排器（单一 SundayRun 实例 · S2→S2.5→S3→FINAL）"""
import os, sys, json, subprocess, datetime, shutil

HERE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/03-连接/scripts"
VAULT = "/Users/chenyouqiang/Documents/LawKB"
PY = "/Users/chenyouqiang/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
TODAY = datetime.date(2026, 9, 6)
TS = TODAY.strftime("%Y%m%d") + "-" + datetime.datetime.now().strftime("%H%M%S")

sys.path.insert(0, HERE)
from intake_sunday_driver import SundayRun

run = SundayRun()
print("[orchestrator] plan:", run.plan)

def call(cmd, cwd=None):
    print("  $ %s" % " ".join(cmd))
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=600)
    out = (p.stdout or "") + (p.stderr or "")
    print(out[-2500:] if len(out) > 2500 else out)
    return p.returncode, out

def backup_dir(src, label):
    root = "/Users/chenyouqiang/WorkBuddy/Claw/backups"
    os.makedirs(root, exist_ok=True)
    dst = os.path.join(root, "周日批_%s_%s" % (label, TS))
    if os.path.exists(src):
        if os.path.exists(dst):
            print("  [六-B] 跳过（本运行已备份）: %s" % dst)
            return dst
        shutil.copytree(src, dst)
        print("  [六-B] 备份 %s -> %s" % (src, dst))
        return dst
    print("  [六-B] 跳过（源不存在）: %s" % src)
    return None

# ============ S2_check_links（重跑 + 真跑校验门禁）============
if "S2_check_links" in run.plan:
    print("\n===== S2_check_links =====")
    try:
        rc, out = call([PY, "check_links.py"], cwd=VAULT)
        # 真跑校验：报告「检查时间」== 今天
        report = os.path.join(VAULT, "知识飞轮系统/03-连接/孤立笔记检测报告/链接检查报告.md")
        check_time_ok = False
        if os.path.exists(report):
            with open(report, encoding="utf-8", errors="ignore") as f:
                head = f.read(800)
            import re
            m = re.search(r"检查时间[:：]\s*(\d{4}-\d{2}-\d{2})", head)
            if m:
                check_time_ok = (m.group(1) == TODAY.isoformat())
                print("[S2 真跑校验] 报告检查时间=%s，今天=%s → %s" % (
                    m.group(1), TODAY.isoformat(), "OK" if check_time_ok else "⚠️不匹配"))
        # 统计摘要
        iso = re.search(r"孤立笔记[:：]\s*(\d+)", out)
        broken = re.search(r"断链[:：]\s*(\d+)", out)
        few = re.search(r"链接数量过少的笔记[:：]\s*(\d+)", out)
        S2_STAT = "孤立%s/断链%s/过少%s" % (
            iso.group(1) if iso else "?", broken.group(1) if broken else "?", few.group(1) if few else "?")
        if not check_time_ok:
            print("⚠️ 告警：check_links 未真正重跑（检查时间≠今天），连接层健康数据可能失真")
        run.stage_done("S2_check_links")
        print("[S2 完成] %s" % S2_STAT)
    except Exception as e:
        run.record_fail("S2_check_links", "异常: %s" % e)
        print("⚠️ S2 失败: %s" % e)

# ============ S2_5_fix_broken（断链自愈 · 含六-B 备份）============
if "S2_5_fix_broken" in run.plan:
    print("\n===== S2_5_fix_broken =====")
    try:
        # 六-B 备份：概念页 + 裁判规则库 + 经验卡片
        backup_dir(os.path.join(VAULT, "知识飞轮系统/03-连接/概念页"), "概念页")
        backup_dir(os.path.join(VAULT, "知识飞轮系统/06-沉淀/裁判规则库"), "裁判规则库")
        backup_dir(os.path.join(VAULT, "知识飞轮系统/02-提炼/经验卡片"), "经验卡片")
        # 步骤A 源链接修复
        rc1, out1 = call([PY, os.path.join(HERE, "fix_source_links.py"), "--apply"])
        # 步骤B 断链消解
        rc2, out2 = call([PY, os.path.join(HERE, "resolve_broken_links.py"), "--apply", "--only-freq", "1"])
        # 读取产物统计
        broken_json = os.path.join(HERE, "broken_resolve_lastrun.json")
        br = {}
        if os.path.exists(broken_json):
            br = json.load(open(broken_json, encoding="utf-8"))
        S2_5_STAT = "源修复+断链消解完成；产物=%s" % json.dumps(br, ensure_ascii=False)[:300]
        run.stage_done("S2_5_fix_broken")
        print("[S2_5 完成] %s" % S2_5_STAT)
    except Exception as e:
        run.record_fail("S2_5_fix_broken", "异常: %s" % e)
        print("⚠️ S2_5 失败: %s" % e)

# ============ S3_relink_graph（连接层补链 + 图谱刷新）============
if "S3_relink_graph" in run.plan:
    print("\n===== S3_relink_graph =====")
    try:
        # 六-B 备份（link_cards_rules 改写 经验卡片/裁判规则库 的 ## 关联 段）
        backup_dir(os.path.join(VAULT, "知识飞轮系统/06-沉淀/裁判规则库"), "裁判规则库")
        backup_dir(os.path.join(VAULT, "知识飞轮系统/02-提炼/经验卡片"), "经验卡片")
        # 补链
        rc, out = call([PY, os.path.join(HERE, "link_cards_rules.py")])
        link_json = os.path.join(HERE, "link_lastrun.json")
        lr = {}
        if os.path.exists(link_json):
            lr = json.load(open(link_json, encoding="utf-8"))
        # 图谱刷新
        call([PY, os.path.join(HERE, "kg_scan.py")])
        call([PY, os.path.join(HERE, "kg_html.py")])
        kg_data = os.path.join(HERE, "kg_data.json")
        kg = {}
        if os.path.exists(kg_data):
            kg = json.load(open(kg_data, encoding="utf-8"))
        S3_STAT = "补链: processed=%s hubs=%s；图谱节点=%s 边=%s" % (
            lr.get("processed"), lr.get("hubs"),
            len(kg.get("nodes", [])) if isinstance(kg.get("nodes"), list) else kg.get("nodes"),
            len(kg.get("edges", [])) if isinstance(kg.get("edges"), list) else kg.get("edges"))
        run.stage_done("S3_relink_graph")
        print("[S3 完成] %s" % S3_STAT)
    except Exception as e:
        run.record_fail("S3_relink_graph", "异常: %s" % e)
        print("⚠️ S3 失败: %s" % e)

# ============ FINAL ============
print("\n===== FINAL =====")
fails = run.finalize()
print("[FINAL] failed_stages=%s" % fails)
