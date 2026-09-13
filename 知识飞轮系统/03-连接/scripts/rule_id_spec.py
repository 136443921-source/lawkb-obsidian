#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rule_id_spec.py —— 规则卡编号规范的**单一真源解析器**

> 供 next_rule_id.py（取号器）与 rule_id_guard.py（守卫）共用。
> 创立：2026-09-11，起因是一次典型的「硬编码抄白名单」事故。

## 为什么要有这个模块

2026-09-11 实测发现：规范《_规则卡编号体系规范.md》第二节白名单**实际 21 个域**，
而守卫与取号器里硬编码的却是 **14 个域**（抄自摄入自动化 prompt 里的旧版本），
导致 103 张完全合规的卡（AY 案由路由 90 / RA 名誉权 6 / CL 承揽 3 / RN·XR·YS·RY 各 1）
被误报为「域码不在白名单」，整整 103 条 WARN 全是噪音。

同一天还发现取号器里的领域名沿用了**已被规范 v1.2.0 修正的错误版本**
（`CS=建设工程 / JG=鉴定`，物理事实是 `CS=案例 / JG=建设工程`）。

**教训**：凡是「规范里有、代码里也要有」的清单，硬编码必然漂移。
规范是唯一真相，代码只负责解析，不负责复述。

## 用法

    from rule_id_spec import load_spec
    spec = load_spec()
    spec.domains            # {"PI": "人伤/人身损害", "AY": "案由路由/案由定性", ...}
    "AY" in spec            # True
    spec.is_whitelisted("AY")
    spec.card_type_domain   # {"AY": "案由路由卡"} —— 卡型专用域约束

解析失败时回退到内置兜底清单并打印警告，**绝不因规范改版而让门禁崩溃**。
"""

import os
import re

# 规范文件路径（相对本文件：03-连接/scripts → 06-沉淀/裁判规则库）
SPEC_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "../../06-沉淀/裁判规则库/_规则卡编号体系规范.md",
    )
)

# 兜底清单：规范解析失败时使用（2026-09-11 实测 21 域，与规范第二节一致）
FALLBACK_DOMAINS = {
    "PI": "人伤/人身损害", "HT": "合同风险", "CF": "慈善法/公益合规",
    "HG": "合规与政府监管", "LN": "律师实务/办案方法", "PR": "程序法/诉讼程序",
    "SH": "商事/公司股权", "GZ": "工伤/工亡", "CS": "案例/案例研究",
    "JG": "建设工程/建工", "CL": "承揽", "HY": "婚姻家事",
    "GS": "公司治理", "LD": "劳动争议", "HJ": "环境/其他",
    "AY": "案由路由/案由定性", "RA": "名誉权/人格权", "RN": "姓名权/人格权",
    "XR": "肖像权/人格权", "YS": "隐私权/人格权", "RY": "荣誉权/人格权",
}

# 卡型专用域：规范规定这些域码仅特定 card_type 可用，其他卡不得占用
# （规范第二节「🆕 2026-09-06 新增第 15 域 AY」条目）
CARD_TYPE_DOMAIN = {"AY": "案由路由卡"}

_ROW_RE = re.compile(r"^\|\s*\**([A-Z]{2})\**\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$", re.M)
_SEC_RE = re.compile(
    r"^##\s*二、域代码白名单.*?$(.*?)^##\s*三、", re.M | re.S
)


def _clean(s):
    """去掉 markdown 强调标记与括号补充说明。"""
    s = s.replace("**", "").replace("`", "").strip()
    s = re.sub(r"[（(]\s*(?:\d{4}-\d{2}-\d{2}[^）)]*)?\s*新增\s*[）)]", "", s)
    s = re.sub(r"\s*（[^）]*）\s*$", "", s)
    return s.strip()


class Spec:
    def __init__(self, domains, source, ok=True, warn=""):
        self.domains = domains
        self.source = source
        self.ok = ok
        self.warn = warn
        self.card_type_domain = dict(CARD_TYPE_DOMAIN)

    def __contains__(self, dom):
        return dom in self.domains

    def is_whitelisted(self, dom):
        return dom in self.domains

    def name(self, dom):
        return self.domains.get(dom, dom)

    def __len__(self):
        return len(self.domains)


def load_spec(path=None, quiet=False):
    """从规范文件解析域代码白名单。失败则回退兜底清单。"""
    p = path or SPEC_PATH
    try:
        with open(p, encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        if not quiet:
            print(f"⚠️ 规范读取失败（{e}），回退内置兜底白名单（{len(FALLBACK_DOMAINS)} 域）",
                  file=__import__("sys").stderr)
        return Spec(dict(FALLBACK_DOMAINS), "fallback", ok=False, warn=str(e))

    m = _SEC_RE.search(text)
    if not m:
        if not quiet:
            print("⚠️ 规范中未定位到「二、域代码白名单」章节，回退内置兜底白名单",
                  file=__import__("sys").stderr)
        return Spec(dict(FALLBACK_DOMAINS), "fallback", ok=False, warn="section not found")

    domains = {}
    for code, name, _cnt in _ROW_RE.findall(m.group(1)):
        if code in ("域码",):        # 表头行
            continue
        domains[code] = _clean(name)

    if len(domains) < 5:
        if not quiet:
            print("⚠️ 规范白名单解析结果过少，疑似格式变更，回退内置兜底白名单",
                  file=__import__("sys").stderr)
        return Spec(dict(FALLBACK_DOMAINS), "fallback", ok=False, warn="parsed too few")

    return Spec(domains, p, ok=True)


if __name__ == "__main__":
    s = load_spec()
    print(f"规范来源：{s.source}")
    print(f"解析状态：{'OK' if s.ok else 'FALLBACK ' + s.warn}")
    print(f"域数量：{len(s)}\n")
    for k, v in s.domains.items():
        ct = f"  ← 卡型专用域，仅 {s.card_type_domain[k]} 可用" if k in s.card_type_domain else ""
        print(f"  {k}  {v}{ct}")
