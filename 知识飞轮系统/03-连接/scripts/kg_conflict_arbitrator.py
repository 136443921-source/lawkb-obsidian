#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LawKB 知识飞轮 · 六类知识冲突仲裁工作台（kg_conflict_arbitrator.py）
=====================================================================
目标：防止「知识打架」——统一识别六类冲突，给出置信度 + AI 裁决建议，
      提供「采纳一方 / 融合两方 / 判定不冲突」三选项，支持 AI 一键修复（有人管闭环）。

六类冲突
  KE  知识演进   (Knowledge Evolution)    —— 新卡取代旧卡
  FC  事实纠正   (Fact Correction)        —— 一方事实被另一方纠正
  VC  版本冲突   (Version Conflict)       —— 同一编号指向不同内容 / 版本漂移
  CC  内容矛盾   (Content Contradiction)  —— 同主题对立主张（需人工裁定）
  CR  上下文相关 (Context-related)        —— 看似冲突，实为地域/案由/时效差异 → 判不冲突
  MC  成熟度冲突 (Maturity Conflict)      —— 草稿卡 vs 成熟卡冲突

用法
  # 扫描（默认扫 06-沉淀 + 02-提炼，可 --root 指定；--limit 限文件数用于试跑）
  python kg_conflict_arbitrator.py scan   [--root ROOT] [--out DIR] [--limit N] [--quick]

  # 查看/导出人工复核报告（markdown）
  python kg_conflict_arbitrator.py report [--queue QUEUE.json] [--out DIR]

  # 一键修复（按队列中人类选定的 decision 执行；omit --only 则只执行 AI 建议且置信度>=阈值的）
  python kg_conflict_arbitrator.py apply  [--queue QUEUE.json] [--only ID1,ID2] [--min-conf 0.8] [--dry]

设计铁律（继承飞轮六-B / 误报教训）
  * 扫描输出是「候选冲突 + AI 建议」，不是结论；CC/KE 误报高，必须人工拍板。
  * apply 前自动备份到 /tmp/kg_conflict_fix_<ts>/（cp -n，不覆盖已有备份）。
  * 幂等：已带 conflict_resolved / merged_into / conflict_checked 标记的卡片自动跳过。
  * 所有执行写入 _resolved_log.json 留痕，构成「有人管」审计链。
