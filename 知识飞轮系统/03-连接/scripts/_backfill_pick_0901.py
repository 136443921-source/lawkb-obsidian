# -*- coding: utf-8 -*-
"""
09-01 漏窗回补助选文（SELECT_3 · 带 title 全局去重）
=====================================================
输入：_backfill_cands_0901.json（HTTP 通道 S1 翻页 + S1.5 文件夹递归挖得）
输出：_backfill_pick_0901.json（每库 ≤3 篇，全局 ≤15 篇）

三重去重（本轮新增第 2、3 重，治「同名跨库重复入选」）：
  1. media_id 精确去重（对 ingested 集合）
  2. title 对 ingested 集合去重（治 media_id 构造差异导致的假阴性）
  3. title 对本轮候选内部去重（治同一篇被多库收录而重复入选）
另：排除 08-30/08-31 已蒸馏的 shortlist 标题（避免重复造卡）。
"""
import json, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
KB = os.path.join(os.path.dirname(os.path.dirname(BASE)), "ima_intake_state.json")
CANDS = os.path.join(BASE, "_backfill_cands_0901.json")
OUT = os.path.join(BASE, "_backfill_pick_0901.json")
PREFIX = "wechatarticle_62fe55a7567bc291dfbbee29900b27c3_"

from intake_runner import score_article

# 08-30 / 08-31 已蒸馏造卡的标题（防重复造卡）
ALREADY_MINED = [
    "买卖合同纠纷法律适用疑难问题", "合同纠纷案：违约损失赔偿金额计算公式",
    "最高人民法院发布50个民间借贷纠纷裁判规则深度解析",
    "行政庭审质证干货", "办案手记：房屋租赁纠纷常见争议焦点",
    "行政复议实操指南", "首诊负责制度", "专家辅助人定义",
    "医疗费赔偿项目及相关法律问题", "药品管理法实施条例修订主要内容",
    "麻醉药品和精神药品经营管理", "法务如何写好《案件分析报告》",
    "公益事业捐赠票据使用管理办法",
    "民政部关于基金会等社会组织不得提供公益捐赠回扣",
    "关于支持新型冠状病毒感染的肺炎疫情防控有关捐赠税收政策",
]


# 人工优选白名单（2026-09-01）：score_article 对慈善库标题命中率极低（最高 5 分），
# 自动选出的「使用指引/目录框架」属纯导航文件、无实质知识内容（灌水），
# 按价值保障条款人工替换为官方法规/指引原文（捐赠物资计价、公开募捐备案、减免税）。
# ⚠️ 备选目标「贵州物资捐赠管理指引」「贵州省慈善条例」「捐赠票据免税实操」
#    经查 media_id 均已在 ingested 集合内（已摄入），故不可选，已排除。
MANUAL_PRIORITY = {
    "慈善组织合规AI 助手": [
        "捐赠物资计价和捐赠票据开具",
        "慈善组织公开募捐方案备案指引",
        "进口慈善捐赠物资减免税手续",
    ],
}
MANUAL_MATCH = MANUAL_PRIORITY

def norm(t):
    return "".join((t or "").split())


def build_media_id(c):
    """构造标准 media_id（2026-09-01 修复）。

    ⚠️ 坑：挖池脚本对非 wechatarticle 类型（markdown_/pdf_/docx_ 等）取 rawid[:32] 后，
    所有 markdown 文件的 rawid 都会塌缩成同一个字符串（'markdown_62fe55a7567bc291dfbbee2'
    正好 32 位），导致 std_mid 构造错误 → fetch 必然 220030。
    故：wechatarticle 走 prefix+32位rawid+kb_id；其余类型直接用原始 media_id_raw。
    """
    rawid = c.get("rawid", "")
    if rawid.startswith(("markdown_", "pdf_", "docx_", "ppt_", "txt_", "web_")):
        return c.get("media_id_raw", "")
    if rawid.startswith("folder_"):
        return ""
    return PREFIX + rawid + c["lib_id"]


def main():
    state = json.load(open(KB, encoding="utf-8"))
    ingested_mids, ingested_titles = set(), set()
    for lid, info in state["libraries"].items():
        for x in info.get("ingested", []):
            if isinstance(x, dict):
                ingested_mids.add(x.get("media_id", ""))
                ingested_titles.add(norm(x.get("title", "")))
            else:
                ingested_mids.add(str(x))

    cands = json.load(open(CANDS, encoding="utf-8"))["candidates"]

    picked, seen_titles, stats = {}, set(), {}
    for lib, arr in cands.items():
        scored = []
        for c in arr:
            rawid = c.get("rawid", "")
            title = c.get("title", "")
            # 文件夹/脏数据过滤
            if rawid.startswith("folder_"):
                continue
            nt = norm(title)
            if not nt:
                continue
            # 去重 1：media_id（按类型正确构造）
            std_mid = build_media_id(c)
            if not std_mid:
                continue
            if std_mid in ingested_mids:
                continue
            # 去重 2：title 对 ingested
            if nt in ingested_titles:
                continue
            # 去重 3：title 对本轮已选
            if nt in seen_titles:
                continue
            # 排除历史已蒸馏
            if any(m in title for m in ALREADY_MINED):
                continue
            sc, hits = score_article(title)
            scored.append((sc, title, c, hits))
        scored.sort(key=lambda x: (-x[0], x[1]))
        top = scored[:3]
        # 人工优选覆盖：按 MANUAL_MATCH 顺序命中替换（治自动评分选出导航文件）
        if lib in MANUAL_MATCH:
            manual = []
            for kw in MANUAL_MATCH[lib]:
                for sc, title, c, hits in scored:
                    # ⚠️ 去重改用 title：markdown 文件 rawid 会塌缩成同一字符串，不能用 rawid 判重
                    if kw in title and norm(title) not in [norm(m[1]) for m in manual]:
                        manual.append((sc, title, c, hits))
                        break
            if manual:
                top = manual[:3]
        picked[lib] = [{
            "lib": lib, "lib_id": c["lib_id"], "rawid": c["rawid"],
            "title": title, "media_id_raw": c["media_id_raw"],
            "folder": c.get("folder"), "score": sc, "hits": hits,
            "std_media_id": build_media_id(c),
        } for sc, title, c, hits in top]
        for it in picked[lib]:
            seen_titles.add(norm(it["title"]))
        stats[lib] = {"scored": len(scored), "picked": len(top)}

    total = sum(len(v) for v in picked.values())
    payload = {
        "generated_at": "2026-09-01",
        "window_id": "w_2026-09-01_A1B_channel_down",
        "note": "SELECT_3 + title 全局三重去重；每库≤3、全局≤15。",
        "stats": stats,
        "total_picked": total,
        "picks": picked,
    }
    json.dump(payload, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print("=== 选文结果（每库≤3，全局≤15）===")
    for lib, arr in picked.items():
        print("\n【%s】%d 篇（候选 %d）" % (lib, len(arr), stats[lib]["scored"]))
        for it in arr:
            print("  [%2d] %s" % (it["score"], it["title"][:52]))
    print("\nTOTAL:", total)
    print("SAVED:", OUT)


if __name__ == "__main__":
    main()
