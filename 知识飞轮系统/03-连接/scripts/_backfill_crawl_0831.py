# -*- coding: utf-8 -*-
"""
08-31 回补候选挖掘（HTTP 通道版）
====================================
ima-mcp 工具不在索引（运行态掉线），但 ima-skill HTTP 通道可用（get_knowledge_list）。
本脚本用 HTTP 通道执行 SELECT_3 的 S1（深度翻页）+ S1.5（文件夹递归），
收集各库未摄入候选（media_id / title / 所在文件夹），输出 JSON 供 MCP 恢复后直接消费。

⚠️ 本脚本只做候选挖掘，不取全文、不写 ingested（铁律：取全文失败绝不写 ingested）。
"""
import json, os, sys, urllib.request, datetime

CLIENT_ID = "4e714454151758d08fe77b2e1a803bf2"
API_KEY = open(os.path.expanduser("~/.config/ima/api_key")).read().strip()
STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                     "ima_intake_state.json")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_backfill_cands_0831.json")

# 5 库：name -> (kb_id, lib_id)
LIBS = {
    "合同文书AI助手": ("-_p-ebq3u6R4sDt55-YQ44ugE0L7ldEVf97CEG3sm5s=", "7312048136419112"),
    "律师AI助手": ("1VeYAfEj-dCCoiSqt_1LiV8gqZombqooW77lf6qNX0o=", "7312042960642489"),
    "人伤法律实务助手": ("BAUC45G8kIHCQQet20EjKSKRHi1cjkqjBd2gMX5SElQ=", "7312035322822509"),
    "合规与政府监管AI助手": ("bXnaVyCrvo7BsJmQws1dBENxN-1vERY1dRnU9wzZcKA=", "7333014572917409"),
    "慈善组织合规AI 助手": ("Onlli0sBtIHvlG8Hw3vkgApbRBNhE0VDtki2goUxUac=", "7311644304633438"),
}
PREFIX = "wechatarticle_62fe55a7567bc291dfbbee29900b27c3_"

def ima_api(path, body, timeout=30, retries=3):
    import time
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
                time.sleep(2 * (attempt + 1))
                continue
            raise
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable")

def list_page(kb_id, folder_id=None, cursor=""):
    import time
    body = {"knowledge_base_id": kb_id, "cursor": cursor, "limit": 20}
    if folder_id:
        body["folder_id"] = folder_id
    r = ima_api("openapi/wiki/v1/get_knowledge_list", body)
    time.sleep(0.8)  # 节流：防 403 风控
    if r.get("code") != 0:
        return None, r.get("msg")
    d = r.get("data", {})
    return d, None

def crawl_lib(name, kb_id, lib_id, ingested_set, max_items=400, max_depth=2):
    cands = []
    seen_folders = set()
    stats = {"pages": 0, "folders": 0, "articles_seen": 0, "errors": 0}

    def walk(folder_id, depth):
        if depth > max_depth:
            return
        cursor = ""
        while True:
            d, err = list_page(kb_id, folder_id, cursor)
            if d is None:
                stats["errors"] += 1
                break
            stats["pages"] += 1
            kl = d.get("knowledge_list", [])
            if not kl:
                break
            for it in kl:
                mt = it.get("media_type")
                mid = it.get("media_id", "")
                title = it.get("title", "")
                if mt == 99:  # 文件夹
                    if mid not in seen_folders and mid.startswith("folder_"):
                        seen_folders.add(mid)
                        stats["folders"] += 1
                        walk(mid, depth + 1)
                else:  # 文章/文件
                    stats["articles_seen"] += 1
                    # 构造标准 media_id 比对（prefix_rawid_kbid）
                    rawid = mid[len(PREFIX):] if mid.startswith(PREFIX) else mid
                    std_mid = PREFIX + rawid + lib_id
                    if std_mid not in ingested_set and len(cands) < max_items:
                        cands.append({
                            "lib": name, "lib_id": lib_id,
                            "rawid": rawid[:32], "title": title,
                            "media_id_raw": mid, "folder": folder_id or "root",
                        })
            if d.get("is_end"):
                break
            cursor = d.get("next_cursor", "")
            if not cursor:
                break
            if stats["pages"] > 25:
                break

    walk(None, 0)
    return cands, stats

def main():
    d = json.load(open(STATE, encoding="utf-8"))
    ingested_set = set()
    for lid, info in d["libraries"].items():
        for x in info.get("ingested", []):
            mid = x.get("media_id", "") if isinstance(x, dict) else str(x)
            ingested_set.add(mid)
    print("ingested_total:", d["totals"]["ingested_total"], "| unique mids:", len(ingested_set))

    all_cands = {}
    summary = {}
    for name, (kb_id, lib_id) in LIBS.items():
        cands, stats = crawl_lib(name, kb_id, lib_id, ingested_set)
        all_cands[name] = cands
        summary[name] = {**stats, "cands_found": len(cands)}
        print("[%s] pages=%d folders=%d seen=%d cands=%d err=%d" %
              (name, stats["pages"], stats["folders"], stats["articles_seen"],
               len(cands), stats["errors"]))

    payload = {
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M"),
        "note": "HTTP 通道候选挖掘（S1+S1.5）。仅供 MCP 恢复后回补消费；本清单未取全文、未写 ingested。",
        "summary": summary,
        "candidates": all_cands,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print("SAVED:", OUT)

if __name__ == "__main__":
    main()
