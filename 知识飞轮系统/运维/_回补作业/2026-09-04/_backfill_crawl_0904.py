# -*- coding: utf-8 -*-
"""
09-02 / 09-03 / 09-04 三窗合并回补 · 候选挖掘（HTTP 通道版）
================================================================
背景：3 个 open 漏窗共 45 篇（合同9/律师9/人伤9/合规9/慈善9）。
      ima-mcp 已于 2026-09-04 12:52 恢复（对照组 fetch 成功），具备回补条件。

本脚本只做候选挖掘：
  ✅ S1 深度翻页 + S1.5 文件夹递归
  ✅ 三重去重（media_id / title 对 ingested / title 对候选内部）
  ⛔ 排除 16 个 persistent_220030 内容侧损坏文件（对照组实证）
  ⛔ 不取全文、不写 ingested（铁律）

用法：python3 _backfill_crawl_0904.py [--max-items 60]
产出：_backfill_cands_0904.json
"""
import json, os, sys, time, datetime, urllib.request, urllib.error

CLIENT_ID = open(os.path.expanduser("~/.config/ima/client_id")).read().strip()
API_KEY = open(os.path.expanduser("~/.config/ima/api_key")).read().strip()
BASE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(os.path.dirname(os.path.dirname(BASE)), "ima_intake_state.json")
OUT = os.path.join(BASE, "_backfill_cands_0904.json")

LIBS = {
    "合同文书AI助手":     ("-_p-ebq3u6R4sDt55-YQ44ugE0L7ldEVf97CEG3sm5s=", "7312048136419112"),
    "律师AI助手":         ("1VeYAfEj-dCCoiSqt_1LiV8gqZombqooW77lf6qNX0o=", "7312042960642489"),
    "人伤法律实务助手":   ("BAUC45G8kIHCQQet20EjKSKRHi1cjkqjBd2gMX5SElQ=", "7312035322822509"),
    "合规与政府监管AI助手": ("bXnaVyCrvo7BsJmQws1dBENxN-1vERY1dRnU9wzZcKA=", "7333014572917409"),
    "慈善组织合规AI助手": ("Onlli0sBtIHvlG8Hw3vkgApbRBNhE0VDtki2goUxUac=", "7311644304633438"),
}
PREFIX = "wechatarticle_62fe55a7567bc291dfbbee29900b27c3_"


def ima_api(path, body, timeout=30, retries=3):
    for attempt in range(retries):
        req = urllib.request.Request(
            "https://ima.qq.com/" + path,
            data=json.dumps(body).encode("utf-8"),
            headers={"ima-openapi-clientid": CLIENT_ID, "ima-openapi-apikey": API_KEY,
                     "Content-Type": "application/json",
                     "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 403 and attempt < retries - 1:
                time.sleep(2 * (attempt + 1)); continue
            raise
        except Exception:
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1)); continue
            raise
    return {}


def norm(t):
    return "".join((t or "").split()).lower()


LIB_IDS = ("7312048136419112", "7312042960642489", "7312035322822509",
           "7333014572917409", "7311644304633438")


def raw32(mid):
    """抽取 32 位 rawid（兼容 wechatarticle_/markdown_/pdf_ 等前缀，且兼容是否已带库ID后缀）。"""
    r = mid
    for lid in LIB_IDS:
        if r.endswith(lid):
            r = r[: -len(lid)]
            break
    seg = r.rsplit("_", 1)[-1]
    return seg if len(seg) == 32 else r[-32:]


