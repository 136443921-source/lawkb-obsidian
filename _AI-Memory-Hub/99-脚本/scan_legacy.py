#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_legacy.py — 只读盘点遗留资产，提炼方法论进 AI 共享记忆中枢。

扫描源：
  - LEGACY   = /Users/chenyouqiang/Documents/xiaoqianglawkb   (600 个 .md)
  - PROJECTS = /Users/chenyouqiang/.workbuddy/projects        (1104 个 .jsonl 会话)

红线（违反即为事故）：
  - 只读：绝不修改任何源文件，只读取并产出报告。
  - 隐私：命中身份证/手机号/银行卡/诉讼角色词即丢弃整段，绝不允许个案卷宗入中枢。
  - 不灌爆：相似度去重聚合 + auto-ingest 封顶 --max-ingest（默认20）+ 复用 write_back 0.85 相似度拦截与备份。
  - 只提炼方法论与工作流事实。

用法：
  python3 scan_legacy.py --dry-run               # 只产出报告，不写回中枢
  python3 scan_legacy.py --auto-ingest           # 高价值候选自动写回（workflow/decision/preference/rule，封顶20）
  python3 scan_legacy.py --include-jsonl         # 额外扫描 projects 的 .jsonl 会话（默认只扫旧库 md）
  python3 scan_legacy.py --auto-ingest --include-jsonl --max-ingest 15
