#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
9655 单机驾驶舱 · 实扫管线 v2（输出 9360 格式 scorecard_data.json + 系统组件注册表 system_registry.json）
==============================================================
唯一真源：/Users/chenyouqiang/Documents/LawKB/lawtwin/律师分身系统（单机密文版）/
复用旧版 scan_9655.py 的全部探针（六维 / 版本锁 / 门禁 / 脱敏 / 缺口 / 架构），
输出 9360 门户消费的 scorecard_data.json（screens + dims + total + grade）；
P0 扩展：实扫 ~/.workbuddy/skills + mcp.json + LawKB，输出 system_registry.json
（数字分身系统全组件注册表：智能体/工作流/子系统/连接器/知识库 + 健康态），
供驾驶舱"数据变化→各屏全面更新"的实时骨架使用。

原则（对齐 R-LN-114 教训 · 杜绝假健康）：
1. 走实源，禁止凭记忆填数；扫不到的字段标 "需人工确认"。
2. 门禁状态 = 真探进程（pgrep），不靠 socket 文件存在判定。
3. 脚本只读，不产生破坏性写入；解析失败不崩溃，逐段 try/except。

刷新：python3 scan_9655.py          # 生成 scorecard_data.json
      python3 scan_9655.py --print  # 顺便打印摘要
