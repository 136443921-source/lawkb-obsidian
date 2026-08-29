#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backfill_yuandian_ids.py  v1.0  (2026-08-28)

用途
----
为裁判规则库全部卡片（R-*.md）回填「华宇元典（yuandian）可查标识符」，
打通在线对账。

设计铁律（不可放松）
--------------------
1. **绝不猜测**：只写卡片正文/frontmatter 中**真实存在**的案号锚点；
   语义相似度、标题近似一律不作为写入依据（否则污染去重表）。
2. **案号优先于 hash id**：案号（ah）是人可复核、接口可直查的稳定锚点；
   32 位 hash id 只是厂商内部代理键，仅对**已实证命中**的案号写入。
3. **诚实挂起**：无任何案号锚点的卡片写 `yuandian_source_pending: true`，
   不编造 id / 不留空占位。
4. **写前备份 + 文件数断言 + 幂等**：默认 dry-run，--apply 才落盘。

字段语义
--------
yuandian_ah            归一化案号（半角括号），可直接喂给 yuandian_rh_case_details 的 ah 参数
yuandian_case_id       32 位 hash id，仅实证命中才写
yuandian_case_type     普通案例 / 权威案例
yuandian_verified      true=已实证命中；false=已实证「库内未收录」
yuandian_verify_pending true=有案号锚点但本轮未实证（留待后续月度对账消费）
yuandian_miss_reason   verified:false 时的原因说明
yuandian_source_pending true=无任何案号锚点，无法在线对账（诚实挂起）
yuandian_checked       本次核验/回填日期

用法
----
  python3 backfill_yuandian_ids.py                 # dry-run
  python3 backfill_yuandian_ids.py --apply         # 落盘（自动备份）
  python3 backfill_yuandian_ids.py --report out.md # 附带写明细报告
