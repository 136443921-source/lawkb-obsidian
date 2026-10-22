#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
意图预判引擎 · 动作链触发逻辑（P1-1 · 2026-10-21）
=================================================
把「动作链与意图预判骨架.md」落成可调用触发逻辑：
  匹配链(trigger_keywords) → 识别已完节点 → 输出「预判」提议（只提议，不自动执行）。

权威数据源：同目录 action_chains.yaml（机器可读 SSOT）。
授权铁律：预判【只提议不自动执行】，除非老强明说"直接做"（PREF-010 / 决策权留用户）。

用法：
  python3 intent_predict.py --text "起草一份代理词" --context "已起草完成"
  python3 intent_predict.py --text "批量重编号" --context "dry-run 已出清单" --chain B
  python3 intent_predict.py --text "修复了脚本 bug" --context "修复完成" --json
  python3 intent_predict.py --list
"""
import os
import re
import sys
import json
import argparse

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML 不可用（托管 Python 应内置 6.0.3）")
    sys.exit(2)

HERE = os.path.dirname(os.path.abspath(__file__))
YAML_PATH = os.path.join(HERE, "action_chains.yaml")


def load_chains(path=YAML_PATH):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("chains", [])


def match_chain(text, context, chains):
    """按 trigger_keywords 命中数选最佳链；上下文含本链节点名（如"docx导出双轨"）
    视为本链进行中的强信号（0.5 权重），解决"后续请求不带原始触发词"的漏匹配。
    返回 (chain, score)。"""
    best, best_score = None, 0.0
    for c in chains:
        score = float(sum(1 for k in c.get("trigger_keywords", []) if k in text))
        score += 0.5 * sum(1 for n in c.get("nodes", []) if n in context)
        if score > best_score:
            best, best_score = c, score
    return best, best_score


def detect_node(chain, context):
    """在 context 中按节点名出现顺序，定位最近一次完成的节点（最后一个命中）。"""
    nodes = chain.get("nodes", [])
    last_idx = -1
    for i, n in enumerate(nodes):
        if n in context:
            last_idx = i
    return last_idx


def build_result(chain, node_idx, matched_score=0):
    """由链 + 当前节点序号生成预判结果 dict（只提议，不执行）。"""
    nodes = chain.get("nodes", [])
    ant = {a["node"]: a["suggest"] for a in chain.get("anticipation", [])}
    cid, cname = chain["id"], chain["name"]
    if not nodes:
        return None
    if node_idx < 0:
        # 链刚触发：预判从第二节点起步
        nxt = nodes[1] if len(nodes) > 1 else None
        sugg = ant.get(nodes[0]) or (f"从「{nxt}」开始？" if nxt else "")
        return {
            "chain": cid, "name": cname, "matched": matched_score,
            "current_node": "(链触发)", "next_node": nxt,
            "message": f"[预判·链{cid}] 命中「{cname}」，建议起步：{sugg}（只提议，不自动执行）",
            "auto": False, "force_ask": bool(chain.get("force_ask", False)),
        }
    if node_idx >= len(nodes) - 1:
        term = chain.get("terminal", nodes[-1])
        return {
            "chain": cid, "name": cname, "matched": matched_score,
            "current_node": nodes[-1], "next_node": None,
            "message": f"[预判·链{cid}] 已到终止节点（{term}），无需继续；可收尾。",
            "auto": False, "force_ask": bool(chain.get("force_ask", False)),
        }
    nxt = nodes[node_idx + 1]
    sugg = ant.get(nodes[node_idx]) or f"是否进行下一步：{nxt}？"
    return {
        "chain": cid, "name": cname, "matched": matched_score,
        "current_node": nodes[node_idx], "next_node": nxt,
        "message": f"[预判·链{cid}] 检测到「{nodes[node_idx]}」已完成/进行中，建议下一步：{sugg}（只提议，不自动执行）",
        "auto": False, "force_ask": bool(chain.get("force_ask", False)),
    }


def suggest(text, context="", chains=None):
    if chains is None:
        chains = load_chains()
    chain, score = match_chain(text, context, chains)
    if chain is None or score == 0:
        return None  # 无链命中，不预判，避免噪音
    idx = detect_node(chain, context) if context else -1
    return build_result(chain, idx, score)


def main():
    ap = argparse.ArgumentParser(description="意图预判引擎（动作链触发逻辑）")
    ap.add_argument("--text", default="", help="本轮用户请求/意图文本（用于匹配链）")
    ap.add_argument("--context", default="", help="近期上下文（含已完成节点信号）")
    ap.add_argument("--chain", default=None, help="强制指定链 id（跳过匹配）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--list", action="store_true", help="列出全部链概要")
    args = ap.parse_args()

    chains = load_chains()
    if args.list:
        for c in chains:
            print(f"链-{c['id']} {c['name']} | 节点 {len(c.get('nodes', []))} | "
                  f"触发词 {', '.join(c.get('trigger_keywords', [])[:4])}…")
        return

    if args.chain:
        chain = next((c for c in chains if c["id"] == args.chain), None)
        if chain is None:
            print(f"[ERROR] 未找到链 {args.chain}")
            sys.exit(1)
        idx = detect_node(chain, args.context) if args.context else -1
        res = build_result(chain, idx, 1)
    else:
        if not args.text:
            print("[ERROR] 需提供 --text（或 --list）")
            sys.exit(1)
        res = suggest(args.text, args.context, chains)

    if res is None:
        print("[预判] 无链命中，不干扰。")
        return
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(res["message"])


if __name__ == "__main__":
    main()