def main():
    max_items = 60
    if "--max-items" in sys.argv:
        max_items = int(sys.argv[sys.argv.index("--max-items") + 1])

    d = json.load(open(STATE, encoding="utf-8"))
    ingested_set, ingested_titles = set(), set()
    for lid, info in d["libraries"].items():
        for x in info.get("ingested", []):
            if isinstance(x, dict):
                mid = x.get("media_id", "")
                ingested_set.add(mid)
                if x.get("title"):
                    ingested_titles.add(norm(x["title"]))
            else:
                ingested_set.add(str(x))
    ingested_rawids = {raw32(m) for m in ingested_set}

    broken = set()
    for x in d.get("failed_220030", []):
        mid = x.get("media_id") if isinstance(x, dict) else x
        if mid:
            broken.add(mid)
    broken_raw = {raw32(m) for m in broken}

    print("ingested_total=%s | unique mids=%d | broken220030=%d"
          % (d["totals"]["ingested_total"], len(ingested_set), len(broken)))

    all_cands, summary = {}, {}
    seen_title_global = set()

    for name, (kb_id, lib_id) in LIBS.items():
        cands, seen_folders = [], set()
        stats = {"pages": 0, "folders": 0, "articles_seen": 0, "errors": 0,
                 "dup_title": 0, "broken_skip": 0}

        def walk(folder_id, depth):
            if depth > 3:
                return
            cursor = ""
            for _ in range(30):
                body = {"knowledge_base_id": kb_id, "limit": 50, "cursor": cursor}
                if folder_id:
                    body["folder_id"] = folder_id
                try:
                    r = ima_api("openapi/wiki/v1/get_knowledge_list", body)
                except Exception as e:
                    stats["errors"] += 1
                    print("  !! %s err %s" % (name, str(e)[:80]))
                    return
                if r.get("errcode") not in (0, None):
                    stats["errors"] += 1
                    return
                stats["pages"] += 1
                kl = (r.get("data") or r).get("knowledge_list", []) or []
                if not kl:
                    break
                for it in kl:
                    mt = it.get("media_type")
                    mid = it.get("media_id", "")
                    title = (it.get("title") or "").strip()
                    if mt == 99:
                        if mid.startswith("folder_") and mid not in seen_folders:
                            seen_folders.add(mid)
                            stats["folders"] += 1
                            walk(mid, depth + 1)
                        continue
                    stats["articles_seen"] += 1
                    # 🔧 2026-09-04 修复：HTTP 通道返回的 media_id 已带库ID后缀，
                    #    旧逻辑无条件再拼一次 → std_mid 变成 rawid+lib_id+lib_id，
                    #    与 ingested 集合永远匹配不上 → 去重全面失效（5 库全顶格 60）。
                    std_mid = mid if mid.endswith(lib_id) else mid + lib_id
                    if std_mid in broken or mid in broken:
                        stats["broken_skip"] += 1
                        continue
                    if std_mid in ingested_set or mid in ingested_set:
                        stats["dup_mid"] = stats.get("dup_mid", 0) + 1
                        continue
                    # 第三重：rawid 级去重（治 media_id 构造差异导致的假阴性）
                    _raw32 = raw32(std_mid)
                    if _raw32 in ingested_rawids or _raw32 in broken_raw:
                        stats["dup_rawid"] = stats.get("dup_rawid", 0) + 1
                        continue
                    nt = norm(title)
                    if nt and (nt in ingested_titles or nt in seen_title_global):
                        stats["dup_title"] += 1
                        continue
                    if len(cands) >= max_items:
                        return
                    seen_title_global.add(nt)
                    cands.append({
                        "lib": name, "lib_id": lib_id,
                        "media_id": std_mid,
                        "title": title,
                        "file_size": it.get("file_size", ""),
                        "create_time": it.get("create_time", ""),
                        "folder": folder_id or "root",
                        "parse_progress": it.get("parse_progress"),
                        "can_fetch_content": it.get("can_fetch_content"),
                    })
                if r.get("is_end") or (r.get("data") or {}).get("is_end"):
                    break
                cursor = (r.get("data") or r).get("next_cursor", "")
                if not cursor:
                    break

        walk(None, 0)
        all_cands[name] = cands
        summary[name] = {**stats, "cands_found": len(cands)}
        print("[%-12s] pages=%-3d folders=%-3d seen=%-4d cands=%-3d 跳过:已摄入(mid)=%d 已摄入(rawid)=%d 已摄入(重名)=%d 220030=%d err=%d"
              % (name, stats["pages"], stats["folders"], stats["articles_seen"],
                 len(cands), stats.get("dup_mid", 0), stats.get("dup_rawid", 0),
                 stats["dup_title"], stats["broken_skip"], stats["errors"]))

    payload = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "purpose": "09-02/03/04 三窗合并回补（45 篇）候选池",
        "safety": "未取全文、未写 ingested（铁律）；已排除 16 个 persistent_220030 内容侧损坏文件",
        "summary": summary,
        "candidates": all_cands,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print("SAVED:", OUT)
    print("TOTAL CANDS:", sum(len(v) for v in all_cands.values()))


if __name__ == "__main__":
    main()
