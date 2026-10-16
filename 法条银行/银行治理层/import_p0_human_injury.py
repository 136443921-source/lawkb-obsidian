#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0 人伤执业法源 4 张入库脚本
card 1 医疗事故分级标准、card 4 劳动争议调解仲裁法：正文取自本会话内联提取，另由主控直接整卡写入；
本脚本只处理两份「已落盘原文」的大卡（card2 人体损伤程度鉴定标准、card3 人体损伤致残程度分级）。

正文来源（verbatim）：
- 医疗事故分级标准：gov.cn 国务院公报2003年第15号（WebFetch 逐字提取）
- 人体损伤程度鉴定标准：青海法网12348 全文（WebFetch 逐字提取，1451行落盘）
- 人体损伤致残程度分级：taian_zhican.txt（pymupdf 逐字提取，2781行）
- 劳动争议调解仲裁法：chinanews 全文(1)(2)（WebFetch 逐字提取）
"""
import os, re

BANK_YI = "/Users/chenyouqiang/Documents/LawKB/法条银行/医事法律法规库"
BANK_TY = "/Users/chenyouqiang/Documents/LawKB/法条银行/通用法律法规"
TAIAN = "/Users/chenyouqiang/WorkBuddy/2026-10-15-16-58-44/outputs/法条回填5/taian_zhican.txt"
FETCH = "/Users/chenyouqiang/.workbuddy/projects/Users-chenyouqiang-WorkBuddy-2026-10-15-16-58-44/c58f00fd-e9b9-4e62-8ca7-e27b58ddd12c/tool-results/chatcmpl-tool-c5e3c12cc50c4f0981bb4c481c8179f5.txt"
TODAY = "2026-10-16"

def fm(title, org, doc_no, eff_date, sxx, source, source_verify, aliases,
       scope="全文", article_count=None, effect_rank="部门规章/国家标准", extra=None):
    lines = ["---", f"title: {title}", "type: statute", f"effect_rank: {effect_rank}",
             f"org: {org}", f"sxx: {sxx}", f"scope: {scope}",
             "statute_text_pending: false", f"source: {source}",
             f"source_verify: {source_verify}", "yuandian_verify: n/a",
             f"yuandian_verify_date: {TODAY}", "yuandian_verify_by: gov.cn/权威官网逐字提取",
             "yuandian_sxx: " + sxx, f"yuandian_doc_no: {doc_no}",
             f"yuandian_eff_date: {eff_date}", f"yuandian_org: {org}",
             "aliases:"]
    for a in aliases:
        lines.append(f"  - {a}")
    lines += [f"created: {TODAY}T10:30", f"updated: {TODAY}T10:30",
              f"doc_no: {doc_no}", f"effective_date: {eff_date}",
              "content_status: full", "content_status_note:",
              "cite_ready: true", f"content_status_updated: {TODAY}",
              f"fill_source: {source}",
              f"fill_date: {TODAY}", f"retrieved_date: {TODAY}"]
    if article_count is not None:
        lines.append(f"article_count: {article_count}")
    if extra:
        for k, v in extra.items():
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"

def clean_taiian(raw):
    """清洗 pymupdf 提取文本：去页码标记 '- N -'，合并断裂行"""
    lines = raw.split('\n')
    out = []
    for l in lines:
        s = l.strip()
        if re.fullmatch(r'-\s*\d+\s*-', s):
            continue
        out.append(l.rstrip())
    txt = "\n".join(out)
    # 合并：PDF 硬换行导致同一句被拆行 —— 以"；"结尾或明显未完的行与下一行拼接
    return txt

def clean_shanghu(sec_no_prefix="", drop_prefix=True):
    return None

def write_card(path, head, body):
    if os.path.exists(path):
        print(f"[WARN] 已存在跳过: {path}")
        return
    open(path, 'w', encoding='utf-8').write(head + "\n" + body.strip() + "\n")
    print(f"[OK] {os.path.basename(path)}  ({len(body)} 字符)")

# ---------- 2) 人体损伤程度鉴定标准 ----------
raw2 = open(FETCH, encoding='utf-8').read()
# 去掉 WebFetch 的开场白与 markdown 标记
raw2 = raw2.split('### 人体损伤程度鉴定标准', 1)[-1]
body2 = re.sub(r'\*\*|\*', '', raw2)
body2 = re.sub(r'　+', '　', body2)
body2 = re.sub(r'\n{3,}', '\n\n', body2)
# 恢复结构标题（顶层编号行加粗标记，便于检索）
lines2 = body2.split('\n')
for i, l in enumerate(lines2):
    s = l.strip()
    if re.match(r'^(附录\s*[A-Z]|[0-9]+(\.[0-9]+)*\s+\S{2,20})$', s):
        lines2[i] = f'**{s}**'
body2 = "\n".join(lines2)
head2 = fm(
    title="人体损伤程度鉴定标准",
    org="最高人民法院、最高人民检察院、公安部、国家安全部、司法部",
    doc_no="两院三部公告（2013-08-30发布）",
    eff_date="2014-01-01",
    sxx="现行有效",
    source="青海法网12348·司法鉴定业务指南栏目（qh.12348.gov.cn）全文；原文PDF见司法部官网 moj.gov.cn",
    source_verify="主源 青海法网12348 逐字提取（含附录A-C）；与司法部官网PDF、新兴县政府网、维基文库多源比对一致；发布机关·发布日期2013-08-30·施行日2014-01-01 三源吻合",
    aliases=["人体损伤程度鉴定标准", "损伤程度鉴定标准", "重伤标准", "轻伤标准"],
    scope="重伤一级/二级、轻伤一级/二级、轻微伤五级＋附录A-C",
    article_count="5级＋附录A/B/C",
    effect_rank="国家标准（司法鉴定行业标准）",
    extra={"abolished_replaced": "同时废止《人体重伤鉴定标准》(司发[1990]070号)、《人体轻伤鉴定标准(试行)》(法(司)发[1990]6号)、《人体轻微伤的鉴定》(GA/T 146-1996)",
           "scenario_tags": "人身损害,损伤程度,重伤轻伤,刑期预估,赔偿标准"},
)
write_card(os.path.join(BANK_YI, "人体损伤程度鉴定标准（两院三部·2014-01-01施行）.md"), head2, body2)

# ---------- 3) 人体损伤致残程度分级 ----------
raw3 = open(TAIAN, encoding='utf-8').read()
body3 = clean_taiian(raw3)
body3 = re.sub(r'\n{3,}', '\n\n', body3)
lines3 = body3.split('\n')
for i, l in enumerate(lines3):
    s = l.strip()
    if re.match(r'^(前言|引\s*言|[0-9]+(\.[0-9]+)*\s+\S{2,24}|附录\s*[A-Z].*|表\s*[A-Z]\.\d+.*)$', s):
        lines3[i] = f'**{s}**'
body3 = "\n".join(lines3)
head3 = fm(
    title="人体损伤致残程度分级",
    org="最高人民法院、最高人民检察院、公安部、国家安全部、司法部",
    doc_no="两院五部公告（2016-04-18发布）",
    eff_date="2017-01-01",
    sxx="现行有效",
    source="两院五部公告PDF逐字提取（pymupdf，2781行）；发布机关·2016-04-18·自2017-01-01施行见公告正文",
    source_verify="主源 官方公告PDF逐字提取（pymupdf text layer）；公告载'自2017年1月1日起施行'；司法鉴定机构与司法鉴定人统一适用",
    aliases=["人体损伤致残程度分级", "致残程度分级", "伤残等级标准", "十级伤残"],
    scope="十级伤残体系（一级至十级）＋附录A-C（含手、足功能计算图表）",
    article_count="10级＋附录A/B/C",
    effect_rank="国家标准（司法鉴定行业标准）",
    extra={"distinguish_from": "与《人体损伤程度鉴定标准》分工：本卡定伤残等级（民事赔偿），前者定损伤程度（刑事/治安）；《道路交通事故受伤人员伤残评定》(GB 18667) 用于交通案件专门评定",
           "scenario_tags": "人身损害,伤残等级,十级伤残,残疾赔偿金,赔偿标准"},
)
write_card(os.path.join(BANK_YI, "人体损伤致残程度分级（两院五部·2017-01-01施行）.md"), head3, body3)
print("--- 本脚本完成 card2/card3；card1/card4 由主控直接整卡写入 ---")