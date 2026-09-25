#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_rule_package.py — 规则包生成器（B 方案 P0-3 · 参数化版）
================================================================
读取真实资产 → 按域装配标准规则包。支持：
  - 按「域库目录」采集（合同/医疗/慈善合规等单一域库）
  - 按「card_type 横切标签」全局采集（审判要件/裁量尺度等跨域类型）

设计铁律（来自老强系统规则）：
  - 无第三方依赖（不依赖 yaml），frontmatter 用正则解析，避免环境漂移。
  - 只读源、只新建包，绝不改源资产（六-B：源资产只读，导出子集落 OPC）。
  - 剔除「关联（知识飞轮连接层自动补链 …）」自动段（内部噪音，不入包）。
  - yuandian_source_pending=true 的卡 → 标 source_pending，绝不冒充权威法源。
  - 个案卷宗/当事人隐私不入包；包内资产须来自登记册实测（本包为导出子集）。

用法：
  python3 gen_rule_package.py --domain 慈善合规          # 生成指定域完整包
  python3 gen_rule_package.py --domain 合同 --dry        # 仅打印命中统计，不写文件
  python3 gen_rule_package.py --list                    # 列出可生成域
"""
import os
import re
import json
import argparse
import datetime

ROOT = os.path.expanduser("~/Documents/LawKB")
DOMAIN_LIB   = os.path.join(ROOT, "知识飞轮系统/06-沉淀")
LAW_BANK     = os.path.join(ROOT, "法条银行")
PKG_ROOT     = os.path.join(ROOT, "OPC 一人公司/01-规则包")
TODAY = datetime.date.today().isoformat()

# ----------------------------------------------------------------------------
# 域配置：每个域指定卡片源 + 法条源 + 内规源 + 经验卡源 + 计费域 + 输出命名
#   card_dir        : 单一域库目录（按目录采集全部 R-*.md）
#   card_type       : 横切标签——在 06-沉淀 全库按 frontmatter.card_type 筛选
#   title_contains  : 横切补充——标题含任一关键字即入选（与 card_type 取并集）
#   laws_dir / laws_title_contains : 法条源（可选 + 标题筛选）
#   manual_path     : 内规手册（可选；无则包内标注"本域暂无专属内规手册"）
#   exp_card_dirs   : 经验卡目录列表（可选）
# ----------------------------------------------------------------------------
DOMAIN_CONFIG = {
    "慈善合规": {
        "label": "慈善合规规则包",
        "card_dir": "知识飞轮系统/06-沉淀/慈善合规域库",
        "card_type": None, "title_contains": None,
        "laws_dir": "法条银行/慈善合规类法律法规", "laws_title_contains": None,
        "manual_path": "知识库/慈法知识库/慈善组织法律顾问实务与合规建设/基金会合规管理手册（试行）（2025版）.md",
        "exp_card_dirs": ["小德合规管理系统/03-经验卡片/慈法合规"],
        "billing_domain": "慈善合规",
        "rules_file": "charity_rules.json", "assembly_title": "慈善合规规则汇编",
        "desc": "慈善组织（基金会、慈善总会、社会服务机构）合规运营",
    },
    "合同": {
        "label": "合同风险规则包",
        "card_dir": "知识飞轮系统/06-沉淀/合同风险规则库",
        "card_type": None, "title_contains": None,
        "laws_dir": "法条银行/通用实体法", "laws_title_contains": ["合同", "民法典"],
        "manual_path": None,
        "exp_card_dirs": ["小德合规管理系统/03-经验卡片/合同合规"],
        "billing_domain": "合同风险",
        "rules_file": "contract_rules.json", "assembly_title": "合同风险规则汇编",
        "desc": "合同起草/审查/履约/争议全周期风险识别与处置",
    },
    "医疗": {
        "label": "医疗人伤规则包",
        "card_dir": "知识飞轮系统/06-沉淀/人伤法域库/医疗人损",
        "card_type": None, "title_contains": None,
        "laws_dir": "法条银行/医事法律法规库", "laws_title_contains": None,
        "manual_path": None,
        "exp_card_dirs": ["小德合规管理系统/03-经验卡片/医疗纠纷章卡", "小德合规管理系统/03-经验卡片/医院合规"],
        "billing_domain": "医疗人伤",
        "rules_file": "medical_rules.json", "assembly_title": "医疗人伤规则汇编",
        "desc": "医疗事故/医疗损害责任纠纷的过错认定、参与度、赔偿规则",
    },
    "审判要件": {
        "label": "审判要件规则包",
        "card_dir": None,
        "card_type": "审判要件", "title_contains": None,
        "laws_dir": "法条银行/程序法", "laws_title_contains": None,
        "manual_path": None,
        "exp_card_dirs": [],
        "billing_domain": "审判要件",
        "rules_file": "trial_elements_rules.json", "assembly_title": "审判要件规则汇编",
        "desc": "跨域横切：各案由审判要件拆解（按 card_type=审判要件 全库筛选）",
    },
    "裁量尺度": {
        "label": "裁量尺度规则包",
        "card_dir": None,
        "card_type": "裁量尺度", "title_contains": ["裁量"],
        "laws_dir": "法条银行/通用实体法", "laws_title_contains": ["裁量", "处罚", "量刑", "刑罚"],
        "manual_path": None,
        "exp_card_dirs": [],
        "billing_domain": "裁量尺度",
        "rules_file": "discretion_rules.json", "assembly_title": "裁量尺度规则汇编",
        "desc": "跨域横切：处罚/赔偿/量刑裁量基准（card_type=裁量尺度 或 标题含'裁量'）",
    },
    # ───────── M1 P1 批量封装：12 个域库（目录模式）─────────
    "案由路由": {
        "label": "案由路由规则包",
        "card_dir": "知识飞轮系统/06-沉淀/案由路由卡族",
        "card_type": None, "title_contains": None,
        "laws_dir": "法条银行/程序法", "laws_title_contains": ["案由", "诉讼"],
        "manual_path": None,
        "exp_card_dirs": [],
        "billing_domain": "案由路由",
        "rules_file": "cause_routing_rules.json", "assembly_title": "案由路由规则汇编",
        "desc": "民事/刑事/行政案件案由识别与管辖路由",
    },
    "证据规则": {
        "label": "证据规则规则包",
        "card_dir": "知识飞轮系统/06-沉淀/证据规则卡族",
        "card_type": None, "title_contains": None,
        "laws_dir": "法条银行/程序法", "laws_title_contains": ["民事诉讼", "刑事", "证据"],
        "manual_path": None,
        "exp_card_dirs": [],
        "billing_domain": "证据规则",
        "rules_file": "evidence_rules.json", "assembly_title": "证据规则汇编",
        "desc": "举证责任/证据资格/证明标准",
    },
    "婚姻家庭": {
        "label": "婚姻家庭规则包",
        "card_dir": "知识飞轮系统/06-沉淀/婚姻家庭域库",
        "card_type": None, "title_contains": None,
        "laws_dir": "法条银行/通用实体法", "laws_title_contains": ["民法典"],
        "manual_path": None,
        "exp_card_dirs": [],
        "billing_domain": "婚姻家庭",
        "rules_file": "family_rules.json", "assembly_title": "婚姻家庭规则汇编",
        "desc": "婚姻/继承/抚养家事纠纷",
    },
    "公司法": {
        "label": "公司法规则包",
        "card_dir": "知识飞轮系统/06-沉淀/公司法域库",
        "card_type": None, "title_contains": None,
        "laws_dir": "法条银行/通用实体法", "laws_title_contains": ["公司", "企业", "商事", "合伙"],
        "manual_path": None,
        "exp_card_dirs": [],
        "billing_domain": "公司法",
        "rules_file": "company_rules.json", "assembly_title": "公司法规则汇编",
        "desc": "公司设立/治理/股权/解散",
    },
    "劳动人事": {
        "label": "劳动人事规则包",
        "card_dir": "知识飞轮系统/06-沉淀/劳动人事域库",
        "card_type": None, "title_contains": None,
        "laws_dir": "法条银行/通用实体法", "laws_title_contains": ["劳动", "劳动合同", "工伤", "社会保险"],
        "manual_path": None,
        "exp_card_dirs": [],
        "billing_domain": "劳动人事",
        "rules_file": "labor_rules.json", "assembly_title": "劳动人事规则汇编",
        "desc": "劳动合同/工伤/社保/人事",
    },
    "律师实务": {
        "label": "律师实务规则包",
        "card_dir": "知识飞轮系统/06-沉淀/律师实务域库",
        "card_type": None, "title_contains": None,
        "laws_dir": "法条银行/通用法律法规", "laws_title_contains": ["律师"],
        "manual_path": None,
        "exp_card_dirs": [],
        "billing_domain": "律师实务",
        "rules_file": "lawyer_rules.json", "assembly_title": "律师实务规则汇编",
        "desc": "律师执业规范/代理/文书",
    },
    "商事纠纷": {
        "label": "商事纠纷规则包",
        "card_dir": "知识飞轮系统/06-沉淀/商事纠纷域库",
        "card_type": None, "title_contains": None,
        "laws_dir": "法条银行/通用实体法", "laws_title_contains": ["商事", "买卖", "合同", "借款"],
        "manual_path": None,
        "exp_card_dirs": [],
        "billing_domain": "商事纠纷",
        "rules_file": "commercial_rules.json", "assembly_title": "商事纠纷规则汇编",
        "desc": "买卖/借款/合同等商事争议",
    },
    "刑事": {
        "label": "刑事规则包",
        "card_dir": "知识飞轮系统/06-沉淀/刑事域库",
        "card_type": None, "title_contains": None,
        "laws_dir": "法条银行/通用实体法", "laws_title_contains": ["刑法", "刑事", "犯罪"],
        "manual_path": None,
        "exp_card_dirs": [],
        "billing_domain": "刑事",
        "rules_file": "criminal_rules.json", "assembly_title": "刑事规则汇编",
        "desc": "罪名/构成要件/量刑",
    },
    "合规": {
        "label": "合规规则包",
        "card_dir": "知识飞轮系统/06-沉淀/合规域库",
        "card_type": None, "title_contains": None,
        "laws_dir": "法条银行/监管类", "laws_title_contains": ["合规", "监管", "行政"],
        "manual_path": None,
        "exp_card_dirs": [],
        "billing_domain": "合规",
        "rules_file": "compliance_rules.json", "assembly_title": "合规规则汇编",
        "desc": "企业合规/监管/行政合规",
    },
    "建设工程": {
        "label": "建设工程规则包",
        "card_dir": "知识飞轮系统/06-沉淀/建设工程域库",
        "card_type": None, "title_contains": None,
        "laws_dir": "法条银行/通用实体法", "laws_title_contains": ["民法典"],
        "manual_path": None,
        "exp_card_dirs": [],
        "billing_domain": "建设工程",
        "rules_file": "construction_rules.json", "assembly_title": "建设工程规则汇编",
        "desc": "施工/发包/工程量/价款",
    },
    "通用裁判": {
        "label": "通用裁判规则包",
        "card_dir": "知识飞轮系统/06-沉淀/通用裁判规则库",
        "card_type": None, "title_contains": None,
        "laws_dir": "法条银行/程序法", "laws_title_contains": ["裁判", "诉讼", "审判"],
        "manual_path": None,
        "exp_card_dirs": [],
        "billing_domain": "通用裁判",
        "rules_file": "general_adjudication_rules.json", "assembly_title": "通用裁判规则汇编",
        "desc": "通用审判/诉讼规则",
    },
    "案例库": {
        "label": "案例规则包",
        "card_dir": "知识飞轮系统/06-沉淀/案例库",
        "card_type": None, "title_contains": None,
        "laws_dir": "法条银行/最高院指导案例", "laws_title_contains": None,
        "manual_path": None,
        "exp_card_dirs": [],
        "billing_domain": "案例",
        "rules_file": "case_rules.json", "assembly_title": "案例规则汇编",
        "desc": "类案与指导案例参考（本域以案例为主，法条源配最高院指导案例）",
    },
    "人伤法": {
        "label": "人伤法规则包",
        "card_dir": "知识飞轮系统/06-沉淀/人伤法域库",
        "card_type": None, "title_contains": None,
        "laws_dir": "法条银行/司法解释", "laws_title_contains": ["人身损害", "医疗损害", "道路", "交通", "精神损害"],
        "manual_path": None,
        "exp_card_dirs": [],
        "billing_domain": "人伤法",
        "rules_file": "personal_injury_rules.json", "assembly_title": "人伤法规则汇编",
        "desc": "人身损害（医疗/工伤/交通/其他）纠纷：过错认定、参与度、赔偿规则",
    },
}

# ───────────────────────── frontmatter 解析（无 yaml） ─────────────────────────
def parse_frontmatter(text):
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)$', text, re.S)
    if not m:
        return {}, text
    fm_raw, body = m.group(1), m.group(2)
    fm, cur_list, cur_key = {}, None, None
    for line in fm_raw.splitlines():
        if line.startswith('- '):
            if cur_list is not None:
                cur_list.append(line[2:].strip())
            continue
        mm = re.match(r'^([\w]+)\s*:\s*(.*)$', line)
        if mm:
            key, val = mm.group(1), mm.group(2).strip()
            if val == '':
                cur_list, cur_key = [], key
                fm[key] = cur_list
            else:
                fm[key] = val
                cur_list, cur_key = None, None
    return fm, body

def clean_md(t):
    if not t:
        return ""
    t = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', t)       # wikilink 别名形式 → 显示名
    t = re.sub(r'\[\[([^\]]+)\]\]', r'\1', t)                   # wikilink 纯形式
    t = re.sub(r'==([^=]+)==', r'\1', t)                       # 强调 ==
    t = re.sub(r'`+', '', t)                                    # 行内代码
    t = re.sub(r'\n{3,}', '\n\n', t).strip()
    return t

def strip_quotes(s):
    s = (s or "").strip()
    if len(s) >= 2 and s[0] in '"\'“\'' and s[-1] in '"\'”':
        return s[1:-1].strip()
    return s

# ───────────────────────── 正文分段 ─────────────────────────
SEC_RE = re.compile(r'^##\s+(.+?)\s*$', re.M)
AUTO_LINK_RE = re.compile(r'关联（知识飞轮连接层自动补链')
def parse_sections(body):
    secs, matches = {}, list(SEC_RE.finditer(body))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start, end = m.end(), (matches[i+1].start() if i+1 < len(matches) else len(body))
        if AUTO_LINK_RE.search(title):
            continue  # 剔除自动补链段
        secs[title] = body[start:end].strip()
    return secs

META_KEYWORDS = ['关联案件', '原文索引', '相关笔记', '关联（', '索引', '备注', '来源', '相关链接', '飞轮源']
def is_meta_section(title):
    return any(k in title for k in META_KEYWORDS)

def pick(secs, *needles):
    for title, content in secs.items():
        for n in needles:
            if n in title:
                return clean_md(content)
    return ""

def content_sections(secs):
    return {t: clean_md(c) for t, c in secs.items() if not is_meta_section(t) and clean_md(c)}

# ───────────────────────── 1. 规则卡采集（目录 / 横切双模式） ─────────────────────────
CARD_RE = re.compile(r'^R-.*\.md$')

def iter_rfiles(base):
    for dp, _, fs in os.walk(base):
        if os.path.basename(dp).startswith('.'):
            continue
        for f in fs:
            if CARD_RE.match(f):
                yield os.path.join(dp, f)

def card_keep(fm, title, cfg):
    """入选判定：目录模式全收；横切模式按 card_type / title_contains（并集）"""
    if cfg.get("card_dir"):
        return True
    ct = cfg.get("card_type")
    tc = cfg.get("title_contains") or []
    if ct and any(t in str(fm.get("card_type", "")) for t in ([ct] if isinstance(ct, str) else ct)):
        return True
    if tc and any(t in title for t in tc):
        return True
    return False

def collect_rules(cfg, dry=False):
    rules, hit_log, q = [], [], {'source_pending': 0, 'no_summary': 0, 'no_keypoints': 0}
    pending_ids = []
    base = os.path.join(ROOT, cfg["card_dir"]) if cfg.get("card_dir") else DOMAIN_LIB
    for path in iter_rfiles(base):
        try:
            text = open(path, encoding="utf-8").read()
        except Exception:
            continue
        fm, body = parse_frontmatter(text)
        rule_id = str(fm.get("rule_id", "")).strip()
        if not rule_id:
            continue
        title = strip_quotes(str(fm.get("title", "")).strip())
        if not card_keep(fm, title, cfg):
            continue
        secs = parse_sections(body)
        csecs = content_sections(secs)
        summary = pick(secs, "规则摘要") or (next(iter(csecs.values())) if csecs else "")
        keypoints = pick(secs, "适用要点") or (max(csecs.values(), key=len) if csecs else "")
        anti = pick(secs, "反例", "常见错误")
        related = fm.get("related_links") or []
        if not isinstance(related, list):
            related = [related]
        pending = str(fm.get("yuandian_source_pending", "")).strip().lower() == "true"
        if pending:
            q['source_pending'] += 1
            pending_ids.append(rule_id)
        if not summary:
            q['no_summary'] += 1
        if not keypoints:
            q['no_keypoints'] += 1
        rules.append({
            "rule_id": rule_id, "title": title,
            "card_type": fm.get("card_type", ""), "updated": fm.get("updated", ""),
            "tags": fm.get("tags") or [], "source_pending": pending,
            "summary": summary, "key_points": keypoints,
            "anti_patterns": anti, "related": related, "sections": csecs,
        })
        hit_log.append((rule_id, title, "待核验源" if pending else "ok"))
    rules.sort(key=lambda r: r["rule_id"])
    return rules, hit_log, q, pending_ids

# ───────────────────────── 2. 法律法规 ─────────────────────────
def collect_laws(cfg):
    laws = []
    if not cfg.get("laws_dir"):
        return laws
    d = os.path.join(ROOT, cfg["laws_dir"])
    if not os.path.isdir(d):
        return laws
    tcs = cfg.get("laws_title_contains") or []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".md"):
            continue
        try:
            text = open(os.path.join(d, fn), encoding="utf-8").read()
        except Exception:
            continue
        fm, _ = parse_frontmatter(text)
        title = str(fm.get("title", fn)).strip()
        if tcs and not any(t in title for t in tcs):
            continue
        laws.append({
            "file": fn, "title": title,
            "发文字号": fm.get("发文字号", ""), "制定机关": fm.get("制定机关", ""),
            "发布日期": fm.get("发布日期", ""), "施行日期": fm.get("施行日期", ""),
            "时效性": fm.get("时效性", ""), "效力级别": fm.get("效力级别", ""),
            "核验源": fm.get("核验源", ""), "verify_date": fm.get("verify_date", ""),
        })
    return laws

# ───────────────────────── 3. 内规手册（章节索引） ─────────────────────────
def collect_manual(cfg):
    mp = cfg.get("manual_path")
    if not mp or not os.path.isfile(os.path.join(ROOT, mp)):
        return {"file": "", "chapters": [], "article_count": 0,
                "note": "本域暂无专属内规手册（入包以法律法规 + 规则卡为主）"}
    text = open(os.path.join(ROOT, mp), encoding="utf-8").read()
    chapters, sections = [], []
    for line in text.splitlines():
        m = re.match(r'^##\s+(.+?)\s*$', line)
        if m:
            chapters.append(clean_md(m.group(1)))
        m2 = re.match(r'^###\s+(.+?)\s*$', line)
        if m2:
            sections.append(clean_md(m2.group(1)))
    arts = sorted(set(re.findall(r'第[一二三四五六七八九十百零〇]+条', text)))
    return {"file": mp, "chapters": chapters, "sections": sections,
            "article_count": len(arts), "note": "按正文实抽唯一'第X条'计数，允许小幅口径差。"}

# ───────────────────────── 4. 经验卡（多目录） ─────────────────────────
def collect_exp_cards(cfg):
    cards = []
    for ed in (cfg.get("exp_card_dirs") or []):
        d = os.path.join(ROOT, ed)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".md"):
                continue
            try:
                text = open(os.path.join(d, fn), encoding="utf-8").read()
            except Exception:
                continue
            fm, body = parse_frontmatter(text)
            title = strip_quotes(str(fm.get("title", fn)).strip())
            secs = parse_sections(body)
            summary = ""
            for t in secs.values():
                summary = clean_md(t)
                if len(summary) > 30:
                    break
            cards.append({"file": fn, "title": title, "summary": summary[:200]})
    return cards

# ───────────────────────── 5. 自查清单（从规则卡派生） ─────────────────────────
def collect_checklists(rules):
    return [{"rule_id": r["rule_id"], "title": r["title"]}
            for r in rules if ("清单" in r["title"] or "自查" in r["title"])]

# ───────────────────────── 写出 ─────────────────────────
def write_text(p, s):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)

def build_manifest(cfg, rules, laws, manual, exp, cl, q, pending_ids):
    return {
        "package": cfg["label"], "domain": cfg["domain_key"], "version": "v1.0",
        "generated": TODAY,
        "generator": "gen_rule_package.py（B方案P0-3·参数化·无依赖导出）",
        "source_of_truth": "数字资产登记册（OPC 一人公司/00-数字资产登记册/asset_registry.json）",
        "selection": {
            "mode": "目录" if cfg.get("card_dir") else "横切标签",
            "card_dir": cfg.get("card_dir"), "card_type": cfg.get("card_type"),
            "title_contains": cfg.get("title_contains"),
        },
        "billing": {
            "model": "subscription_by_domain",
            "license_type": "internal_commercial_unit",
            "pricing_owner": "运营部门负责人（定价与定位由运营部门核定，本席只交付规则包质量）",
            "price": "由运营部门负责人核定（本席不代定商务）",
            "scope": "单域订阅；跨域需另购对应域包",
            "redlines": [
                "个案卷宗/当事人隐私绝不入包",
                "包内资产须来自登记册实测，禁编造清单",
                "yuandian_source_pending=true 的条目标'待核验源'，不冒充权威法源"],
        },
        "asset_inventory": {
            "rules": len(rules), "laws": len(laws),
            "internal_manual_articles": manual.get("article_count", 0),
            "experience_cards": len(exp), "checklists": len(cl),
        },
        "quality_report": {
            "source_pending_count": q['source_pending'], "source_pending_ids": pending_ids,
            "missing_summary_count": q['no_summary'], "missing_keypoints_count": q['no_keypoints'],
        },
    }

def build_readme(mf, cfg):
    inv = mf["asset_inventory"]
    return f"""# {cfg['label']} · 使用说明（{mf['version']}）

