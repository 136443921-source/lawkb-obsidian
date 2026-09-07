# -*- coding: utf-8 -*-
"""第五部分 婚姻家庭纠纷 · 六层挂载脚本（2026-09-07）"""
import os, re, json, importlib.util

BASE = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
D = os.path.join(BASE, "02-提炼/审判要件卡")
spec = importlib.util.spec_from_file_location("g", os.path.join(D, "_gen_hy_20260907.py"))
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
CARDS = g.CARDS
OUT = "/tmp/_hy_mount_20260907.md"

GROUPS = [
    ("A 组 · 审理原则与立案审查（审理思路·一、二）", range(1, 4)),
    ("B 组 · 身份关系类纠纷审查（离婚主体·准予离婚·无效与可撤销婚姻·调解）", range(4, 14)),
    ("C 组 · 婚约财产与彩礼返还（审理思路·四（一））", range(14, 19)),
    ("D 组 · 夫妻财产归属与债务定性", range(19, 25)),
    ("E 组 · 财产分割与擅自处分（审理思路·四（六））", range(25, 32)),
    ("F 组 · 与婚姻有关协议的审查（审理思路·五）", range(32, 37)),
    ("G 组 · 损害赔偿（审理思路·六）", range(37, 40)),
    ("H 组 · 扶养、赡养与人身安全保护令（审理思路·七）", range(40, 45)),
    ("I 组 · 附录案例（第四章）", range(45, 53)),
]


def rid(c):
    return g.rid(c["i"])


def base(c):
    return g.fname(c)


def sec_text():
    L = []
    L.append("### 4.9 婚姻家庭纠纷（HY 域 · R-HY-004~055，第七批，52 张）")
    L.append("")
    L.append("> **落盘目录**：`06-沉淀/裁判规则库/婚姻家庭/`（HY 域物理文件总数 55；本批 52 张）")
    L.append("> **母本位置**：第五部分「婚姻家庭纠纷案件审判要件指南」（PDF页254-306 / 书页222-275）")
    L.append("> **取号铁律兑现**：拆卡当日实地取号——HY 物理 max=**003**，起始号 **004**，一次性连续取满 004~055，建卡过程未被并发流水线抢占（建卡后实测 max=055）。")
    L.append("> **法条回填**：本会话华宇元典 / 北大法宝 MCP **未注册进工具表**（已按「判定 MCP 不可用 6 步流程」逐一排查：`connector-states.json` 中 `pkulaw: enabled=True`、`yuandian-mcp: enabled=True`，但真调用报「not found in the deferred tools index」），**降级走权威公开源核填**，卡内标注一律写「**权威源核填**」，**不虚标元典核填**。法条库 **9 部 / 165 条**，卡内引用 **173 条次**。")
    L.append("> **⚠️ 版本陷阱（本批最高价值登记）**：婚后父母出资购房的分割口径**已整体换版**——《婚姻家庭编解释一》第二十九条第二款「婚后父母出资无约即推定赠与双方」已被 **《婚姻家庭编解释二》第八条**（法释〔2025〕1号，2025-02-01 施行）取代，改为「**以出资来源及比例为基础 + 综合考量**」，**婚后父母出资不再当然各半** → 见 [[R-HY-030-父母出资购房分割]]。另：夫妻间房屋给予**不适用赠与合同任意撤销权**（解释二第五条第三款撤销后无须补偿）→ 见 [[R-HY-025-房屋给予未过户的分割与撤销]]。")
    L.append("")
    for title, rng in GROUPS:
        L.append("**%s**" % title)
        L.append("")
        L.append("| 编号 | 卡片 | 审理环节 |")
        L.append("|------|------|----------|")
        for c in CARDS:
            if c["i"] in rng:
                L.append("| [[%s]] | %s | %s |" % (base(c), c["title"], c["review_step"]))
        L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    open(OUT, "w", encoding="utf-8").write(sec_text())
    print("节文本已生成：%s（%d 字符）" % (OUT, len(sec_text())))