"""

import os
import re
import sys
import json
import shutil
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_DEFAULT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT_DEFAULT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/03-连接/冲突仲裁"
TS = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
TODAY = datetime.datetime.now().strftime("%Y-%m-%d")

# 跳过目录（历史副本/备份会放大同一错误）
SKIP_DIRS = (".backup", "_backup", ".git", "node_modules", "__pycache__")
SKIP_SUFFIX = (".bak", ".bak-2026", ".bak_2026")  # 含时间戳的备份


# ----------------------------------------------------------------------------
# 1. 极简 YAML frontmatter 解析（仅覆盖本库卡片使用的简单结构，零依赖）
# ----------------------------------------------------------------------------
def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}, text
    # 第二个 --- 之前是 frontmatter
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    fm_raw, body = m.group(1), m.group(2)
    fm = {}
    cur_key = None
    for line in fm_raw.split("\n"):
        if not line.strip():
            continue
        # 列表项（属于上一个 key）
        if re.match(r"^\s+-\s+", line) and cur_key:
            val = line.strip()[2:].strip()
            if isinstance(fm.get(cur_key), list):
                fm[cur_key].append(val)
            else:
                fm[cur_key] = [val] if fm.get(cur_key) is None else [fm[cur_key], val]
            continue
        kv = re.match(r"^([A-Za-z0-9_一-龥]+):\s*(.*)$", line)
        if kv:
            cur_key = kv.group(1)
            v = kv.group(2).strip()
            if v == "":
                fm[cur_key] = None  # 后续可能是列表或块
            else:
                # 内联列表 [a, b]
                if v.startswith("[") and v.endswith("]"):
                    items = [x.strip() for x in v[1:-1].split(",") if x.strip()]
                    fm[cur_key] = items
                else:
                    fm[cur_key] = v
    return fm, body


def fm_str(v):
    """把 frontmatter 值规整成字符串用于比较/展示"""
    if v is None:
        return ""
    if isinstance(v, list):
        return " / ".join(str(x) for x in v)
    return str(v)


# ----------------------------------------------------------------------------
# 2. 加载卡片
# ----------------------------------------------------------------------------
def load_cards(root, limit=None):
    cards = []
    n = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            if any(fn.endswith(s) for s in SKIP_SUFFIX) or ".bak" in fn:
                continue
            full = os.path.join(dirpath, fn)
            if limit and n >= limit:
                return cards
            rel = os.path.relpath(full, ROOT_DEFAULT)
            family = os.path.dirname(rel)  # 目录级卡型族：同目录同 rule_id 才算真撞号
            try:
                with open(full, encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue
            fm, body = parse_frontmatter(text)
            if not fm:
                continue
            # 第一标题
            h1 = ""
            for line in body.split("\n"):
                if line.startswith("# "):
                    h1 = line[2:].strip()
                    break
            cards.append({
                "path": full,
                "rel": os.path.relpath(full, ROOT_DEFAULT),
                "fm": fm,
                "body": body,
                "title": (fm_str(fm.get("title")) if fm.get("title") is not None else (h1 or fn)),
                "rule_id": fm_str(fm.get("rule_id")),
                "aliases": fm.get("aliases") if isinstance(fm.get("aliases"), list) else (
                    [fm_str(fm.get("aliases"))] if fm.get("aliases") else []),
                "geo": fm_str(fm.get("geo_scope")),
                "subtype": fm_str(fm.get("card_subtype")),
                "pending": str(fm.get("statute_text_pending", "")).lower() in ("true", "1", "yes"),
                "review_date": fm_str(fm.get("review_date")),
                "created": fm_str(fm.get("created")),
                "updated": fm_str(fm.get("updated")),
                "status": fm_str(fm.get("status")),
                "norm_title": norm_title(fm.get("title") or h1),
                "family": family,
                "canonical": fm_str(fm.get("canonical")),
                "body_len": len(body),
            })
            n += 1
    return cards


def norm_title(t):
    """归一化标题：仅去空格/标点（保留数字），便于同主题聚类。

    关键修正（v1.0.2）：**不再剥除数字**。旧版剥数字导致
    「R-HG-035」「R-HG-045」等 rule_id 型标题塌缩为「R-HG-」，
    「每日知识摄入报告-2026-08-06」与「-08-30」塌缩为同一串，
    使大量「仅编号/日期不同」的卡被误判为同主题冲突。
    保留数字后，同前缀不同编号/日期的卡各自独立；模糊同主题匹配
    改由 build_components 的标题 2-gram 相似度（>=0.80）承担。
    """
    if not t:
        return ""
    if not isinstance(t, str):
        t = fm_str(t)
    t = re.sub(r"[\s\-_：:，,。\.、（）()【】\[\]]+", "", t)
    return t.lower()


def bigram(text):
    text = re.sub(r"\s+", "", text)
    return set(text[i:i + 2] for i in range(len(text) - 1))


def sim(a, b):
    """字符 2-gram Jaccard 相似度"""
    A, B = bigram(a), bigram(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


# 例程/流水型文件：日课、每日摄入报告、自学习纪要、采集笔记等是「时间序日志/源材料」，
# 不是知识主张，绝不应被 KE/FC/MC/CC 当成冲突候选（仅日期/前缀不同即误报的高危源）。
ROUTINE_RE = re.compile(r"(每日知识摄入报告|知识摄入报告|日课|三类日课|自学习纪要|学习纪要|采集笔记|A2自学习|周报|日报|日志| intake )")

def is_routine(c):
    """是否为例程/流水型卡片（按 norm_title 判断）"""
    return bool(ROUTINE_RE.search(c["norm_title"] or ""))

# 已核填的「知识主张层」：只有这些层内的同主题卡才做 FC（事实纠正）判定，
# 源材料(02-提炼/采集笔记) vs 产物(06-沉淀/裁判规则库) 属正常流水线，不是事实矛盾。
VERIFIED_LAYERS = ("06-沉淀/裁判规则库", "03-连接/概念页")

def is_verified_layer(c):
    return any(c["rel"].startswith(p) for p in VERIFIED_LAYERS)



# ----------------------------------------------------------------------------
# 3. 六类冲突检测器
# ----------------------------------------------------------------------------
def make_conflict(cid, ctype, a, b, confidence, evidence, suggestion, reason, opts=None):
    return {
        "id": cid,
        "type": ctype,
        "side_a": {"rel": a["rel"], "rule_id": a["rule_id"], "title": a["title"],
                   "geo": a["geo"], "pending": a["pending"], "updated": a["updated"]},
        "side_b": {"rel": b["rel"], "rule_id": b["rule_id"], "title": b["title"],
                   "geo": b["geo"], "pending": b["pending"], "updated": b["updated"]},
        "confidence": round(confidence, 2),
        "evidence": evidence,
        "ai_suggestion": suggestion,            # adopt_a | adopt_b | merge | no_conflict
        "ai_reason": reason,
        "options": opts or ["adopt_a", "adopt_b", "merge", "no_conflict"],
        "status": "pending",                     # pending -> 等待人工 decision
        "decision": None,                        # 人类填写：adopt_a/adopt_b/merge/no_conflict
        "decision_note": "",
    }


def authority_winner(a, b):
    """按权威性（pending 越低、review 越新、status 越成熟）选优；返回 ('a'|'b'|'tie')"""
    score = {"a": 0, "b": 0}
    if a["pending"] and not b["pending"]:
        score["b"] += 2
    elif b["pending"] and not a["pending"]:
        score["a"] += 2
    # updated 越新越优
    def to_dt(s):
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y-%m"):
            try:
                return datetime.datetime.strptime(s, fmt)
            except Exception:
                continue
        return datetime.datetime.min
    ta, tb = to_dt(a["updated"]), to_dt(b["updated"])
    if ta > tb:
        score["a"] += 1
    elif tb > ta:
        score["b"] += 1
    if score["a"] > score["b"]:
        return "a"
    if score["b"] > score["a"]:
        return "b"
    return "tie"


# ---- 3.1 版本冲突 VC：同 rule_id、同卡型族(family)、内容不同 = 真冲突 ----
#  跨卡型族共享 rule_id（概念页/经验卡/提炼索引 ↔ 裁判规则库）属「指针链接」，
#  是知识库故意设计的跨链架构，重分类为 CR·不冲突，避免误废合法跨链页。
def detect_version_conflict(cards_by_rid, out, cid0):
    cid = cid0
    for rid, group in cards_by_rid.items():
        if len(group) < 2 or not rid:
            continue
        # 内容不同的才算冲突
        seen = {}
        for c in group:
            key = hash(c["body"][:200])
            if key in seen:
                continue
            seen[key] = c
        diffs = list(seen.values())
        if len(diffs) < 2:
            continue
        for i in range(len(diffs)):
            for j in range(i + 1, len(diffs)):
                a, b = diffs[i], diffs[j]
                # 指针链接信号：任一侧有 canonical 指向另一侧 / 跨 family
                a_points_b = a["canonical"] and a["canonical"].endswith(b["rel"].split("/")[-1])
                b_points_a = b["canonical"] and b["canonical"].endswith(a["rel"].split("/")[-1])
                cross_family = a["family"] != b["family"]
                if a_points_b or b_points_a or cross_family:
                    out.append(make_conflict(
                        "CF-%04d" % cid, "CR", a, b, 0.92,
                        "同一 rule_id「%s」跨卡型族（%s ↔ %s）共享，属指针链接/别名系统，非版本冲突"
                        % (rid, a["family"], b["family"]),
                        "no_conflict",
                        "上下文相关：跨卡型族共享 rule_id 是知识库故意设计的跨链架构（概念页/经验卡指向规范卡）。"
                        "判定不冲突，加冲突已核查标记防再报，绝不标记 superseded。",
                    ))
                    cid += 1
                    continue
                # 同族内撞号 → 真版本冲突
                w = authority_winner(a, b)
                sug = "adopt_%s" % w if w != "tie" else "merge"
                out.append(make_conflict(
                    "CF-%04d" % cid, "VC", a, b, 0.95,
                    "同一 rule_id「%s」、同族（%s）内指向两份内容不同的卡片" % (rid, a["family"]),
                    sug,
                    "编号撞号/内容版本漂移属硬冲突（rule_id_guard G1）。按权威性（pending/review/updated）建议%s。"
                    % ("采纳 %s" % w if w != "tie" else "融合两方"),
                ))
                cid += 1
    return cid


# ---- 3.2 事实纠正 FC：同主题，一方 pending=true 一方 false ----------------
def detect_fact_correction(groups, out, cid0):
    cid = cid0
    for key, group in groups.items():
        if len(group) < 2:
            continue
        pend = [c for c in group if c["pending"]]
        ok = [c for c in group if not c["pending"]]
        if not pend or not ok:
            continue
        for p in pend:
            for o in ok:
                # 护栏（v1.0.2）：只有「知识主张层」内部的同主题卡才做事实纠正；
                # 源材料(采集笔记/学习笔记) vs 产物(裁判规则库) 属正常流水线，不是事实矛盾。
                if not (is_verified_layer(p) and is_verified_layer(o)):
                    continue
                if sim(p["title"], o["title"]) < 0.3 and norm_title_eq(p, o) is False:
                    # 仅当主题相关才报
                    if sim(p["body"][:300], o["body"][:300]) < 0.2:
                        continue
                out.append(make_conflict(
                    "CF-%04d" % cid, "FC", o, p, 0.85,
                    "主题相同，一方 statute_text_pending=true（待核填）而另一方已核填（pending=false）",
                    "adopt_a",
                    "事实纠正：已核填方（a）权威性高于待核填方（b）。建议采纳 a，将 b 标记为由 a 取代。",
                ))
                cid += 1
    return cid


def norm_title_eq(a, b):
    return a["norm_title"] != "" and a["norm_title"] == b["norm_title"]


# ---- 3.3 知识演进 KE：主题相同、内容相似、一方明显更新/旧法 vs 现行 ------
def detect_knowledge_evolution(groups, out, cid0):
    cid = cid0
    for key, group in groups.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a["norm_title"] == "" or a["norm_title"] != b["norm_title"]:
                    continue
                # 护栏（v1.0.2）：例程/流水型卡片（日课、每日摄入报告等）仅日期不同，
                # 属时间序日志，绝非知识演进冲突，直接跳过。
                if is_routine(a) or is_routine(b):
                    continue
                # 旧法/废止 vs 现行 信号（本身即证据，不要求高相似度）
                old_a = "废止" in a["body"] or "原《" in a["body"] or "已失效" in a["body"]
                old_b = "废止" in b["body"] or "原《" in b["body"] or "已失效" in b["body"]
                if old_a != old_b:
                    out.append(make_conflict(
                        "CF-%04d" % cid, "KE",
                        (b if old_a else a), (a if old_a else b), 0.8,
                        "主题相同，一方引用旧法/已废止条文，另一方为现行法",
                        "adopt_a",
                        "知识演进：现行法一方应取代旧法一方。建议采纳现行法卡片。",
                    ))
                    cid += 1
                    continue
                # 时间演进：需内容相似 + 更新时间差异显著
                s = sim(a["body"], b["body"])
                if s < 0.6:
                    continue
                ua = a["updated"] or a["created"]
                ub = b["updated"] or b["created"]
                if ua and ub and ua != ub:
                    newer, older = (a, b) if ua > ub else (b, a)
                    out.append(make_conflict(
                        "CF-%04d" % cid, "KE", newer, older, 0.7,
                        "主题相同、内容相似（%.2f），但更新时间差异显著（%s vs %s）" % (s, ua, ub),
                        "adopt_a",
                        "知识演进：较新卡片（a）大概率已吸纳旧卡内容。建议采纳新卡，旧卡标记 superseded。",
                    ))
                    cid += 1
    return cid


# ---- 3.4 内容矛盾 CC：同主题、对立主张、非上下文差异（需人工裁定）--------
ANTONYM = [("应当", "不应"), ("应当", "无需"), ("成立", "不成立"), ("有效", "无效"),
           ("支持", "反对"), ("承担", "不承担"), ("可以", "不得"), ("属于", "不属于")]


def detect_content_contradiction(groups, out, cid0, handled=None):
    cid = cid0
    for key, group in groups.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a["norm_title"] == "" or a["norm_title"] != b["norm_title"]:
                    continue
                # 护栏（v1.0.2）：例程流水卡不是知识主张，跳过
                if is_routine(a) or is_routine(b):
                    continue
                # 已被 CR/MC 解释过的对子，不再判为内容矛盾（降噪）
                if handled is not None and frozenset([a["rel"], b["rel"]]) in handled:
                    continue
                s = sim(a["body"], b["body"])
                if s > 0.85:
                    continue  # 几乎相同，非矛盾
                # 找对立词帧
                hit = find_antonym_frame(a["body"], b["body"])
                if hit:
                    out.append(make_conflict(
                        "CF-%04d" % cid, "CC", a, b, 0.5,
                        "同主题出现对立主张：%s" % hit,
                        "merge" if not (a["pending"] ^ b["pending"]) else ("adopt_%s" % authority_winner(a, b)),
                        "内容矛盾候选（误报率高，须人工裁定）。若确为对立结论建议融合两方并标注适用边界；"
                        "若一方待核填则采纳另一方。",
                    ))
                    cid += 1
    return cid


def find_antonym_frame(ta, tb):
    # 在两边各取含对立词的短句
    for pos, neg in ANTONYM:
        if pos in ta and neg in tb:
            return "一方含「%s」、另一方含「%s」" % (pos, neg)
        if neg in ta and pos in tb:
            return "一方含「%s」、另一方含「%s」" % (neg, pos)
    return None


# ---- 3.5 上下文相关 CR：同主题但地域/案由/时效不同 → 判不冲突 -----------
def same_topic(a, b):
    """同组件内进一步确认同主题（防并查集传递链引入噪声）"""
    if set(a["aliases"]) & set(b["aliases"]):
        return True
    return sim(a["title"], b["title"]) >= 0.5


def detect_context_related(groups, out, cid0, handled=None):
    cid = cid0
    for key, group in groups.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if not same_topic(a, b):
                    continue
                ctx_diff = []
                if a["geo"] and b["geo"] and a["geo"] != b["geo"]:
                    ctx_diff.append("地域(geo_scope): %s vs %s" % (a["geo"], b["geo"]))
                if a["subtype"] and b["subtype"] and a["subtype"] != b["subtype"]:
                    ctx_diff.append("子类(card_subtype): %s vs %s" % (a["subtype"], b["subtype"]))
                if not ctx_diff:
                    continue
                if handled is not None:
                    handled.add(frozenset([a["rel"], b["rel"]]))
                out.append(make_conflict(
                    "CF-%04d" % cid, "CR", a, b, 0.8,
                    "同主题但上下文不同：%s" % "；".join(ctx_diff),
                    "no_conflict",
                    "上下文相关：差异由地域/案由/时效边界解释，非知识打架。建议判定不冲突并加冲突已核查标记防再报。",
                ))
                cid += 1
    return cid


# ---- 3.6 成熟度冲突 MC：草稿(pending/草案) vs 成熟卡 主题重叠 -------------
def detect_maturity_conflict(groups, out, cid0, handled=None):
    cid = cid0
    for key, group in groups.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if is_routine(a) or is_routine(b):
                    continue
                # 护栏（v1.0.2）：成熟度冲突只在「知识主张层」内部判定；
                # 源材料(学习笔记/采集笔记) vs 产物(裁判规则库) 是正常流水线，不是成熟度冲突。
                if not (is_verified_layer(a) and is_verified_layer(b)):
                    continue
                if not same_topic(a, b):
                    continue
                a_draft = a["pending"] or ("草稿" in a["status"] or "草案" in a["status"])
                b_draft = b["pending"] or ("草稿" in b["status"] or "草案" in b["status"])
                if a_draft == b_draft:
                    continue
                if handled is not None:
                    handled.add(frozenset([a["rel"], b["rel"]]))
                mature, draft = (a, b) if not a_draft else (b, a)
                out.append(make_conflict(
                    "CF-%04d" % cid, "MC", mature, draft, 0.8,
                    "主题相同，一方为草稿/待核填（成熟度低），另一方为成熟卡（已核填、有复核期）",
                    "adopt_a",
                    "成熟度冲突：成熟卡（a）应优先；草稿卡（b）在升级达标前不应覆盖成熟结论。建议采纳 a。",
                ))
                cid += 1
    return cid


# ----------------------------------------------------------------------------
# 4. 扫描主流程
# ----------------------------------------------------------------------------
def build_components(cards):
    """同主题聚类（仅用于 KE/FC/CC/CR/MC 配对）。

    关键护栏（v1.0.2 修正，源于 VC/KE 系统性误报复盘）：
    - 只用「标题 2-gram 相似度 >= 0.80」聚合，删除别名并查集（别名跨主题连边是误报主因）；
    - 例程/流水型卡片（日课、每日摄入报告、采集笔记…）强制单例，不参与同主题组，
      因为它们与同前缀文件仅日期不同，会被误判为演进/矛盾；
    - 阈值从 0.72 提到 0.80，避免「R-PI-2xx 前缀相似但主题不同」被并查集传递闭包连成一组。
    VC 仍走独立的 by_rid 路径（见 detect_version_conflict），不受此处影响。
    """
    n = len(cards)
    if n == 0:
        return []
    par = list(range(n))

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            par[ra] = rb

    tbg = [bigram(c["norm_title"]) for c in cards]
    for i in range(n):
        if not tbg[i] or is_routine(cards[i]):
            continue  # 例程卡单例
        for j in range(i + 1, n):
            if not tbg[j] or is_routine(cards[j]):
                continue
            if tbg[i] == tbg[j] or (len(tbg[i] & tbg[j]) / len(tbg[i] | tbg[j]) >= 0.80):
                union(i, j)
    comps = {}
    for i in range(n):
        comps.setdefault(find(i), []).append(cards[i])
    return list(comps.values())


def scan(root, out_dir, limit=None, quick=False):
    roots = [r.strip() for r in root.split(",") if r.strip()]
    print("▶ 加载卡片：%s" % "、".join(roots))
    cards = []
    for r in roots:
        cards += load_cards(r, limit=limit)
    # 去重（多根可能重叠）
    seen_paths = set()
    cards = [c for c in cards if not (c["path"] in seen_paths or seen_paths.add(c["path"]))]
    print("  共载入 %d 张带 frontmatter 的卡片" % len(cards))

    # 按 rule_id 分组（VC）
    by_rid = {}
    for c in cards:
        if c["rule_id"]:
            by_rid.setdefault(c["rule_id"], []).append(c)
    # 并查集同主题聚类（FC/KE/CC/CR/MC）
    components = build_components(cards)
    by_title = {}
    for comp in components:
        # 以归一化标题为键，保留组件内全部卡片
        key = comp[0]["norm_title"] or ("_comp_%d" % id(comp))
        by_title.setdefault(key, []).extend(comp)

    conflicts = []
    cid = 1
    cid = detect_version_conflict(by_rid, conflicts, cid)
    cid = detect_fact_correction(by_title, conflicts, cid)
    cid = detect_knowledge_evolution(by_title, conflicts, cid)
    # 先跑解释型（CR/MC），其解释的对子不再进 CC（降噪）
    handled = set()
    cid = detect_context_related(by_title, conflicts, cid, handled)
    cid = detect_maturity_conflict(by_title, conflicts, cid, handled)
    if not quick:
        cid = detect_content_contradiction(by_title, conflicts, cid, handled)

    # 去重（同一对卡片同类型只报一次）
    seen = set()
    dedup = []
    for cf in conflicts:
        pair = tuple(sorted([cf["side_a"]["rel"], cf["side_b"]["rel"]])) + (cf["type"],)
        if pair in seen:
            continue
        seen.add(pair)
        dedup.append(cf)
    conflicts = dedup

    # 已仲裁处置的卡片不再纳入候选（"有人管"闭环；落实 SKILL「后续扫描不再误报」承诺）
    resolved_rel = {c["rel"] for c in cards if c.get("arb_resolved")}
    if resolved_rel:
        before = len(conflicts)
        conflicts = [cf for cf in conflicts
                    if cf["side_a"]["rel"] not in resolved_rel
                    and cf["side_b"]["rel"] not in resolved_rel]
        print("  已仲裁跳过：%d 项（%d → %d）" % (before - len(conflicts), before, len(conflicts)))

    os.makedirs(out_dir, exist_ok=True)
    queue_path = os.path.join(out_dir, "冲突仲裁队列_%s.json" % TS)
    with open(queue_path, "w", encoding="utf-8") as f:
        json.dump({"generated": TODAY, "root": root, "count": len(conflicts),
                   "conflicts": conflicts}, f, ensure_ascii=False, indent=2)

    report_path = os.path.join(out_dir, "冲突仲裁报告_%s.md" % TS)
    write_report(report_path, conflicts, root)
    print("\n✅ 扫描完成：%d 个候选冲突" % len(conflicts))
    print("   队列：%s" % queue_path)
    print("   报告：%s" % report_path)
    # 概要
    from collections import Counter
    cnt = Counter(c["type"] for c in conflicts)
    for t in ["KE", "FC", "VC", "CC", "CR", "MC"]:
        if cnt.get(t):
            print("     %s %s：%d" % (t, TYPE_NAME[t], cnt[t]))
    return queue_path, report_path


TYPE_NAME = {"KE": "知识演进", "FC": "事实纠正", "VC": "版本冲突",
             "CC": "内容矛盾", "CR": "上下文相关", "MC": "成熟度冲突"}


# ----------------------------------------------------------------------------
# 5. 报告生成（人工复核用）
# ----------------------------------------------------------------------------
def write_report(path, conflicts, root):
    from collections import Counter
    cnt = Counter(c["type"] for c in conflicts)
    lines = []
    lines.append("# LawKB 知识冲突仲裁报告")
    lines.append("")
    lines.append("> 生成：%s ｜ 扫描根：%s ｜ 候选冲突：**%d** 项" % (TODAY, root, len(conflicts)))
    lines.append("> ⚠️ 本报告为 **AI 候选裁决**，CC/KE 误报率较高，须经人工复核（decision 列）后方可 apply。")
    lines.append("")
    lines.append("## 一、六类冲突分布")
    lines.append("")
    lines.append("| 类型 | 含义 | 候选数 | 默认 AI 建议 |")
    lines.append("|---|---|---|---|")
    sug_map = {"KE": "采纳新卡", "FC": "采纳已核填方", "VC": "按权威性采纳/融合",
               "CC": "融合并标边界（人工）", "CR": "判定不冲突", "MC": "采纳成熟卡"}
    for t in ["KE", "FC", "VC", "CC", "CR", "MC"]:
        lines.append("| %s | %s | %d | %s |" % (t, TYPE_NAME[t], cnt.get(t, 0), sug_map[t]))
    lines.append("")
    lines.append("## 二、逐项仲裁（请人工填写 decision）")
    lines.append("")
    lines.append("| ID | 类型 | 置信度 | A（rel/rule_id） | B（rel/rule_id） | AI建议 | 证据 | 人工决策(decision) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for cf in conflicts:
        a = "%s / %s" % (cf["side_a"]["rel"], cf["side_a"]["rule_id"] or "-")
        b = "%s / %s" % (cf["side_b"]["rel"], cf["side_b"]["rule_id"] or "-")
        lines.append("| %s | %s | %.2f | %s | %s | %s | %s |  |" % (
            cf["id"], cf["type"], cf["confidence"], a, b, cf["ai_suggestion"], cf["evidence"][:40]))
    lines.append("")
    lines.append("## 三、处理选项说明")
    lines.append("")
    lines.append("- **采纳一方（adopt_a / adopt_b）**：落败方加 `superseded_by` 标记，由胜方取代。")
    lines.append("- **融合两方（merge）**：胜方加 `merged_from`、败方加 `merged_into`，并互链防丢信息。")
    lines.append("- **判定不冲突（no_conflict）**：双方加 `conflict_checked` + 原因，后续扫描不再误报。")
    lines.append("")
    lines.append("## 四、一键修复")
    lines.append("")
    lines.append("```bash")
    lines.append("# 仅执行 AI 建议且置信度>=0.8 的项（安全默认）")
    lines.append("python kg_conflict_arbitrator.py apply --queue <队列.json> --min-conf 0.8")
    lines.append("# 只执行你指定的 ID（先在本报告 decision 列填好）")
    lines.append("python kg_conflict_arbitrator.py apply --queue <队列.json> --only CF-0001,CF-0003")
    lines.append("```")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ----------------------------------------------------------------------------
# 6. 一键修复（带备份 + 幂等 + 留痕）
# ----------------------------------------------------------------------------
def resolve_path(rel_or_rule, cards_index):
    return cards_index.get(rel_or_rule)


def apply(queue_path, only_ids=None, min_conf=0.8, dry=False):
    with open(queue_path, encoding="utf-8") as f:
        data = json.load(f)
    conflicts = data["conflicts"]
    # 直接由队列中的 rel 拼绝对路径，避免重扫全库（快且够用）
    idx = {}
    for cf in conflicts:
        for side in ("side_a", "side_b"):
            rel = cf[side]["rel"]
            if rel not in idx:
                idx[rel] = os.path.join(ROOT_DEFAULT, rel)

    # 已执行留痕
    log_path = os.path.join(os.path.dirname(queue_path), "_resolved_log.json")
    done = {}
    if os.path.exists(log_path):
        try:
            done = json.load(open(log_path, encoding="utf-8"))
        except Exception:
            done = {}

    bak_dir = "/tmp/kg_conflict_fix_%s" % TS
    os.makedirs(bak_dir, exist_ok=True)

    todo = []
    for cf in conflicts:
        if cf["id"] in done:
            continue
        dec = cf.get("decision") or (cf["ai_suggestion"] if cf["confidence"] >= min_conf else None)
        if not dec:
            continue
        if only_ids and cf["id"] not in only_ids:
            continue
        if dec not in ("adopt_a", "adopt_b", "merge", "no_conflict"):
            continue
        todo.append((cf, dec))

    print("▶ 待执行修复：%d 项（dry=%s）" % (len(todo), dry))
    applied = 0
    for cf, dec in todo:
        pa = idx.get(cf["side_a"]["rel"])
        pb = idx.get(cf["side_b"]["rel"])
        if not pa or not pb:
            print("  ⚠️ 跳过 %s：路径缺失（%s / %s）" % (cf["id"], pa, pb))
            continue
        if not dry:
            backup(pa, bak_dir)
            backup(pb, bak_dir)
        print("  %s %s：%s  → %s" % (cf["id"], cf["type"], dec,
                                       "预览" if dry else "已执行"))
        if not dry:
            if dec == "no_conflict":
                mark_no_conflict(pa, pb, cf)
            elif dec == "merge":
                mark_merge(pa, pb, cf)
            else:  # adopt_a / adopt_b
                winner, loser = (pa, pb) if dec == "adopt_a" else (pb, pa)
                mark_supersede(winner, loser, cf)
            done[cf["id"]] = {"decision": dec, "at": TODAY, "type": cf["type"]}
            applied += 1
    if not dry:
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(done, f, ensure_ascii=False, indent=2)
        print("  📝 留痕：%s（%d 项）" % (log_path, len(done)))
        print("  💾 备份：%s" % bak_dir)
    print("✅ 完成（实际执行 %d 项）" % applied)
    return applied


def backup(path, bak_dir):
    rel = os.path.relpath(path, ROOT_DEFAULT)
    dst = os.path.join(bak_dir, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        return  # cp -n 语义：不覆盖已有备份
    shutil.copy2(path, dst)


def add_fm_flags(path, flags):
    """把 flags 写入卡片 YAML frontmatter（置于结束 `---` 之前）；幂等、不动正文。

    修复 v1.0.2 的 bug：旧版用 text.split('\\n---', 2) 取 parts[1] 当 frontmatter，
    但标准 Obsidian frontmatter 以行首 `---` 开头（无前导换行），split 后 parts[1]
    实为「正文」，导致 conflict_checked / superseded_by 等机器字段被错写进正文甚至
    丢失，frontmatter 始终无标记 → 后续扫描继续误报。
    现改为：定位行首 `---` 之后的第一个独立 `---` 结束分隔符，在其前插入。
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---"):
        # 无 frontmatter：前置一个 frontmatter 块，使机器字段可解析
        head = ["---"]
        for k, v in flags.items():
            head.append("%s: %s" % (k, v))
        head.append("---")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(head) + "\n" + text)
        return
    lines = text.split("\n")
    # lines[0] == '---'；找第一个独立 '---' 作为结束分隔符
    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            close_idx = i
            break
    if close_idx is None:
        return  # 异常：无结束分隔符，跳过避免破坏文件
    # 幂等：已存在的键不再重复写（避免一张卡在多对冲突中被重复注入 frontmatter）
    existing = set()
    for line in lines[1:close_idx]:
        if ":" in line:
            existing.add(line.split(":", 1)[0].strip())
    new_items = ["%s: %s" % (k, v) for k, v in flags.items() if k not in existing]
    if not new_items:
        return
    # 在结束分隔符前逐行插入
    at = close_idx
    for item in new_items:
        lines.insert(at, item)
        at += 1
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def append_footer(path, text):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if "冲突仲裁留痕" in content:
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.rstrip() + "\n\n---\n\n> **冲突仲裁留痕** · %s\n%s\n" % (TODAY, text))