> 适用域：{cfg['desc']}
> 生成日期：{mf['generated']} ｜ 计费模式：{mf['billing']['model']} ｜ 许可：{mf['billing']['license_type']}
> 采集模式：{mf['selection']['mode']}（{('目录 '+str(mf['selection']['card_dir'])) if mf['selection']['card_dir'] else ('card_type='+str(mf['selection']['card_type'])+' / title_contains='+str(mf['selection']['title_contains']))}）

## 一、这个包是什么
本包是把「{cfg['billing_domain']}」领域的数字资产（规则卡 / 法律法规 / 内规手册 / 经验卡 / 自查清单）**标准化封装**后，
交付给**运营部门**（内部虚构商业化单元）订阅使用的规则集合。本席只负责把包的质量做高，定价与定位由运营部门负责人核定。

## 二、交付物清单
| 资产 | 数量 | 位置 |
|---|---|---|
| {cfg['billing_domain']}规则卡 | {inv['rules']} 张 | `assets/rules/{cfg['rules_file']}` |
| 法律法规 | {inv['laws']} 部 | `assets/laws/laws_index.json` |
| 内规手册 | {inv['internal_manual_articles']} 条（章节索引） | `assets/internal/internal_index.json` |
| 经验卡 | {inv['experience_cards']} 张 | `assets/cards/` |
| 自查清单 | {inv['checklists']} 份 | `assets/checklists/checklists_index.json` |

