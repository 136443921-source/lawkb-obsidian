#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTI 九维文本质检运行器 (lti_qc9.py)  v4.9.0
=====================================================================
依据《LTI文书质检清单扩展版》把 LTI 文本监控系统从五维升级到九维：
    R 法条真实性 / L 法理逻辑 / C 一致性 / T 溯源 / P 程序
  + S 策略契合 / V 风险预判 / W 表达规范 / E 证据闭环

设计纪律（与既有 LTI 一致）：
  * 门禁：REJECT = 0 才准交付；任一 ❌ 阻断；⚠️ 为提交前补强，不阻断。
  * 宁漏勿误：机械维(C/P/W)与初筛维(R/T)只标 ❌ 于高置信硬错；
    策略/逻辑/证据/风险维(L/S/V/E)为人工确认维，不自动 REJECT，
    须执业律师确认；这守住了「零误报」底线，绝不假装 AI 能判定策略。

依赖：仅 Python 标准库（zipfile / re / html / json / sys / os）。
      docx 通过解压 word/document.xml 抽取文本，无需 python-docx。

用法：
  python3 lti_qc9.py <文书.docx|.md|.txt> [--report out.md]
                       [--manual L=pass S=warn V=warn E=warn]
                       [--legacy-gate /path/to/lti_gate.py]
  exit 0 = PASS（可交付） / exit 1 = REJECT（须修后重跑）