"""
import os
import re
import sys
import json
import glob
import datetime
import urllib.request

V2 = os.path.dirname(os.path.abspath(__file__))
# 旧版探针已 vendored 进 v2（_legacy_probes.py），使 9655-cockpit-v2 自包含、不依赖 outputs/9655-cockpit
sys.path.insert(0, V2)
import _legacy_probes as OLD  # 复用旧版探针（已融入新版）

OUT = os.path.join(V2, "scorecard_data.json")
NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 复用旧版探针工具
pgrep = OLD.pgrep
exists = OLD.exists
read_text = OLD.read_text
p = OLD.p
detect_skill_version = OLD.detect_skill_version
SRC = OLD.SRC
SKILLS_DIR = OLD.SKILLS_DIR
LAWTWIN_CORE = OLD.LAWTWIN_CORE

# ----------------------------------------------------------------------------
# 屏定义（cno, name, url, dot, lawFirm, weight, scored）
# home=作战地图容器(monitor)；cloud=外部链接(monitor)；lawFirm=律所业务屏(全屏显)
# ----------------------------------------------------------------------------
SCREENS_DEF = [
    # 屏名铁律：与 9360 内网版导航逐字一致（rbac.js 为权威源），壳 1:1 复刻、仅数据源换 9655 实扫
    ("home",          "九屏维度",                  "",                                       "m",    False, 0.00, False),
    ("ev",            "车机驾驶舱",                "subapps/ev/index.html",                  "a",    False, 0.10, True),
    ("decision",      "决策思维舱",                "subapps/decision/index.html",            "d",    False, 0.12, True),
    ("flywheel",      "知识飞轮舱",                "subapps/flywheel/index.html",            "b",    False, 0.12, True),
    ("clm",           "案件管理中台",              "subapps/clm/index.html",                 "f",    True,  0.00, True),
    ("xiaode",        "合规管理中台",              "subapps/xiaode/index.html",               "k",    True,  0.00, True),
    ("mock",          "模拟庭审中台",              "subapps/mock/index.html",                 "c",    True,  0.00, True),
    ("contractlifecycle","合同管理中台",           "subapps/contract-lifecycle/index.html",    "g",    True,  0.00, True),
    ("lti",           "AI 幻觉监控舱",             "subapps/lti/index.html",                  "h",    False, 0.15, True),
    ("credits",       "积分监测中台",              "subapps/credits/index.html",              "e",    False, 0.10, True),
    ("conflict",      "知识冲突中台",              "subapps/conflict-arbitration/index.html","conf", False, 0.11, True),
    ("cloud",         "云服务中台",                "https://xiaoqiang-cloud-service.app.workbuddy.host/","i", False, 0.00, False),
    ("mindmodel",     "心智模型中台",              "subapps/mind-models/index.html",          "mm",   False, 0.10, True),
    ("permcenter",    "权限管理中心",              "subapps/permcenter/index.html",           "pc",   False, 0.10, True),
    ("d6permcenter",  "权限调用中台",              "subapps/d6permcenter/index.html",         "d6",   False, 0.10, True),
    # D7/D8 智能体/工作流中台（对标 Harvey Command Center · 已批准方案）
    ("agenthub",      "智能体中台",                "subapps/agenthub/index.html",             "ag",   False, 0.10, True),
    ("workflowhub",   "工作流中台",                "subapps/workflowhub/index.html",          "wf",   False, 0.10, True),
    # D9 共享中枢中台（对标 Harvey Command Center · 已批准方案 · 2026-09-20 老强批准）
    ("sharedhub",     "共享中枢中台",              "subapps/sharedhub/index.html",            "sh",   False, 0.10, True),
    # C9 治理中台（非评分监控位 · 2026-09-25 老强拍板 §5-C.1 方案A非评分变体）：进 screens 但不评分，
    # 三向比对（基线 × rbac × scorecard）因此对齐 → drift=0、校齐率 100%；不造假分，守 R-LN-114
    ("governance",    "OPC治理中台",               "subapps/governance/index.html",           "n",    False, 0.10, False),
]
# 律所屏 9360 真源评分（全屏统一显示）
LAWFIRM_9360_SCORE = {"clm": 66.5, "xiaode": 61.0, "mock": 62.0, "contractlifecycle": 71.0}


def mk_six(score, **over):
    """六维均由实源派生；未单独探测的子维取主分，差异项由 over 覆盖。"""
    base = {
        "fresh": score, "coverage": score, "health": score,
        "output": score, "compliance": score, "automation": score,
    }
    for k, v in over.items():
        if k in base:
            base[k] = v
    return base


# ----------------------------------------------------------------------------
# D7 智能体中台 / D8 工作流中台 · 实扫评分引擎（对标 Harvey Command Center）
# 数据真源：~/.workbuddy/skills/ 实时扫描；分类口径沿用已批准设计规范（20 智能体 / 33 工作流）
# 6 维加权：版本治理15% / 迭代活跃度20% / 系统作用度20%·运行健康20%·审计合规15%·文档完备10%（D7）
#           或 流程覆盖度20%·执行效能20%·审计监控15%·复用度10%（D8）
#   版本治理/迭代活跃度 = 真实实扫值（SKILL.md version + 文件 mtime）
#   其余四维 = SKILL.md 静态可解释代理分（无运行时埋点，UI 明确标注"静态估算"，不冒充遥测）
# ----------------------------------------------------------------------------
AGENT_ROLES = {
    "红队出庭律师": "红蓝对抗·攻击方（预驳回攻击/最残酷庭审压力测试）",
    "蓝队出庭律师": "红蓝对抗·防御方（庭审准备/证据组织/攻防策略）",
    "蓝队律师合同审查": "合同审查防御专家（蓝队口径的条款风险审查）",
    "庭审战情室": "第三方观察员（红蓝对抗全程评估+战情分析报告）",
    "庭审准备助手": "庭前准备（大事记/法官预判/争点提炼）",
    "庭审实时助手": "庭审实时辅助（当庭提示/临场应对）",
    "模拟法庭主控协调器": "庭审推演主控（协调各智能体+落实门禁）",
    "模拟法庭书记员": "庭审记录（查明到庭/笔录/证据台账/争点映射）",
    "模拟法庭庭审系统": "统一庭审推演入口（派发红蓝对抗引擎）",
    "律所主任·管理合伙人": "治理席位（系统运维/红蓝指导/子自动化研判）",
    "律所主任·驾驶舱监控": "驾驶舱全量巡检执行器（每日重扫大屏）",
    "分身系统IT运维员": "系统可靠性工程师（事故取证/建卡/互联）",
    "小德慈善合规中枢": "慈善组织合规中枢（合规审查/制度/方案设计）",
    "小德合规管理系统": "合规管理系统（慈善合规全流程承载）",
    "小哲AI学伴": "教育陪伴智能体（学习辅助/陪练）",
    "元认知分析师": "元认知分析（思维/学习行为分析）",
    "xiaoqianglvshi": "小强律师数字分身·主分身（总入口/咨询路由下游聚合）",
    "法律智能体基座": "法律智能体能力基座（支撑层，供各法律 agent 调用）",
    "法律AI防幻觉能力实测方法": "防幻觉能力实测方法（质量基线实测 agent）",
    "三轮冲击控制器": "红蓝迭代控制器（蓝军→红军三轮冲击编排）",
}
WORKFLOW_ROLES = {
    "诉讼文书红蓝复核工作流": "诉讼/仲裁类文书红蓝对抗复核+ LTI 门禁",
    "非诉文书红蓝复核工作流": "非诉文书红蓝复核（合同/意见/制度类）",
    "案件生命周期大屏流水线": "CLM 扫描→内部大屏+脱敏简报双管线",
    "静态数据看板生成流水线": "文件系统状态→单文件离线 HTML 看板",
    "审判要件卡拆卡流水线": "审判要件指南 PDF→审判要件卡六层挂载",
    "文书范式卡建卡流水线": "文书范式卡（要素式+红线+错例）建卡",
    "合规审查卡建卡流水线": "慈善合规审查卡（R-CF 域）批量建卡",
    "存量卡法条核验段批量回填": "存量卡法条段「元典核填」批量回填",
    "知识飞轮卡库接线": "智能体技能接知识飞轮卡库（可回溯卡源）",
    "裁量尺度卡拆卡流水线": "裁量尺度卡（量化锚点）批量拆建",
    "要件映射卡批量补卡": "要件映射卡指针卡批量补建（LTI 负向拦截）",
    "请求权基础卡族拆卡流水线": "请求权基础/法条竞合卡族拆建",
    "合同审查工作流": "合同审查端到端流程编排",
    "案件全生命周期·编排器": "案件全生命周期主编排器",
    "收案审批流程": "收案审批流程编排",
    "案件归档管理": "案件归档管理流程",
    "cockpit-builder": "驾驶舱 1:1 复刻 9360 构建流水线",
    "yuandian-statute-bridge": "法条实时核验桥接（pkulaw+yuandian 双源）",
    "lawkb-card-field-batch-backfill": "LawKB 卡 frontmatter 字段批量补标",
    "lawkb-conflict-arbitration": "LawKB 知识冲突仲裁（融合/采纳/不冲突）",
    "lawkb-legal-consistency-audit": "LawKB 法条一致性/冲突审计",
    "lawkb-rule-id-governance": "LawKB 编号治理（取号/撞号/改号）",
    "hub-card-backfill": "Obsidian 共享记忆中枢按需补卡流水线",
    "statute-pending-clear": "statute_text_pending 待回源清零",
    "知识飞轮链接与编号治理": "飞轮链接与编号治理 utility 流水线",
    "经验总结与知识沉淀": "经验总结与知识沉淀流程",
    "跨案件模式识别": "跨案件模式识别（类案/策略聚类）",
    "场景化知识推送": "场景化知识推送（按情境命中卡源）",
    "案件全生命周期·案件工作汇报": "案件工作汇报生成",
    "案件全生命周期·程序推进包": "程序推进包生成",
    "案件全生命周期·调解和解方案": "调解和解方案生成",
    "案件全生命周期·门禁体系": "案件门禁体系（合规闸）",
    "案件执行助手": "案件执行流程辅助",
}


def _ver_score(ver):
    if not ver:
        return 0
    if re.match(r"^\d+\.\d+(\.\d+)?$", ver):
        return 100
    return 60


def _iter_score(mtime_str, today):
    try:
        d0 = datetime.date.fromisoformat(mtime_str)
    except Exception:
        return 30
    days = (today - d0).days
    if days <= 14:
        return 100
    elif days <= 30:
        return 85
    elif days <= 90:
        return 70
    elif days <= 180:
        return 50
    return 30


def _health_badge_from_score(score):
    if score >= 85:
        return "🟢健康"
    if score >= 60:
        return "🟡关注"
    return "🔴风险"


def _health_cls(badge):
    if badge.startswith("🟢"):
        return "active"
    if badge.startswith("🟡"):
        return "warn"
    return "alert"


# —— 四个"待采集"维度的静态可解释代理分（无运行时埋点，UI 标注为静态估算）——
def _doc_score(txt):
    # 文档完备：有 description 字段且正文充实（实扫 SKILL.md 结构）
    has_desc = bool(re.search(r"^\s*description\s*:", txt, re.M))
    body_len = len(txt)
    if has_desc and body_len >= 1500:
        return 100
    if has_desc and body_len >= 600:
        return 85
    if has_desc:
        return 70
    return 45


def _role_score(role_text):
    # 系统作用度（D7，人工定级口径·静态落实）：治理席/主分身/基座=极高；中台/中枢/系统/对抗核心/主控/战情/运维=高；辅助/准备/陪练/学伴/分析/实测=中
    t = role_text or ""
    if any(k in t for k in ("治理席位", "主分身", "基座")):
        return 100
    if any(k in t for k in ("中枢", "系统", "对抗", "攻击", "防御", "主控", "战情", "运维", "监控")):
        return 90
    if any(k in t for k in ("准备", "助手", "陪练", "学伴", "书记员", "庭审系统", "合同审查", "冲击", "分析", "实测")):
        return 80
    return 80


def _coverage_score(txt):
    # 流程覆盖度（D8，静态扫描）：正文长度 + 步骤/流程/边界/异常 关键词密度
    body_len = len(txt)
    kw = len(re.findall(r"步骤|流程|边界|异常|分支|兜底|回滚|校验|输入|输出|触发", txt))
    score = 60
    if body_len >= 2000:
        score += 20
    elif body_len >= 1000:
        score += 12
    elif body_len >= 500:
        score += 6
    score += min(20, kw * 2)
    return min(100, score)


def _health_score(txt):
    # 运行健康（D7，静态代理）：无桩代码/待开发标记 + 有清晰触发或用法说明
    if re.search(r"待开发|TODO|FIXME|占位|示例代码|未实现|stub|开发中", txt, re.I):
        return 60
    trig = bool(re.search(r"触发词|trigger|使用说明|用法|使用示例|如何", txt, re.I))
    return 100 if trig else 85


def _compliance_score(name, txt):
    # 审计合规/审计监控（D7/D8，静态代理）：LTI/合规/门禁/回滚/审计/校验 关键词 + 核心系统成员
    core = any(k in name for k in ("律所主任", "合规", "LTI", "门禁", "审计", "xiaoqianglvshi", "legal"))
    kw = bool(re.search(r"LTI|合规|门禁|回滚|审计|校验|REJECT|门禁体系|安全", txt))
    if core and kw:
        return 100
    if core or kw:
        return 90
    return 78


def _exec_score(txt, days):
    # 执行效能（D8，静态代理）：幂等/dry-run/校验 关键词 + 近期活跃
    kw = bool(re.search(r"幂等|dry.?run|可重入|校验|原子|事务", txt, re.I))
    base = 90 if kw else 78
    if days >= 0 and days <= 90:
        base = min(100, base + 8)
    return base


def _reuse_score(name, inbound):
    # 复用度（D8，可实扫）：被其他技能 SKILL.md 引用的次数
    if inbound >= 3:
        return 100
    if inbound >= 1:
        return 88
    return 72


def _dims_for(name, role_map, today, kind, inbound=0):
    """实扫单个技能，计算 6 维评分（版本/迭代为真实值，其余 4 维为静态估算）。"""
    d = os.path.expanduser(os.path.join("~/.workbuddy/skills", name))
    meta = {"version": "", "mtime": "", "updated": ""}
    sk = os.path.join(d, "SKILL.md")
    txt = ""
    if exists(sk):
        txt = read_text(sk)
        for line in txt.splitlines()[:200]:
            ls = line.strip()
            if ls.startswith("version:"):
                meta["version"] = ls.split(":", 1)[1].strip().strip('"').strip("'")
            elif ls.startswith("updated:") or ls.startswith("updated_at:") or ls.startswith("last_updated:"):
                meta["updated"] = ls.split(":", 1)[1].strip().strip('"').strip("'")
    try:
        # 迭代活跃度以 SKILL.md 内容最后编辑时间为真源（目录 mtime 不可靠：仅在新增文件时更新）
        mtime_src = sk if exists(sk) else d
        meta["mtime"] = datetime.date.fromtimestamp(os.path.getmtime(mtime_src)).isoformat()
    except Exception:
        pass
    vs = _ver_score(meta["version"])
    it = _iter_score(meta["mtime"], today)
    doc = _doc_score(txt)
    days = -1
    if meta["mtime"]:
        try:
            days = (today - datetime.date.fromisoformat(meta["mtime"])).days
        except Exception:
            days = -1
    if kind == "agent":
        role = _role_score(role_map.get(name, ""))
        health = _health_score(txt)
        compliance = _compliance_score(name, txt)
        dims = {"ver": vs, "iter": it, "role": role, "health": health, "compliance": compliance, "doc": doc}
        composite = round(0.15 * vs + 0.20 * it + 0.20 * role + 0.20 * health + 0.15 * compliance + 0.10 * doc, 1)
        dims_keys = ("版本治理", "迭代活跃度", "系统作用度", "运行健康", "审计合规", "文档完备")
    else:
        coverage = _coverage_score(txt)
        exec_s = _exec_score(txt, days)
        compliance = _compliance_score(name, txt)
        reuse = _reuse_score(name, inbound)
        dims = {"ver": vs, "iter": it, "coverage": coverage, "exec": exec_s, "compliance": compliance, "reuse": reuse}
        composite = round(0.15 * vs + 0.20 * it + 0.20 * coverage + 0.20 * exec_s + 0.15 * compliance + 0.10 * reuse, 1)
        dims_keys = ("版本治理", "迭代活跃度", "流程覆盖度", "执行效能", "审计监控", "复用度")
    badge = _health_badge_from_score(composite)
    return {
        "name": name, "version": meta["version"], "updated": meta["updated"],
        "ver_score": vs, "iter_score": it, "iter_days": days,
        "health": badge, "role": role_map.get(name, ""),
        "dims": dims, "dims_keys": dims_keys, "composite": composite,
    }


def scan_skills_center():
    """实扫 ~/.workbuddy/skills/，按已批准口径分类为智能体/工作流，输出 6 维评分（含静态估算的四维）。"""
    today = datetime.date.today()
    skills_dir = os.path.expanduser("~/.workbuddy/skills")
    # 复用度（D8）：一次遍历所有技能 SKILL.md，统计工作流名被引用次数
    inbound = {w: 0 for w in WORKFLOW_ROLES}
    if exists(skills_dir):
        for entry in sorted(os.listdir(skills_dir)):
            sk = os.path.join(skills_dir, entry, "SKILL.md")
            if not exists(sk):
                continue
            t = read_text(sk)
            for w in WORKFLOW_ROLES:
                if w in t:
                    inbound[w] += 1
    agents = [_dims_for(n, AGENT_ROLES, today, "agent") for n in AGENT_ROLES]
    workflows = [_dims_for(n, WORKFLOW_ROLES, today, "workflow", inbound.get(n, 0)) for n in WORKFLOW_ROLES]

    def summ(items, kind):
        n = len(items)
        avg_vs = round(sum(i["ver_score"] for i in items) / n, 0) if n else 0
        avg_it = round(sum(i["iter_score"] for i in items) / n, 0) if n else 0
        nov = sum(1 for i in items if not i["version"])
        healthy = sum(1 for i in items if i["health"] == "🟢健康")
        comp = round(sum(i["composite"] for i in items) / n, 1) if n else 0
        new_dims = ("role", "health", "compliance", "doc") if kind == "agent" else ("coverage", "exec", "compliance", "reuse")
        new_avg = {dk: (round(sum(i["dims"][dk] for i in items) / n, 0) if n else 0) for dk in new_dims}
        return {"n": n, "avg_vs": avg_vs, "avg_it": avg_it, "nov": nov,
                "healthy": healthy, "composite": comp, "new_avg": new_avg}

    return {"agents": agents, "workflows": workflows,
            "agent_summary": summ(agents, "agent"), "wf_summary": summ(workflows, "workflow")}


def scan_shared_hub():
    """实扫 Obsidian 共享记忆中枢 (_AI-Memory-Hub)，输出 6 维评分 + 子库分布 + 作用链路数据。
    真源：~/Documents/LawKB/_AI-Memory-Hub/（老强所有 AI 项目唯一永久事实源）。
    6 维：协议治理15% / 迭代活跃度20% / 覆盖完备度20% / 运行健康20% / 审计合规15% / 文档完备10%。
      协议治理/迭代活跃度/覆盖完备度 = 真实实扫值；运行健康/审计合规/文档完备 = frontmatter 静态可解释代理分
      （UI 明确标注"静态估算"，不冒充运行时遥测；后续接中枢 git 提交埋点可直换真值）。
    全部 try/except 包裹，扫不到的字段诚实降级，不凭记忆填数（对齐 R-LN-114）。"""
    hub = os.path.expanduser("~/Documents/LawKB/_AI-Memory-Hub")
    today = datetime.date.today()
    META = {"README.md", "AGENTS.md"}
    SUBS = ["00-全局规则", "01-用户偏好", "02-当前项目", "03-决策档案", "04-Workflows",
            "04-每日日志", "05-归档", "06-经验沉淀", "07-卡族总索引", "08-心智资产", "99-脚本"]

    def _iter_from_days(days):
        if days < 0:
            return 45
        if days <= 1:
            return 100
        if days <= 3:
            return 90
        if days <= 7:
            return 80
        if days <= 14:
            return 65
        return 45

    sub_counts, total_cards = {}, 0
    for s in SUBS:
        d = os.path.join(hub, s)
        n = 0
        if exists(d):
            for p in glob.glob(os.path.join(d, "**", "*.md"), recursive=True):
                if os.path.basename(p) in META:
                    continue
                n += 1
        sub_counts[s] = n
        total_cards += n
    non_empty = sum(1 for s in SUBS if sub_counts.get(s, 0) > 0)

    # 协议治理（真实）：README/AGENTS schema 存在 + 全局规则含 version 字段占比
    readme_ok = exists(os.path.join(hub, "README.md"))
    agents_ok = exists(os.path.join(hub, "AGENTS.md"))
    gr_dir = os.path.join(hub, "00-全局规则")
    gr_total, gr_ver = 0, 0
    if exists(gr_dir):
        for p in glob.glob(os.path.join(gr_dir, "*.md")):
            if os.path.basename(p) in META:
                continue
            gr_total += 1
            if re.search(r"^\s*version\s*:", read_text(p), re.M):
                gr_ver += 1
    ver_ratio = (gr_ver / gr_total) if gr_total else 0
    if readme_ok and agents_ok:
        gov = round(70 + 30 * ver_ratio)
    elif readme_ok or agents_ok:
        gov = round(50 + 20 * ver_ratio)
    else:
        gov = 30

    # 迭代活跃度（真实）：04-每日日志 最近 mtime 距今天数
    log_dir = os.path.join(hub, "04-每日日志")
    last_log_days = -1
    if exists(log_dir):
        mtimes = []
        for p in glob.glob(os.path.join(log_dir, "*.md")):
            if os.path.basename(p) in META:
                continue
            try:
                mtimes.append(datetime.date.fromtimestamp(os.path.getmtime(p)))
            except Exception:
                pass
        if mtimes:
            last_log_days = (today - max(mtimes)).days
    iter_s = _iter_from_days(last_log_days)

    # 覆盖完备度（真实）：子库非空率（07-卡族总索引/README/AGENTS 已含在 100 封顶内）
    cov = round(100 * non_empty / len(SUBS))

    # 运行健康/审计合规/文档完备（静态估算，全量卡 frontmatter 扫描）
    status_active, status_total, deprecated, key_leak, sub_idx = 0, 0, 0, 0, 0
    recall_cards, writeback_hits = 0, 0
    family = {"RULE": 0, "PREF": 0, "PROJ": 0, "DEC": 0, "WF": 0}
    for s in SUBS:
        d = os.path.join(hub, s)
        if not exists(d):
            continue
        if exists(os.path.join(d, "_索引.md")):
            sub_idx += 1
        for p in glob.glob(os.path.join(d, "**", "*.md"), recursive=True):
            if os.path.basename(p) in META:
                continue
            status_total += 1
            t = read_text(p)
            sm = re.search(r"^\s*status\s*:\s*(\w+)", t, re.M)
            if sm and sm.group(1).lower() == "active":
                status_active += 1
            if re.search(r"status\s*:\s*deprecated", t, re.I):
                deprecated += 1
            if re.search(r"(password|secret|token|api_key|私钥|密码)\s*[:=]\s*\S+", t, re.I) \
                    and not re.search(r"不打印明文|不存明文|禁止入中枢|禁止把密钥", t):
                key_leak += 1
            bn = os.path.basename(p)
            for k in family:
                if bn.upper().startswith(k):
                    family[k] += 1
            if s == "02-当前项目" or s == "03-决策档案":
                recall_cards += 1
            if s == "04-每日日志" and re.search(r"回写|write_back|writeback", t, re.I):
                writeback_hits += 1
    active_ratio = (status_active / status_total) if status_total else 0
    health = round(60 + 40 * active_ratio)
    # 审计合规：无密钥泄漏 + status 完整
    if key_leak == 0 and status_total > 0:
        compliance = 95 if deprecated > 0 else 100
    elif key_leak == 0 or status_total > 0:
        compliance = 85
    else:
        compliance = 70
    # 文档完备：README + 07-卡族总索引 + 子目录 _索引.md
    idx_present = bool(glob.glob(os.path.join(hub, "07-卡族总索引", "*.md")))
    doc = 0
    doc += 34 if readme_ok else 0
    doc += 33 if idx_present else 0
    doc += min(33, sub_idx * 10)
    doc = min(100, doc)

    composite = round(0.15 * gov + 0.20 * iter_s + 0.20 * cov + 0.20 * health
                      + 0.15 * compliance + 0.10 * doc, 1)
    dims_keys = ("协议治理", "迭代活跃度", "覆盖完备度", "运行健康", "审计合规", "文档完备")
    dims = {"gov": gov, "iter": iter_s, "cov": cov, "health": health,
            "compliance": compliance, "doc": doc}

    # 需求拷问门禁遥测（Grill-Me · 运行时真值）：读 grill_events.jsonl 聚合
    grill_gate = _probe_grill_gate()

    return {
        "sub_counts": sub_counts, "total_cards": total_cards, "sub_count": non_empty,
        "gov": gov, "iter": iter_s, "cov": cov, "health": health,
        "compliance": compliance, "doc": doc, "composite": composite,
        "dims_keys": dims_keys, "dims": dims,
        "last_log_days": last_log_days,
        "active_ratio": round(active_ratio * 100, 0),
        "deprecated": deprecated, "key_leak": key_leak,
        "sub_idx": sub_idx, "idx_present": idx_present,
        "recall_cards": recall_cards, "writeback_hits": writeback_hits,
        "arbitration": deprecated, "family": family,
        "grill_gate": grill_gate,
    }


# 法律域专项技能 + 任务派发器 接线总集（与 /tmp/wire_grill.py 保持一致；grill 自身单列、router 统一入口已纳入计数）。
# 用于 D9「接线覆盖」：扫描各 SKILL.md 头部是否含 grill 引用 → 声明接线 / 未接清单。
# 口径：72 个下游法律域专项技能 + 1 个统一入口(legal-consult-router) = 73，hook 仍按名豁免 router 硬拦截，行为不变。
GRILL_WIRE_TARGETS = [
    "诉讼文书红蓝复核工作流", "非诉文书红蓝复核工作流", "蓝队出庭律师", "红队出庭律师",
    "庭审准备助手", "庭审实时助手", "庭审战情室", "模拟法庭庭审系统", "模拟法庭主控协调器",
    "模拟法庭书记员", "模拟法庭红蓝对抗工作流", "证据整理助手", "诉讼可视化助手",
    "ai-mock-court-judge", "上诉策略分析", "判决书分析助手", "对方律师律所画像",
    "利益冲突审查", "收案审批流程", "案件执行助手", "案件归档管理",
    "案件全生命周期·案件工作汇报", "案件全生命周期·程序推进包", "案件全生命周期·编排器",
    "案件全生命周期·调解和解方案", "案件全生命周期·门禁体系", "trial-prep-pipeline",
    "跨案件模式识别",
    "合同审查工作流", "合同审查门禁", "蓝队律师合同审查", "red-team-contract-review",
    "红蓝复核批量修正工作流", "合同文书管理系统", "法律文书docx交付流水线",
    "法律文书写作助手", "法律文书审查助手（非合同类）", "法律文书法理逻辑复核",
    "法律备忘录", "blue-team-contract-review-standard-v1.0",
    "法律检索助手", "类案检索助手", "类案大数据分析", "china-judgments-api",
    "court-case-database-api", "prc-legal-research-case-search",
    "prc-legal-research-company-search", "prc-legal-research-law-search",
    "legal-database-search", "legal-provision-verify", "法律AI防幻觉能力实测方法",
    "小德合规管理系统", "小德慈善合规中枢", "医院合规与纠纷处理", "数据合规审查",
    "税务合规审查", "股权激励方案设计", "charity-dispute-resolution",
    "charity-financial-compliance", "charity-institutional-system",
    "charity-writing-assistant", "foundation-transparency-auditor",
    "人损纠纷专项", "医疗纠纷专项", "tanan-lvshi",
    "经验总结与知识沉淀", "结案报告生成", "法律服务报价助手", "lawyer-prompt-library",
    "lawyer-yourself-skill", "咨询轨迹沉淀",
    "司法裁判规则图谱",
    # 统一入口（法律咨询域派发器）：预置接入、hook 按名豁免其硬拦截；纳入计数使面板如实体现「域级全入口覆盖 = 73/73（含 router）」
    "legal-consult-router",
]
GRILL_WIRE_BASE = os.path.expanduser("~/.workbuddy/skills")


def _probe_grill_gate():
    """需求拷问门禁（Grill-Me）运行时遥测：读 grill_events.jsonl 聚合 + 声明接线扫描。
    事件：invoke=门禁触发（进入拷问）/ aligned=对齐卡产出（成功对齐）/ skip=直接放行。
    caller(可选)=下游消费方技能名 → 实测触发集合（消除"声明>执行"盲区）。
    指标：调用量(invoke) + 对齐率(aligned/invoke) + 放行数(skip) + 拦截率(invoke/(invoke+skip))；
          并扫描 GRILL_WIRE_TARGETS 各 SKILL.md 是否含 grill 引用 → declared(声明接线)/unwired(未接清单)。
    文件缺失/为空 → 返回待采集状态（不虚构，对齐 R-LN-114 零假健康原则）。"""
    log = os.path.expanduser("~/.workbuddy/metrics/grill_events.jsonl")
    # 声明接线扫描（静态，基于技能头部引用）
    declared = 0
    unwired = []
    for name in GRILL_WIRE_TARGETS:
        fp = os.path.join(GRILL_WIRE_BASE, name, "SKILL.md")
        wired = False
        if exists(fp):
            try:
                t = open(fp, encoding="utf-8").read()
                wired = ("需求拷问前置门禁" in t) or ("grill-me-legal-preprocessor" in t)
            except Exception:
                pass
        if wired:
            declared += 1
        else:
            unwired.append(name)
    if not exists(log):
        return {"available": False, "invoke": 0, "aligned": 0, "skip": 0,
                "align_rate": 0, "intercept_rate": 0, "status": "待采集",
                "callers": [], "declared": declared, "unwired": unwired,
                "total": len(GRILL_WIRE_TARGETS)}
    invoke = aligned = skip = 0
    callers = set()
    try:
        with open(log, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                e = (rec.get("event") or "").lower()
                if e == "invoke":
                    invoke += 1
                elif e == "aligned":
                    aligned += 1
                elif e == "skip":
                    skip += 1
                c = (rec.get("caller") or "").strip()
                if c:
                    callers.add(c)
    except Exception:
        return {"available": False, "invoke": 0, "aligned": 0, "skip": 0,
                "align_rate": 0, "intercept_rate": 0, "status": "读取异常",
                "callers": [], "declared": declared, "unwired": unwired,
                "total": len(GRILL_WIRE_TARGETS)}
    decisions = invoke + skip  # 门禁总决策数（触发 vs 放行）
    align_rate = round(aligned / invoke * 100, 1) if invoke else 0.0
    intercept_rate = round(invoke / decisions * 100, 1) if decisions else 0.0
    return {"available": True, "invoke": invoke, "aligned": aligned, "skip": skip,
            "align_rate": align_rate, "intercept_rate": intercept_rate,
            "status": "运行中" if (invoke + skip) > 0 else "已接线·无事件",
            "callers": sorted(callers), "declared": declared, "unwired": unwired,
            "total": len(GRILL_WIRE_TARGETS)}


def probe_http_up(url, timeout=2):
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception:
        return False


def probe_lawkb_count():
    """知识体规模（卡库文件数）· 实扫 LawKB 飞轮系统 06-沉淀。"""
    base = os.path.expanduser("~/Documents/LawKB/知识飞轮系统/06-沉淀")
    if not exists(base):
        return 0, "需人工确认"
    n = 0
    for _ in glob.glob(os.path.join(base, "**", "*.md"), recursive=True):
        n += 1
    return n, "实扫 {0} 个 md".format(n)


def probe_disk_usage(path):
    try:
        st = os.statvfs(path)
        free = st.f_bavail * st.f_frsize
        total = st.f_blocks * st.f_frsize
        used_pct = int((1 - free / total) * 100)
        return used_pct
    except Exception:
        return -1


def probe_host_metrics():
    """主机实时指标（macOS 优先实采 top/vm_stat/sysctl；Linux 回退 /proc；sandbox/无命令则诚实降级）。
    返回 cpu_pct / mem_pct / load1 / uptime_h（均 <0 表示未取到）。"""
    res = {"cpu_pct": -1, "mem_pct": -1, "load1": -1, "uptime_h": -1, "ok": False, "note": "需人工确认"}
    try:
        import subprocess, time
        def run(cmd, timeout=3):
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
        # —— macOS 实采 ——
        try:
            top = run(["top", "-l", "1", "-n", "0"])
            m = re.search(r"CPU usage:\s*([\d.]+)%\s*user,\s*([\d.]+)%\s*sys", top)
            if m:
                res["cpu_pct"] = round(float(m.group(1)) + float(m.group(2)), 1)
            m = re.search(r"Load Avg:\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)", top)
            if m:
                res["load1"] = float(m.group(1))
        except Exception:
            pass
        try:
            vm = run(["vm_stat"])
            pages = {}
            for line in vm.splitlines():
                mm = re.match(r"\s*([\w ]+):\s*(\d+)\.", line)
                if mm:
                    pages[mm.group(1).strip()] = int(mm.group(2))
            free = pages.get("Pages free", 0) + pages.get("Pages speculative", 0)
            active = pages.get("Pages active", 0)
            inactive = pages.get("Pages inactive", 0)
            wired = pages.get("Pages wired down", 0)
            comp = pages.get("Pages occupied by compressor", 0)
            total = free + active + inactive + wired + comp
            if total:
                res["mem_pct"] = round((active + wired + comp) / total * 100, 1)
        except Exception:
            pass
        try:
            bt = run(["sysctl", "-n", "kern.boottime"])
            mm = re.search(r"sec\s*=\s*(\d+)", bt)
            if mm:
                res["uptime_h"] = round((time.time() - int(mm.group(1))) / 3600, 1)
        except Exception:
            pass
        # —— Linux 回退（sandbox 等）——
        if res["load1"] < 0 and os.path.exists("/proc/loadavg"):
            with open("/proc/loadavg") as f:
                res["load1"] = float(f.read().split()[0])
        if res["mem_pct"] < 0 and os.path.exists("/proc/meminfo"):
            mi = {}
            for line in open("/proc/meminfo"):
                k, v = line.split(":", 1); mi[k.strip()] = int(v.split()[0])
            tot, avail = mi.get("MemTotal", 0), mi.get("MemAvailable", 0)
            if tot:
                res["mem_pct"] = round((tot - avail) / tot * 100, 1)
        if res["uptime_h"] < 0 and os.path.exists("/proc/uptime"):
            with open("/proc/uptime") as f:
                res["uptime_h"] = round(float(f.read().split()[0]) / 3600, 1)
        res["ok"] = any(v >= 0 for k, v in res.items() if k in ("cpu_pct", "mem_pct", "load1", "uptime_h"))
        res["note"] = "" if res["ok"] else "本机命令不可用·需人工确认"
    except Exception:
        pass
    return res


def probe_credits():
    """WorkBuddy 积分余额（实读 ~/.workbuddy/workbuddy.db session_usage）。
    取最近会话 used/size 算余额；累计会话数。无库则诚实降级。"""
    db = os.path.expanduser("~/.workbuddy/workbuddy.db")
    out = {"ok": False, "balance": -1, "used": -1, "size": -1, "sessions": -1, "note": "需人工确认"}
    try:
        import sqlite3
        if not os.path.exists(db):
            return out
        c = sqlite3.connect(db); cur = c.cursor()
        cur.execute("SELECT SUM(used), SUM(size), COUNT(*) FROM session_usage")
        s_used, s_size, n = cur.fetchone()
        c.close()
        # ⚠️ 用全会话 SUM 聚合口径（累计消耗），不用最新单条会话（新鲜会话 used=0 会假报 100% 健康）
        out["used"] = int(s_used or 0); out["size"] = int(s_size or 0)
        out["balance"] = out["size"] - out["used"]
        out["sessions"] = int(n or 0)
        out["ok"] = True; out["note"] = ""
    except Exception:
        pass
    return out


def probe_mcp_activity():
    """各 MCP 接口活跃度（代理指标·非计费真值·待采集）。
    实读 ~/.workbuddy/usage-log.json 的 mcps 字段：每个 MCP 的 recentDates(调用日期列表)/lastUsedDate/firstSeenDate。
    返回 {mcp_id: {active_total, active_7d, last_used, first_seen}}。无源则空 dict（诚实降级）。"""
    import json as _json
    from datetime import date as _date
    p = os.path.expanduser("~/.workbuddy/usage-log.json")
    out = {}
    try:
        if not os.path.exists(p):
            return out
        d = _json.load(open(p, encoding="utf-8"))
        mcps = d.get("mcps", {}) or {}
        today = _date.today()
        for mid, m in mcps.items():
            dates = []
            for x in (m.get("recentDates") or []):
                try:
                    dates.append(_date.fromisoformat(x))
                except Exception:
                    pass
            active_total = len(dates)
            active_7d = sum(1 for x in dates if (today - x).days <= 7)
            out[mid] = {
                "active_total": active_total,
                "active_7d": active_7d,
                "last_used": m.get("lastUsedDate", ""),
                "first_seen": m.get("firstSeenDate", ""),
            }
    except Exception:
        pass
    return out


def probe_lawkb_today_count():
    """知识飞轮今日新增 md 数（实扫 06-沉淀 mtime == 今日）。"""
    base = os.path.expanduser("~/Documents/LawKB/知识飞轮系统/06-沉淀")
    if not exists(base):
        return 0
    n = 0
    today = datetime.date.today().strftime("%Y-%m-%d")
    for p in glob.glob(os.path.join(base, "**", "*.md"), recursive=True):
        try:
            if datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d") == today:
                n += 1
        except Exception:
            pass
    return n


def probe_metacognition():
    """实扫元认知耦合度（2026-09-19 新增 · 经老强特批接入 scorecard 薄壳实时渲染）：
    决策卡↔轨迹卡双链(耦合度①) + 决策卡引用 HOW-I-THINK(耦合度②) + 纠错捕获(verdict=结论对但理由错)。
    真源：LawKB/知识飞轮系统 04-LOG/决策日志 + 02-提炼/经验卡片/思维轨迹 + 06-沉淀/HOW-I-THINK.md。
    不虚构：扫不到如实降级（对齐 R-LN-114）。"""
    KB = os.path.expanduser("~/Documents/LawKB/知识飞轮系统")
    DEC = os.path.join(KB, "04-LOG", "决策日志")
    TRAJ = os.path.join(KB, "02-提炼", "经验卡片", "思维轨迹")
    HOW = os.path.join(KB, "06-沉淀", "HOW-I-THINK.md")
    SKIP = {"_模板_决策卡.md", "_索引.md", "模板.md", "README.md", "索引.md"}

    def dec_files():
        out = []
        if exists(DEC):
            for f in sorted(os.listdir(DEC)):
                if f.endswith(".md") and f not in SKIP:
                    out.append(f)
        return out

    def traj_files():
        out = []
        if exists(TRAJ):
            for f in sorted(os.listdir(TRAJ)):
                if f.endswith(".md") and (f.startswith("轨迹卡-") or f.startswith("思维轨迹-")) and f not in SKIP:
                    out.append(f)
        return out

    decs = dec_files()
    dec_total = len(decs)
    c1 = c2 = err = 0
    for f in decs:
        t = read_text(os.path.join(DEC, f))
        if re.search(r"\[\[(?:轨迹卡|思维轨迹)", t):
            c1 += 1
        if "[[HOW-I-THINK" in t:
            c2 += 1
        if re.search(r"verdict\s*[:=]\s*结论对但理由错", t) or re.search(r"\*\*判定\*\*\s*[:：]\s*结论对但理由错", t):
            err += 1
    traj_all = traj_files()
    traj_real = len([f for f in traj_all if not f.startswith("轨迹卡-模板")])
    traj_total = len(traj_all)
    how_total = 0
    if exists(HOW):
        for line in read_text(HOW).splitlines():
            if line.startswith("## ") or line.startswith("### "):
                how_total += 1
    c1_pct = round(c1 / dec_total * 100, 1) if dec_total else 0
    c2_pct = round(c2 / dec_total * 100, 1) if dec_total else 0
    return {
        "decision_total": dec_total,
        "traj_total": traj_total,
        "traj_real": traj_real,
        "how_total": how_total,
        "c1_linked": c1,
        "c2_linked": c2,
        "c1_pct": c1_pct,
        "c2_pct": c2_pct,
        "error_capture": err,
        "scanned_at": NOW,
    }


# ----------------------------------------------------------------------------
# 分身消费卡族分布（实扫 LawKB 知识飞轮 · 17 族 · 含真实引用代理 + 运行时埋点真值接口）
# ----------------------------------------------------------------------------
CARD_FAM_ORDER = [
    "裁判规则库(R-*)", "案由路由卡", "证据规则卡", "通用裁判规则卡", "实务规则卡",
    "文书范式卡", "庭审主持卡", "请求权基础卡", "裁量尺度卡", "赔偿计算卡",
    "审判要件卡", "类案检索报告卡族", "条号位移卡族", "要件映射卡",
    "慈善合规卡", "合规治理卡", "合同实务卡", "人伤医疗卡", "商事纠纷卡",
    "劳动人事卡", "建设工程卡", "案例规则卡", "决策卡", "思维轨迹卡",
    "经验卡片", "HOW-I-THINK",
]
# 卡片扫描源（知识飞轮内被分身消费的卡族库存真源）
CARD_SCAN_DIRS = [
    "06-沉淀/裁判规则库",
    "06-沉淀/类案检索报告卡族",
    "06-沉淀/条号位移卡族",
    "02-提炼/经验卡片",
    "03-连接/概念页",
]
# 运行时埋点真值接口：分身各模块消费卡时写一行 JSONL {"card": "<basename>", "family": "<族>"}
# 存在且非空则优先作为精确消费真值；否则回退 backlink 代理（见 probe_card_references）。
REF_TELEMETRY_LOG = os.path.expanduser("~/.workbuddy/metrics/card_consumption.jsonl")


def _classify_card_family(rel):
    """把 LawKB 知识飞轮内某 md 文件（rel = 相对知识飞轮系统的路径）归类到 17 卡族之一。"""
    name = os.path.basename(rel)
    low = name.lower()
    if rel.startswith("02-提炼/经验卡片/思维轨迹") or "思维轨迹" in name or "轨迹卡" in name:
        return "思维轨迹卡"
    if "审判要件" in name: return "审判要件卡"
    if "文书范式" in name: return "文书范式卡"
    if "裁量尺度" in name: return "裁量尺度卡"
    if "请求权基础" in name: return "请求权基础卡"
    if "类案检索报告" in name: return "类案检索报告卡族"
    if "条号位移" in name: return "条号位移卡族"
    if "要件映射" in name: return "要件映射卡"
    if "how-i-think" in low: return "HOW-I-THINK"
    if rel.startswith("06-沉淀/裁判规则库/"): return "裁判规则库(R-*)"
    if rel.startswith("06-沉淀/类案检索报告卡族/"): return "类案检索报告卡族"
    if rel.startswith("06-沉淀/条号位移卡族/"): return "条号位移卡族"
    if rel.startswith("02-提炼/经验卡片/"): return "经验卡片"
    if rel.startswith("03-连接/概念页/"):
        if name.startswith("R-AY-"): return "案由路由卡"
        if name.startswith("R-CF-"): return "慈善合规卡"
        if name.startswith("R-HG-"): return "合规治理卡"
        if name.startswith("R-HT-"): return "合同实务卡"
        if name.startswith("R-PI-"): return "人伤医疗卡"
        if name.startswith("R-PR-"): return "庭审主持卡"
        if name.startswith("R-LN-"): return "文书范式卡"
        if name.startswith("R-SH-"): return "商事纠纷卡"
        if name.startswith("R-LD-"): return "劳动人事卡"
        if name.startswith("R-LE-"): return "证据规则卡"
        if name.startswith("R-JG-"): return "建设工程卡"
        if name.startswith("R-CASE-"): return "案例规则卡"
        if name.startswith("R-"): return "通用裁判规则卡"
        if name.startswith("DEC-") or name.startswith("决策"): return "决策卡"
    return None


def _collect_cards():
    """返回 [(basename_lower(去扩展名), family), ...]，即知识飞轮内全部被分身可消费的卡（库存全集）。"""
    KB = os.path.expanduser("~/Documents/LawKB/知识飞轮系统")
    cards = []
    for d in CARD_SCAN_DIRS:
        root = os.path.join(KB, d)
        if not exists(root):
            continue
        for dp, _, fns in os.walk(root):
            for fn in fns:
                if not fn.lower().endswith(".md"):
                    continue
                rel = os.path.relpath(os.path.join(dp, fn), KB)
                fam = _classify_card_family(rel)
                if fam:
                    cards.append((os.path.splitext(fn)[0].lower(), fam))
    return cards


def probe_card_families():
    """实扫「分身消费卡族·库存分布」：按《07-卡族总索引》17 族归类计数（全库存，参照口径）。"""
    counts = {f: 0 for f in CARD_FAM_ORDER}
    uncategorized = 0
    total = 0
    try:
        for _, fam in _collect_cards():
            counts[fam] += 1
            total += 1
    except Exception:
        pass
    dist = [[f, counts[f]] for f in CARD_FAM_ORDER if counts[f] > 0]
    return {
        "dist": dist,
        "family_count": len(dist),
        "total_classified": sum(counts.values()),
        "uncategorized": 0,
        "total_scanned": total,
        "scanned_at": NOW,
    }


def _load_runtime_refs():
    """读取运行时埋点真值（JSONL：每行 {"card": basename, "family": 族}）。无则返回空 dict。"""
    refs = {}
    if not exists(REF_TELEMETRY_LOG):
        return refs
    try:
        with open(REF_TELEMETRY_LOG, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                c = (d.get("card") or "").strip().lower()
                if c:
                    refs[c] = d.get("family") or refs.get(c)
    except Exception:
        pass
    return refs


def probe_card_references():
    """实扫「分身消费卡族·真实引用分布」：只统计被分身各模块真实引用过的卡（精确消费口径）。
    真实引用信号优先级：
      1) 运行时埋点真值（REF_TELEMETRY_LOG 存在且非空）→ 精确消费事件聚合；
    2) 回退 Obsidian 双向链接入度（backlink）：仅统计被「分身运行模块」真实引用过的卡——
       消费源 = 用户级技能(161) + 决策日志 + 经验卡片 + 03-连接/概念页中的非卡案件笔记/报告；
       排除卡库自身的目录/索引(MOC)页互链（否则近 100% 被引、失去分辨力）。卡 basename 在消费源中
       被 `[[链接]]` 引用 ≥1 次，即视为被分身系统真实消费。
    全部 try/except 包裹，不凭记忆填数（对齐 R-LN-114）。UI 明示数据源（runtime / backlink）。"""
    cards = []
    try:
        cards = _collect_cards()
    except Exception:
        pass
    stock_basenames = set(b for b, _ in cards)
    stock_total = len(cards)

    # 1) 运行时埋点真值优先
    runtime = _load_runtime_refs()
    if runtime:
        counts = {f: 0 for f in CARD_FAM_ORDER}
        valid = 0
        for c, fam in runtime.items():
            if c in stock_basenames and fam in counts:
                counts[fam] += 1
                valid += 1
        dist = [[f, counts[f]] for f in CARD_FAM_ORDER if counts[f] > 0]
        return {
            "dist": dist, "family_count": len(dist), "total_referenced": valid,
            "total_stock": stock_total,
            "ref_rate": round(valid / stock_total * 100, 1) if stock_total else 0,
            "source": "runtime埋点真值", "scanned_at": NOW,
        }

    # 2) backlink 代理（精确消费口径）：只统计被「分身运行模块」真实引用过的卡。
    #    消费源 = 用户级技能(161) + 决策日志 + 经验卡片 + 03-连接/概念页中的「非卡」案件笔记/报告；
    #    排除卡库自身的目录/索引(MOC)页互链（否则几乎 100% 被引，失去分辨力）。
    ref_basenames = set()
    FLY = os.path.expanduser("~/Documents/LawKB/知识飞轮系统")
    SKILLS = os.path.expanduser("~/.workbuddy/skills")
    SRC_MODULE_DIRS = [
        SKILLS,
        os.path.join(FLY, "04-LOG", "决策日志"),
        os.path.join(FLY, "02-提炼", "经验卡片"),
    ]
    SRC_MIXED_DIR = os.path.join(FLY, "03-连接", "概念页")  # 卡与案件笔记混放，仅取非卡文件为消费源

    def _harvest(src):
        for m in re.finditer(r"\[\[([^\[\]|#]+)\]", src):
            seg = m.group(1).strip().split("/")[-1].strip().lower()
            if seg:
                ref_basenames.add(seg)

    for sr in SRC_MODULE_DIRS:
        if not exists(sr):
            continue
        for dp, _, fns in os.walk(sr):
            for fn in fns:
                if not fn.lower().endswith(".md"):
                    continue
                try:
                    _harvest(read_text(os.path.join(dp, fn)))
                except Exception:
                    continue
    if exists(SRC_MIXED_DIR):
        for dp, _, fns in os.walk(SRC_MIXED_DIR):
            for fn in fns:
                if not fn.lower().endswith(".md"):
                    continue
                rel = os.path.relpath(os.path.join(dp, fn), FLY)
                if _classify_card_family(rel):
                    continue  # 跳过卡库自身（索引/MOC/卡页），仅案件笔记/报告作为消费源
                try:
                    _harvest(read_text(os.path.join(dp, fn)))
                except Exception:
                    continue

    counts = {f: 0 for f in CARD_FAM_ORDER}
    for bn, fam in cards:
        if bn in ref_basenames:
            counts[fam] += 1
    dist = [[f, counts[f]] for f in CARD_FAM_ORDER if counts[f] > 0]
    total_ref = sum(counts.values())
    return {
        "dist": dist, "family_count": len(dist), "total_referenced": total_ref,
        "total_stock": stock_total,
        "ref_rate": round(total_ref / stock_total * 100, 1) if stock_total else 0,
        "source": "backlink(分身运行模块引用)代理·非运行时埋点", "scanned_at": NOW,
    }


# ----------------------------------------------------------------------------
# 各屏评分（实源驱动；无探测则诚实降级）
# ----------------------------------------------------------------------------
def build_screens(probes, registry=None):
    four, phases, vl, gaps, sec, gate, deploylog = probes
    daemon = gate["daemon_running"]
    vl_items = vl["items"]
    vl_filled = sum(1 for it in vl_items if it["target_ver"]) / len(vl_items) * 100 if vl_items else 0
    drift_n = sum(1 for it in vl_items if it.get("drift"))
    l1_enc = four["l1"]["status"].startswith("✅")
    infer_ok = four["inference"]["status"].startswith("✅")
    deploy_done = sum(1 for x in phases if x["status"].startswith("✅")) / len(phases) * 100 if phases else 0
    gap_closed = sum(1 for x in gaps["items"] if x["status"].startswith("✅")) / len(gaps["items"]) * 100 if gaps["items"] else 0
    kb_n, kb_ev = probe_lawkb_count()
    disk_pct = probe_disk_usage(SRC)
    port9655 = probe_http_up("http://127.0.0.1:9655/", 2)
    deploy_n = len(deploylog["records"])
    kb_bd = probe_lawkb_breakdown(SRC)
    host = probe_host_metrics()
    credits = probe_credits()
    mcp_act = probe_mcp_activity()
    fly_today = probe_lawkb_today_count()
    skills_center = scan_skills_center()
    sharedhub = scan_shared_hub()
    metacog = probe_metacognition()
    cardfam = probe_card_families()
    cardref = probe_card_references()

    ctx = dict(four=four, vl=vl, gaps=gaps, sec=sec, gate=gate, deploylog=deploylog,
               disk_pct=disk_pct, port9655=port9655, kb_n=kb_n, kb_bd=kb_bd,
               host=host, credits=credits, mcp_act=mcp_act, fly_today=fly_today, skills_center=skills_center,
               sharedhub=sharedhub, metacog=metacog, cardfam=cardfam, cardref=cardref)

    screens = []
    for (key, name, url, dot, lawFirm, weight, scored) in SCREENS_DEF:
        if not scored:
            # 容器 / 外部链接：不纳入评分
            screens.append(_screen_obj(key, name, url, dot, lawFirm, weight, False, None, None, [], None, None, "监控位 · 不纳入评分"))
            continue
        if lawFirm:
            sc = LAWFIRM_9360_SCORE.get(key, 60.0)
            screens.append(_screen_obj(key, name, url, dot, lawFirm, weight, True, round(sc, 1),
                                       mk_six(round(sc, 1)), [], False, None,
                                       "9360 真源业务屏 · 全屏显示"))
            continue
        # 监控屏：按实源派生
        sc, over, kpis, flag, risk = _screen_metric(key, dict(
            daemon=daemon, vl_filled=vl_filled, drift_n=drift_n, l1_enc=l1_enc,
            infer_ok=infer_ok, deploy_done=deploy_done, gap_closed=gap_closed,
            kb_n=kb_n, kb_ev=kb_ev, disk_pct=disk_pct, port9655=port9655,
            host=host, credits=credits,
            deploy_n=deploy_n, vl_total=len(vl_items), vl_filled_n=sum(1 for it in vl_items if it["target_ver"]),
            gaps_items=gaps["items"], skills_center=skills_center, sharedhub=sharedhub,
        ))
        # D7/D8：用真实 6 维标签驱动评分环六维条（覆盖通用 six 的泛化标签）
        six_dims = None
        if key == "agenthub":
            sm = skills_center["agent_summary"]; na = sm["new_avg"]
            six_dims = [("版本治理", sm["avg_vs"]), ("迭代活跃度", sm["avg_it"]),
                        ("系统作用度", na["role"]), ("运行健康", na["health"]),
                        ("审计合规", na["compliance"]), ("文档完备", na["doc"])]
        elif key == "workflowhub":
            sm = skills_center["wf_summary"]; na = sm["new_avg"]
            six_dims = [("版本治理", sm["avg_vs"]), ("迭代活跃度", sm["avg_it"]),
                        ("流程覆盖度", na["coverage"]), ("执行效能", na["exec"]),
                        ("审计监控", na["compliance"]), ("复用度", na["reuse"])]
        elif key == "sharedhub":
            h = ctx["sharedhub"]
            six_dims = [("协议治理", h["gov"]), ("迭代活跃度", h["iter"]),
                        ("覆盖完备度", h["cov"]), ("运行健康", h["health"]),
                        ("审计合规", h["compliance"]), ("文档完备", h["doc"])]
        gaps_items = gaps["items"] if key == "conflict" else None
        screens.append(_screen_obj(key, name, url, dot, lawFirm, weight, True, round(sc, 1),
                                   mk_six(round(sc, 1), **over), kpis, flag, None, risk,
                                   gaps=gaps_items, panels=panels_for(key, ctx), sixDims=six_dims,
                                   metacog=ctx["metacog"]))
    return screens, sharedhub


def _screen_obj(key, name, url, dot, lawFirm, weight, scored, score, six, kpis, flag, risk, note="", gaps=None, panels=None, sixDims=None, metacog=None):
    return {
        "key": key, "name": name, "cno": _cno_of(key), "url": url, "dot": dot,
        "lawFirm": lawFirm, "weight": weight, "scoring": scored,
        "score": score, "six": six, "kpis": kpis, "gaps": gaps, "panels": panels,
        "sixDims": sixDims, "metacog": metacog,
        "updated": NOW if not lawFirm else "2026-09-18(9360真源)",
        "flag": flag, "risk": risk or note,
    }


_CNO_MAP = {k: v for (k, v, *_ ) in []}
def _cno_of(key):
    for (k, name, url, dot, lawFirm, weight, scored) in SCREENS_DEF:
        if k == key:
            # cno 来自 rbac.js 体系；此处硬编码映射保持与门户一致
            return {"home": "C0", "ev": "C1", "decision": "C2", "flywheel": "C3",
                    "clm": "C4", "xiaode": "C5", "mock": "C6", "contractlifecycle": "C7",
                    "lti": "C8", "governance": "C9", "credits": "D1", "conflict": "D2",                     "cloud": "D3",
                    "mindmodel": "D4", "permcenter": "D5", "d6permcenter": "D6",
                    "agenthub": "D7", "workflowhub": "D8", "sharedhub": "D9"}.get(key, "")
    return ""


def _screen_metric(key, m):
    if key == "ev":  # 车机驾驶舱 — 只反映 9655 驾驶舱本体健康，解耦 LTI 门禁 daemon（方案A）
        # 门户可达（port9655，由 launchd KeepAlive 保活）是驾驶舱本体在线的硬指标；
        # LTI 门禁守护进程（lti-gate-daemon）与 9655 无关，改为并列状态子卡片，不再作为满分开关。
        host = m.get("host") or {}
        cpu = host.get("cpu_pct", -1)
        mem = host.get("mem_pct", -1)
        overload = (isinstance(cpu, (int, float)) and cpu > 85) or (isinstance(mem, (int, float)) and mem > 90)
        if m["port9655"]:
            sc = 88.0 if overload else 100.0   # 门户在线即本体健康；主机过载轻微扣分
        else:
            sc = 35.0  # 门户不可达 = 驾驶舱本体挂了（严重，但区别于门禁停）
        kpis = [
            ["9655 门户", "✅ HTTP 200" if m["port9655"] else "⚠️ 不可达"],
            ["LTI 门禁守护进程", ("✅ 运行中" if m["daemon"] else "🔄 未启动") + "（独立状态·不计入本屏评分）"],
            ["主机负载", "CPU {0}% · 内存 {1}%".format(cpu, mem) if cpu >= 0 and mem >= 0 else "—"],
        ]
        return sc, {}, kpis, (not m["port9655"]), "车机驾驶舱本体实时状态（门户可达 + 主机健康）；LTI 门禁状态仅作并列展示，不再作为满分开关"
    if key == "decision":  # 版本基线
        sc = m["vl_filled"]
        return sc, {}, [["版本锁回填", "{0}/{1}".format(m["vl_filled_n"], m["vl_total"])],
                         ["实测漂移", "{0} 项⚠️".format(m["drift_n"]) if m["drift_n"] else "0 项✅"]], \
               m["drift_n"] > 0, "版本锁实地探测 vs 总体方案快照"
    if key == "flywheel":  # 知识飞轮舱
        cov = min(100.0, m["kb_n"] / 8.0) if m["kb_n"] else 0.0  # 800+ 卡为满
        sc = cov
        return sc, {"coverage": cov}, [["卡库规模", "{0} 个 md".format(m["kb_n"])],
                                       ["覆盖", "{0:.0f}%".format(cov)]], \
               m["kb_n"] == 0, "知识飞轮卡库规模与覆盖"
    if key == "lti":  # 门禁运行
        sc = 60.0 if m["daemon"] else 30.0
        return sc, {"compliance": 45.0 if m["daemon"] else 30.0}, \
               [["门禁守护进程", "✅ 运行中" if m["daemon"] else "🔄 未启动"],
                ["REJECT 闭环", "⚠️ 待试点回填"]], \
               not m["daemon"], "LTI 五维 QC 门禁真探活"
    if key == "credits":  # 积分监测中台 —— 评分环用 WorkBuddy 积分余额率（真值），不再用磁盘分冒充
        cr = m.get("credits", {}) or {}
        bal = cr.get("balance", -1); size = cr.get("size", -1)
        if size and size > 0 and bal >= 0:
            rate = bal / float(size)
            sc = round(rate * 100.0, 1)
            flag = rate < 0.3
            risk = "WorkBuddy 积分余额率 {0:.1f}%（临界预警）".format(sc) if flag else "WorkBuddy 积分余额率 {0:.1f}%".format(sc)
        else:
            sc = 50.0; flag = True; risk = "积分数据需人工确认"
        return sc, {}, [["积分余额率", "{0:.1f}%".format(sc)],
                         ["余额/容量", "{0}/{1}".format(bal, size) if bal >= 0 else "需确认"]], \
               flag, risk
    if key == "conflict":  # 配置冲突
        sc = 85.0 if m["gap_closed"] >= 80 else 60.0
        return sc, {}, [["缺口闭环", "{0:.0f}%".format(m["gap_closed"])],
                         ["架构层一致", "✅" if m["infer_ok"] else "⚠️"]], \
               False, "配置一致性与缺口闭环度"
    if key == "mindmodel":  # 心智模型中台
        sc = 80.0 if m["infer_ok"] else 45.0
        return sc, {"health": 70.0 if m["infer_ok"] else 40.0}, \
               [["推理层 M1", "✅ 就绪" if m["infer_ok"] else "🔄 待校验"],
                ["网络策略", "allow_external"]], \
               not m["infer_ok"], "推理层与模型可用性"
    if key == "permcenter":  # 访问控制
        sc = 90.0 if m["l1_enc"] else 50.0
        return sc, {"compliance": 95.0 if m["l1_enc"] else 50.0}, \
               [["L1 密文封装", "✅ 已加密" if m["l1_enc"] else "🔄 待加密"],
                ["role key", "macOS 钥匙串"]], \
               not m["l1_enc"], "L1 人格层加密与访问控制"
    if key == "d6permcenter":  # 权限调用中台
        sc = 80.0 if m["deploy_n"] > 0 else 40.0
        return sc, {}, [["部署记录", "{0} 份".format(m["deploy_n"])],
                         ["审计轨迹", "06-部署记录"]], \
               m["deploy_n"] == 0, "部署记录与权限调用留存"
    if key == "agenthub":  # 智能体中台（D7）
        sm = m["skills_center"]["agent_summary"]
        na = sm["new_avg"]
        sc = sm["composite"]
        return sc, {}, [["智能体总数", str(int(sm["n"]))],
                        ["版本治理均分", str(int(sm["avg_vs"]))],
                        ["迭代活跃度均分", str(int(sm["avg_it"]))],
                        ["系统作用度均分", str(int(na["role"]))],
                        ["运行健康均分", str(int(na["health"]))],
                        ["审计合规均分", str(int(na["compliance"]))],
                        ["文档完备均分", str(int(na["doc"]))],
                        ["🟢健康基线", str(int(sm["healthy"]))]], \
               False, "智能体中台·{0} 个具名智能体·6 维实扫（版本/迭代=真实值，作用度/健康/合规/文档=SKILL.md 静态估算）".format(sm["n"])
    if key == "workflowhub":  # 工作流中台（D8）
        sm = m["skills_center"]["wf_summary"]
        na = sm["new_avg"]
        sc = sm["composite"]
        return sc, {}, [["工作流总数", str(int(sm["n"]))],
                        ["版本治理均分", str(int(sm["avg_vs"]))],
                        ["迭代活跃度均分", str(int(sm["avg_it"]))],
                        ["流程覆盖度均分", str(int(na["coverage"]))],
                        ["执行效能均分", str(int(na["exec"]))],
                        ["审计监控均分", str(int(na["compliance"]))],
                        ["复用度均分", str(int(na["reuse"]))],
                        ["无版本", str(int(sm["nov"]))],
                        ["🟢健康基线", str(int(sm["healthy"]))]], \
               sm["nov"] > 0, "工作流中台·{0} 条流水线·6 维实扫（版本/迭代=真实值，覆盖度/效能/监控/复用=SKILL.md 静态估算）".format(sm["n"])
    if key == "sharedhub":  # 共享中枢中台（D9）
        h = m["sharedhub"]
        sc = h["composite"]
        return sc, {}, [["卡总量", str(int(h["total_cards"]))],
                        ["子库数", str(int(h["sub_count"]))],
                        ["协议治理分", str(int(h["gov"]))],
                        ["迭代活跃度分", str(int(h["iter"]))],
                        ["覆盖完备度分", str(int(h["cov"]))],
                        ["运行健康分", str(int(h["health"]))],
                        ["审计合规分", str(int(h["compliance"]))],
                        ["文档完备分", str(int(h["doc"]))],
                        ["最近日志", ("{0}天前".format(h["last_log_days"]) if h["last_log_days"] >= 0 else "需确认")],
                        ["门禁调用量", str(int(h.get("grill_gate", {}).get("invoke", 0)))],
                        ["门禁对齐率", "{0}%".format(h.get("grill_gate", {}).get("align_rate", 0))],
                        ["门禁已声明接线", str(int(h.get("grill_gate", {}).get("declared", 0)))],
                        ["门禁实测触发", str(len(h.get("grill_gate", {}).get("callers", [])))]], \
               h["key_leak"] > 0, "共享中枢中台·{0} 子库 / {1} 卡 · 6 维实扫（协议/迭代/覆盖=真实值，健康/合规/文档=frontmatter 静态估算）".format(h["sub_count"], h["total_cards"])
    return 60.0, {}, [["状态", "需人工确认"]], True, "未映射探针"


def probe_lawkb_breakdown(base_dir):
    """知识体分布：06-沉淀 各子目录 md 实扫计数（真实，非凭记忆）。"""
    base = os.path.expanduser("~/Documents/LawKB/知识飞轮系统/06-沉淀")
    out = {}
    if not exists(base):
        return out
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        if os.path.isdir(d):
            n = len(glob.glob(os.path.join(d, "**", "*.md"), recursive=True))
            out[name] = n
    return out


def panels_for(key, ctx):
    """把实扫探针数据转为 9360 风格面板（KPI 卡 / 状态模块卡），零虚构。
    仅使用已在 probes 中真实探测到的数据：四层架构 / 版本锁 / 缺口 / 门禁 / 磁盘 / 卡库 / 部署记录。"""
    four = ctx["four"]; vl = ctx["vl"]; gaps = ctx["gaps"]; sec = ctx["sec"]
    gate = ctx["gate"]; dl = ctx["deploylog"]; disk_pct = ctx["disk_pct"]
    port9655 = ctx["port9655"]; kb_n = ctx["kb_n"]; kb_bd = ctx["kb_bd"]
    P = []

    def lyr_mod(name, d):
        return {"name": name, "status": "active" if d["status"].startswith("✅") else "silent",
                "detail": d.get("detail", ""), "stats": [["证据", (d.get("evidence", "—") or "")[:16]]]}

    if key == "ev":
        h = ctx.get("host", {})
        def _hcls(v, hi):
            if v is None or v < 0: return "silent"
            if v >= hi: return "alert"
            if v >= hi * 0.75: return "warn"
            return "active"
        def _hv(v, unit=""):
            return ("{0}{1}".format(v, unit) if (v is not None and v >= 0) else "需人工确认")
        mods_host = [
            {"name": "CPU 占用", "status": _hcls(h.get("cpu_pct"), 85),
             "detail": ("实采 {0}%".format(h.get("cpu_pct")) if h.get("cpu_pct", -1) >= 0 else "本机命令不可用·需人工确认"),
             "stats": [["CPU", _hv(h.get("cpu_pct"), "%")]]},
            {"name": "内存占用", "status": _hcls(h.get("mem_pct"), 90),
             "detail": ("实采 {0}%".format(h.get("mem_pct")) if h.get("mem_pct", -1) >= 0 else "需人工确认"),
             "stats": [["MEM", _hv(h.get("mem_pct"), "%")]]},
            {"name": "系统负载(1m)", "status": _hcls(h.get("load1"), 4),
             "detail": ("loadavg {0}".format(h.get("load1")) if h.get("load1", -1) >= 0 else "需人工确认"),
             "stats": [["LOAD", _hv(h.get("load1"))]]},
            {"name": "运行时长", "status": "active" if h.get("uptime_h", -1) >= 0 else "silent",
             "detail": ("{0} 小时".format(h.get("uptime_h")) if h.get("uptime_h", -1) >= 0 else "需人工确认"),
             "stats": [["UPTIME", _hv(h.get("uptime_h"), "h")]]},
        ]
        P.append({"title": "主机实时指标（实采 macOS/Linux）", "kind": "modules", "mods": mods_host})
        P.append({"title": "主机与门禁守护", "kind": "modules", "mods": [
            {"name": "LTI 门禁守护进程", "status": "active" if gate["daemon_running"] else "alert",
             "detail": gate["daemon_status"] + "；plist 已装=" + ("是" if gate["plist_installed"] else "否"),
             "stats": [["守护进程", "运行中" if gate["daemon_running"] else "未启动"],
                       ["plist", "已装" if gate["plist_installed"] else "缺"],
                       ["门禁版本", gate.get("lti_version", "—")], ["REJECT", "待回填"]]},
            {"name": "9655 门户服务", "status": "active" if port9655 else "alert",
             "detail": "http://127.0.0.1:9655/ " + ("HTTP 200 可达" if port9655 else "不可达"),
             "stats": [["端口", "9655"], ["绑定", "127.0.0.1"], ["状态", "200" if port9655 else "DOWN"]]},
        ]})
        if disk_pct >= 0:
            dcls = "alert" if disk_pct >= 90 else ("silent" if disk_pct >= 75 else "active")
            P.append({"title": "磁盘水位", "kind": "modules", "mods": [
                {"name": "单机密文版源目录", "status": dcls,
                 "detail": "源目录磁盘占用 {0}%".format(disk_pct), "pct": disk_pct,
                 "stats": [["占用", "{0}%".format(disk_pct)],
                           ["水位", "高" if disk_pct >= 90 else ("中" if disk_pct >= 75 else "低")]]}]})

    elif key == "decision":
        mods = []
        for it in vl["items"]:
            filled = bool(it.get("target_ver"))
            if it.get("drift"):
                stt = "alert"
            elif filled:
                stt = "active"
            else:
                stt = "silent"
            mods.append({"name": it["name"], "status": stt,
                         "detail": "快照版本 {0} → 实测 {1} {2}".format(
                             it.get("source_ver", "—"), it.get("target_ver", "—"), it.get("drift", "")),
                         "stats": [["优先级", it.get("priority", "—")],
                                   ["快照", it.get("source_ver", "—")],
                                   ["实测", it.get("target_ver", "—") or "待回填"]]})
        P.append({"title": "技能版本锁明细（实扫）", "kind": "modules", "mods": mods})

    elif key == "flywheel":
        mods = [{"name": sub, "status": "active" if n else "silent",
                 "detail": "{0} 个 md".format(n), "stats": [["md", n]]}
                for sub, n in kb_bd.items()]
        P.append({"title": "知识体分布（06-沉淀 实扫）", "kind": "modules", "mods": mods})
        P.append({"title": "卡库规模", "kind": "kpis", "rows": [
            ["文档总数", "{0} 个 md".format(kb_n)],
            ["覆盖度", "{0:.0f}%".format(min(100.0, kb_n / 8.0))],
            ["今日变更", "{0} 个".format(ctx.get("fly_today", 0))]]})

    elif key == "lti":
        qc = gate.get("qc_dimensions", [])
        P.append({"title": "门禁守护进程", "kind": "modules", "mods": [
            {"name": "LTI 门禁守护进程", "status": "active" if gate["daemon_running"] else "alert",
             "detail": gate["daemon_status"] + "；" + gate.get("gate_detail", ""),
             "stats": [["版本", gate.get("lti_version", "—")],
                       ["守护进程", "运行中" if gate["daemon_running"] else "未启动"],
                       ["plist", "已装" if gate["plist_installed"] else "缺"],
                       ["REJECT", "待回填"]]},
            {"name": "五维 QC 门禁", "status": "active",
             "detail": "R 法条真实 / L 法理逻辑 / C 一致性 / T 溯源 / P 程序；REJECT=0 才准交付。",
             "stats": [[d, "✓"] for d in qc]},
        ]})

    elif key == "credits":
        cr = ctx.get("credits", {})
        bal = cr.get("balance", -1); used = cr.get("used", -1); size = cr.get("size", -1); sess = cr.get("sessions", -1)
        bal_rate = "{0:.1f}%".format(bal / float(size) * 100) if (bal >= 0 and size and size > 0) else "—"
        mods_cr = [{"name": "积分余额（workbuddy.db 聚合·真值）", "status": "active" if bal >= 0 else "silent",
                     "detail": "workbuddy.db session_usage 实读；余额 = 容量 - 已用。",
                     "stats": [["余额", "{0}".format(bal) if bal >= 0 else "—"],
                               ["已用", "{0}".format(used) if used >= 0 else "—"],
                               ["容量", "{0}".format(size) if size >= 0 else "—"],
                               ["余额率", bal_rate],
                               ["会话数", "{0}".format(sess) if sess >= 0 else "—"]]}]
        P.append({"title": "WorkBuddy 积分余额（实读 ~/.workbuddy/workbuddy.db）", "kind": "modules", "mods": mods_cr})
        dcls = "alert" if disk_pct >= 90 else ("silent" if disk_pct >= 75 else "active")
        backups = glob.glob("/tmp/lawtwin_deploy_*")
        P.append({"title": "存储与备份（独立指标·不计入积分分）", "kind": "modules", "mods": [
            {"name": "源目录磁盘水位", "status": dcls,
             "detail": "源目录占用 {0}%".format(disk_pct) if disk_pct >= 0 else "需确认",
             "pct": disk_pct if disk_pct >= 0 else 0,
             "stats": [["占用", "{0}%".format(disk_pct) if disk_pct >= 0 else "—"]]},
            {"name": "备份基线", "status": "active" if backups else "silent",
             "detail": "备份基线目录 /tmp/lawtwin_deploy_*；按六-B 铁律部署前须建。",
             "stats": [["基线", "{0} 个".format(len(backups)) if backups else "缺"]]},
        ]})
        # ⚠️ 各 MCP 接口积分（代理指标·非计费真值·待采集）
        mcp_act = ctx.get("mcp_act", {}) or {}
        if mcp_act:
            mods_mcp = []
            for mid, a in sorted(mcp_act.items()):
                mods_mcp.append({"name": mid, "status": "active" if a["active_7d"] > 0 else "silent",
                                 "detail": "代理指标（调用活跃度）·非接口级计费真值·待采集；最近使用 {0}".format(a["last_used"] or "—"),
                                 "stats": [["累计活跃天数", "{0}".format(a["active_total"])],
                                           ["近7日活跃", "{0}".format(a["active_7d"])]]})
            P.append({"title": "各 MCP 接口积分（⚠️ 代理指标·非计费真值·待采集）", "kind": "modules", "mods": mods_mcp})

    elif key == "conflict":
        mods = []
        for g in gaps["items"]:
            if "已消除" in g["status"]:
                stt = "active"
            elif "部分" in g["status"] or "⚠️" in g["status"]:
                stt = "alert"
            else:
                stt = "silent"
            mods.append({"name": g["id"] + " " + g["name"], "status": stt,
                         "detail": g["status"],
                         "stats": [["状态", g["status"].split("（")[0]]]})
        P.append({"title": "配置缺口实扫（G1–G6）", "kind": "modules", "mods": mods})

    elif key == "mindmodel":
        f = four
        P.append({"title": "分身四层架构健康", "kind": "modules", "mods": [
            lyr_mod("L0 内核层（路由+双基座）", f["l0"]),
            lyr_mod("L1 人格层（AES-256 密文）", f["l1"]),
            lyr_mod("L2 数据层（本地知识+M2）", f["l2"]),
            lyr_mod("推理层 M1（lawtwin-infer）", f["inference"]),
        ]})

    elif key == "permcenter":
        l1 = four["l1"]; km = sec.get("key_mgmt", {})
        P.append({"title": "访问控制与密钥管理", "kind": "modules", "mods": [
            {"name": "L1 人格层加密", "status": "active" if l1["status"].startswith("✅") else "silent",
             "detail": l1.get("detail", "") + "；round-trip 待人工确认。",
             "stats": [["状态", l1["status"]]]},
            {"name": "密钥管理", "status": "silent",
             "detail": km.get("detail", "按 api_key_env 注入；L1 密码存 macOS 钥匙串；跨所重授权不打印明文。"),
             "stats": [["管理", "钥匙串/环境变量"]]},
            {"name": "role key 持有", "status": "active",
             "detail": "L1 密文封装明文密钥存 macOS 钥匙串（role key 按角色隔离）。",
             "stats": [["位置", "macOS 钥匙串"]]},
        ]})

    elif key == "d6permcenter":
        recs = dl["records"][:8]
        mods = [{"name": r["file"], "status": "active", "detail": "最近修改 " + r["mtime"],
                 "stats": [["时间", r["mtime"]]]} for r in recs]
        P.append({"title": "部署记录留存（06-部署记录 实扫）", "kind": "modules", "mods": mods})

    elif key == "agenthub":  # 智能体中台（D7 · Harvey 式）
        sc = ctx["skills_center"]; sm = sc["agent_summary"]; na = sm["new_avg"]
        P.append({"title": "智能体中台 KPI（实扫 6 维 · 对标 Harvey）", "kind": "kpis", "rows": [
            ["智能体总数", str(int(sm["n"]))],
            ["版本治理均分", str(int(sm["avg_vs"]))],
            ["迭代活跃度均分", str(int(sm["avg_it"]))],
            ["系统作用度均分", str(int(na["role"]))],
            ["运行健康均分", str(int(na["health"]))],
            ["审计合规均分", str(int(na["compliance"]))],
            ["文档完备均分", str(int(na["doc"]))],
            ["🟢健康基线", str(int(sm["healthy"]))],
            ["六维加权基线", str(sm["composite"])],
        ]})
        mods = [{"name": a["name"], "status": _health_cls(a["health"]),
                 "detail": (a["role"] or ""),
                 "stats": [["版本", a["version"] or "—"],
                           ["迭代", "{0}天前".format(a["iter_days"]) if a["iter_days"] >= 0 else "需确认"],
                           ["版本治理", str(a["ver_score"])],
                           ["迭代活跃度", str(a["iter_score"])],
                           ["系统作用度", str(a["dims"]["role"])],
                           ["运行健康", str(a["dims"]["health"])],
                           ["审计合规", str(a["dims"]["compliance"])],
                           ["文档完备", str(a["dims"]["doc"])],
                           ["健康", a["health"]]]} for a in sc["agents"]]
        P.append({"title": "智能体清单（6 维 · Harvey 式）", "kind": "modules", "mods": mods})

    elif key == "workflowhub":  # 工作流中台（D8 · Harvey 式）
        sc = ctx["skills_center"]; sm = sc["wf_summary"]; na = sm["new_avg"]
        P.append({"title": "工作流中台 KPI（实扫 6 维 · 对标 Harvey）", "kind": "kpis", "rows": [
            ["工作流总数", str(int(sm["n"]))],
            ["版本治理均分", str(int(sm["avg_vs"]))],
            ["迭代活跃度均分", str(int(sm["avg_it"]))],
            ["流程覆盖度均分", str(int(na["coverage"]))],
            ["执行效能均分", str(int(na["exec"]))],
            ["审计监控均分", str(int(na["compliance"]))],
            ["复用度均分", str(int(na["reuse"]))],
            ["无版本", str(int(sm["nov"]))],
            ["🟢健康基线", str(int(sm["healthy"]))],
            ["六维加权基线", str(sm["composite"])],
        ]})
        mods = [{"name": w["name"], "status": _health_cls(w["health"]),
                 "detail": (w["role"] or ""),
                 "stats": [["版本", w["version"] or "—"],
                           ["迭代", "{0}天前".format(w["iter_days"]) if w["iter_days"] >= 0 else "需确认"],
                           ["版本治理", str(w["ver_score"])],
                           ["迭代活跃度", str(w["iter_score"])],
                           ["流程覆盖度", str(w["dims"]["coverage"])],
                           ["执行效能", str(w["dims"]["exec"])],
                           ["审计监控", str(w["dims"]["compliance"])],
                           ["复用度", str(w["dims"]["reuse"])],
                           ["健康", w["health"]]]} for w in sc["workflows"]]
        P.append({"title": "工作流清单（6 维 · Harvey 式）", "kind": "modules", "mods": mods})

    elif key == "sharedhub":  # 共享中枢中台（D9 · Harvey 式）
        h = ctx["sharedhub"]
        P.append({"title": "共享中枢 KPI（实扫 · 对标 Harvey）", "kind": "kpis", "rows": [
            ["卡总量", str(int(h["total_cards"]))],
            ["子库数", str(int(h["sub_count"]))],
            ["协议治理分", str(int(h["gov"]))],
            ["迭代活跃度分", str(int(h["iter"]))],
            ["覆盖完备度分", str(int(h["cov"]))],
            ["运行健康分", str(int(h["health"]))],
            ["审计合规分", str(int(h["compliance"]))],
            ["文档完备分", str(int(h["doc"]))],
            ["最近日志", ("{0}天前".format(h["last_log_days"]) if h["last_log_days"] >= 0 else "需确认")],
            ["六维加权基线", str(h["composite"])],
        ]})
        # 需求拷问门禁遥测（Grill-Me · 运行时真值 · 读 grill_events.jsonl）
        gg = h.get("grill_gate", {}) or {}
        if gg.get("available"):
            P.append({"title": "需求拷问门禁遥测（Grill-Me · 运行时真值）", "kind": "kpis", "rows": [
                ["门禁状态", gg.get("status", "—")],
                ["调用量(invoke)", str(int(gg.get("invoke", 0)))],
                ["对齐率(aligned/invoke)", "{0}%".format(gg.get("align_rate", 0))],
                ["放行数(skip)", str(int(gg.get("skip", 0)))],
                ["拦截率(invoke/决策)", "{0}%".format(gg.get("intercept_rate", 0))],
            ]})
        else:
            P.append({"title": "需求拷问门禁遥测（Grill-Me · 运行时真值）", "kind": "kpis", "rows": [
                ["门禁状态", gg.get("status", "待采集")],
                ["调用量(invoke)", "—"],
                ["对齐率", "—"],
                ["放行数(skip)", "—"],
                ["拦截率", "—"],
            ]})
        # 门禁接线覆盖（声明 vs 实测 · 消除"声明>执行"盲区）
        gg2 = h.get("grill_gate", {}) or {}
        total = int(gg2.get("total", 0))
        declared = int(gg2.get("declared", 0))
        callers = gg2.get("callers", []) or []
        unwired = gg2.get("unwired", []) or []
        cover_rows = [
            ["接线总集", str(total)],
            ["已声明接线", str(declared)],
            ["实测触发(caller)", str(len(callers))],
        ]
        if callers:
            cover_rows.append(["实测触发清单", "、".join(callers)])
        if unwired:
            if len(unwired) > 12:
                cover_rows.append(["未接清单", "、".join(unwired[:12]) + " …等{0}个".format(len(unwired))])
            else:
                cover_rows.append(["未接清单", "、".join(unwired)])
        P.append({"title": "门禁接线覆盖（Grill-Me · 声明 vs 实测）", "kind": "kpis", "rows": cover_rows})
        # 子库分布（11 个子目录 md 实扫计数）
        total = h["total_cards"] or 1
        mods_sub = []
        for sub, n in h["sub_counts"].items():
            pct = round(n / total * 100, 1) if total else 0
            stt = "active" if n > 0 else "silent"
            mods_sub.append({"name": sub, "status": stt, "detail": "{0} 个 md".format(n),
                             "stats": [["md", n], ["占比", "{0}%".format(pct)]]})
        P.append({"title": "子库分布（_AI-Memory-Hub 实扫）", "kind": "modules", "mods": mods_sub})
        # 作用链路：共享中枢 → 律师数字分身 作用情况（四道闸 + 卡族分布）
        fam = h["family"]
        mods_role = [
            {"name": "中枢供给规模", "status": "active",
             "detail": "分身系统可消费记忆资产总量 = {0} 卡".format(h["total_cards"]),
             "stats": [["卡总量", h["total_cards"]], ["子库", h["sub_count"]]]},
            {"name": "召回协议(Recal)执行", "status": "active",
             "detail": "分身启动按 PROJ/DEC 卡召回中枢（{0} 张项目/决策卡被引用）".format(h["recall_cards"]),
             "stats": [["召回卡", h["recall_cards"]], ["状态", "✅ 已接中枢"]]},
            {"name": "写回协议(Write-back)执行", "status": "active" if h["writeback_hits"] > 0 else "warn",
             "detail": "任务产出回写中枢（每日日志含回写标记 {0} 次）".format(h["writeback_hits"]),
             "stats": [["回写命中", h["writeback_hits"]]]},
            {"name": "冲突仲裁命中", "status": "active" if h["arbitration"] >= 0 else "silent",
             "detail": "中枢仲裁知识冲突（05-归档 deprecated 处理 {0} 张）".format(h["arbitration"]),
             "stats": [["仲裁", h["arbitration"]], ["泄露", h["key_leak"]]]},
        ]
        P.append({"title": "共享中枢 → 律师数字分身 作用链路（供给/召回/写回/仲裁）", "kind": "modules", "mods": mods_role})
        mods_fam = [{"name": "RULE 规则卡族", "status": "active", "detail": "{0} 张".format(fam["RULE"]),
                     "stats": [["卡", fam["RULE"]]]},
                    {"name": "PREF 偏好卡族", "status": "active", "detail": "{0} 张".format(fam["PREF"]),
                     "stats": [["卡", fam["PREF"]]]},
                    {"name": "PROJ 项目卡族", "status": "active", "detail": "{0} 张".format(fam["PROJ"]),
                     "stats": [["卡", fam["PROJ"]]]},
                    {"name": "DEC 决策卡族", "status": "active", "detail": "{0} 张".format(fam["DEC"]),
                     "stats": [["卡", fam["DEC"]]]},
                    {"name": "WF 工作流卡族", "status": "active", "detail": "{0} 张".format(fam["WF"]),
                     "stats": [["卡", fam["WF"]]]}]
        P.append({"title": "记忆中枢卡族（_AI-Memory-Hub · RULE/PREF/PROJ/DEC/WF 文件名前缀实扫）", "kind": "modules", "mods": mods_fam})

        # ===== 分身消费卡族分布（精确口径：只统计被分身各模块真实引用过的卡）=====
        cr = ctx.get("cardref", {})
        cr_stock = cr.get("total_stock", 0) or 1
        cr_rate = cr.get("ref_rate", 0)
        P.append({"title": "分身消费卡族分布·汇总（被引用·真实消费 · 数据源：{0}）".format(cr.get("source", "backlink代理")), "kind": "kpis", "rows": [
            ["被引用卡族", "{0} 族".format(cr.get("family_count", 0))],
            ["被引用卡量", "{0} 张".format(cr.get("total_referenced", 0))],
            ["引用率", "{0}%".format(cr_rate)],
            ["库存合计", "{0} 张".format(cr.get("total_stock", 0))],
        ]})
        cr_mods = []
        for (fn, n) in cr.get("dist", []):
            rate = round(n / cr_stock * 100, 1) if cr_stock else 0
            cr_mods.append({"name": fn, "status": "active" if n > 0 else "silent",
                            "detail": "被引用 {0} 张（占库存 {1}%）".format(n, rate),
                            "stats": [["被引", n], ["占库存", "{0}%".format(rate)]]})
        P.append({"title": "分身消费卡族分布（被引用·真实消费 · 按《07-卡族总索引》17 族）", "kind": "modules", "mods": cr_mods})

        # 卡族库存全量分布（参照口径，保留）
        cf = ctx.get("cardfam", {})
        cf_total = cf.get("total_classified", 0) or 1
        cf_mods = []
        for (fn, n) in cf.get("dist", []):
            pct = round(n / cf_total * 100, 1) if cf_total else 0
            cf_mods.append({"name": fn, "status": "active" if n > 0 else "silent",
                            "detail": "{0} 张（占库存 {1}%）".format(n, pct),
                            "stats": [["卡", n], ["占比", "{0}%".format(pct)]]})
        P.append({"title": "卡族库存分布（全量·参照口径 · 非消费）", "kind": "modules", "mods": cf_mods})

    return P


def grade_of(v):
    """单一等级函数（全站统一口径，避免方法论文字与实算不一致）。"""
    if v >= 90: return "A 优秀"
    if v >= 75: return "B 良好"
    if v >= 60: return "C 合格"
    if v >= 45: return "D 待改进"
    return "E 高危"


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------
def main():
    probes = (
        OLD.scan_four_layer(), OLD.scan_phases(), OLD.scan_version_lock(),
        OLD.scan_gaps(), OLD.scan_security(), OLD.scan_gate(), OLD.scan_deploylog(),
    )
    screens, sharedhub = build_screens(probes)
    four, phases, vl, gaps, sec, gate, deploylog = probes

    # 全局六维（复用旧版 compute_score 的六维分量；dims 即六维部署健康真源）
    dims_dict, _old_total, _old_grade = OLD.compute_score(phases, four, sec, gate, vl, gaps)
    dims = [{"name": k, "val": v,
             "color": {"部署就绪度": "#5b9bff", "架构健康度": "#2dd4bf", "安全合规度": "#a78bfa",
                       "门禁运行度": "#ef5350", "版本锁回填": "#34d399", "缺口闭环度": "#f59e0b"}.get(k, "#94a3b8")}
            for k, v in dims_dict.items()]

    # 环形总评 = 六维算术平均（与 dims 条一致，杜绝"屏加权均值"式假自洽，对齐 R-LN-114 教训）
    total = round(sum(d["val"] for d in dims) / len(dims), 1) if dims else 0.0
    grade = grade_of(total)

    flags = []
    for r in sec["redlines"]:
        if r["status"].startswith("⚠️"):
            flags.append("🔴 " + r["text"])
    if not gate["daemon_running"]:
        flags.append("🔴 LTI 门禁守护进程未启动（待 launchctl load）")
    if not flags:
        flags.append("🟢 暂无高危告警")

    data = {
        "screens": screens,
        "dims": dims,
        "sharedhub": sharedhub,
        "gaps": gaps["items"],
        "total": total,
        "grade": grade,
        "generated_at": NOW,
        "note": "环形总评 = 六维部署健康综合均值(与维度条一致)；各屏监控卡片/评分总表为独立探针明细，不反向聚合进总评；律所 4 屏(C4/C5/C6/C7)全屏显示且权重 0、不影响总评。",
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if "--print" in sys.argv:
        print("✅ scorecard_data.json 已生成（9360 格式）")
        print("   环形总评(六维均值)：{0}（{1}）".format(total, grade))
        print("   六维：{0}".format(" / ".join("{0} {1}".format(d["name"], d["val"]) for d in dims)))
        print("   屏数：{0}（律所 4 屏全屏显示）｜ 告警旗：{1}".format(
            len(screens), " / ".join(flags)))


if __name__ == "__main__":
    main()
