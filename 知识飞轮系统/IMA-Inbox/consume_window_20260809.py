# -*- coding: utf-8 -*-
"""消费 w_2026-08-08 漏窗：将 14 篇 2026-08-09 已落盘笔记登记为 ingested，
并将窗口从 pending_windows 移入 consumed_windows。幂等可复跑。"""
import json, os, shutil, datetime

PATH = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/ima_intake_state.json"
BACKUP = PATH + ".bak-20260809-" + datetime.datetime.now().strftime("%H%M%S")

with open(PATH, "r", encoding="utf-8") as f:
    st = json.load(f)

shutil.copy2(PATH, BACKUP)
print("backup ->", BACKUP)

PREFIX = "wechatarticle_62fe55a7567bc291dfbbee29900b27c3_"
# media_id 后缀 -> (library_kb_id, title, value)
NOTES = {
    "0858a0ced31dc6bbc0ca9d36e82c8cf4": ("7312048136419112", "民事纠纷私了和解协议书（标准文本）— 蒸馏笔记", 8),
    "640206c116d4ca6232e27fe0698aaca7": ("7312048136419112", "交通事故赔偿协议书（范本与审查要点）— 蒸馏笔记", 8),
    "361a7224f9b79ee17f190a54c758e587": ("7312048136419112", "家庭财产分家协议（范本与审查要点）— 蒸馏笔记", 8),
    "7aa8216df4df85c1cf353903dff5b96e": ("7312048136419112", "贵州高院〈商品房买卖合同纠纷案件审判要件指南〉（2025）", 9),
    "ec1dd3a3c761148a35f9774205e3364d": ("7312042960642489", "虚假诉讼审查与移送公安机关（裁判规则）— 蒸馏笔记", 9),
    "9ed8477d30bc7c7cf875255eb4ef5289": ("7312042960642489", "申请再审材料清单（实务指引）— 蒸馏笔记", 9),
    "4d15e3465c9f0c5f2d3ff70a4a0a29ae": ("7312042960642489", "新生儿缺血缺氧性脑病医疗损害鉴定案（司法部入库案例）— 蒸馏笔记", 9),
    "36dbe9718102f9f28932803da6686124": ("7312035322822509", "医疗事故罪44宗画像（72份文书统计）— 蒸馏笔记", 9),
    "abfaa2b6e846514a6219b43831ebf86b": ("7312035322822509", "医疗事故罪入罪红线（韩杰案）— 蒸馏笔记", 9),
    "ae8a8692c9078a3e2820421e9ba5821d": ("7312035322822509", "医患纠纷高发真相（非医术因素）— 蒸馏笔记", 6),
    "d98a4a256fb3be221d53cebf16201da0": ("7312035322822509", "医疗损害诉讼时效起算（(2022)粤民再152号）— 蒸馏笔记", 9),
    "0b2c58e204edd8fc44168f50cdcb0a13": ("7312035322822509", "道交和解后起诉医院（侵权竞合）— 蒸馏笔记", 9),
    "77cbe7b680b1ee890602aeeb44b6b193": ("7333014572917409", "律师办理企业合规体系建设业务操作指引（2026）（试行）", 9),
    "57e9fffcd4d501624a20a5af094fea08": ("7311644304633438", "谁捐的要讲清楚（捐赠署名权与公益纯粹性）— 蒸馏笔记", 8),
}

INGESTED_AT = "2026-08-09T18:30"
WINDOW = "2026-08-08"

added = []
lib_counts = {}
for suffix, (kb, title, val) in NOTES.items():
    mid = PREFIX + suffix + kb
    # 去重校验
    existing = [x for x in st["libraries"][kb]["ingested"] if x.get("media_id") == mid]
    if existing:
        print("SKIP dup:", mid)
        continue
    entry = {
        "media_id": mid,
        "title": title,
        "create_time": 1786262400000,  # 2026-08-08 约值
        "ingested_at": INGESTED_AT,
        "value": val,
        "source": "ima_true",
        "ima_source_pending": False,
        "window": WINDOW,
        "occupies_new_quota": False,
        "create_time_approx": True,
    }
    st["libraries"][kb]["ingested"].append(entry)
    added.append(mid)
    lib_counts[kb] = lib_counts.get(kb, 0) + 1
    print("ADD", kb, title)

print("\nAdded per library:", lib_counts, "total", len(added))

# 移动窗口
pw = st.get("pending_windows", [])
target = None
for i, w in enumerate(pw):
    if w.get("window_id") == "w_2026-08-08":
        target = pw.pop(i)
        break
if target is None:
    print("WARN: w_2026-08-08 not found in pending_windows")
else:
    target["a1_done"] = lib_counts.get("7312048136419112", 0)
    target["b_done"] = sum(lib_counts.get(k, 0) for k in ["7312042960642489", "7312035322822509", "7333014572917409", "7311644304633438"])
    for k, meta in target.get("libraries", {}).items():
        meta["done"] = lib_counts.get(k, 0)
    target["consumed_at"] = INGESTED_AT
    target["consumed_by"] = "automation-1783920420205 v1.13 续跑（2026-08-09 回补 w_2026-08-08）"
    target["fault_resolution"] = "2026-08-09 续跑会话中 ima-mcp 已挂载，14 篇全部此前已 fetch 落盘（media_id 32位rawid+kb_id 构造），本次仅补登状态文件。"
    target["note"] = "实际分布：合同4/律师3/人伤5/合规1/慈善1=14（含1篇前序 carryover：贵州高院商品房指南）；合规、慈善各仅1篇因当日该库仅此新增。"
    target["status"] = "consumed_full"
    st.setdefault("consumed_windows", []).append(target)
    print("MOVED w_2026-08-08 -> consumed_windows")

# 状态与总计
st["ima_status"] = "runtime_healthy_consumed_2026-08-09"
st["updated"] = INGESTED_AT
st["last_run_ts_ms"] = 1786262400000

tot = st.setdefault("totals", {})
a1_add = lib_counts.get("7312048136419112", 0)
b_add = sum(lib_counts.get(k, 0) for k in ["7312042960642489", "7312035322822509", "7333014572917409", "7311644304633438"])
tot["A1_done"] = tot.get("A1_done", 0) + a1_add
tot["A1_target"] = max(tot.get("A1_target", 9), tot["A1_done"])
tot["B_done"] = tot.get("B_done", 0) + b_add
tot["B_target"] = max(tot.get("B_target", 36), tot["B_done"])
tot["last_run"] = INGESTED_AT
tot["window_consumed"] = WINDOW
tot["all_pending"] = len(st.get("pending_windows", [])) == 0

st.setdefault("resolved_in_continuation", {})
st["resolved_in_continuation"]["window_consumed_2026-08-08"] = (
    "A1 合同库4篇（私了/交通事故/分家/贵州高院指南）+ B 律师3（虚假诉讼/再审/新生儿鉴定）+ 人伤5（医疗事故罪44宗/韩杰案/医患真相/时效起算/道交和解诉医）+ 合规1（合规体系建设指引2026）+ 慈善1（谁捐的要讲清楚）= 14篇；全部 IMA 真源（source=ima_true），occupies_new_quota=false。不占新配额，为 08-08 配置态故障漏窗回补。"
)

with open(PATH, "w", encoding="utf-8") as f:
    json.dump(st, f, ensure_ascii=False, indent=2)
print("\nDONE. totals:", tot)
print("pending_windows left:", [w.get("window_id") for w in st.get("pending_windows", [])])
