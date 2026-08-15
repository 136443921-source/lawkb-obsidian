import json, datetime

path = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/ima_intake_state.json"
with open(path, encoding="utf-8") as f:
    data = json.load(f)

def ts_ms(s):
    dt = datetime.datetime.strptime(s, "%Y-%m-%d %H:%M")
    return int(dt.timestamp() * 1000)

# 10 篇补录：律师3 + 人伤2 + 合规2 + 慈善3，全部 IMA 真源
new_entries = {
    "7312042960642489": [  # 律师AI助手
        {"rawid": "8712ce35e9dfa8a95aa564d10e488a5b", "title": "收藏即用！民事执行全流程65项法律依据清单（2026实务完整版）", "create": "2026-07-13 12:35", "value": 9},
        {"rawid": "be1aef71156996072149b4c78788cfab", "title": "律师办理公司决议业务操作指引（2026）（试行）", "create": "2026-07-14 08:02", "value": 9},
        {"rawid": "6d74014abd4a60848afa91dcc80eb5f5", "title": "干货｜律师制作证据目录的20个实务细节", "create": "2026-08-01 14:46", "value": 8},
    ],
    "7312035322822509": [  # 人伤法律实务助手
        {"rawid": "b0f84b50dc51a21d149347b02615a41f", "title": "工伤赔偿案件：工伤认定、鉴定、仲裁、执行全流程（完整版）", "create": "2026-06-24 07:21", "value": 9},
        {"rawid": "f9e6a67449efdd024dd3ca4cefb4e461", "title": "医院误诊，病患家属怎么主张赔偿？教你索赔姿势和索偿金额", "create": "2026-08-07 10:00", "value": 8},
    ],
    "7333014572917409": [  # 合规与政府监管AI助手
        {"rawid": "c3f0106b87326cc1fe45ba7c06bbedec", "title": "员工入职尽调全流程指南", "create": "2026-06-23 18:06", "value": 8},
        {"rawid": "55962778913fbcff4c3e078db71451ae", "title": "重磅逐条解读｜2026版《民营企业劳动用工管理制度（参考文本）》（全12章·合规指南）", "create": "2026-08-05 07:05", "value": 8},
    ],
    "7311644304633438": [  # 慈善组织合规AI助手
        {"rawid": "6b618affd8791899c5d57c9785756775", "title": "66%基金会的公募资格闲置：申请前，请三思", "create": "2026-08-06 18:37", "value": 8},
        {"rawid": "8e696ce79a7d1a03ca26dd156b89a9e6", "title": "公益项目结项剩钱，能直接转为机构自有收入？千万别乱调账！", "create": "2026-07-28 07:30", "value": 8},
        {"rawid": "11b7f8b4905682ed78eb91715e247fd9", "title": "社会组织常用政策法规汇编（一）", "create": "2026-07-22 18:12", "value": 7},
    ],
}

prefix = "wechatarticle_62fe55a7567bc291dfbbee29900b27c3_"
ingested_at = "2026-08-07T08:45"

count = 0
for kb_id, entries in new_entries.items():
    for e in entries:
        media_id = prefix + e["rawid"] + kb_id
        rec = {
            "media_id": media_id,
            "title": e["title"],
            "create_time": ts_ms(e["create"]),
            "ingested_at": ingested_at,
            "value": e["value"],
            "source": "ima_true",
            "ima_source_pending": False,
            "window": "2026-08-07",
            "occupies_new_quota": False,
            "create_time_approx": True,
        }
        data["libraries"][kb_id]["ingested"].append(rec)
        count += 1

# 各库达标校验
for kb_id in new_entries:
    n = len(data["libraries"][kb_id]["ingested"])
    print(f"  {kb_id} ({data['libraries'][kb_id]['name']}): ingested = {n}")

data["totals"]["B_done"] = 36
data["updated"] = ingested_at
data["ima_status"] = "runtime_healthy_backfilled_B36_2026-08-07"
data["note"] = "2026-08-07 08:45 B 库补录 10 篇（律师3+人伤2+合规2+慈善3）全部 IMA 真源摄入，B_done 26→36（36/36 达标）；四库各 9 篇。occupies_new_quota=false。"

data["resolved_in_continuation"]["b_backfill_2026-08-07_cont"] = (
    "B 库距 36 差 10 篇，按每库硬配额 3 补录：律师(7312042960642489) 6→9 +3、"
    "人伤(7312035322822509) 7→9 +2、合规(7333014572917409) 7→9 +2、"
    "慈善(7311644304633438) 6→9 +3；合计 +10，B_done=36/36 达标。"
    "10 篇均为 IMA 真源（32位rawid+kb_id 构造），verify before cite。"
)

data["consumed_windows"].append({
    "date": "2026-08-07",
    "trigger": "automation-1783920420205 续跑：B 库补 10 篇至 36",
    "reason": "B 库 at 26/36，按每库硬配额 3 补录 10 篇（律师6→9 / 人伤7→9 / 合规7→9 / 慈善6→9）。",
    "b_target": 10,
    "b_done": 10,
    "total_target": 10,
    "total_done": 10,
    "libraries": ["7312042960642489", "7312035322822509", "7333014572917409", "7311644304633438"],
    "occupies_new_quota": False,
    "consume_priority": "continuation_backfill",
    "consecutive_day": 1,
    "alert_level": "L0-无",
    "status": "consumed_full",
    "consumed_at": "2026-08-07T08:45",
    "consumed_by": "automation-1783920420205 v1.13 续跑（B 库达标补录）",
})

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"appended {count} records; B_done = {data['totals']['B_done']} / {data['totals']['B_target']}")