## 三、使用限制
- 仅限内部虚构商业化单元订阅使用，**非对外公开售卖**。
- 含「待核验源」标记的条目（共 {mf['quality_report']['source_pending_count']} 条，清单见 `assets/rules/source_pending_list.json`），商用前须由运营/合规负责人复核法源（元典核验）。
- 个案卷宗、当事人隐私**绝不**进入本包。

## 四、更新与订阅
- 本包随源资产迭代；版本号与 `CHANGELOG.md` 同步。
- 计费与订阅档位由运营部门负责人核定（见 `manifest.json › billing`）。
"""

def build_license():
    return """# 商业化授权条款（内部虚构商业化单元）

1. **授权对象**：本包授权给「运营部门」（一人公司内部虚构商业化单元）订阅使用。
2. **许可类型**：`internal_commercial_unit` —— 内部商业化封装，非对外公开售卖。
3. **定价权**：本包订阅价格、定位、对外商务条件，由**运营部门负责人**独立核定；规则包制作方（数字资产运维官）不参与定价。
4. **使用边界**：
   - 包内资产须按域订阅使用，跨域需另购对应域包。
   - 含「待核验源」标记的条目，商用前须由运营/合规负责人复核法源。
   - 个案卷宗、当事人隐私信息严禁随包流转。
