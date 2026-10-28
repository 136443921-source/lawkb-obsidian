#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LawKB 知识飞轮系统 · 法条引用全量抽取器

用途：扫描 知识飞轮系统 下全部 .md，抽取所有《XX法》第N条 引用，归一化为
      (法律标准名, 条号int)，并抓取引用后文（含逐字引文）供后续做：
      A 条号越界 / B 同条异文（法条内容一致性）/ C 版本混用 / D 法理逻辑冲突。
输出：/tmp/lawkb_audit/citations.json  + 控制台摘要
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT = "/tmp/lawkb_audit/citations.json"

# —— 法律名归一化：别名 -> provision_index 索引名 ——
ALIAS = {
    "民法典": "民法典", "中华人民共和国民法典": "民法典",
    # —— 旧法不归一（历史法条豁免前置，2026-10 补丁）——
    # 侵权责任法/合同法/物权法/担保法/婚姻法/继承法/民法总则 现均已并入《民法典》，
    # 属历史法条引用，按铁律豁免，不纳入现行法一致性校验；保留原名使其落在
    # provision_index 之外被跳过，避免「旧条号 vs 新法正文」的伪越界/伪异文。
    "民法总则": "民法总则", "合同法": "合同法", "物权法": "物权法",
    "侵权责任法": "侵权责任法", "担保法": "担保法", "婚姻法": "婚姻法",
    "继承法": "继承法", "总则编": "总则编",
    "民事诉讼法": "民事诉讼法", "民诉法": "民事诉讼法",
    "中华人民共和国民事诉讼法": "民事诉讼法",
    "民事诉讼法司法解释": "民事诉讼法司法解释",
    "民诉法解释": "民事诉讼法司法解释",
    "最高人民法院关于适用《中华人民共和国民事诉讼法》的解释": "民事诉讼法司法解释",
    "公司法": "公司法", "中华人民共和国公司法": "公司法",
    "刑法": "刑法", "中华人民共和国刑法": "刑法",
    "刑事诉讼法": "刑事诉讼法", "刑诉法": "刑事诉讼法",
    "中华人民共和国刑事诉讼法": "刑事诉讼法",
    "行政诉讼法": "行政诉讼法", "行诉法": "行政诉讼法",
    "中华人民共和国行政诉讼法": "行政诉讼法",
    "行政处罚法": "行政处罚法", "中华人民共和国行政处罚法": "行政处罚法",
    "行政强制法": "行政强制法", "中华人民共和国行政强制法": "行政强制法",
    "买卖合同司法解释": "买卖合同司法解释",
    "最高人民法院关于审理买卖合同纠纷案件适用法律问题的解释": "买卖合同司法解释",
}

