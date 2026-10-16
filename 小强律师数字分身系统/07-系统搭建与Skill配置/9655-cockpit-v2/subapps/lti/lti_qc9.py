#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LTI 九维文本质检运行器 (lti_qc9.py)  v4.9.2
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
      "法条现行有效", "条号款项项号精确", "引用与事实主张配对", "已查但书例外", "无新法/特别法冲突",
      "法条银行回查：引用法名须匹配本地 statute 卡，cite_ready=false 不可条号级引用"]),
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


# ---------------------------------------------------------------------------
# 法条银行回查（v4.9.1 新增 · R-fb001/R-fb002 · v4.9.2 翻转默认）
# 背景：法条银行 106+ 张卡已有 cite_ready 字段（true=可安全条号级引用），
#       但该字段此前只是「标记」未接门禁。本函数把它接进 R 维度初筛：
#       文书引用《xxx》时，回查本地法条银行对应卡的 cite_ready，
#       false 即提示本地卡不可直引（版本漂移/空壳/重定向桩）。
# 纪律（守 LTI「宁漏勿误·零误报」底线）：
#   - 【v4.9.2 翻转】默认已升为 REJECT 硬闸门：命中 cite_ready=false 即阻断交付，
#     杜绝「起草流程靠人记得看 gate」的疏漏（2026-10-15 收官复盘决议）。
#   - --lenient-fatiao 为回退阀：降级为 WARN 不阻断（用于文书确引外部权威源、
#     本地库滞后等须人工判断的场景），老强可按需开启。
#   - --strict-fatiao 保留为兼容旧调用（现即为默认行为，等效 no-op）。
#   - 匹配不到卡不提示：本地库非全量，无卡 ≠ 无法可引。
# ---------------------------------------------------------------------------
FATIAO_BANK_CANDIDATES = [
    "/Users/chenyouqiang/Documents/LawKB/法条银行",
]


def _find_bank():
    for p in FATIAO_BANK_CANDIDATES:
        if os.path.isdir(p):
            return p
    return None


def _load_bank_index():
    """扫描法条银行 statute 卡，返回 [{file, cite_ready, content_status, article_count}]"""
    bank = _find_bank()
    if not bank:
        return []
    idx = []
    skip_dirs = {"_archive", "银行治理层"}
    for dp, dn, fn in os.walk(bank):
        dn[:] = [d for d in dn if d not in skip_dirs]
        for name in fn:
            if not name.endswith(".md"):
                continue
            p = os.path.join(dp, name)
            try:
                t = open(p, encoding="utf-8").read()
            except Exception:
                continue
            if not t.startswith("---"):
                continue
            ls = t.split("\n")
            close = None
            for i in range(1, len(ls)):
                if ls[i].strip() == "---":
                    close = i
                    break
            if close is None:
                continue
            fm = "\n".join(ls[1:close])
            if not re.search(r"^type:\s*statute\s*$", fm, re.M):
                continue
            cr = re.search(r"^cite_ready:\s*(\S+)", fm, re.M)
            cs = re.search(r"^content_status:\s*(\S+)", fm, re.M)
            idx.append({
                "file": name[:-3],
                "cite_ready": cr.group(1) if cr else "?",
                "content_status": cs.group(1) if cs else "?",
            })
    return idx


def _norm_name(s):
    """归一化法名：去空格、去版本/文号后缀与「·标记后缀」，便于模糊匹配。
    「·XXXX」后缀（如 ·2025修正 / ·关键条文回填版 / ·2023修正）是版本或标记，
    非不同法，须与「（主席令…）」文号一并剥离——否则旧版/桩卡文件名带后缀，
    真实引用《法名（令号）》归一化后对其不上，R-fb001 永远触发不了（v4.9.2 修复）。"""
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"[（(].*?[）)]", "", s)
    s = re.sub(r"[·•].*$", "", s)  # 剥版本/标记后缀
    return s


# 常见机关/主体前缀——规范法名常带而本地卡文件名常省略，匹配前剥离
_PREFIX_STRIP = [
    "最高人民法院", "最高人民检察院", "中华人民共和国", "国务院",
    "公安部", "民政部", "国家卫生健康委员会", "国家卫生健康委", "国家卫生计生委",
    "国家医疗保障局", "国家药品监督管理局", "国家市场监督管理总局",
    "中国证券监督管理委员会", "中国银行保险监督管理委员会",
]


def _core_name(s):
    """进一步剥离机关前缀，取核心法名"""
    for p in _PREFIX_STRIP:
        if s.startswith(p):
            s = s[len(p):]
    return s