"""
import sys
import os
import re
import json
import html
import zipfile
import argparse

# ---------------------------------------------------------------------------
# 九维规范（与 lti_dimensions_v9.json 同源；内嵌以保证脚本自包含可跑）
# ---------------------------------------------------------------------------
DIMS = [
    ("R", "法条真实性", "真实·现行有效·配对", "partial",
     "法条编造 / 失效 / 错引",
     ["三渠道一致性核验（元典/qcc/法条银行）≥2 源一致", "条号+正文+时效性三项一致",
      "法条现行有效", "条号款项项号精确", "引用与事实主张配对", "已查但书例外", "无新法/特别法冲突"]),
    ("L", "法理逻辑", "论证自洽·教义锚定", "manual",
     "逻辑断裂 / 教义错锚",
     ["论证链完整自洽（事实→依据→请求）", "事实主张与请求一一对应", "教义锚定清晰", "已做反向证伪", "无逻辑跳步/循环论证"]),
    ("C", "一致性", "案号名称金额不打架", "auto",
     "案号 / 名称 / 金额矛盾",
     ["案号(304)全文一致", "当事人名称(302)一致、诉讼地位不串", "金额(301)数字单位一致、大小写无冲突",
      "证件号/信用代码/联系方式一致", "日期链内部一致", "案由/法院/法官一致"]),
    ("T", "溯源", "事实法条有出处", "partial",
     "关键事实无出处支撑",
     ["每条法条标法名+条号可回查", "每项事实主张有出处", "引用材料实体存在/已入证据册",
      "关键主张有类案支撑或标待补强", "原件/复制件标注清楚"]),
    ("P", "程序", "格式·期限·签署合规", "auto",
     "期限超期 / 签署授权缺失",
     ["文书格式齐全（标题/当事人/请求/理由/落款）", "申请形式合规", "期限时点声明完整",
      "期限精确计算", "签署/授权完备", "送达请求与副本份数明确"]),
    ("S", "策略契合度", "服务核心争点目标", "manual",
     "偏离主线 / 暴露弱点",
     ["服务本案核心争点与诉讼目标", "与整体诉讼策略/防守主线一致", "不节外生枝、不暴露己方弱点"]),
    ("V", "风险预判", "识别驳回 / 反击风险", "manual",
     "重大风险未识别",
     ["已识别被驳回/不予准许风险点", "已预判对方反击位并写应对", "证据持有人/程序路径是否最优"]),
    ("W", "表达规范", "中性·精准·得当", "partial",
     "用词失真 / 重大歧义",
     ["法言法语中性、无主观溢美词", "用词精准、无冗余(如『第一款』)", "繁简得当、层次清晰"]),
    ("E", "证据闭环", "主张逐条有证据", "partial",
     "核心主张飘空无佐证",
     ["每项事实主张能指到具体证据", "证据册与文书主张逐条闭环", "无『主张飘空』(说了无佐证)",
      "当事人意思表示/授权/主观状态类事实须建陈述时间轴并扫描全案矛盾陈述，单点证据不得定论(E1004)"]),
]
MANUAL = {"L", "S", "V", "E"}
AUTO_OK = {"C", "P"}
PARTIAL = {"R", "T", "W"}

CJK = r'[一-鿿]'


# ---------------------------------------------------------------------------
# 文本抽取
# ---------------------------------------------------------------------------
def extract_text(path):
    if path.lower().endswith(".docx"):
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        paras = re.split(r"</w:p>", xml)
        out = []
        for p in paras:
            ts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.DOTALL)
            s = "".join(ts)
            s = (s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                   .replace("&quot;", '"').replace("&apos;", "'"))
            if s.strip():
                out.append(s.strip())
        return "\n".join(out)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


# ---------------------------------------------------------------------------
# 机械 / 初筛检查（仅在高置信硬错时标 ❌，其余 ⚠️/✅，守零误报）
# ---------------------------------------------------------------------------
def check_R(text):
    f = []
    for bad in ["中华人民共和国合同法", "中华人民共和国物权法", "中华人民共和国担保法",
                "中华人民共和国民法总则", "中华人民共和国侵权责任法"]:
        if bad in text:
            f.append(("REJECT", "R001", f"引用已废止法律：{bad}"))
    # 条文引用缺法名包裹（《》）→ 提示补全可回查
    if re.search(r"第\d+条", text) and "《" not in text:
        f.append(("WARN", "R-trace", "存在『第X条』但未标注《法名》，不可回查"))
    return f


def check_C(text):
    f = []
    # 案号抽取：形如 （2026）黔0330民初6658号
    cases = re.findall(r"（\d{4}）" + CJK + r"+[一-鿿A-Za-z]*\d+号", text)
    if cases:
        uniq = sorted(set(cases))
        if len(uniq) > 1:
            f.append(("WARN", "C304", f"出现 {len(uniq)} 个不同案号，需确认是否同一案：{uniq}"))
    # 金额：抓 数字+元 / 数字+万元，提示存在多金额需人工核对大小写
    amts = re.findall(r"(\d[\d,.]*)\s*万元?", text)
    # 仅当存在明显『万』与『元』混用于同一标的表述时提示（保守，不自动 REJECT）
    if "万元" in text and re.search(r"\d[\d,.]*\s*元(?!的)", text):
        f.append(("WARN", "C301", "文本同时出现『万元』与『元』金额，建议接 C301 数值比对器核对大小写/单位一致"))
    # 当事人诉讼地位串味提示
    if ("原告" in text and "被告" in text):
        pass  # 深度名称一致性交给 lti_gate.py C302
    return f


def check_P(text):
    f = []
    need_blocks = [("当事人", ["原告", "被告", "申请人", "被申请人"]),
                   ("请求事项", ["诉讼请求", "请求事项", "申请事项"]),
                   ("理由", ["事实与理由", "理由", "事实"]),
                   ("落款", ["此致", "具状人", "代理人", "年月日"])]
    for name, keys in need_blocks:
        if not any(k in text for k in keys):
            f.append(("WARN", "P-format", f"文书可能缺『{name}』板块（格式不全）"))
    # 期限声明 vs 计算
    if "举证期限" in text or "期限" in text:
        if not re.search(r"\d{4}年\d{1,2}月\d{1,2}日", text):
            f.append(("WARN", "P401", "提及期限但未见精确届满日，建议补全期限计算"))
    return f


def check_W(text):
    f = []
    fixes = [("签定合同", "签订合同"), ("法人代表", "法定代表人"), ("追诉期", "诉讼时效")]
    for wrong, right in fixes:
        if wrong in text:
            f.append(("WARN", "W901", f"术语不规范：『{wrong}』应为『{right}』"))
    if "第一款" in text:
        f.append(("WARN", "W902", "存在『第一款』等冗余表述，建议精简（条号已含款项）"))
    return f


def check_T(text):
    f = []
    if "《" in text and "第" in text:
        # 有引用但未标出处附件/证据册 → 提示
        if "证据册" not in text and "附件" not in text and "在案" not in text:
            f.append(("WARN", "T501", "引用法条/事实但未见『证据册/附件/在案』出处标注，建议补溯源"))
    return f


def check_E(text):
    f = []
    # E1004 矛盾陈述扫描（部分自动·仅 WARN 不阻断）：当事人意思表示/授权类肯定表述
    # 须先建陈述时间轴+矛盾扫描，防止「单点证据定论」（6658 制裁评估误判根因）。
    intent_markers = ["获本人承认", "已追认", "真实意思为", "授权真实", "本人确认", "自认真实"]
    scan_markers = ["陈述时间轴", "矛盾陈述", "矛盾即悬置", "悬而未决", "争议中",
                   "前后矛盾", "多处不一致", "未予查明", "未认定授权有效"]
    if any(m in text for m in intent_markers) and not any(s in text for s in scan_markers):
        f.append(("WARN", "E1004",
                  "检测到当事人意思/授权类肯定表述，请确认已完成『矛盾陈述扫描』"
                  "（建陈述时间轴+矛盾即悬置）；单点证据不得定论，详见经验卡-当事人陈述矛盾扫描"))
    return f


AUTO_FN = {"R": check_R, "C": check_C, "P": check_P, "W": check_W, "T": check_T, "E": check_E}


# ---------------------------------------------------------------------------
# 审计落盘（v4.9.0 新增）：S/V/W/E 命中趋势真实写入 jsonl
# 纪律：仅写真实数据，绝不编造命中；写失败打印明确提示、不写假记录。
# ---------------------------------------------------------------------------
def write_audit(doc, verdict, findings, manual_status):
    import datetime
    audit_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit")
    try:
        os.makedirs(audit_dir, exist_ok=True)
    except Exception as e:
        print(f"   ⚠️ 审计目录创建失败（{audit_dir}）：{e}；本次审计未落盘。")
        return
    audit_path = os.path.join(audit_dir, "lti_qc9_audit.jsonl")
    dims_status = {}
    for code, name, one, kind, hard, items in DIMS:
        if code in MANUAL:
            st = manual_status.get(code, "warn")
        else:
            lvl = "pass"
            for l, r, rs in findings[code]:
                if l == "REJECT":
                    lvl = "reject"
                elif l == "WARN" and lvl != "reject":
                    lvl = "warn"
            st = lvl
        hits = [r for l, r, rs in findings[code] if l in ("REJECT", "WARN")]
        dims_status[code] = {"status": st, "hits": hits, "hit_count": len(hits)}
    rec = {
        "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "doc": os.path.basename(doc),
        "verdict": verdict,
        "dims": dims_status,
        "svwe_trend": {k: dims_status[k]["hit_count"] for k in ("S", "V", "W", "E")},
        "version": "4.9.0",
    }
    try:
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"\n📝 审计已落盘：{audit_path}（S/V/W/E 命中趋势累计中）")
    except Exception as e:
        print(f"   ⚠️ 审计写盘失败（{audit_path}）：{e}；本次未落盘（不编造）。")


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="LTI 九维文本质检运行器 v4.9.0")
    ap.add_argument("doc", help="待质检文书 .docx/.md/.txt")
    ap.add_argument("--report", help="输出 markdown 报告路径")
    ap.add_argument("--manual", default="",
                    help="人工确认维结果，如 L=pass S=warn V=warn E=warn")
    ap.add_argument("--legacy-gate", default="",
                    help="可选：调用既有 lti_gate.py 做 R/C/T/P 深度校验（best-effort）")
    ap.add_argument("--interactive", action="store_true",
                    help="开启逐维人工问询（仅本地真终端使用；默认非交互，人工维记 warn 不阻断）")
    args = ap.parse_args()

    if not os.path.exists(args.doc):
        print(f"❌ 文件不存在: {args.doc}")
        return 2

    print(f"======== LTI 九维质检 (v4.9.0) ========")
    print(f"文书: {args.doc}\n")

    text = extract_text(args.doc)

    # 人工确认维解析
    manual_res = {}
    for kv in [x for x in args.manual.split() if "=" in x]:
        k, v = kv.split("=", 1)
        manual_res[k.strip().upper()] = v.strip().lower()
    # 非交互（默认）：人工维记 warn（待确认，不阻断）；--interactive 且真终端才逐维问询
    interactive = args.interactive and sys.stdin.isatty()

    findings = {d[0]: [] for d in DIMS}
    manual_status = {}

    for code, name, one, kind, hard, items in DIMS:
        if kind == "auto" or kind == "partial":
            fs = AUTO_FN.get(code, lambda t: [])(text)
            findings[code] = fs
        # 人工维
        if code in MANUAL:
            if code in manual_res:
                st = manual_res[code]
            elif interactive:
                ans = input(f"  [{code} {name}] 请确认（pass/warn/reject，默认 warn）：").strip().lower()
                st = ans or "warn"
            else:
                st = "warn"  # 非交互：默认待确认，不阻断
            manual_status[code] = st

    # 汇总 verdict
    reject_count = 0
    warn_count = 0
    for code, name, one, kind, hard, items in DIMS:
        for lvl, rule, reason in findings[code]:
            if lvl == "REJECT":
                reject_count += 1
            elif lvl == "WARN":
                warn_count += 1
    for code, st in manual_status.items():
        if st == "reject":
            reject_count += 1
        elif st == "warn":
            warn_count += 1

    verdict = "REJECT" if reject_count > 0 else "PASS"

    # 输出报告
    lines = [f"# LTI 九维质检报告（v4.9.0）", "", f"- 文书：`{os.path.basename(args.doc)}`",
             f"- 门禁：**{'❌ REJECT（须修后重跑）' if verdict=='REJECT' else '✅ PASS（可交付）'}**",
             f"- ❌ REJECT 计数：{reject_count}　⚠️ 待补强：{warn_count}（补完即归零）", ""]
    lines.append("| 维 | 名称 | 结论 | 关键发现 |")
    lines.append("|---|---|---|---|")
    for code, name, one, kind, hard, items in DIMS:
        if code in MANUAL:
            st = manual_status[code]
            mark = {"pass": "✅", "warn": "⚠️", "reject": "❌"}.get(st, "⚠️")
            note = {"pass": "人工确认通过", "warn": "人工待确认/补强", "reject": "人工判 REJECT"}.get(st, "")
            # 合并自动启发式（check_E 等）：auto WARN/REJECT 优先，确保 E1004 不被人工 pass 压制
            auto_reasons = []
            auto_lvl = None
            for l, r, rs in findings[code]:
                if l == "REJECT":
                    auto_lvl = "❌"
                elif l == "WARN" and auto_lvl != "❌":
                    auto_lvl = "⚠️"
                auto_reasons.append(f"[{l}] {rs}")
            if auto_lvl == "❌":
                mark, note = "❌", "自动 REJECT（启发式）"
            elif auto_lvl == "⚠️":
                mark, note = "⚠️", f"自动⚠️(启发式)+{note}"
            detail = f"{note}（硬错：{hard}）" + ("；" + "；".join(auto_reasons) if auto_reasons else "")
            lines.append(f"| {code} | {name} | {mark} | {detail} |")
        else:
            lvl = "✅"
            reasons = []
            for l, r, rs in findings[code]:
                if l == "REJECT":
                    lvl = "❌"
                elif l == "WARN" and lvl != "❌":
                    lvl = "⚠️"
                reasons.append(f"[{l}] {rs}")
            detail = "；".join(reasons) if reasons else "自动检查无异常"
            lines.append(f"| {code} | {name} | {lvl} | {detail} |")
    lines.append("")
    lines.append("> 纪律：REJECT=0 才准交付；机械维(C/P)+初筛维(R/T/W)自动检查，"
                 "策略/逻辑/证据/风险维(L/S/V/E)须执业律师人工确认，不自动阻断（守零误报）。")
    lines.append("> 规范源：`lti_dimensions_v9.json`。深度 R/C/T/P 建议并行调用既有 `lti_gate.py`。")

    report = "\n".join(lines)
    print(report)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"\n📄 报告已写：{args.report}")

    # 可选：调用 legacy gate 做深度 R/C/T/P
    if args.legacy_gate and os.path.exists(args.legacy_gate):
        print(f"\n── 并行调用既有 lti_gate.py（best-effort）──")
        os.system(f'{sys.executable} "{args.legacy_gate}" "{args.doc}"')

    # 审计落盘：S/V/W/E 命中趋势真实写入 jsonl（best-effort，绝不编造）
    write_audit(args.doc, verdict, findings, manual_status)

    return 1 if verdict == "REJECT" else 0


if __name__ == "__main__":
    sys.exit(main())