"""

import argparse
import datetime
import json
import os
import re
import shutil
import sys

ROOT = "/Users/chenyouqiang/Documents/LawKB"
CARDS_DIR = os.path.join(ROOT, "知识飞轮系统/06-沉淀/裁判规则库")
LEDGER = "/tmp/yuandian_results.json"
LEDGER_FALLBACK = os.path.join(ROOT, "知识飞轮系统/03-连接/yuandian_results.json")

TODAY = datetime.date.today().isoformat()

# ---------- 锚点识别 ----------
AH_RE = re.compile(
    r"[（(]\s*(\d{4})\s*[)）]\s*([\u4e00-\u9fa5A-Za-z0-9〔〕\[\]（）()]{2,40}?)\s*号"
)
GUIDE_RE = re.compile(r"指导(?:性)?案例\s*(\d{1,3})\s*号")

# 指导案例号 → 已实证映射的真实案号
GUIDE_KNOWN = {
    "33": "(2012)民四终字第1号",
    "67": "(2015)民申字第2532号",
    "24": "(2013)锡民终字第497号",
    "17": "(2008)二中民终字第00453号",
}

BAD_AH_TOKENS = ("法释", "；", ";", "法发", "号令")

# ---- 污染隔离（v1.1 关键修复）----
# 知识飞轮连接层会把「别的笔记文件名」写进卡片末尾的自动补链区块和
# related_links 字段；这些文件名里常带案号，但**不是本卡的源案例**。
# 实测 R-PI-145（工伤认定）就被共现笔记里的 (2021)最高法民再145号
# （房屋租赁合同无效案）污染。故锚点只从「本体内容」提取。
FM_EXCLUDE_KEYS = {
    "related_links", "related", "related_law", "related_rules",
    "related_notes", "related_cards", "cross_link",
}
BODY_CUT_RE = re.compile(r"^#{1,3}\s*(关联|相关笔记|共现笔记|自动补链|关联笔记)", re.M)


def norm_ah(s: str) -> str:
    """归一化案号：全角括号→半角，去空白。"""
    s = s.strip()
    s = s.replace("（", "(").replace("）", ")")
    s = re.sub(r"\s+", "", s)
    return s


def valid_ah(s: str) -> bool:
    if any(t in s for t in BAD_AH_TOKENS):
        return False
    if not re.match(r"^\(\d{4}\)", s):
        return False
    if len(s) < 8 or len(s) > 48:
        return False
    return True


def clean_body(body: str) -> str:
    """截掉知识飞轮自动补链区块（关联/相关笔记/共现笔记）及其之后内容。"""
    m = BODY_CUT_RE.search(body)
    return body[:m.start()] if m else body


def clean_fm(fm_lines):
    """剔除 related_* 等自动补链字段（含其缩进续行）。"""
    out, skip = [], False
    for ln in fm_lines:
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", ln)
        if m:
            skip = m.group(1) in FM_EXCLUDE_KEYS
        elif re.match(r"^\s*\S", ln) and not ln.startswith((" ", "\t", "-")):
            skip = False
        if not skip:
            out.append(ln)
    return out


def extract_anchors(fm_lines, body):
    """只从「本体内容」提取锚点；返回 (案号列表, 指导案例号列表)。"""
    text = "\n".join(clean_fm(fm_lines)) + "\n" + clean_body(body)
    return _scan(text)


def _scan(text: str):
    ahs, guides = [], []
    for m in AH_RE.finditer(text):
        raw = m.group(0)
        a = norm_ah(raw)
        if valid_ah(a) and a not in ahs:
            ahs.append(a)
    for m in GUIDE_RE.finditer(text):
        g = m.group(1)
        if g not in guides:
            guides.append(g)
    return ahs, guides


# ---------- frontmatter 读写 ----------
def split_fm(text: str):
    """返回 (fm_lines, body, has_fm)。fm_lines 不含起止 ---。"""
    if not text.startswith("---"):
        return [], text, False
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return [], text, False
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:]), True
    return [], text, False


def fm_get_keys(fm_lines):
    keys = {}
    for idx, ln in enumerate(fm_lines):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", ln)
        if m:
            keys[m.group(1)] = idx
    return keys


def fm_apply(fm_lines, upserts: dict, deletes: set):
    """就地 upsert/delete，返回 (new_lines, changed_bool)。"""
    lines = list(fm_lines)
    changed = False

    # delete（含块式列表续行一并清除）
    for k in deletes:
        while True:
            keys = fm_get_keys(lines)
            if k not in keys:
                break
            i = keys[k]
            del lines[i]
            while i < len(lines) and re.match(r"^\s+\S", lines[i]) \
                    and not re.match(r"^\s*#{1,3}\s", lines[i]):
                del lines[i]
            changed = True

    # upsert
    for k, v in upserts.items():
        if isinstance(v, list):
            val = "[" + ", ".join('"%s"' % x for x in v) + "]"
        elif v is True:
            val = "true"
        elif v is False:
            val = "false"
        elif isinstance(v, str) and (v.startswith("(") or " " in v):
            val = '"%s"' % v
        else:
            val = str(v)
        newline = "%s: %s" % (k, val)
        keys = fm_get_keys(lines)
        if k in keys:
            if lines[keys[k]].rstrip() != newline:
                lines[keys[k]] = newline
                changed = True
        else:
            lines.append(newline)
            changed = True
    return lines, changed


def rebuild(fm_lines, body):
    return "---\n" + "\n".join(fm_lines) + "\n---\n" + body.lstrip("\n")


# ---------- 主流程 ----------
def load_ledger():
    path = LEDGER if os.path.exists(LEDGER) else LEDGER_FALLBACK
    if not os.path.exists(path):
        print("[FATAL] 找不到实查台账：%s" % path)
        sys.exit(2)
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def prune_snapshots(cards_dir, keep=2, dry=False):
    """快照保留上限：同名基线的 `.bak-*` 目录只保留「最近 keep 份」，删除更早的。

    背景（2026-08-29 事故）：单次回填任务反复 `--apply`，每次 copytree 一份全量副本，
    一次任务即产生 5 份 × 619 文件 = 3086 个冗余副本（约 15 MB），且全部漏进 git
    ——根因是 .gitignore 的 `*.bak` 只匹配**文件**，匹配不到 `xxx.bak-时间戳` **目录**。

    策略：保留最近 N 份（默认 2）。回滚通常用最近快照，故不保留"最早基线"，
    避免保留策略与 .gitignore 白名单打架（白名单保留的是最近两份）。
    """
    parent = os.path.dirname(cards_dir.rstrip("/")) or "."
    base = os.path.basename(cards_dir.rstrip("/"))
    prefix = base + ".bak-"

    def _snap_key(name, full):
        """排序键：优先取目录名内嵌的时间戳 `YYYYMMDD-HHMMSS`。

        注意：**不能用 mtime 排序**。2026-08-29 实测 5 个快照目录的 mtime 全被
        Obsidian 索引/扫描进程刷成同一时刻，按 mtime 排序会把最新的基线误判为最旧、
        进而误删。目录名内嵌时间戳才是稳定可靠的序。
        """
        m = re.search(r"(\d{8}-\d{6})", name)
        if m:
            return m.group(1)
        return "00000000-000000_%013.3f" % os.path.getmtime(full)  # 无时间戳者当最旧

    snaps = []
    for name in os.listdir(parent):
        full = os.path.join(parent, name)
        if name.startswith(prefix) and os.path.isdir(full):
            snaps.append((_snap_key(name, full), name, full))

    if len(snaps) <= keep:
        return [], [n for _k, n, _f in snaps]

    snaps.sort(key=lambda x: x[0])               # 时间戳升序：最旧的在前
    doomed = snaps[:len(snaps) - keep]           # 超出上限的从最旧开始删
    removed = []
    for _k, name, full in doomed:
        if dry:
            print("  [预演] 将删除旧快照 %s" % name)
        else:
            shutil.rmtree(full)
            print("  [清理] 已删除旧快照 %s" % name)
        removed.append(name)

    kept = [n for _k, n, _f in snaps[len(snaps) - keep:]]
    return removed, kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="落盘（默认 dry-run）")
    ap.add_argument("--report", default="", help="写明细报告到指定 md 路径")
    ap.add_argument("--keep-snapshots", type=int, default=2,
                    help="快照保留上限：只保留最近 N 份 .bak-* 副本（默认 2）")
    ap.add_argument("--prune-only", action="store_true",
                    help="只清理过期快照，不执行回填")
    ap.add_argument("--prune-dry", action="store_true",
                    help="配合 --prune-only：只预演，不真删")
    args = ap.parse_args()

    if args.prune_only:
        print("===== 仅清理过期快照（保留最近 %d 份）=====" % args.keep_snapshots)
        removed, kept = prune_snapshots(CARDS_DIR, args.keep_snapshots, dry=args.prune_dry)
        print("删除 %d 份：%s" % (len(removed), ", ".join(removed) or "无"))
        print("保留 %d 份：%s" % (len(kept), ", ".join(kept)))
        return

    ledger, ledger_path = load_ledger()
    hit = {norm_ah(k): v for k, v in ledger.get("hit", {}).items()}
    miss = {norm_ah(x) for x in ledger.get("miss", [])}
    hit_no_id = {norm_ah(x) for x in ledger.get("hit_id_unknown", [])}

    files = []
    for dp, _dn, fn in os.walk(CARDS_DIR):
        for f in fn:
            if f.endswith(".md"):
                files.append(os.path.join(dp, f))
    files.sort()
    total_before = len(files)
    print("扫描卡片：%d 张（台账：%s）" % (total_before, ledger_path))
    print("台账 hit=%d  hit_id_unknown=%d  miss=%d" % (len(hit), len(hit_no_id), len(miss)))

    buckets = {
        "verified_with_id": [],
        "verified_no_id": [],
        "miss_confirmed": [],
        "verify_pending": [],
        "source_pending": [],
        "no_fm_skipped": [],
    }
    changed_files = []
    plan = []  # (path, new_text)
    pending_ahs = set()  # 全库尚未实证的案号（含副锚点）

    for path in files:
        rel = os.path.relpath(path, CARDS_DIR)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        fm_lines, body, has_fm = split_fm(text)
        if not has_fm:
            buckets["no_fm_skipped"].append(rel)
            continue

        ahs, guides = extract_anchors(fm_lines, body)
        # 指导案例映射补位
        for g in guides:
            if g in GUIDE_KNOWN and GUIDE_KNOWN[g] not in ahs:
                ahs.append(GUIDE_KNOWN[g])

        upserts, deletes = {}, set()

        if not ahs:
            upserts["yuandian_source_pending"] = True
            upserts["yuandian_checked"] = TODAY
            deletes |= {"yuandian_ah", "yuandian_case_id", "yuandian_case_type",
                        "yuandian_verified", "yuandian_verify_pending", "yuandian_miss_reason"}
            buckets["source_pending"].append(rel)
        else:
            # 择优：优先取「已实证命中」的案号作为主锚点
            primary = None
            for a in ahs:
                if a in hit:
                    primary = a
                    break
            if primary is None:
                for a in ahs:
                    if a in hit_no_id:
                        primary = a
                        break
            if primary is None:
                primary = ahs[0]

            upserts["yuandian_ah"] = primary
            upserts["yuandian_checked"] = TODAY
            # 注：v1.2 移除 yuandian_ah_all 字段 —— 案号清单是正文派生数据，
            # 随时可由本脚本重新提取；写入后会与连接层并发进程互相改写（写-改-写循环）。
            deletes.add("yuandian_ah_all")
            deletes.add("yuandian_source_pending")

            if primary in hit:
                rec = hit[primary]
                upserts["yuandian_case_id"] = rec["id"]
                if rec.get("type"):
                    upserts["yuandian_case_type"] = rec["type"]
                upserts["yuandian_verified"] = True
                deletes |= {"yuandian_verify_pending", "yuandian_miss_reason"}
                buckets["verified_with_id"].append((rel, primary, rec["id"]))
            elif primary in hit_no_id:
                upserts["yuandian_verified"] = True
                deletes |= {"yuandian_verify_pending", "yuandian_miss_reason"}
                buckets["verified_no_id"].append((rel, primary))
            elif primary in miss:
                upserts["yuandian_verified"] = False
                upserts["yuandian_miss_reason"] = "华宇元典库内未收录该案号"
                deletes |= {"yuandian_verify_pending", "yuandian_case_id", "yuandian_case_type"}
                buckets["miss_confirmed"].append((rel, primary))
            else:
                upserts["yuandian_verify_pending"] = True
                deletes |= {"yuandian_verified", "yuandian_miss_reason"}
                buckets["verify_pending"].append((rel, primary))

            # 副锚点也登记进待实证队列（主锚点已命中不代表副锚点命中）
            for a in ahs:
                if a not in hit and a not in hit_no_id and a not in miss:
                    pending_ahs.add(a)

        new_lines, changed = fm_apply(fm_lines, upserts, deletes)
        if changed:
            plan.append((path, rebuild(new_lines, body)))
            changed_files.append(rel)

    # ---- 汇总 ----
    print("\n===== 回填计划 =====")
    print("已实证命中(含 id)  : %d 张" % len(buckets["verified_with_id"]))
    print("已实证命中(无 id)  : %d 张" % len(buckets["verified_no_id"]))
    print("实证未收录         : %d 张" % len(buckets["miss_confirmed"]))
    print("有案号待实证       : %d 张" % len(buckets["verify_pending"]))
    print("无锚点·诚实挂起    : %d 张" % len(buckets["source_pending"]))
    print("无 frontmatter 跳过: %d 张" % len(buckets["no_fm_skipped"]))
    print("需改写文件         : %d 张" % len(changed_files))

    anchored = (len(buckets["verified_with_id"]) + len(buckets["verified_no_id"])
                + len(buckets["miss_confirmed"]) + len(buckets["verify_pending"]))
    print("可在线对账覆盖率   : %d/%d = %.1f%%" % (anchored, total_before, anchored * 100.0 / max(total_before, 1)))

    if not args.apply:
        print("\n[DRY-RUN] 未写盘。加 --apply 执行。")
    else:
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        bak = CARDS_DIR + ".bak-yuandian-" + stamp
        shutil.copytree(CARDS_DIR, bak)
        n_bak = sum(len(fn) for _dp, _dn, fn in os.walk(bak))
        n_src = sum(len(fn) for _dp, _dn, fn in os.walk(CARDS_DIR))
        assert n_bak == n_src, "备份文件数不一致 %d != %d，中止" % (n_bak, n_src)
        print("\n[备份] %s （%d 文件）" % (bak, n_bak))
        # 快照保留上限：清理超出 keep 份的旧副本，杜绝反复 --apply 产生指数级冗余
        _removed, _kept = prune_snapshots(CARDS_DIR, args.keep_snapshots)
        if _removed:
            print("[快照治理] 已清理 %d 份旧副本，保留最近 %d 份" % (len(_removed), len(_kept)))

        for path, new_text in plan:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_text)
        after = sum(1 for _dp, _dn, fn in os.walk(CARDS_DIR) for f in fn if f.endswith(".md"))
        assert after == total_before, "写后 md 文件数漂移 %d != %d" % (after, total_before)
        print("[写盘] %d 张已更新；md 文件数断言通过 (%d)" % (len(plan), after))
        print("[回滚] rm -rf '%s' && mv '%s' '%s'" % (CARDS_DIR, bak, CARDS_DIR))

    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write("# 裁判规则库·华宇元典标识符回填明细\n\n")
            f.write("- 生成时间：%s\n- 卡片总数：%d\n- 可在线对账：%d (%.1f%%)\n\n"
                    % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                       total_before, anchored, anchored * 100.0 / max(total_before, 1)))
            f.write("## 一、已实证命中（写入 ah + hash id）%d 张\n\n" % len(buckets["verified_with_id"]))
            f.write("| 卡片 | 案号 | yuandian id |\n|---|---|---|\n")
            for rel, a, i in buckets["verified_with_id"]:
                f.write("| %s | %s | `%s` |\n" % (rel, a, i))
            f.write("\n## 二、已实证命中但 id 未提取 %d 张\n\n" % len(buckets["verified_no_id"]))
            for rel, a in buckets["verified_no_id"]:
                f.write("- %s ← %s\n" % (rel, a))
            f.write("\n## 三、实证未收录 %d 张\n\n" % len(buckets["miss_confirmed"]))
            for rel, a in buckets["miss_confirmed"]:
                f.write("- %s ← %s\n" % (rel, a))
            f.write("\n## 四、有案号锚点·待后续实证 %d 张\n\n" % len(buckets["verify_pending"]))
            f.write("| 卡片 | 案号 |\n|---|---|\n")
            for rel, a in buckets["verify_pending"]:
                f.write("| %s | %s |\n" % (rel, a))
            f.write("\n## 五、无案号锚点·诚实挂起 %d 张\n\n" % len(buckets["source_pending"]))
            f.write("（`yuandian_source_pending: true`，此类卡源自公众号文章/学习笔记/法条解读，"
                    "本身不对应特定裁判文书，无法也不应伪造案号。）\n")
        print("[报告] %s" % args.report)

    # 供后续自动化消费的待实证队列
    q = {
        "generated": TODAY,
        "verify_queue": sorted(pending_ahs),
        "note": "月度对账自动化按批消费；查询时**不得传 type 参数**（会排除普通案例库造成假阴性）。",
    }
    qp = os.path.join(ROOT, "知识飞轮系统/03-连接/yuandian_verify_queue.json")
    if args.apply:
        with open(qp, "w", encoding="utf-8") as f:
            json.dump(q, f, ensure_ascii=False, indent=1)
        print("[队列] %s （%d 个案号待实证）" % (qp, len(q["verify_queue"])))
    else:
        print("[队列-预览] %d 个案号待实证" % len(q["verify_queue"]))


if __name__ == "__main__":
    main()
