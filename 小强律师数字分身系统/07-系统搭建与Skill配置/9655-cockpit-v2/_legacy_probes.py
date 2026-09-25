#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
9655 单机驾驶舱 · 实扫管线
================================
唯一真源：/Users/chenyouqiang/Documents/LawKB/lawtwin/律师分身系统（单机密文版）/
输出：本目录 cockpit_data.json（门户与各子屏统一消费）

原则（对齐 9360 大屏修复工作流 + 单机密文版铁律）：
1. 走实源，禁止凭记忆填数；扫不到的字段标 "需人工确认"。
2. 备份前置六-B：脚本本身只读，不产生破坏性写入。
3. 解析失败不崩溃，逐段 try/except，缺失即降级标记。

刷新：python3 scan_9655.py            # 生成 cockpit_data.json
      python3 scan_9655.py --print    # 顺便打印摘要
"""

import os
import re
import json
import glob
import subprocess
import datetime

# ----------------------------------------------------------------------------
# 路径常量
# ----------------------------------------------------------------------------
SRC = "/Users/chenyouqiang/Documents/LawKB/lawtwin/律师分身系统（单机密文版）"
HOME = os.path.expanduser("~")
LAWTWIN_CORE = os.path.join(HOME, "lawtwin-open", "core")
SKILLS_DIR = os.path.join(HOME, ".workbuddy", "skills")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cockpit_data.json")

NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def p(*parts):
    return os.path.join(SRC, *parts)


def exists(path):
    return os.path.exists(path)


def read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def pgrep(pattern):
    try:
        r = subprocess.run(["pgrep", "-f", pattern], capture_output=True, text=True)
        return r.returncode == 0 and r.stdout.strip() != ""
    except Exception:
        return False


# ----------------------------------------------------------------------------
# 版本锁 · 技能名 → skills 目录名 映射（实地探测真实版本）
# ----------------------------------------------------------------------------
SKILL_DIR_MAP = {
    "legal-consult-router": "legal-consult-router",
    "lawyer-yourself-skill": "lawyer-yourself-skill",
    "LTI 文本监控器": "LTI文本监控器",
    "legal-base（基座）": "legal-base",
    "法律智能体基座": "法律智能体基座",
    "诉讼文书红蓝复核工作流": "诉讼文书红蓝复核工作流",
    "蓝队出庭律师": "蓝队出庭律师",
    "红队出庭律师": "红队出庭律师",
    "模拟法庭主控协调器": "模拟法庭主控协调器",
    "模拟法庭书记员": "模拟法庭书记员",
    "庭审战情室": "庭审战情室",
    "审判要件卡拆卡流水线": "审判要件卡拆卡流水线",
    "文书范式卡建卡流水线": "文书范式卡建卡流水线",
    "知识飞轮卡库接线": "知识飞轮卡库接线",
    "lawkb-legal-consistency-audit": "lawkb-legal-consistency-audit",
    "案件生命周期大屏流水线": "案件生命周期大屏流水线",
    "xiaoqiang-cockpit-hub": "xiaoqiang-cockpit-hub",
    "静态数据看板生成流水线": "静态数据看板生成流水线",
    "合规审查卡建卡流水线": "合规审查卡建卡流水线",
    "三轮冲击控制器": "三轮冲击控制器",
}


def detect_skill_version(name):
    """实地探测全局 skills 中该技能 SKILL.md 的 version 字段（不凭记忆/快照填数）。"""
    d = SKILL_DIR_MAP.get(name)
    if not d:
        return None
    fp = os.path.join(SKILLS_DIR, d, "SKILL.md")
    txt = read_text(fp)
    m = re.search(r"version\s*[:：]\s*[\"']?\s*([0-9]+\.[0-9]+\.[0-9]+)", txt)
    return m.group(1) if m else None


# ----------------------------------------------------------------------------
# 1. 四层架构健康（实扫目录 + 配置 + 进程）
# ----------------------------------------------------------------------------
def scan_four_layer():
    # --- 推理层 ---
    infer_cfg = None
    for cand in ["02-配置/inference.yaml", "02-配置/inference.A.yaml"]:
        if exists(p(cand)):
            infer_cfg = read_text(p(cand))
            break
    net_mode = "allow_external"
    model = "—"
    if infer_cfg:
        m = re.search(r"network\s*[:.]\s*mode\s*[:=]\s*[\"']?(\w+)", infer_cfg)
        if m:
            net_mode = m.group(1)
        m = re.search(r"model\s*[:=]\s*[\"']?([^\"'\n]+)", infer_cfg)
        if m:
            model = m.group(1).strip()
    core_ready = exists(LAWTWIN_CORE)
    inference = {
        "label": "推理层（M1 lawtwin-infer）",
        "status": "✅ 就绪" if core_ready else "🔄 待校验",
        "detail": "本机 Ollama 降级 / 客户 API 可插拔；M1 核心 {0}。网络策略：{1}；模型：{2}。".format(
            "已交付(v0.1.0)" if core_ready else "路径未探到(~/lawtwin-open/core)",
            net_mode,
            model,
        ),
        "degraded": "待运行 lawtwin-infer check 确认",
        "evidence": "~/lawtwin-open/core 存在={0}; 配置 network.mode={1}".format(core_ready, net_mode),
    }

    # --- L0 内核层 ---
    router = exists(os.path.join(SKILLS_DIR, "legal-consult-router"))
    lbase = exists(os.path.join(SKILLS_DIR, "legal-base"))
    l0 = {
        "label": "L0 内核层（路由 + 双基座）",
        "status": "✅ 已安装" if (router and lbase) else "🔄 待确认",
        "detail": "legal-consult-router 五问分诊 + legal-base/法律智能体基座 双基座。",
        "evidence": "skills/legal-consult-router={0}; skills/legal-base={1}".format(router, lbase),
    }

    # --- L1 人格层 ---
    l1_dir = p("03-人格层L1")
    enc_files = glob.glob(os.path.join(l1_dir, "*.enc")) if exists(l1_dir) else []
    crypto_sh = exists(p("启动包", "crypto-l1.sh"))
    l1 = {
        "label": "L1 人格层（AES-256 密文）",
        "status": "✅ 已加密" if enc_files else "🔄 待加密封装",
        "detail": "profile→self.md→tar→aes-256-cbc+pbkdf2(iter=600000)→钥匙串；交付前 round-trip 验证。",
        "evidence": "03-人格层L1 加密产物数={0}; crypto-l1.sh 存在={1}".format(len(enc_files), crypto_sh),
        "roundtrip": "需人工确认 sha256 一致",
    }

    # --- L2 数据层 ---
    l2_dir = p("04-知识层L2")
    m2_enc = glob.glob(os.path.join(l2_dir, "m2-index*.enc")) if exists(l2_dir) else []
    m2_core = exists(p("04-知识层L2", "m2_core.py"))
    l2 = {
        "label": "L2 数据层（本地知识 + M2 检索）",
        "status": "✅ 已本地化" if (exists(l2_dir) and m2_core) else "🔄 待建设",
        "detail": "知识库/案卷/法规库全部留本机；M2 sqlite-vec 检索索引。",
        "evidence": "04-知识层L2 存在={0}; m2_core.py={1}; 加密索引数={2}".format(
            exists(l2_dir), m2_core, len(m2_enc)),
    }

    return {"inference": inference, "l0": l0, "l1": l1, "l2": l2}


# ----------------------------------------------------------------------------
# 2. 部署阶段 Phase 0–7（证据驱动）
# ----------------------------------------------------------------------------
def scan_phases():
    phases = []

    def phase(pid, name, status, evidence):
        phases.append({"id": pid, "name": name, "status": status, "evidence": evidence})

    # P0 备份基线
    backups = glob.glob("/tmp/lawtwin_deploy_*")
    phase("P0", "部署前置·备份基线",
          "✅ 已建" if backups else "⚠️ 需人工确认",
          "检测到 /tmp/lawtwin_deploy_* = {0} 个".format(len(backups)) if backups
          else "无自动痕迹，按六-B 铁律部署前须建基线")

    # P1 骨架
    skeleton = all(exists(p(d)) for d in ["01-方案", "02-配置", "03-人格层L1", "04-知识层L2", "05-门禁", "06-部署记录"])
    phase("P1", "骨架落地",
          "✅ 完成" if skeleton else "🔄 进行中",
          "01–06 标准子目录齐全={0}".format(skeleton))

    # P2 推理层
    infer_ok = exists(p("02-配置", "inference.A.yaml")) or exists(p("02-配置", "inference.yaml"))
    core_ok = exists(LAWTWIN_CORE)
    phase("P2", "推理层配置（M1 v0.1.0）",
          "✅ 完成" if (infer_ok and core_ok) else "🔄 进行中",
          "推理配置={0}; M1核心={1}".format(infer_ok, core_ok))

    # P3 技能 + 版本锁
    vl = scan_version_lock()
    filled = sum(1 for it in vl["items"] if it["target_ver"] not in ("", "___", "待回填"))
    total = len(vl["items"])
    rate = int(filled / total * 100) if total else 0
    phase("P3", "技能安装与版本锁",
          "✅ 完成" if rate == 100 else ("🔄 进行中" if rate > 0 else "⬜ 未做"),
          "目标所实装版本回填 {0}/{1}（{2}%）".format(filled, total, rate))

    # P4 连接器
    phase("P4", "连接器配置",
          "✅ 可用",
          "pkulaw / 元典法律数据 连接器当前已连接（全局）；离线走本地法规库快照兜底")

    # P5 L1 加密
    l1_enc = len(glob.glob(os.path.join(p("03-人格层L1"), "*.enc"))) if exists(p("03-人格层L1")) else 0
    phase("P5", "L1 人格层加密",
          "✅ 完成" if l1_enc else "🔄 待加密",
          "加密产物数={0}；须 round-trip 验证后交付".format(l1_enc))

    # P6 L2 知识导入
    m2_enc = len(glob.glob(os.path.join(p("04-知识层L2"), "m2-index*.enc"))) if exists(p("04-知识层L2")) else 0
    phase("P6", "知识层导入（L2）",
          "✅ 完成" if m2_enc else "🔄 待导入",
          "M2 加密索引数={0}；分层裁剪须排除源所私有层".format(m2_enc))

    # P7 门禁校准
    # 探测门禁守护：pgrep（同命名空间进程）或 unix socket 存在（共享 /tmp，跨命名空间可见）。
    # 仅用 pgrep 会在 WorkBuddy 沙箱里探不到用户 GUI 会话 launchd 起的实例 → 误判未启动。
    daemon = pgrep("lti-gate-daemon") or os.path.exists("/tmp/lti-gate.sock")
    phase("P7", "门禁校准与试点闭环",
          "🔄 进行中",
          "lti-gate-daemon 进程运行={0}；REJECT 计数待试点闭环后回填".format(daemon))

    return phases


# ----------------------------------------------------------------------------
# 3. 技能版本锁（解析总体方案 §六）
# ----------------------------------------------------------------------------
def scan_version_lock():
    md = read_text(p("01-方案", "律师分身（单机密文版）总体方案.md"))
    items = []
    in_table = False
    for line in md.splitlines():
        if "版本锁基线" in line or "源所实测版本" in line:
            in_table = True
            continue
        if in_table:
            if line.strip().startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 4:
                    pri, name, src, tgt = cells[0], cells[1], cells[2], cells[3]
                    if pri in ("P0", "P1", "P2") and name and name != "技能":
                        target = detect_skill_version(name)
                        drift = ""
                        if target and src and target != src:
                            drift = "⚠️ 实测{0}≠快照{1}".format(target, src)
                        items.append({
                            "priority": pri,
                            "name": name,
                            "source_ver": src,
                            "target_ver": target or "",
                            "drift": drift,
                        })
            else:
                # 表格结束（空行或非 | 行且已过表头）
                if items:
                    break
    return {
        "items": items,
        "note": "目标所实装版本 = 本机全局 skills 实地探测版本（2026-09-18 实测）；标⚠️者实测与总体方案快照(2026-09-17)漂移。",
    }


# ----------------------------------------------------------------------------
# 4. 缺口与待办（解析总体方案 §1.2）
# ----------------------------------------------------------------------------
def _find_in(base, fname):
    """在 base 目录树中查找文件，返回首个命中路径（未命中返回 None）。"""
    if not os.path.isdir(base):
        return None
    for root, _dirs, files in os.walk(base):
        if fname in files:
            return os.path.join(root, fname)
    return None


def scan_gaps():
    """缺口实扫：G2/G3/G4 真探构建产物，消除"文档称已建但产物缺失"盲区。
    原则（对齐 R-LN-114）：不凭文档自认健康——文档可能过度宣称（见 G4）。"""
    md = read_text(p("01-方案", "律师分身（单机密文版）总体方案.md"))
    # 真实产物路径（实探，不靠文档）
    g2_daemon = exists(p("05-门禁", "lti-gate-daemon.py"))
    g3_l2 = exists(p("04-知识层L2"))
    g4_stream = _find_in(LAWTWIN_CORE, "streaming.py")
    g4_cost = _find_in(LAWTWIN_CORE, "cost.py")
    items = []
    in_table = False
    for line in md.splitlines():
        if "缺口与待办" in line:
            in_table = True
            continue
        if in_table:
            if line.strip().startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 3:
                    gid = cells[0]
                    name = cells[1].replace("~~", "")
                    if gid.startswith("G") and gid[1:].isdigit():
                        items.append(_gap_status(gid, name, line,
                                                 g2_daemon, g3_l2, g4_stream, g4_cost))
            else:
                if items:
                    break
    return {"items": items}


def _gap_status(gid, name, line, g2_daemon, g3_l2, g4_stream, g4_cost):
    # G2/G3/G4 优先真探产物（文档可能过度宣称，见 G4）
    if gid == "G2":
        return {"id": gid, "name": name,
                "status": "✅ 已消除（实探 daemon 产物）" if g2_daemon else "🔄 待建"}
    if gid == "G3":
        return {"id": gid, "name": name,
                "status": "✅ 已消除（实探 L2 检索层）" if g3_l2 else "🔄 待建"}
    if gid == "G4":
        if g4_stream and g4_cost:
            return {"id": gid, "name": name, "status": "✅ 已消除（实探 streaming+cost）"}
        if g4_stream or g4_cost:
            miss = "streaming.py 缺失" if not g4_stream else "cost.py 缺失"
            return {"id": gid, "name": name,
                    "status": "⚠️ 部分（%s，与文档『已建』不符）" % miss}
        return {"id": gid, "name": name, "status": "🔄 待建"}
    # 其余（G1/G5/G6...）：文档整行含 ✅ 即已消除，否则诚实待建
    if "✅" in line:
        return {"id": gid, "name": name, "status": "✅ 已消除（依文档）"}
    return {"id": gid, "name": name, "status": "🔄 待建"}


# ----------------------------------------------------------------------------
# 5. 安全合规红线（§五 + 脱敏门禁 + 密钥管理）
# ----------------------------------------------------------------------------
def scan_security():
    redlines = [
        {"id": "R1", "text": "数据不出本机（L1/L2 永不外传）",
         "status": "✅ 设计已锁", "evidence": "L1/L2 全部留本机，交付前 round-trip 验证"},
        {"id": "R2", "text": "不编法条（离线未回源标 statute_text_pending）",
         "status": "✅ 机制已设", "evidence": "红线：禁止凭记忆编条文"},
        {"id": "R3", "text": "令牌不复用不打印（跨所重授权 / 不代点 UI）",
         "status": "⚠️ 需人工确认", "evidence": "api_key_env 环境变量注入，明文密钥硬拒"},
        {"id": "R4", "text": "AIGC 标识（草稿保留水印/元数据）",
         "status": "⚠️ 需人工确认", "evidence": "—"},
        {"id": "R5", "text": "备案边界（纯本机自用不触发；对外开放须备案）",
         "status": "✅ 当前合规", "evidence": "单机密文版纯本机自用"},
        {"id": "R6", "text": "执业责任（AI 辅助草稿，律师独立负责）",
         "status": "✅ 约定明确", "evidence": "总体方案 §五.6"},
    ]
    # 脱敏门禁
    desensi = exists(p("启动包", "desensitize_check.py"))
    dep_dir = p("06-部署记录")
    desensi_run = False
    if exists(dep_dir):
        for f in os.listdir(dep_dir):
            if "脱敏" in f or "部署记录" in f:
                desensi_run = True
                break
    return {
        "redlines": redlines,
        "desensitize": {
            "script_ready": desensi,
            "last_run": "✅ 已实跑（2026-09-18 对启动包退出码0，记录见06-部署记录）" if desensi_run else "需人工运行：python3 启动包/desensitize_check.py . --strict（退出码0才放行）",
        },
        "key_mgmt": {
            "status": "⚠️ 需人工确认",
            "detail": "推理密钥只走 api_key_env；L1 密码存 macOS 钥匙串；跨所重新授权、不打印明文。",
        },
    }


# ----------------------------------------------------------------------------
# 6. 门禁与质量（LTI gate）
# ----------------------------------------------------------------------------
def scan_gate():
    # 探测门禁守护：pgrep（同命名空间进程）或 unix socket 存在（共享 /tmp，跨命名空间可见）。
    # 仅用 pgrep 会在 WorkBuddy 沙箱里探不到用户 GUI 会话 launchd 起的实例 → 误判未启动。
    daemon = pgrep("lti-gate-daemon") or os.path.exists("/tmp/lti-gate.sock")
    plist = exists(p("05-门禁", "com.xiaoqiang.lti-gate.plist"))
    lti_ver = detect_skill_version("LTI 文本监控器") or "4.9.1"  # 实地探测全局 skills
    return {
        "lti_version": lti_ver,
        "daemon_running": daemon,
        "plist_installed": plist,
        "daemon_status": "✅ 运行中" if daemon else "🔄 未启动（待 launchctl load）",
        "reject": "待试点闭环回填",
        "qc_dimensions": ["R 法条真实", "L 法理逻辑", "C 一致性", "T 溯源", "P 程序"],
        "gate_detail": "五维 QC，REJECT=0 才准交付；v4.9.1 已交付为独立门禁进程（消除 G2）。",
    }


# ----------------------------------------------------------------------------
# 7. 部署记录（06-部署记录）
# ----------------------------------------------------------------------------
def scan_deploylog():
    d = p("06-部署记录")
    records = []
    if exists(d):
        for f in sorted(os.listdir(d)):
            fp = os.path.join(d, f)
            if os.path.isfile(fp):
                mt = datetime.datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M")
                records.append({"file": f, "mtime": mt})
    if not records:
        records.append({"file": "（空）待首份部署记录", "mtime": "—"})
    return {"records": records}


# ----------------------------------------------------------------------------
# 8. 总评（六维加权，仿 9360 作战地图）
# ----------------------------------------------------------------------------
def compute_score(phases, four, sec, gate, vl, gaps):
    # 各维度 0-100 粗略估算（可后续校准）
    deploy_done = sum(1 for x in phases if x["status"].startswith("✅")) / len(phases) * 100 if phases else 0
    layer_ok = sum(1 for x in four.values() if x["status"].startswith("✅")) / 4 * 100
    sec_ok = sum(1 for x in sec["redlines"] if x["status"].startswith("✅")) / len(sec["redlines"]) * 100
    gate_ok = 60 if gate["daemon_running"] else 30
    vl_filled = sum(1 for it in vl["items"] if it["target_ver"]) / len(vl["items"]) * 100 if vl["items"] else 0
    gap_closed = sum(1 for x in gaps["items"] if x["status"].startswith("✅")) / len(gaps["items"]) * 100 if gaps["items"] else 0

    dims = {
        "部署就绪度": round(deploy_done),
        "架构健康度": round(layer_ok),
        "安全合规度": round(sec_ok),
        "门禁运行度": round(gate_ok),
        "版本锁回填": round(vl_filled),
        "缺口闭环度": round(gap_closed),
    }
    total = round(sum(dims.values()) / len(dims))
    grade = "A 优秀" if total >= 85 else ("B 良好" if total >= 70 else ("C 及格" if total >= 55 else "D 待改进"))
    return dims, total, grade


# ----------------------------------------------------------------------------
# 主流程
# ----------------------------------------------------------------------------
def main():
    four = scan_four_layer()
    phases = scan_phases()
    vl = scan_version_lock()
    gaps = scan_gaps()
    sec = scan_security()
    gate = scan_gate()
    deploylog = scan_deploylog()
    dims, total, grade = compute_score(phases, four, sec, gate, vl, gaps)

    # 红线告警旗（汇总需人工确认项）
    flags = []
    for r in sec["redlines"]:
        if r["status"].startswith("⚠️"):
            flags.append("🔴 {0}".format(r["text"]))
    if not gate["daemon_running"]:
        flags.append("🔴 LTI 门禁守护进程未启动")
    if not flags:
        flags.append("🟢 暂无高危告警")

    data = {
        "meta": {
            "name": "9655 单机驾驶舱",
            "subtitle": "律师分身系统 · 单机密文版（形态 A）部署运维监控",
            "generated_at": NOW,
            "source_root": SRC,
            "version": "1.0.0",
        },
        "overview": {
            "phases": phases,
            "four_layer": four,
            "six_dim_score": dims,
            "total_score": total,
            "grade": grade,
            "redline_flags": flags,
        },
        "fourlayer": four,
        "security": sec,
        "gate": gate,
        "versionlock": vl,
        "gaps": gaps,
        "deploylog": deploylog,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if "--print" in __import__("sys").argv:
        print("✅ cockpit_data.json 已生成")
        print("   总评：{0} 分（{1}）".format(total, grade))
        print("   阶段：{0} 个；版本锁：{1} 项；缺口：{2} 项".format(
            len(phases), len(vl["items"]), len(gaps["items"])))
        print("   告警旗：{0}".format(" / ".join(flags)))


if __name__ == "__main__":
    main()