def _lcs_len(a, b):
    """最长公共子串长度（用于判断两个法名是否指向同一部法）"""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i-1] == b[j-1]:
                cur[j] = prev[j-1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


# 虚词/骨架字符：这些字的差异不影响法名指向同一部法
# （"若干" vs "问题"、"最高人民法院" vs 无前缀 等表述差异）
_VAGUE_CHARS = set(
    "若干问题最高人民法检院察国务院公安部民政的中华共和国"
    "和国卫生健康医疗保障药品监督市场证券银行保险"
    "管理委员会议定办法暂行试行版修订正案"
    "一二三四五六七八九十〇零关于适用解"
)


def _real_diff(a, b):
    """两侧独有的实义字符集合（剔除虚词后的差异）"""
    sa, sb = set(a), set(b)
    return (sa - sb) - _VAGUE_CHARS, (sb - sa) - _VAGUE_CHARS


def _same_law(cited_name, file_name):
    """判断文书引用的法名与库卡文件名是否指向同一部法。
    双保险：① 骨架足够长（LCS≥8）② 实义字符无冲突（无独有实义字）。
    防误配：买卖合同 ↔ 技术合同 共享长骨架「关于审理…纠纷案件适用法律…
    若干问题」，但『买卖』与『技术』为实义独有字 → 判为不同法。"""
    a, b = _norm_name(cited_name), _norm_name(file_name)
    if a == b:
        return True
    if _lcs_len(a, b) < 8:
        return False
    oa, ob = _real_diff(a, b)
    return not oa and not ob


def check_R_fatiao_bank(text, strict=True):
    """文书引用 → 法条银行 cite_ready 回查"""
    f = []
    idx = _load_bank_index()
    if not idx:
        return f  # 库不可用：不提示（无回源≠有问题），由人工按铁律处理

    # 提取文书中的《法名》
    cited = re.findall(r"《([^》]{2,60})》", text)
    if not cited:
        return f

    bank_norm = {}
    for it in idx:
        k = _norm_name(it["file"])
        prev = bank_norm.get(k)
        # 同名/近名多卡时，优先保留 cite_ready=true 的现行主卡
        # （如技术合同解释同时存在 2004 旧版桩卡 false 与 2020 现行主卡 true，
        #  引用规范法名应命中现行主卡，不因遍历顺序不确定而误取旧版）
        if prev is None or (prev["cite_ready"] != "true" and it["cite_ready"] == "true"):
            bank_norm[k] = it

    seen = set()
    for c in cited:
        cn = _norm_name(c)
        if cn in seen:
            continue
        seen.add(cn)
        hit = bank_norm.get(cn)
        if hit is None:
            # 层级1：机关前缀剥离后精确匹配
            ck = _core_name(cn)
            for k, it in bank_norm.items():
                if _core_name(k) == ck:
                    hit = it
                    break
        if hit is None:
            # 层级2：骨架匹配（LCS≥8）且实义字符无冲突
            # （应对"若干/问题""有/无机关前缀"等表述差异，同时防止
            #   买卖合同 ↔ 技术合同 这类共享骨架的误配）
            best_len, best_it = 0, None
            for k, it in bank_norm.items():
                if _lcs_len(cn, k) < 8:
                    continue
                if not _same_law(c, it["file"]):
                    continue
                if _lcs_len(cn, k) > best_len:
                    best_len, best_it = _lcs_len(cn, k), it
            if best_it is not None:
                hit = best_it
        if hit is None:
            continue  # 本地无该卡：不提示
        if hit["cite_ready"] == "false":
            lvl = "REJECT" if strict else "WARN"
            f.append((lvl, "R-fb001",
                      f"法条银行回查：『{c}』对应卡 `{hit['file']}` "
                      f"cite_ready=false（{hit['content_status']}），本地卡不可条号级引用——"
                      f"请确认已改用现行版本，勿引旧版/空壳"))
        elif hit["cite_ready"] == "?":
            f.append(("WARN", "R-fb002",
                      f"法条银行回查：『{c}』对应卡 `{hit['file']}` 缺 cite_ready 字段，"
                      f"请先跑 fatiao_g4_upgrade.py 补标"))
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
        "version": "4.9.2",
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
    ap = argparse.ArgumentParser(description="LTI 九维文本质检运行器 v4.9.2")
    ap.add_argument("doc", help="待质检文书 .docx/.md/.txt")
    ap.add_argument("--report", help="输出 markdown 报告路径")
    ap.add_argument("--manual", default="",
                    help="人工确认维结果，如 L=pass S=warn V=warn E=warn")
    ap.add_argument("--legacy-gate", default="",
                    help="可选：调用既有 lti_gate.py 做 R/C/T/P 深度校验（best-effort）")
    ap.add_argument("--interactive", action="store_true",
                    help="开启逐维人工问询（仅本地真终端使用；默认非交互，人工维记 warn 不阻断）")
    ap.add_argument("--lenient-fatiao", action="store_true", dest="lenient_fatiao",
                    help="法条银行回查宽松模式：cite_ready=false 仅 WARN 不阻断（默认已升为 REJECT 硬闸门，本开关为回退阀）")
    ap.add_argument("--strict-fatiao", action="store_true", dest="strict_fatiao",
                    help="（兼容旧调用）法条银行回查严格模式：cite_ready=false 升为 REJECT（现为默认行为）")
    ap.add_argument("--no-fatiao-bank", action="store_true", dest="no_fatiao_bank",
                    help="关闭法条银行回查")
    args = ap.parse_args()

    if not os.path.exists(args.doc):
        print(f"❌ 文件不存在: {args.doc}")
        return 2

    print(f"======== LTI 九维质检 (v4.9.2) ========")
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

    # v4.9.2 法条银行回查（R 维度初筛·cite_ready；默认 REJECT 硬闸门）
    if not getattr(args, "no_fatiao_bank", False):
        fb = check_R_fatiao_bank(text, strict=not getattr(args, "lenient_fatiao", False))
        findings["R"].extend(fb)
        if fb:
            n_rf = sum(1 for l, r, _ in fb if l == "REJECT")
            n_wf = sum(1 for l, r, _ in fb if l == "WARN")
            print(f"🔎 法条银行回查：{len(fb)} 项命中"
                  f"（❌{n_rf} / ⚠️{n_wf}）"
                  f"{'［宽松模式：cite_ready=false 仅 WARN］' if getattr(args, 'lenient_fatiao', False) else '［默认严格：cite_ready=false 已升 REJECT］'}")
        else:
            print("🔎 法条银行回查：无可疑引用（或本地无对应卡）")

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
    lines = [f"# LTI 九维质检报告（v4.9.2）", "", f"- 文书：`{os.path.basename(args.doc)}`",
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
