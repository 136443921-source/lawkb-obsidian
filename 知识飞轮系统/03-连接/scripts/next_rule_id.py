#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
next_rule_id.py —— LawKB 裁判规则卡 **取号器（单一真源）**

> 建立原因（2026-09-11）：取号原为「提示词口头规则」（各 automation / SKILL 里各写一遍
> `find . -name "R-<域>-*.md" | sort | tail`），存在三个致命漏洞：
>   ① 只扫**文件名**，而规范规定「文件名仅为别名，唯一标识以 frontmatter `rule_id` 为准」
>      → 治理过的卡（文件名与 rule_id 不一致）会让 max 算错；
>   ② 取号到落盘之间有**时间窗口**，并发流水线（拆卡 / 摄入 / 回灌）会互撞，
>      实证：2026-09-11 12:27 摄入自动化建的 R-HT-249/250/251 撞上 09-10 证据规则目录同号旧卡；
>   ③ 规则分散在多个 prompt 里，改一处漏一处。
> → 解法：**取号唯一入口化 + 预留登记（reserve）**，把口头规则固化为代码。

## 用法

    # 1) 查看各域基线（只读，最常用作体检）
    python3 next_rule_id.py --list

    # 2) 取 1 个号（预览，不写预留）
    python3 next_rule_id.py --domain HT --peek

    # 3) 正式取号（写入预留，防并发）—— 一次取满，禁止逐个取
    python3 next_rule_id.py --domain HT --n 15
    # 输出：R-HT-254 ~ R-HT-268（已预留，落盘后请 --commit）

    # 4) 落盘完成后提交（清除预留）
    python3 next_rule_id.py --commit R-HT-254 R-HT-255 ...
    # 或全部提交
    python3 next_rule_id.py --commit-all

    # 5) 放弃预留（建卡失败/改计划）
    python3 next_rule_id.py --release R-HT-254

    # 6) 查看当前预留
    python3 next_rule_id.py --reservations

## 铁律

