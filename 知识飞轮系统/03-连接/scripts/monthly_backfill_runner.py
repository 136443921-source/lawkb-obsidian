#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
月度蒸馏回灌 · 专项补索引运行器（增量版 v2.2）
- 修复「目录 0 文件/不存在」类否定结论未二次复核的根因（safe_walk 防护）
- 过滤口径：未索引 + (created 或 updated) 在窗口内（非纯 created 月份）
- 元文件/治理文件排除；批戳污染退回 created
- 六-B：写入前 cp 备份 + 字节校验；异常回滚
- 分轮次写入（默认每轮 ≤50，避开 v2.1 单轮 >150 上限告警）
"""
import os, sys, re, shutil, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from intake_monthly_driver import BackfillScanner

SELF_MD = os.path.expanduser("~/.workbuddy/skills/xiaoqianglvshi/self.md")
BACKUP_DIR = os.path.expanduser("~/.workbuddy/skills/xiaoqianglvshi/backups")
ANCHOR = "> 索引随月度蒸馏增长"
MONTH_START = "2026-10-01"
ROUND_CAP = 50


def backup_self():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    dst = os.path.join(BACKUP_DIR, "self_backup_backfill_%s" % ts)
    shutil.copyfile(SELF_MD, dst)
    a = os.path.getsize(SELF_MD)
    b = os.path.getsize(dst)
    assert a == b, "备份字节数不一致 %d != %d" % (a, b)
    return dst, a


def extract_indexed_paths(txt):
    idx = txt.find("## 经验索引区")
    if idx < 0:
        return set()
    sec = txt[idx:]
    paths = set()
    for ln in sec.split("\n"):
        if not ln.startswith("|"):
            # 索引区结束（遇到下一个 ## 或 EOF 前最后的 > 锚点之后）
            if ln.startswith("## ") and ln.strip() != "## 经验索引区（指针表 · 由月度蒸馏回灌）":
                break
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[1].startswith("`") and cells[1].endswith("`"):
            paths.add(cells[1].strip("`"))
    return paths


def build_rows(cands):
    out = []
    for c in cands:
        pointer = "%s-%s" % (c["prefix"], c["title"])
        path = "`%s`" % c["rel"]
        summary = (c.get("summary") or "").replace("\n", " ").replace("|", "／")
        out.append("| %s | %s | %s |" % (pointer, path, summary))
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="真正写入（默认仅报数）")
    ap.add_argument("--round-cap", type=int, default=ROUND_CAP)
    args = ap.parse_args()

    # 0. 读 self.md
    txt = open(SELF_MD, encoding="utf-8").read()
    if ANCHOR not in txt:
        print("❌ 未找到索引增长锚点行，中止"); sys.exit(1)

    # 1. 去重集合
    already = extract_indexed_paths(txt)
    print("[去重] 当前索引区已收录路径数:", len(already))

    # 2. 扫描（apply 时跑 LTI；报数时 skip_lti 加快）
    sc = BackfillScanner()
    res = sc.collect(MONTH_START, already, skip_lti=not args.apply)
    cands = res["candidates"]
    print("[扫描] dir_report:", res["dir_report"])
    print("[扫描] excluded:", res["excluded"])
    print("[扫描] pollution stamps:", len(res["pollution"]))
    print("[候选] 待补总数:", len(cands))
    from collections import Counter
    print("[候选] 分类:", dict(Counter(c["prefix"] for c in cands)))
    if res.get("lti_blocked"):
        print("[LTI 拦截]:", res["lti_blocked"])

    if not args.apply:
        print("\n--- 仅报数模式（加 --apply 才写入）---")
        # 预演轮次切分
        rounds = [cands[i:i + args.round_cap] for i in range(0, len(cands), args.round_cap)]
        print("将分 %d 轮写入，每轮 ≤%d：" % (len(rounds), args.round_cap))
        for i, r in enumerate(rounds):
            print("  轮 %d: %d 条" % (i + 1, len(r)))
        return

    if not cands:
        print("无可补，退出"); return

    # 3. 分轮写入（六-B：每轮写入前单独 cp 备份 + 字节校验，异常可秒级回滚）
    rounds = [cands[i:i + args.round_cap] for i in range(0, len(cands), args.round_cap)]
    inserted_total = 0
    pre_lines = open(SELF_MD, encoding="utf-8").read().count("\n") + 1
    anchors = []
    for i, r in enumerate(rounds):
        dst, sz = backup_self()
        anchors.append(dst)
        rows = build_rows(r)
        block = "\n".join(rows) + "\n"
        cur = open(SELF_MD, encoding="utf-8").read()
        pos = cur.find(ANCHOR)
        assert pos >= 0
        # 锚点行前插入（保持原行结构：锚点行单独成行）
        new = cur[:pos] + block + cur[pos:]
        open(SELF_MD, "w", encoding="utf-8").write(new)
        post_lines = open(SELF_MD, encoding="utf-8").read().count("\n") + 1
        assert post_lines == pre_lines + len(rows), "行数校验失败 %d != %d" % (post_lines, pre_lines + len(rows))
        pre_lines = post_lines
        inserted_total += len(rows)
        print("[六-B] 轮 %d 备份: %s (%d字节) | 写入 %d 条，累计 %d，当前 %d 行"
              % (i + 1, dst, sz, len(rows), inserted_total, post_lines))

    # 5. 日志
    log_path = os.path.join(HERE, "..", "月度回灌日志.md")
    log_path = os.path.abspath(log_path)
    ts_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    line = "- [北京时间 %s] 专项补索引(修复裁判规则库漏扫)：新增 %d 条（裁判规则 %d / 经验卡片 %d），索引区现约 %d 行（LTI 拦截 %d 条）。扫描目录: %s\n" % (
        ts_now, inserted_total,
        sum(1 for c in cands if c["prefix"] == "裁判规则"),
        sum(1 for c in cands if c["prefix"] == "经验卡片"),
        pre_lines, len(res.get("lti_blocked", [])),
        " + ".join(res["dir_report"].keys()))
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)
    print("[日志] 已追加:", log_path)
    print("[完成] 共补 %d 条。回滚锚点:", dst)


if __name__ == "__main__":
    main()