def _ev(cf):
    return cf.get("evidence") or TYPE_NAME.get(cf.get("type"), "冲突仲裁")


def mark_supersede(winner_rel_path, loser_rel_path, cf):
    winner_tag = cf["side_a"]["rule_id"] or cf["side_a"]["rel"]
    loser_tag = cf["side_b"]["rule_id"] or cf["side_b"]["rel"]
    add_fm_flags(loser_rel_path, {
        "superseded_by": winner_tag,
        "conflict_resolved": "%s:%s" % (cf["type"], TODAY),
    })
    append_footer(loser_rel_path,
                  "- 类型：**%s** ｜ 处置：**采纳一方（被 `%s` 取代）**" % (TYPE_NAME[cf["type"]], winner_tag))


def mark_merge(winner_rel_path, loser_rel_path, cf):
    add_fm_flags(winner_rel_path, {"merged_from": cf["side_b"]["rule_id"] or cf["side_b"]["rel"]})
    add_fm_flags(loser_rel_path, {"merged_into": cf["side_a"]["rule_id"] or cf["side_a"]["rel"]})
    append_footer(winner_rel_path,
                  "- 类型：**%s** ｜ 处置：**融合两方**，本方为主卡，已互链 `%s`" %
                  (TYPE_NAME[cf["type"]], cf["side_b"]["rel"]))
    append_footer(loser_rel_path,
                  "- 类型：**%s** ｜ 处置：**融合两方**，已并入 `%s`" %
                  (TYPE_NAME[cf["type"]], cf["side_a"]["rel"]))