"""
import os
import re
import io
import sys
import json
import subprocess
import argparse
import datetime
import collections

HUB = "/Users/chenyouqiang/Documents/LawKB/_AI-Memory-Hub"
LEGACY = "/Users/chenyouqiang/Documents/xiaoqianglawkb"
PROJECTS = "/Users/chenyouqiang/.workbuddy/projects"
REPORT_DIR = os.path.join(HUB, "04-每日日志")

# 方法论关键词（命中即可能是有价值片段）
KW = ["红蓝复核", "红蓝对抗", "模拟法庭", "意思表示真实", "冒名诉讼", "法条核验", "法条缓存",
      "LTI", "docx 双轨", "双轨交付", "知识飞轮", "取号", "撞号", "冲突仲裁", "安全铁律", "六-B",
      "双目录同步", "IMA回传", "回传", "流水线", "SOP", "方法论构建", "复盘方法论",
      "合规审查", "审查意见书", "反向质疑", "预驳回攻击", "合同审查", "代理词"]

# 强信号（用于 jsonl 严格提取 & 分类）
STRONG = {
    "workflow": ["红蓝复核", "红蓝对抗", "模拟法庭", "docx 双轨", "双轨交付", "知识飞轮",
                 "取号", "撞号", "流水线", "SOP", "工作流", "复盘方法论", "双目录同步", "IMA回传"],
    "decision": ["拍板", "确立为", "决议", "定调", "就这么定", "决定采用"],
    "preference": ["偏好", "铁律", "习惯", "要求", "忌", "慎用", "不喜欢"],
    "rule": ["LTI", "法条核验", "法条缓存", "门禁", "五维", "合规审查", "冲突仲裁"],
}

# 隐私模式（命中即丢弃整段）：身份证 / 手机号 / 银行卡 / 诉讼角色词
PRIV = re.compile(
    r"\d{17}[\dXx]|1[3-9]\d{9}|\d{16,19}|身份证号|案号|原告|被告|"
    r"申请人|被申请人|上诉人|被上诉人|银行卡号|手机号",
    re.IGNORECASE)

# 路径黑名单：法条原文 / 个案卷宗 / 剪藏，不属于老强的方法论，跳过
EXCLUDE_PATH = ["法律法规库", "承办案件", "Clippings", "指导案例", "裁判文书库",
                "起诉状", "代理词", "执行异议"]
# 法条噪声：含>=2处"第X条"引用且无强工作流动词 -> 视为法条原文
_LAW_RE = re.compile(r"第[一二三四五六七八九十百0-9]+条")
def is_law_noise(seg):
    return len(_LAW_RE.findall(seg)) >= 2 and not any(k in seg for k in STRONG["workflow"])

# 高质量来源白名单（老强专属方法论目录）；非白名单仅当含超强信号词才保留
WHITELIST_DIR = ["执业技能库", "红队", "蓝队", "模拟法庭", "知识飞轮", "合同审查",
                 "法条", "LTI", "复盘", "双轨", "合规", "审查", "取号", "撞号", "冲突",
                 "厚德基金会", "公益", "律师"]
SUPER = ["红蓝复核", "红蓝对抗", "模拟法庭", "docx 双轨", "双轨交付", "知识飞轮", "取号",
         "撞号", "冲突仲裁", "安全铁律", "六-B", "双目录同步", "IMA回传", "LTI", "法条核验",
         "法条缓存", "反向质疑", "预驳回攻击"]
def source_ok(path, seg):
    if any(d in path for d in WHITELIST_DIR):
        return True
    return any(k in seg for k in SUPER)

KW_RE = re.compile("|".join(re.escape(k) for k in KW))
STRONG_RE = re.compile("|".join(re.escape(k) for k in sum(STRONG.values(), [])))


def priv_hit(t):
    """命中隐私模式即 True。"""
    return bool(PRIV.search(t))


def grep_files(root, ext, pattern, timeout=120):
    """grep -rl 预筛命中文件（只读，不读内容），返回路径列表。"""
    try:
        r = subprocess.run(["grep", "-rl", "-E", pattern, root, "--include=" + ext],
                           capture_output=True, text=True, timeout=timeout)
        return [l for l in r.stdout.splitlines() if l.strip()]
    except Exception:
        return []


def extract_window(text, kw_list, window=160):
    """取含关键词的窗口片段（前后 window 字符），去换行。"""
    m = re.search("|".join(re.escape(k) for k in kw_list), text)
    if not m:
        return None
    s = max(0, m.start() - window)
    e = min(len(text), m.end() + window)
    return text[s:e].replace("\n", " ").strip()


def classify(seg):
    """按强信号词分类。"""
    for t, kws in STRONG.items():
        if any(k in seg for k in kws):
            return t
    return "workflow"


def scan_md(path):
    """逐行扫描 md，返回 [(片段, 行号)]。跳过黑名单路径与法条噪声。"""
    if any(x in path for x in EXCLUDE_PATH):
        return []
    out = []
    try:
        for i, line in enumerate(io.open(path, encoding="utf-8", errors="ignore"), 1):
            if KW_RE.search(line) and not priv_hit(line) and not is_law_noise(line) and source_ok(path, line):
                w = extract_window(line, KW)
                if w and len(w) >= 20:
                    out.append((w, i))
    except Exception:
        pass
    return out


def scan_jsonl(path):
    """解析 jsonl 会话，提取含强信号的较长方法论述说。"""
    out = []
    try:
        with io.open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    j = json.loads(line)
                except Exception:
                    continue
                text = ""
                c = j.get("content")
                if isinstance(c, str):
                    text = c
                elif isinstance(c, list):
                    for it in c:
                        if isinstance(it, dict):
                            if it.get("type") == "input_text":
                                text += it.get("text", "")
                            elif "text" in it:
                                text += it.get("text", "")
                if STRONG_RE.search(text) and not priv_hit(text) and not is_law_noise(text) and source_ok(path, text):
                    w = extract_window(text, sum(STRONG.values(), []))
                    if w and len(w) >= 80:  # jsonl 严格：只取长段，避免口头禅噪声
                        out.append((w, 0))
    except Exception:
        pass
    return out


def short(p):
    return p.replace(HUB, "<hub>").replace(LEGACY, "<legacy>").replace(PROJECTS, "<projects>")


def do_ingest(items, maxn, dry):
    """复用 write_back.py 写回中枢（自带 0.85 拦截 + /tmp 备份）。"""
    wb = os.path.join(HUB, "99-脚本", "write_back.py")
    n = 0
    for it in items:
        if n >= maxn:
            break
        if it["type"] not in ("workflow", "decision", "preference", "rule"):
            continue
        title = it["seg"][:40].replace("\n", " ").strip() or "遗留资产提炼"
        body = "来源：%s\n\n%s" % (it["path"], it["seg"][:400])
        cmd = [sys.executable, wb, "--type", it["type"], "--title", title, "--body", body]
        if dry:
            cmd.append("--dry-run")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            last = (r.stdout or r.stderr).strip().splitlines()
            print("  ingest[%d] %s: %s" % (n + 1, it["type"], last[-1][:120] if last else "ok"))
            n += 1
        except Exception as e:
            print("  ingest 失败: %s" % e)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--auto-ingest", action="store_true")
    ap.add_argument("--include-jsonl", action="store_true")
    ap.add_argument("--max-ingest", type=int, default=20)
    args = ap.parse_args()
    if not args.dry_run and not args.auto_ingest:
        args.dry_run = True

    today = datetime.date.today().strftime("%Y-%m-%d")
    print("扫描源: 旧库 %s + projects %s%s" % (LEGACY, PROJECTS,
          " (含jsonl)" if args.include_jsonl else " (仅md)"))

    cands = []  # (src, seg, path)
    md_files = grep_files(LEGACY, "*.md", "|".join(KW))
    print("旧库命中 md: %d" % len(md_files))
    for p in md_files:
        for seg, ln in scan_md(p):
            cands.append(("md", seg, p))
    if args.include_jsonl:
        jf = grep_files(PROJECTS, "*.jsonl", "|".join(sum(STRONG.values(), [])))
        print("projects 命中 jsonl: %d" % len(jf))
        for p in jf:
            for seg, ln in scan_jsonl(p):
                cands.append(("jsonl", seg, p))

    # 去重聚合（前40字为指纹）
    seen = {}
    dedup = []
    for src, seg, path in cands:
        key = seg[:40]
        if key in seen:
            if path not in seen[key][2]:
                seen[key][2].append(path)
            continue
        seen[key] = [src, seg, [path]]
        dedup.append(seen[key])
    print("原始片段 %d → 去重后 %d" % (len(cands), len(dedup)))

    # 分类
    items = [{"type": classify(seg), "seg": seg, "path": paths[0], "sources": paths}
             for src, seg, paths in dedup]

    # 写报告
    os.makedirs(REPORT_DIR, exist_ok=True)
    rep = os.path.join(REPORT_DIR, "legacy-scan-%s.md" % today)
    L = []
    L.append("# 遗留资产盘点报告 %s" % today)
    L.append("")
    L.append("- 扫描源：`%s` (md %d) + `%s` (jsonl %s)" %
             (LEGACY, len(md_files), PROJECTS, "含" if args.include_jsonl else "未含"))
    L.append("- 原始片段 %d，去重后 %d" % (len(cands), len(dedup)))
    L.append("- 模式：%s" % ("dry-run（仅报告）" if not args.auto_ingest else "auto-ingest（自动写回封顶%d）" % args.max_ingest))
    L.append("")
    bytype = collections.defaultdict(list)
    for it in items:
        bytype[it["type"]].append(it)
    for t in ["workflow", "decision", "preference", "rule"]:
        L.append("## %s（%d）" % (t, len(bytype[t])))
        for it in bytype[t][:60]:
            snip = it["seg"][:120].replace("|", "/")
            L.append("- [%s] `%s` — %s" % (t, short(it["path"]), snip))
        L.append("")
    io.open(rep, "w", encoding="utf-8").write("\n".join(L))
    print("报告已写: %s" % rep)

    if args.auto_ingest:
        print("=== 自动写回（复用 write_back 拦截+备份）===")
        # 按价值排序：workflow/decision 优先
        order = {"workflow": 0, "decision": 1, "preference": 2, "rule": 3}
        items.sort(key=lambda x: order.get(x["type"], 9))
        n = do_ingest(items, args.max_ingest, dry=False)
        print("自动写回 %d 条（其余留待人工确认）" % n)

    return rep


if __name__ == "__main__":
    main()
