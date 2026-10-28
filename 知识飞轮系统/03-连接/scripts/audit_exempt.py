#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_exempt.py · 法条一致性巡检「豁免前置」共享模块

作用：在 A/B/C 冲突检测与反向核验之前，筛掉「看似疑点、实为合法」的引用，
把月度候选噪声从 ~195 压到个位数。三类豁免（与 2026-09-04 / 2026-10-28 两轮
人工核验结论一致）：

  1. 测试夹具：刻意构造的假条号（如 LTI 防幻觉实测里的 民法典9999）。
  2. 工具/元数据文件：审计报告、巡检报告、防幻觉评估等非知识卡。
  3. 历史法条正确引用：旧法/已废止法/条号变迁说明性文字
     （如「原《合同法》第167条」对应《民法典》第634条；
      买卖合同解释2012版第38条已删除现由民法典634条规范；
      公司法解释五对旧法第21条的解释）。

⚠️ 本模块只「豁免」，绝不「放行真实错误」。真实条号越界/错配仍会被检出。
   任何新增豁免项须有人工核验依据，禁止凭记忆新增。
"""

# —— (law, art) 已知历史法条引用白名单（人工核验过的合法旧法引用）——
HISTORICAL_OK = {
    ("买卖合同司法解释", 38),   # 2012版第38条已删除，现由民法典634条规范（指导案例67号自述变迁）
}

# —— 旧法/历史法条 上下文标记：出现其一即视为合法旧法引用 ——
OLD_LAW_MARKERS = (
    "原《", "（已废止）", "已废止", "2012版", "旧法", "（已删除）",
    "第38条已删除", "现由民法典第", "解释五", "原合同法", "原物权法",
    "旧公司法", "原《合同法》", "原《物权法》", "修正前", "（2018年）",
    "原《民法通则》", "原《担保法》", "已被",
)

# —— 工具/元数据文件路径片段（非知识卡，不参与一致性判定）——
META_PATH_FRAGMENTS = (
    "LTI防幻觉", "防幻觉能力", "审计报告", "巡检报告", "巡检摘要",
    "一致性审计报告", "一致性巡检归档",
)

import re as _re

def art_base(art):
    """条号键（可能含后缀如 '37_1'/'26'）提取数字基数；非法返回 None"""
    if art is None:
        return None
    m = _re.match(r"\s*(\d+)", str(art))
    return int(m.group(1)) if m else None


def is_meta_file(path):
    """路径命中工具/元数据片段 → 豁免"""
    p = path or ""
    return any(f in p for f in META_PATH_FRAGMENTS)


def is_test_fixture(law, art):
    """刻意构造的假条号（如 9999）→ 豁免（兼容字符串条号键）"""
    b = art_base(art)
    return b is not None and (b >= 9999 or b <= 0)


def is_historical(law, art, ctx="", quote=""):
    """(law, art) 命中白名单，或上下文含旧法标记 → 合法历史引用"""
    if (law, art_base(art)) in HISTORICAL_OK:
        return True
    blob = " ".join([ctx or "", quote or ""])
    return any(m in blob for m in OLD_LAW_MARKERS)


def is_exempt(law, art, path="", ctx="", quote=""):
    """综合豁免判定：命中任一即豁免（不参与 A/B/C 判定）"""
    if is_test_fixture(law, art):
        return True
    if is_meta_file(path):
        return True
    if is_historical(law, art, ctx, quote):
        return True
    return False