5. **责任**：本包为合规参考工具，不替代法律意见；重大合规决策须由持证人员/外部律师把关。
"""

def build_changelog(mf, cfg):
    inv = mf["asset_inventory"]
    sel = mf["selection"]
    return f"""# 变更日志 · {cfg['label']}

## {mf['version']} · {mf['generated']}
- 首版交付（B 方案 P0-3 · 参数化生成器）。
- 采集模式：{sel['mode']}（{sel.get('card_dir') or (sel.get('card_type'),)}）。
- 规则卡 {inv['rules']} 张。
- 法律法规 {inv['laws']} 部、内规手册 {inv['internal_manual_articles']} 条章节索引、经验卡 {inv['experience_cards']} 张、自查清单 {inv['checklists']} 份。
- 质量标记：待核验源 {mf['quality_report']['source_pending_count']} 条、缺摘要 {mf['quality_report']['missing_summary_count']} 条、缺要点 {mf['quality_report']['missing_keypoints_count']} 条。
- 定价占位：由运营部门负责人核定（本席不代定）。
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", help="目标域：" + " / ".join(DOMAIN_CONFIG.keys()))
    ap.add_argument("--list", action="store_true", help="列出可生成域")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    if args.list:
        for k, c in DOMAIN_CONFIG.items():
            mode = "目录" if c.get("card_dir") else "横切"
            print(f"  {k}  [{mode}]  {c['billing_domain']}")
        return
    if not args.domain or args.domain not in DOMAIN_CONFIG:
        print("❌ 须指定 --domain，可选：" + " / ".join(DOMAIN_CONFIG.keys()))
        raise SystemExit(2)

    cfg = dict(DOMAIN_CONFIG[args.domain]); cfg["domain_key"] = args.domain
    rules, hit_log, q, pending_ids = collect_rules(cfg)
    laws = collect_laws(cfg)
    manual = collect_manual(cfg)
    exp = collect_exp_cards(cfg)
    cl = collect_checklists(rules)
    mf = build_manifest(cfg, rules, laws, manual, exp, cl, q, pending_ids)

    if args.dry:
        print(f"[dry][{args.domain}] 规则卡 {len(rules)} ｜ 法规 {len(laws)} ｜ 内规 {manual.get('article_count',0)} 条 ｜ 经验卡 {len(exp)} ｜ 清单 {len(cl)}")
        print(f"[dry] 质量：待核验源 {q['source_pending']} ｜ 缺摘要 {q['no_summary']} ｜ 缺要点 {q['no_keypoints']}")
        for rid, title, flag in hit_log[:8]:
            print(f"  {rid}  {title}  [{flag}]")
        if len(hit_log) > 8:
            print(f"  ... 共 {len(hit_log)} 张")
        return

    OUT = os.path.join(PKG_ROOT, f"rule_package_{args.domain}_v1.0")
    write_text(os.path.join(OUT, "manifest.json"), json.dumps(mf, ensure_ascii=False, indent=2))
    write_text(os.path.join(OUT, "README.md"), build_readme(mf, cfg))
    write_text(os.path.join(OUT, "LICENSE_COMMERCIAL.md"), build_license())
    write_text(os.path.join(OUT, "CHANGELOG.md"), build_changelog(mf, cfg))
    write_text(os.path.join(OUT, "assets/rules", cfg["rules_file"]), json.dumps(rules, ensure_ascii=False, indent=2))
    write_text(os.path.join(OUT, "assets/rules/source_pending_list.json"),
               json.dumps({"count": len(pending_ids), "rule_ids": pending_ids}, ensure_ascii=False, indent=2))
    write_text(os.path.join(OUT, "assets/laws/laws_index.json"), json.dumps(laws, ensure_ascii=False, indent=2))
    write_text(os.path.join(OUT, "assets/internal/internal_index.json"), json.dumps(manual, ensure_ascii=False, indent=2))
    write_text(os.path.join(OUT, "assets/cards/exp_cards_index.json"), json.dumps(exp, ensure_ascii=False, indent=2))
    write_text(os.path.join(OUT, "assets/checklists/checklists_index.json"), json.dumps(cl, ensure_ascii=False, indent=2))

    md = [f"# {cfg['assembly_title']}（v1.0·{TODAY}·共 {len(rules)} 张）\n"]
    for r in rules:
        md.append(f"\n## {r['rule_id']} {r['title']}")
        if r['source_pending']:
            md.append("> ⚠️ 待核验源（商用前须复核法源）")
        if r['card_type']:
            md.append(f"\n*类型：{r['card_type']} ｜ 更新：{r['updated']}*")
        if r['summary']:
            md.append(f"\n**规则摘要**\n{r['summary']}")
        if r['key_points'] and r['key_points'] != r['summary']:
            md.append(f"\n**适用要点**\n{r['key_points']}")
        if r['anti_patterns']:
            md.append(f"\n**反例 / 常见错误**\n{r['anti_patterns']}")
    write_text(os.path.join(OUT, "assets/rules", cfg["assembly_title"] + ".md"), "\n".join(md))

    print(f"✅ {cfg['label']} → {OUT}")
    print(f"   规则卡 {len(rules)} ｜ 法规 {len(laws)} ｜ 内规 {manual.get('article_count',0)} 条 ｜ 经验卡 {len(exp)} ｜ 清单 {len(cl)}")
    print(f"   质量：待核验源 {q['source_pending']} ｜ 缺摘要 {q['no_summary']} ｜ 缺要点 {q['no_keypoints']}")

if __name__ == "__main__":
    main()