1. **禁止绕过本脚本手工取号**（`find`/`sort`/凭记忆 一律判流程缺陷）。
2. **一次取满**：批量建卡前一次性取足数量，不要建一张取一张（并发窗口最小化）。
3. **落盘即 commit**：卡片写完必须 `--commit`，否则号段被永久占用。
4. **口径**：只看 frontmatter `rule_id`，不看文件名。
5. **预留有效期 24 小时**，超时自动释放，防止建卡中断导致号段泄漏。
"""

import os
import re
import sys
import json
import argparse
from datetime import datetime, timedelta
from collections import defaultdict

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库"
RESERVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_rule_id_reservations.json")
RESERVE_TTL_HOURS = 24

# 白名单**动态解析**规范第二节（2026-09-11 起），不再硬编码。
# 历史教训：原硬编码版本为 14 域且 `CS=建设工程 / JG=鉴定`（与规范 v1.2.0 已修正的
# 领域名互换错误一致），实测规范实为 21 域、`CS=案例 / JG=建设工程`。
# 现改为从规范实时解析，规范改版后脚本自动跟随。
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from rule_id_spec import load_spec
    _SPEC = load_spec()
except Exception as _e:                                    # pragma: no cover
    _SPEC = None
    print(f"⚠️ rule_id_spec 加载失败（{_e}），白名单校验降级为放行", file=sys.stderr)

WHITELIST = set(_SPEC.domains) if _SPEC else set()
DOMAIN_NAMES = dict(_SPEC.domains) if _SPEC else {}

RULE_ID_RE = re.compile(r'^rule_id:\s*"?\s*(R-([A-Z]{2})-(\d{3}))', re.M)


def scan_library():
    """扫描全库，返回 {域: set(序号int)} 与 {域: [(path, rule_id)]}。以 frontmatter rule_id 为准。"""
    nums = defaultdict(set)
    detail = defaultdict(list)
    if not os.path.isdir(ROOT):
        print(f"❌ 库目录不存在：{ROOT}", file=sys.stderr)
        sys.exit(1)
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if not d.startswith(".") and d != "_备份"]
        for f in fn:
            if not f.endswith(".md"):
                continue
            p = os.path.join(dp, f)
            try:
                s = open(p, encoding="utf-8", errors="ignore").read(15000)
            except Exception:
                continue
            m = RULE_ID_RE.search(s)
            if m:
                rid, dom, num = m.group(1), m.group(2), int(m.group(3))
                nums[dom].add(num)
                detail[dom].append((os.path.relpath(p, ROOT), rid))
    return nums, detail


def load_reservations():
    """读取预留，并清理超过 TTL 的过期项。"""
    if not os.path.exists(RESERVE_FILE):
        return {"updated": None, "items": []}
    try:
        data = json.load(open(RESERVE_FILE, encoding="utf-8"))
    except Exception:
        return {"updated": None, "items": []}
    now = datetime.now()
    alive = []
    for it in data.get("items", []):
        try:
            ts = datetime.fromisoformat(it["ts"])
        except Exception:
            continue
        if now - ts < timedelta(hours=RESERVE_TTL_HOURS):
            alive.append(it)
    if len(alive) != len(data.get("items", [])):
        save_reservations({"updated": now.isoformat(timespec="seconds"), "items": alive})
    return {"updated": data.get("updated"), "items": alive}


def save_reservations(data):
    data["updated"] = datetime.now().isoformat(timespec="seconds")
    with open(RESERVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def reserved_nums(dom, res=None):
    res = res or load_reservations()
    return {int(it["num"]) for it in res["items"]
            if it["domain"] == dom and it["num"].isdigit()}


def next_nums(dom, n, nums, res):
    """取域内下一个可用的 n 个连续号（跳过已用 + 已预留）。"""
    used = set(nums.get(dom, set())) | reserved_nums(dom, res)
    start = max(used) + 1 if used else 1
    out, cur = [], start
    while len(out) < n:
        if cur not in used:
            out.append(cur)
        cur += 1
        if cur > 999:
            raise SystemExit(f"❌ {dom} 域号段耗尽（>999），需扩位或开新域")
    return out


def cmd_list(args):
    nums, detail = scan_library()
    res = load_reservations()
    print(f"=== 各域 rule_id 基线（frontmatter 口径 · {datetime.now():%Y-%m-%d %H:%M}）===")
    print(f"{'域':<4}{'卡数':>6}{'唯一号':>7}{'冲突':>6}{'max':>6}{'下一可用':>9}   说明")
    print("-" * 78)
    total_conflict = 0
    for dom in sorted(nums, key=lambda d: -len(detail[d])):
        cards = len(detail[dom])
        uniq = len(nums[dom])
        conflict = cards - uniq
        total_conflict += conflict
        mx = max(nums[dom])
        nxt = next_nums(dom, 1, nums, res)[0]
        mark = "" if dom in WHITELIST else f"  ⚠️不在14域白名单"
        flag = f"  🔴撞号{conflict}组" if conflict > 0 else ""
        print(f"{dom:<4}{cards:>6}{uniq:>7}{conflict:>6}{mx:>6}{nxt:>9}{mark}{flag}")
    print("-" * 78)
    print(f"合计：{sum(len(v) for v in detail.values())} 张卡 / {len(nums)} 个域 / 同号冲突 {total_conflict} 组")
    off = [d for d in nums if d not in WHITELIST]
    if off:
        print(f"⚠️ 白名单外域码：{', '.join(sorted(off))}（共 {sum(len(detail[d]) for d in off)} 张卡）")
    if res["items"]:
        print(f"📌 当前预留 {len(res['items'])} 个号（--reservations 查看）")


def cmd_get(args):
    dom = args.domain.upper()
    if WHITELIST and dom not in WHITELIST and not args.allow_offlist:
        print(f"❌ 域码 {dom} 不在 {len(WHITELIST)} 域白名单（{', '.join(sorted(WHITELIST))}）。",
              file=sys.stderr)
        print(f"   若确需新域，请先在《_规则卡编号体系规范.md》第二节登记，再加 --allow-offlist。",
              file=sys.stderr)
        sys.exit(2)
    nums, detail = scan_library()
    res = load_reservations()
    got = next_nums(dom, args.n, nums, res)
    ids = [f"R-{dom}-{i:03d}" for i in got]
    if args.peek:
        print(f"🔍 预览（未预留）：{ids[0]}" + (f" ~ {ids[-1]}（共 {len(ids)} 个）" if len(ids) > 1 else ""))
        return
    for i in got:
        res["items"].append({
            "domain": dom, "num": f"{i:03d}",
            "ts": datetime.now().isoformat(timespec="seconds"),
            "note": args.note or "",
        })
    save_reservations(res)
    print(f"✅ 已取号并预留 {len(ids)} 个：")
    print(f"   {ids[0]}" + (f" ~ {ids[-1]}" if len(ids) > 1 else ""))
    for i in ids[:20]:
        print(f"     {i}")
    if len(ids) > 20:
        print(f"     …（共 {len(ids)} 个）")
    print(f"\n⚠️ 落盘后务必执行：python3 {os.path.basename(__file__)} --commit-all")
    print(f"   （预留 {RESERVE_TTL_HOURS} 小时后自动释放，建卡中断不会永久占号）")


def cmd_commit(args):
    res = load_reservations()
    if args.commit_all:
        n = len(res["items"])
        save_reservations({"updated": None, "items": []})
        print(f"✅ 已提交全部预留 {n} 个，预留表清空。")
        return
    targets = set()
    for t in args.ids:
        m = re.match(r'^R-([A-Z]{2})-(\d{3})$', t.upper())
        if m:
            targets.add((m.group(1), m.group(2)))
        else:
            print(f"⚠️ 忽略非法 rule_id：{t}")
    kept = [it for it in res["items"] if (it["domain"], it["num"]) not in targets]
    removed = len(res["items"]) - len(kept)
    save_reservations({"updated": None, "items": kept})
    print(f"✅ 已提交 {removed} 个；剩余预留 {len(kept)} 个。")


def cmd_reservations(args):
    res = load_reservations()
    if not res["items"]:
        print("📭 当前无预留号段。")
        return
    print(f"=== 预留号段（{len(res['items'])} 个 · TTL {RESERVE_TTL_HOURS}h）===")
    for it in res["items"]:
        print(f"  R-{it['domain']}-{it['num']}   {it['ts']}   {it.get('note','')}")


def main():
    ap = argparse.ArgumentParser(description="LawKB 裁判规则卡取号器（单一真源）")
    ap.add_argument("--list", action="store_true", help="列出各域基线（只读体检）")
    ap.add_argument("--domain", "-d", help="域码，如 HT / PI / CF")
    ap.add_argument("--n", type=int, default=1, help="取号数量（批量建卡一次取满，默认 1）")
    ap.add_argument("--peek", action="store_true", help="仅预览下一可用号，不写预留")
    ap.add_argument("--note", help="预留备注（如批次名）")
    ap.add_argument("--commit", nargs="*", dest="ids", help="提交指定 rule_id，清除预留")
    ap.add_argument("--commit-all", action="store_true", help="提交全部预留")
    ap.add_argument("--release", help="放弃指定 rule_id 的预留")
    ap.add_argument("--reservations", action="store_true", help="查看当前预留")
    ap.add_argument("--allow-offlist", action="store_true",
                    help="允许使用白名单外的域码（白名单动态解析自规范第二节）")
    args = ap.parse_args()

    if args.list:
        cmd_list(args)
    elif args.domain:
        cmd_get(args)
    elif args.commit_all or args.ids is not None:
        cmd_commit(args)
    elif args.release:
        m = re.match(r'^R-([A-Z]{2})-(\d{3})$', args.release.upper())
        if not m:
            print("❌ 格式应为 R-XX-NNN"); sys.exit(2)
        args.ids = [args.release]
        cmd_commit(args)
    elif args.reservations:
        cmd_reservations(args)
    else:
        ap.print_help()
        print("\n💡 常用：--list 查基线 ｜ -d HT --n 15 批量取号 ｜ --commit-all 落盘后提交")


if __name__ == "__main__":
    main()
