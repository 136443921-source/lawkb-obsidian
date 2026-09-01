#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IMA 全量爬库器 v1.0（2026-08-30）
============================================================
用途：递归遍历 IMA 5 个知识库的**完整目录树**，产出逐篇可开采清单，
      并与 ima_intake_state.json 的已摄入集合比对，算出真实未开采量。

背景：每日摄入自动化（v1.17）只扫根目录、不展开文件夹，导致 95% 资料
      从未进入候选池（详见 _运维/IMA摄入量衰减诊断报告-2026-08-30.md）。

用法：
  python3 ima_library_crawler.py                # 全量爬 5 库
  python3 ima_library_crawler.py --libs 合同文书AI助手   # 只爬指定库（模糊匹配）
  python3 ima_library_crawler.py --dry-run      # 只探目录树，不拉文章明细（快）

产出（默认落 _运维/IMA爬库产出/）：
  ima_full_inventory.json   全量逐篇明细（media_id/title/路径/create_time/是否已摄入）
  ima_dir_tree.json         目录树结构（含每层篇数）
  IMA可开采清单-YYYY-MM-DD.md  人读清单报告

安全：凭证只在运行时从 ~/.config/ima/ 读取，不硬编码、不落日志、不打印。
"""
import json
import os
import re
import sys
import time
import argparse
from pathlib import Path
from collections import defaultdict
from urllib import request, error

# ---------------- 配置 ----------------
BASE = "https://ima.qq.com/openapi/wiki/v1"
LIST_EP = f"{BASE}/get_knowledge_list"
PAGE = 50                      # API 上限 50
SLEEP = 0.25                   # 限流间隔（秒）
MAX_RETRY = 3

VAULT = Path("/Users/chenyouqiang/Documents/LawKB")
FW = VAULT / "知识飞轮系统"
STATE_PATH = FW / "ima_intake_state.json"
OUT_DIR = FW / "_运维" / "IMA爬库产出"

LIBS = {
    "7312048136419112": "合同文书AI助手",
    "7312042960642489": "律师AI助手",
    "7312035322822509": "人伤法律实务助手",
    "7333014572917409": "合规与政府监管AI助手",
    "7311644304633438": "慈善组织合规AI助手",
}

# 文件夹类型（media_type=99 为文件夹，非可开采文章）
FOLDER_TYPE = 99
DATE = time.strftime("%Y-%m-%d")


def load_cred():
    """从 ~/.config/ima/ 或环境变量读取凭证（绝不打印）。"""
    cid = os.environ.get("IMA_OPENAPI_CLIENTID", "").strip()
    key = os.environ.get("IMA_OPENAPI_APIKEY", "").strip()
    if not cid:
        p = Path.home() / ".config/ima/client_id"
        if p.exists():
            cid = p.read_text().strip()
    if not key:
        p = Path.home() / ".config/ima/api_key"
        if p.exists():
            key = p.read_text().strip()
    if not cid or not key:
        print("❌ 缺少 IMA 凭证。请配置 ~/.config/ima/client_id 与 api_key，"
              "或设置环境变量 IMA_OPENAPI_CLIENTID / IMA_OPENAPI_APIKEY。", file=sys.stderr)
        sys.exit(2)
    return cid, key


def call_list(cid, key, kb_id, folder_id=None, cursor="", limit=PAGE):
    """调用 get_knowledge_list，带重试。返回 (items, is_end, next_cursor, current_path)。"""
    body = {"knowledge_base_id": kb_id, "limit": limit, "cursor": cursor}
    if folder_id:
        body["folder_id"] = folder_id
    data = json.dumps(body).encode("utf-8")
    req = request.Request(LIST_EP, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("ima-openapi-clientid", cid)
    req.add_header("ima-openapi-apikey", key)

    last_err = None
    for attempt in range(1, MAX_RETRY + 1):
        try:
            with request.urlopen(req, timeout=30) as resp:
                j = json.loads(resp.read().decode("utf-8"))
            return (j.get("knowledge_list") or [], j.get("is_end", True),
                    j.get("next_cursor", ""), j.get("current_path") or [])
        except Exception as e:                      # noqa: BLE001
            last_err = e
            if attempt < MAX_RETRY:
                time.sleep(SLEEP * attempt * 2)
    print(f"   ⚠️ 请求失败已重试{MAX_RETRY}次：{last_err}", file=sys.stderr)
    return ([], True, "", [])


def page_all(cid, key, kb_id, folder_id, stat):
    """翻页取尽某目录（或根目录）的全部条目。"""
    items, cursor, guard = [], "", 0
    while True:
        batch, is_end, nxt, path = call_list(cid, key, kb_id, folder_id, cursor)
        items.extend(batch)
        stat["calls"] += 1
        time.sleep(SLEEP)
        if is_end or not nxt or nxt == cursor:
            return items, path
        cursor = nxt
        guard += 1
        if guard > 300:                            # 防死循环
            print("   ⚠️ 翻页超过 300 次，强制中断", file=sys.stderr)
            return items, path


def load_ingested():
    """读取状态文件，返回 (set(完整media_id), set(rawid32))。"""
    full, raw32 = set(), set()
    if not STATE_PATH.exists():
        print(f"⚠️ 状态文件不存在：{STATE_PATH}", file=sys.stderr)
        return full, raw32
    try:
        st = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception as e:                          # noqa: BLE001
        print(f"⚠️ 状态文件解析失败：{e}", file=sys.stderr)
        return full, raw32
    libs = st.get("libraries") or {}
    for _lib, v in libs.items():
        if not isinstance(v, dict):
            continue
        for mid in (v.get("ingested") or []):
            if isinstance(mid, dict):
                mid = mid.get("media_id", "")
            if not isinstance(mid, str) or not mid:
                continue
            full.add(mid)
            seg = mid.split("_")[-1]
            if len(seg) == 32:
                raw32.add(seg)
    return full, raw32


def is_ingested(mid, full, raw32):
    if mid in full:
        return True
    seg = mid.split("_")[-1]
    return len(seg) == 32 and seg in raw32


def crawl_lib(cid, key, kb_id, name, ingested_full, ingested_raw, dry_run=False):
    """递归爬取单个库，返回 (文章列表, 目录树节点列表, 统计)。"""
    stat = {"calls": 0, "folders": 0, "articles": 0}
    articles, dir_nodes = [], []
    # (folder_id, folder_name, path_tuple)
    queue = [(None, name, (name,))]
    seen_dirs = set()

    while queue:
        fid, fname, path = queue.pop(0)
        key_seen = fid or "__ROOT__"
        if key_seen in seen_dirs:
            continue
        seen_dirs.add(key_seen)

        items, cur_path = page_all(cid, key, kb_id, fid, stat)
        subs, arts = [], []
        for it in items:
            mt = it.get("media_type")
            if mt == FOLDER_TYPE or it.get("folder_info"):
                fi = it.get("folder_info") or {}
                sub_id = fi.get("folder_id") or it.get("media_id")
                sub_name = fi.get("name") or it.get("title") or "?"
                subs.append((sub_id, sub_name,
                             int(fi.get("file_number") or 0),
                             int(fi.get("folder_number") or 0)))
            else:
                arts.append(it)

        stat["folders"] += len(subs)
        dir_nodes.append({
            "folder_id": fid, "name": fname, "path": "/".join(path),
            "article_count": len(arts), "subfolder_count": len(subs),
            "subfolders": [{"id": s[0], "name": s[1], "file_number": s[2]} for s in subs],
        })

        if not dry_run:
            for a in arts:
                mid = a.get("media_id", "")
                articles.append({
                    "media_id": mid,
                    "title": a.get("title", ""),
                    "media_type": a.get("media_type"),
                    "create_time": int(a.get("create_time") or 0),
                    "path": "/".join(path),
                    "can_fetch": bool(a.get("can_fetch_content")),
                    "ingested": is_ingested(mid, ingested_full, ingested_raw),
                })
        stat["articles"] += len(arts)

        for sub_id, sub_name, _fn, _sn in subs:
            queue.append((sub_id, sub_name, path + (sub_name,)))

        print(f"   📂 {fname:<28} 文章 {len(arts):>4}  子目录 {len(subs):>3}   (累计调用 {stat['calls']})")

    return articles, dir_nodes, stat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--libs", default="", help="只爬指定库（名称模糊匹配，逗号分隔）")
    ap.add_argument("--dry-run", action="store_true", help="只探目录树，不落文章明细")
    args = ap.parse_args()

    cid, key = load_cred()
    ingested_full, ingested_raw = load_ingested()
    print(f"已摄入集合：完整 media_id {len(ingested_full)} 条 / rawid32 {len(ingested_raw)} 条\n")

    targets = LIBS
    if args.libs:
        kws = [k.strip() for k in args.libs.split(",") if k.strip()]
        targets = {k: v for k, v in LIBS.items() if any(w in v for w in kws)}
        if not targets:
            print(f"❌ 未匹配到库：{args.libs}", file=sys.stderr)
            sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_articles, all_dirs, summary = [], {}, {}

    for kb_id, name in targets.items():
        print(f"\n=== 开始爬库：{name}（{kb_id}）===")
        arts, dirs, stat = crawl_lib(cid, key, kb_id, name,
                                     ingested_full, ingested_raw, args.dry_run)
        all_articles.extend(arts)
        all_dirs[kb_id] = {"name": name, "dirs": dirs}
        n_ing = sum(1 for a in arts if a["ingested"])
        summary[kb_id] = {
            "name": name, "articles": len(arts), "ingested": n_ing,
            "mineable": len(arts) - n_ing, "folders": stat["folders"],
            "api_calls": stat["calls"],
        }
        print(f"   ✅ {name}：文章 {len(arts)} / 已摄入 {n_ing} / "
              f"可开采 {len(arts) - n_ing} / 目录 {stat['folders']}")

    # ---------- 落盘 ----------
    stamp = time.strftime("%Y-%m-%d")
    inv_path = OUT_DIR / "ima_full_inventory.json"
    tree_path = OUT_DIR / "ima_dir_tree.json"
    inv_path.write_text(json.dumps({
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dry_run": args.dry_run,
        "summary": summary,
        "articles": all_articles,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    tree_path.write_text(json.dumps(all_dirs, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- Markdown 报告 ----------
    md = [f"# IMA 各库真实可开采清单（{stamp}）", "",
          "> 由 `03-连接/scripts/ima_library_crawler.py` 全量递归爬库产出。",
          "> 口径：仅统计真实文章（已排除 `media_type=99` 文件夹）；"
          "「已摄入」取自 `ima_intake_state.json`。", ""]
    md += ["## 一、总览", "",
           "| 库 | 文章总数 | 已摄入 | **可开采** | 开采率 | 目录数 | API调用 |",
           "|---|---:|---:|---:|---:|---:|---:|"]
    ta = ti = tm = 0
    for _k, s in summary.items():
        rate = s["ingested"] / s["articles"] * 100 if s["articles"] else 0
        md.append(f"| {s['name']} | {s['articles']} | {s['ingested']} | "
                  f"**{s['mineable']}** | {rate:.1f}% | {s['folders']} | {s['api_calls']} |")
        ta += s["articles"]; ti += s["ingested"]; tm += s["mineable"]
    rate = ti / ta * 100 if ta else 0
    md.append(f"| **合计** | **{ta}** | **{ti}** | **{tm}** | **{rate:.1f}%** | "
              f"{sum(s['folders'] for s in summary.values())} | "
              f"{sum(s['api_calls'] for s in summary.values())} |")

    md += ["", "## 二、各库目录级可开采量（TOP 目录）", ""]
    for kb_id, d in all_dirs.items():
        rows = sorted(d["dirs"], key=lambda x: -x["article_count"])
        md += [f"### {d['name']}", "",
               "| 目录路径 | 文章数 |", "|---|---:|"]
        for r in rows[:25]:
            md.append(f"| {r['path']} | {r['article_count']} |")
        if len(rows) > 25:
            md.append(f"| …（其余 {len(rows)-25} 个目录，详见 ima_dir_tree.json） | |")
        md.append("")

    if not args.dry_run:
        md += ["## 三、高价值未开采文章（按路径聚合，示例每库 15 篇）", ""]
        for kb_id, d in all_dirs.items():
            pool = [a for a in all_articles
                    if a["path"].startswith(d["name"]) and not a["ingested"]]
            md += [f"### {d['name']}（未开采 {len(pool)} 篇）", ""]
            for a in pool[:15]:
                md.append(f"- {a['title'][:60]}  \n  `{a['path']}`")
            if len(pool) > 15:
                md.append(f"- …… 其余 {len(pool)-15} 篇见 `ima_full_inventory.json`")
            md.append("")

    md_path = OUT_DIR / f"IMA可开采清单-{stamp}.md"
    md_path.write_text("\n".join(md), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"✅ 爬库完成：文章 {ta} / 已摄入 {ti} / 可开采 {tm}（开采率 {rate:.1f}%）")
    print(f"   明细 JSON：{inv_path}")
    print(f"   目录树 JSON：{tree_path}")
    print(f"   清单报告：{md_path}")


if __name__ == "__main__":
    main()
