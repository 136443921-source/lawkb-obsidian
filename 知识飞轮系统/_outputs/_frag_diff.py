#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A 线 · 7 个同号碎片「内容 diff 比对」生成器（只读）
=================================================
对 dry-run 发现的 7 个 rule_id 在 06-沉淀 内多份主卡，逐对：
  - 提取 frontmatter 关键字段（title/card_type/updated/source/created）
  - 计算正文相似度（difflib）
  - 给初步判定：重复副本 / 撞号不同内容 / 部分重叠
产出：_outputs/A线-7碎片内容diff比对-20260921.md
"""
import os, re, difflib

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
OUT = os.path.join(ROOT, "_outputs")

pairs = [
    ("R-CF-052", "06-沉淀/裁判规则库/慈善/R-CF-052.md",
                "06-沉淀/裁判规则库/慈法合规/R-CF-052-税前扣除资格双比例红线公益支出公募70非公募8管理费10-12.md"),
    ("R-CF-053", "06-沉淀/裁判规则库/慈善/R-CF-053.md",
                "06-沉淀/裁判规则库/慈法合规/R-CF-053-基金会互捐核心真实最终受益人执行方公开遴选募捐资金非自有资金.md"),
    ("R-CF-076", "06-沉淀/裁判规则库/慈善/R-CF-076-慈善组织信息公开以公开为原则不公开为例外捐赠人享有查询复制权.md",
                "06-沉淀/裁判规则库/慈善/R-CF-076-慈善合规数值红线速查-LTI映射桥.md"),
    ("R-CF-173", "06-沉淀/裁判规则库/慈善/R-CF-173-捐赠财产指定专项基金用途不能实现捐赠人可撤销并请求返还.md",
                "06-沉淀/裁判规则库/慈法合规/R-CF-173-捐赠财产指定专项基金用途不能实现捐赠人可撤销并请求返还.md"),
    ("R-HT-101", "06-沉淀/裁判规则库/合同风险/R-HT-101-保证方式约定不明推定为一般保证保证期间届满责任消灭.md",
                "06-沉淀/裁判规则库/合同风险/R-HT-101-代理意见写作规范.md"),
    ("R-HT-102", "06-沉淀/裁判规则库/合同风险/R-HT-102.md",
                "06-沉淀/裁判规则库/合同风险/R-HT-102-合同相对性实际交易方认定.md"),
    ("R-PI-157", "06-沉淀/裁判规则库/人伤法/R-PI-157.md",
                "06-沉淀/裁判规则库/人伤法/R-PI-157-医疗告知义务代签与举证不能.md"),
]

def read(p):
    fp = os.path.join(ROOT, p)
    if not os.path.exists(fp):
        return None, None, False
    txt = open(fp, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", txt, re.S)
    if m:
        return m.group(1), m.group(2), True
    return "", txt, False

def field(fm, key):
    m = re.search(r"^" + re.escape(key) + r":\s*(.*)$", fm, re.M)
    return m.group(1).strip() if m else "(无)"

def infer(rid, fm_a, body_a, fm_b, body_b):
    """给初步判定与建议（不改卡，只建议）"""
    ta, tb = field(fm_a, "title"), field(fm_b, "title")
    ua, ub = field(fm_a, "updated"), field(fm_b, "updated")
    ca, cb = len(body_a), len(body_b)
    ratio = difflib.SequenceMatcher(None, body_a, body_b).ratio()
    # 标题是否指向同一主题
    same_topic = ta != "(无)" and tb != "(无)" and (ta[:8] == tb[:8] or ratio > 0.6)
    if ratio > 0.9:
        tag = "🔵 高度重复（副本）"
        # 谁更新/更全
        if ca >= cb and (ua >= ub or ua == "(无)"):
            keep, drop = "A", "B"
        else:
            keep, drop = "B", "A"
        advice = f"建议保留 {keep}（更新{getattr(__import__('__builtins__'),'max',max)(ua,ub)}/字数{getattr(__import__('__builtins__'),'max',max)(ca,cb)}），删除 {drop} 副本"
    elif ratio < 0.35:
        tag = "🔴 撞号不同内容（同 rule_id 异主题）"
        advice = "建议**重编号**（P0-4 编号治理）：两份各取新 rule_id，不可删并"
    else:
        tag = "🟡 部分重叠（可能融合）"
        advice = "建议人工比对后融合，或保留较全一份、另一份补遗"
    return tag, ratio, ta, tb, ua, ub, ca, cb, advice

L = []
L.append("# A 线 · 7 个同号碎片「内容 diff 比对」")
L.append("")
L.append("> 生成日期：2026-09-21 | 性质：**只读比对，未修改/删除任何卡片**")
L.append("> 判定说明：🔵高度重复→删副本留现行；🟡部分重叠→融合；🔴撞号异内容→重编号(P0-4)")
L.append("")
L.append("| rule_id | 相似度 | 判定 | 建议 |")
L.append("|---|---|---|---|")

detail = []
for rid, pa, pb in pairs:
    fa, ba, oka = read(pa)
    fb, bb, okb = read(pb)
    if fa is None or fb is None:
        L.append(f"| {rid} | - | ⚠️ 文件缺失 | 检查路径 |")
        detail.append(f"\n## {rid} ⚠️ 文件缺失\n- A: {pa} 存在={oka}\n- B: {pb} 存在={okb}")
        continue
    tag, ratio, ta, tb, ua, ub, ca, cb, advice = infer(rid, fa, ba, fb, bb)
    L.append(f"| {rid} | {ratio:.2f} | {tag} | {advice} |")
    detail.append(f"\n## {rid} — {tag}（相似度 {ratio:.2f}）")
    detail.append(f"\n**A** `{pa}`")
    detail.append(f"- title: {ta}")
    detail.append(f"- card_type: {field(fa,'card_type')} | updated: {ua} | created: {field(fa,'created')}")
    detail.append(f"- 正文长度: {ca} 字 | source: {field(fa,'source')[:40]}")
    detail.append(f"\n**B** `{pb}`")
    detail.append(f"- title: {tb}")
    detail.append(f"- card_type: {field(fb,'card_type')} | updated: {ub} | created: {field(fb,'created')}")
    detail.append(f"- 正文长度: {cb} 字 | source: {field(fb,'source')[:40]}")
    detail.append(f"\n**建议**：{advice}")

L.extend(detail)
L.append("\n")
md_path = os.path.join(OUT, "A线-7碎片内容diff比对-20260921.md")
open(md_path, "w", encoding="utf-8").write("\n".join(L))
print("报告写入:", md_path)
# 打印摘要
for line in L[:12]:
    print(line)