CN_NUM = {"零": 0, "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4,
          "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "两": 2}
CN_UNIT = {"十": 10, "百": 100, "千": 1000}

# 条文后缀归一（最长匹配补全，2026-10 补丁）：「第X条之一」→ 索引键 "X_1"
# provision_index 以 "37_1" 形式存「第37条之一」，扫描器须保留后缀才能正确命中正文。
SUFFIX_MAP = {"之一": "_1", "之二": "_2", "之三": "_3", "之四": "_4", "之五": "_5"}


def cn2int(s: str):
    """中文数字(含十百千万) -> int；失败返回 None"""
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    total, section, number = 0, 0, 0
    for ch in s:
        if ch in CN_NUM:
            number = CN_NUM[ch]
        elif ch in CN_UNIT:
            unit = CN_UNIT[ch]
            section += (number if number else 1) * unit
            number = 0
        elif ch == "万":
            section = (section + number) * 10000
            total += section
            section, number = 0, 0
        else:
            return None  # 含非数字字符，判定失败
    return total + section + number


# 《法律名》第N条（支持阿拉伯/中文数字，支持 之X / 第X款 后缀）
# ⚠️ 最长匹配：法律名常含嵌套书名号（如《最高人民法院关于适用《民事诉讼法》的解释》），
#    须捕获最外层完整标题，否则会被误截成内层《民事诉讼法》→ 错挂到 306 条的民诉法，
#    造成 308/309 等「条号越界」假阳性（2026-09/10 两轮均出现）。
# ⚠️ 性能：否定类必须含 \n，否则非闭合书名号会让正则跨行回溯至文件末尾（灾难性回溯）。
#    法条引用不跨行，单行内匹配既正确又线性。
CITE_RE = re.compile(
    # 最长匹配 + 线性无回溯：
    # 法律名正文用 [^》《\n]*（排除书名号本身，避免贪婪吃掉内层《》导致截断），
    # 嵌套《》交给有界迭代 {0,3}（法律标题至多 1 层嵌套，留 3 倍余量）。
    # 整体为简单字符类的有界重复，匹配时间为 O(n) 线性，杜绝跨行灾难性回溯。
    # group(3) 捕获「之一/第X款」等后缀，归一为索引键后缀（如 37_1），最长匹配补全。
    r"《((?:[^》《\n]*《[^》\n]*》){0,3}[^》《\n]*)》[^。；\n]{0,12}?第\s*([0-9〇一二三四五六七八九十百千万零两]{1,12})\s*条\s*((?:之一|之二|之三|之四|之五|第[0-9]+款|[（(][^）)\n]{1,6}[）)]))?"
)

QUOTE_OPEN = {'"': '"', "'": "'", "“": "”"}


# 明显是 YAML/markdown 元数据而非法律引文 —— 直接丢弃，防误报
JUNK_PREFIX = ("related_links", "tags:", "aliases", "rule_id", "created",
               "updated", "confidence", "source", "domain", "status",
               "knowledge_called", "layer", "see_also", "---", "#")


def grab_quote(tail: str, limit: int = 300):
    """从引用后文抓逐字引文（书名号/引号包裹的最长一段），剔除 YAML 噪声"""
    head = tail[:limit]
    for op, cl in QUOTE_OPEN.items():
        i = head.find(op)
        if 0 <= i <= 40:
            j = head.find(cl, i + 1)
            if j > i:
                q = head[i + 1:j].strip()
                if len(q) < 8:          # 太短的不算有效引文
                    continue
                if q.startswith(JUNK_PREFIX) or "\n" in q:
                    continue            # YAML 键 / 跨行 = 元数据，非引文
                return q
    return None


def norm_law(raw: str):
    raw = raw.strip()
    if raw in ALIAS:
        return ALIAS[raw]
    # 去"中华人民共和国"前缀再试
    s = raw.replace("中华人民共和国", "")
    if s in ALIAS:
        return ALIAS[s]
    return None                       # 非索引覆盖法，标 None


def main():
    citations = []
    files = 0
    law_counter = Counter()
    per_file = Counter()

    for dirpath, dirnames, filenames in os.walk(ROOT):
        # 排除备份/历史副本目录（同一错误会被放大十余倍，污染统计）
        dirnames[:] = [d for d in dirnames
                       if not d.startswith(".") and not d.startswith("_backup")
                       and d not in ("node_modules",)]
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            fp = os.path.join(dirpath, fn)
            files += 1
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except Exception:
                continue
            rel = os.path.relpath(fp, ROOT)
            for m in CITE_RE.finditer(text):
                law_raw, art_raw, suffix = m.group(1), m.group(2), (m.group(3) or "")
                art_base = cn2int(art_raw)
                # art_key：用于 provision_index 查正文（"37_1" 形式）；art_num：用于条号越界判定（纯基数）
                art_key = (str(art_base) + SUFFIX_MAP.get(suffix, suffix)) if art_base is not None else None
                law = norm_law(law_raw)
                line_no = text.count("\n", 0, m.start()) + 1
                tail = text[m.end(): m.end() + 300]
                quote = grab_quote(tail)
                citations.append({
                    "file": rel,
                    "line": line_no,
                    "law_raw": law_raw,
                    "law": law,
                    "art_raw": art_raw + suffix,
                    "art": art_key,          # 字符串键：37_1 / 26
                    "art_num": art_base,     # 整数基数：37 / 26（供越界判定）
                    "quote": quote,
                    "ctx": tail[:120].replace("\n", " "),
                })
                if law:
                    law_counter[law] += 1
                    per_file[rel] += 1

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(citations, f, ensure_ascii=False, indent=1)

    total = len(citations)
    indexed = sum(1 for c in citations if c["law"])
    with_quote = sum(1 for c in citations if c["quote"])
    bad_art = sum(1 for c in citations if c["art"] is None)

    print("=" * 66)
    print("LawKB 知识飞轮系统 · 法条引用抽取结果")
    print("=" * 66)
    print(f"扫描文件数        : {files}")
    print(f"抽取引用总数      : {total}")
    print(f"  其中命中索引法  : {indexed}   （可自动校验条号/内容）")
    print(f"  未覆盖法(待人工): {total - indexed}")
    print(f"  含逐字引文      : {with_quote}   （可做内容一致性比对）")
    print(f"  条号解析失败    : {bad_art}")
    print("-" * 66)
    print("法律分布（索引覆盖的 10 部）:")
    for law, n in law_counter.most_common():
        print(f"  {law:22} {n}")
    print("-" * 66)
    other = Counter(c["law_raw"] for c in citations if not c["law"])
    print("未覆盖法律 Top15（人工判断是否需要补权威源）:")
    for law, n in other.most_common(15):
        print(f"  {law:32} {n}")
    print("=" * 66)
    print(f"明细已存: {OUT}")


if __name__ == "__main__":
    sys.exit(main())