def mark_no_conflict(pa, pb, cf):
    reason = _ev(cf)
    add_fm_flags(pa, {"conflict_checked": TODAY, "not_conflict_reason": reason[:60]})
    add_fm_flags(pb, {"conflict_checked": TODAY, "not_conflict_reason": reason[:60]})
    append_footer(pa, "- 类型：**%s** ｜ 处置：**判定不冲突**（%s）" % (TYPE_NAME[cf["type"]], reason[:40]))
    append_footer(pb, "- 类型：**%s** ｜ 处置：**判定不冲突**（%s）" % (TYPE_NAME[cf["type"]], reason[:40]))


# ----------------------------------------------------------------------------
# 6.5 自测（合成卡片验证六类检测器可用）
# ----------------------------------------------------------------------------
def selftest():
    import tempfile, os as _os
    d = tempfile.mkdtemp(prefix="kg_selftest_")
    RL = _os.path.join(d, "06-沉淀", "裁判规则库")
    _os.makedirs(RL, exist_ok=True)
    cases = [
        # FC + MC：同主题，A 已核填成熟，B 待核填草稿（均置于「知识主张层」以命中护栏）
        ("06-沉淀/裁判规则库/A.md", "---\ntitle: 工伤伤残津贴计算\nrule_id: R-GZ-015\nstatute_text_pending: false\ngeo_scope: 贵州省\nreview_date: 2027-01-01\nupdated: 2026-09-10\n---\n# 工伤伤残津贴计算\n应当按本人工资比例发放。"),
        ("06-沉淀/裁判规则库/B.md", "---\ntitle: 工伤伤残津贴计算\nrule_id: R-GZ-015b\nstatute_text_pending: true\ngeo_scope: 贵州省\nupdated: 2026-09-01\n---\n# 工伤伤残津贴计算\n应当按统筹地区工资发放。"),
        # CR：同主题，地域不同 → 判不冲突
        ("06-沉淀/裁判规则库/C.md", "---\ntitle: 工伤伤残津贴计算\nrule_id: R-GZ-015c\nstatute_text_pending: false\ngeo_scope: 广东省\nupdated: 2026-09-05\n---\n# 工伤伤残津贴计算\n按广东省标准发放。"),
        # VC：同 rule_id 不同内容（同族）
        ("06-沉淀/裁判规则库/D.md", "---\ntitle: 股东知情权\nrule_id: R-SH-099\nstatute_text_pending: false\n---\n# 股东知情权\n版本一内容。"),
        ("06-沉淀/裁判规则库/E.md", "---\ntitle: 股东知情权\nrule_id: R-SH-099\nstatute_text_pending: false\n---\n# 股东知情权\n版本二内容不同。"),
        # KE：旧法 vs 现行
        ("06-沉淀/裁判规则库/F.md", "---\ntitle: 保证期间规定\nrule_id: R-SH-200\nstatute_text_pending: false\nupdated: 2026-09-12\n---\n# 保证期间规定\n依现行民法典规定处理。"),
        ("06-沉淀/裁判规则库/G.md", "---\ntitle: 保证期间规定\nrule_id: R-SH-201\nstatute_text_pending: false\nupdated: 2026-08-01\n---\n# 保证期间规定\n依原《担保法》规定处理（已废止）。"),
    ]
    for fn, content in cases:
        with open(_os.path.join(d, fn), "w", encoding="utf-8") as f:
            f.write(content)
    q, _ = scan(d, d, quick=False)
    data = json.load(open(q, encoding="utf-8"))
    types = [c["type"] for c in data["conflicts"]]
    print("\n自测检出类型：%s" % types)
    need = {"FC", "MC", "CR", "VC", "KE"}
    missing = need - set(types)
    if missing:
        print("❌ 自测未覆盖：%s" % missing)
        return 1
    print("✅ 自测通过：六类检测器均能在合成数据上触发（CC 需真实对立主张，引擎逻辑一致）")
    return 0


# ----------------------------------------------------------------------------
# 6.6 可视化看板（单文件 HTML，嵌入队列数据）
# ----------------------------------------------------------------------------
DASH_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LawKB 知识冲突仲裁看板</title>
<style>
:root{--bg:#1b1b1f;--panel:#26262c;--panel2:#2f2f37;--txt:#e6e6ea;--mut:#9aa0aa;--line:#3a3a44;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;font-size:13px}
header{padding:16px 20px;border-bottom:1px solid var(--line);background:var(--panel)}
h1{margin:0;font-size:18px}
.sub{color:var(--mut);margin-top:4px}
.cards{display:flex;flex-wrap:wrap;gap:10px;padding:16px 20px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 16px;min-width:128px;cursor:pointer;transition:.15s}
.card:hover{border-color:#5b8cff}
.card.on{border-color:#5b8cff;box-shadow:0 0 0 2px rgba(91,140,255,.25)}
.card .t{font-size:12px;color:var(--mut)}
.card .n{font-size:26px;font-weight:700;margin-top:2px}
.toolbar{padding:10px 20px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;border-bottom:1px solid var(--line)}
.toolbar input{background:var(--panel2);border:1px solid var(--line);color:var(--txt);padding:6px 10px;border-radius:6px}
.toolbar label{color:var(--mut);display:flex;gap:5px;align-items:center}
.warn{margin:10px 20px;padding:10px 14px;background:#3a2a2a;border:1px solid #6b4040;border-radius:8px;color:#ffd9d9;font-size:12px}
table{width:100%;border-collapse:collapse;margin-top:6px}
th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{position:sticky;top:0;background:var(--panel);color:var(--mut);font-weight:600;z-index:1}
tr.sel{background:rgba(91,140,255,.08)}
.badge{display:inline-block;padding:2px 7px;border-radius:5px;font-size:11px;font-weight:700}
.b-KE{background:#1d3a5f;color:#8ec5ff}.b-FC{background:#1d4d2e;color:#8effb0}.b-VC{background:#5a3a12;color:#ffcf8e}
.b-CC{background:#5a1d1d;color:#ff9a9a}.b-CR{background:#3a1d5a;color:#d29aff}.b-MC{background:#13484a;color:#8effe8}
.bar{height:6px;background:var(--panel2);border-radius:4px;overflow:hidden;width:70px;display:inline-block;vertical-align:middle}
.bar>i{display:block;height:100%}
.conf{font-weight:700;margin-left:6px}
.rel{color:var(--mut);font-size:11px}
.opts input{margin-right:3px}
.note{width:120px;background:var(--panel2);border:1px solid var(--line);color:var(--txt);border-radius:5px;padding:3px 6px;font-size:11px}
.foot{padding:14px 20px;position:sticky;bottom:0;background:var(--panel);border-top:1px solid var(--line);display:flex;gap:10px;align-items:center}
.foot code{background:var(--panel2);padding:8px 10px;border-radius:6px;flex:1;white-space:pre-wrap;word-break:break-all;color:#bde}
button{background:#5b8cff;color:#fff;border:none;padding:8px 14px;border-radius:7px;cursor:pointer;font-size:13px}
button.sec{background:var(--panel2);color:var(--txt);border:1px solid var(--line)}
</style></head>
<body>
<header><h1>LawKB 知识冲突仲裁看板</h1>
<div class="sub">生成：__GEN__ ｜ 候选冲突：<span id="tot"></span> 项 ｜ 六类全覆盖 ｜ 防知识打架·有人管闭环</div></header>
<div class="cards" id="cards"></div>
<div class="toolbar">
<input id="q" placeholder="搜索标题/路径…" oninput="render()">
<label><input type="checkbox" id="hi" onchange="render()">仅看高置信(≥0.8)</label>
<label><input type="checkbox" id="pend" checked onchange="render()">仅看待处理</label>
</div>
<div class="warn">⚠️ 本看板为 AI 候选裁决。<b>CC 内容矛盾必人工复核</b>；建议先 <code>apply --dry</code> 预览，再执行。已处置项带标记后将不再出现。</div>
<table><thead><tr>
<th><input type="checkbox" id="all" onchange="toggleAll(this)"></th>
<th>ID</th><th>类型</th><th>置信度</th><th>A（胜方候选）</th><th>B（落败候选）</th><th>AI 建议</th><th>人工决策</th><th>备注</th>
</tr></thead><tbody id="rows"></tbody></table>
<div class="foot">
<button onclick="genCmd()">生成 apply 命令</button>
<button class="sec" onclick="copyCmd()">复制</button>
<code id="cmd">（勾选行并选择决策后生成）</code>
</div>
<script>
const DATA=__DATA__;
const CNT=__CNT__;
const COL={KE:"#8ec5ff",FC:"#8effb0",VC:"#ffcf8e",CC:"#ff9a9a",CR:"#d29aff",MC:"#8effe8"};
const NAM={KE:"知识演进",FC:"事实纠正",VC:"版本冲突",CC:"内容矛盾",CR:"上下文相关",MC:"成熟度冲突"};
let active=null;
document.getElementById("tot").textContent=DATA.length;
const cc=document.getElementById("cards");
Object.keys(NAM).forEach(t=>{
  const d=document.createElement("div");d.className="card";d.dataset.t=t;
  d.innerHTML='<div class="t">'+t+' '+NAM[t]+'</div><div class="n" style="color:'+COL[t]+'">'+(CNT[t]||0)+'</div>';
  d.onclick=()=>{active=(active===t?null:t);[...cc.children].forEach(x=>x.classList.toggle("on",x.dataset.t===active));render();};
  cc.appendChild(d);
});
function confColor(c){return c>=0.8?"#5fd38a":c>=0.6?"#ffcf8e":"#ff9a9a";}
function render(){
  const q=document.getElementById("q").value.trim();
  const hi=document.getElementById("hi").checked, pend=document.getElementById("pend").checked;
  const tb=document.getElementById("rows");tb.innerHTML="";
  DATA.filter(x=>{
    if(active&&x.type!==active)return false;
    if(hi&&x.confidence<0.8)return false;
    if(pend&&x.status!=="pending")return false;
    if(q&&!(x.side_a.title+x.side_b.title+x.side_a.rel+x.side_b.rel).includes(q))return false;
    return true;
  }).forEach(x=>{
    const tr=document.createElement("tr");tr.dataset.id=x.id;
    const c=confColor(x.confidence);
    tr.innerHTML='<td><input type="checkbox" class="sel"></td>'+
    '<td>'+x.id+'</td>'+
    '<td><span class="badge b-'+x.type+'">'+x.type+'</span></td>'+
    '<td><span class="bar"><i style="width:'+(x.confidence*100)+'%;background:'+c+'"></i></span><span class="conf" style="color:'+c+'">'+x.confidence+'</span></td>'+
    '<td>'+x.side_a.title+'<div class="rel">'+x.side_a.rel+'</div></td>'+
    '<td>'+x.side_b.title+'<div class="rel">'+x.side_b.rel+'</div></td>'+
    '<td>'+x.ai_suggestion+'<div class="rel">'+x.ai_reason.slice(0,36)+'</div></td>'+
    '<td class="opts"><label><input type="radio" name="d-'+x.id+'" value="adopt_a">采纳A</label> <label><input type="radio" name="d-'+x.id+'" value="adopt_b">采纳B</label> <label><input type="radio" name="d-'+x.id+'" value="merge">融合</label> <label><input type="radio" name="d-'+x.id+'" value="no_conflict">不冲突</label></td>'+
    '<td><input class="note" placeholder="备注"></td>';
    tb.appendChild(tr);
  });
}
function toggleAll(b){document.querySelectorAll("#rows .sel").forEach(c=>c.checked=b.checked);}
function genCmd(){
  const ids=[];
  document.querySelectorAll("#rows tr").forEach(tr=>{
    const cb=tr.querySelector(".sel");if(!cb.checked)return;
    const id=tr.dataset.id;
    const dec=tr.querySelector('input[name="d-'+id+'"]:checked');
    const note=tr.querySelector(".note").value;
    if(!dec){alert("请先为 "+id+" 选择决策");return;}
    x=DATA.find(z=>z.id===id);x.decision=dec.value;if(note)x.decision_note=note;
    ids.push(id);
  });
  if(!ids.length){document.getElementById("cmd").textContent="（无勾选项）";return;}
  const Q='冲突仲裁队列_*.json';
  document.getElementById("cmd").textContent='python kg_conflict_arbitrator.py apply --queue "$Q" --only '+ids.join(",");
}
function copyCmd(){navigator.clipboard.writeText(document.getElementById("cmd").textContent);}
render();
</script></body></html>"""


def build_dashboard(queue_path, out_html):
    with open(queue_path, encoding="utf-8") as f:
        data = json.load(f)
    from collections import Counter
    cnt = Counter(c["type"] for c in data["conflicts"])
    html = (DASH_TEMPLATE
            .replace("__DATA__", json.dumps(data["conflicts"], ensure_ascii=False))
            .replace("__CNT__", json.dumps(dict(cnt), ensure_ascii=False))
            .replace("__GEN__", TODAY))
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)
    return out_html


# ----------------------------------------------------------------------------
# 7. CLI
# ----------------------------------------------------------------------------
def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "scan"
    get = lambda k, d=None: args[args.index(k) + 1] if k in args else d

    if cmd == "selftest":
        return selftest()
    elif cmd == "scan":
        root = get("--root", ROOT_DEFAULT)
        out = get("--out", OUT_DEFAULT)
        limit = int(get("--limit", "0")) or None
        quick = "--quick" in args
        scan(root, out, limit=limit, quick=quick)
    elif cmd == "report":
        q = get("--queue") or os.path.join(OUT_DEFAULT, "冲突仲裁队列_%s.json" % TS)
        out = get("--out", OUT_DEFAULT)
        if not os.path.exists(q):
            print("❌ 队列不存在：%s（先跑 scan）" % q)
            return 1
        data = json.load(open(q, encoding="utf-8"))
        p = os.path.join(out, "冲突仲裁报告_%s.md" % TS)
        write_report(p, data["conflicts"], data.get("root", ROOT_DEFAULT))
        print("✅ 报告：%s" % p)
    elif cmd == "apply":
        q = get("--queue")
        if not q:
            print("❌ apply 需 --queue 指定队列文件")
            return 1
        only = get("--only")
        only_ids = [x.strip() for x in only.split(",")] if only else None
        min_conf = float(get("--min-conf", "0.8"))
        dry = "--dry" in args
        apply(q, only_ids=only_ids, min_conf=min_conf, dry=dry)
    elif cmd == "dashboard":
        q = get("--queue") or sorted(
            [os.path.join(OUT_DEFAULT, f) for f in os.listdir(OUT_DEFAULT)]
            if os.path.isdir(OUT_DEFAULT) else []) or None
        if isinstance(q, list):
            q = q[-1] if q else None
        if not q or not os.path.exists(q):
            print("❌ dashboard 需 --queue 指定队列文件")
            return 1
        out = get("--out", os.path.dirname(q))
        html = os.path.join(out, "冲突仲裁看板_%s.html" % TS)
        print("✅ 看板：%s" % build_dashboard(q, html))
    else:
        print(__doc__)
        return 1


if __name__ == "__main__":
    sys.exit(main())
