#!/usr/bin/env python3
# user_profile_sync.py — 老强用户偏好漂移校验（只读，不改写任何文件）
# 扫描五处偏好落点，检测关键偏好键的覆盖度 / 矛盾漂移，防分叉。
# 用法: python3 user_profile_sync.py
import os, re, datetime

HOME = os.path.expanduser("~")
USER_ID = "user-75c7265a-5f11-4420-9e71-be28329d68fd-personal"

LOCATIONS = [
    ("L1_云profile镜像", "file", os.path.join(HOME, ".workbuddy", USER_ID, "MEMORY.md")),
    ("L2_USER-PROFILE", "file", os.path.join(HOME, "Documents/LawKB/_AI-Memory-Hub/01-用户偏好/USER-PROFILE.md")),
    ("L3_PREF卡片", "prefdir", os.path.join(HOME, "Documents/LawKB/_AI-Memory-Hub/01-用户偏好")),
    ("L4_工作区memory", "file", os.path.join(HOME, "WorkBuddy/Claw/.workbuddy/memory/MEMORY.md")),
    ("L5_工作区日志", "logdir", os.path.join(HOME, "WorkBuddy/Claw/.workbuddy/memory")),
]

# 关键偏好键 -> 探测词（任一命中即视为该落点"覆盖"此键）
CANONICAL_KEYS = {
    "称呼(老强/小强)": ["老强", "小强"],
    "决策权留用户(A/B/C)": ["决策权", "A/B/C", "多选项"],
    "先结论后展开": ["一句话结论", "结论前置", "先结论"],
    "直接批评不奉承": ["不喜奉承", "直接批评", "奉承"],
    "歧义先问": ["歧义先问", "不瞎猜", "AskUserQuestion", "先问"],
    "安全六-B铁律": ["六-B", "六－B", "六—B", "六_B"],
    "cp-n备份": ["cp -n", "备份到 /tmp", "时间戳目录"],
    "个人目录红线": ["个人目录", "只读扫描"],
    "不凭记忆灌条文": ["凭记忆", "本地权威源", "statute_text_pending", "不凭记忆"],
    "本地源引证第X条": ["第 X 条", "第X条", "相关规定"],
    "法条pkulaw主源": ["pkulaw", "北大法宝", "元典"],
    "LTI交付门禁": ["LTI", "REJECT", "五维"],
    "慎用刑事定性": ["虚假诉讼", "存疑", "刑事定性"],
    "收尾六件套": ["收尾六件套", "双目录同步", "主动提议沉淀"],
    "批量处置≤10": ["每轮", "10 份", "幂等"],
    "Fix-the-source": ["Fix-the-source", "改模板"],
    "主动提议沉淀": ["主动提议沉淀", "沉淀成卡", "要不要沉淀"],
    "小哲口令": ["小哲", "学伴"],
    "否定型结论铁律": ["否定型结论", "实物", "交叉验证"],
    "长标识写全值": ["长标识", "写全值", "media_id"],
    "技术标识变体假阴性": ["变体", "假阴性", "零引用"],
}


def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""
    except Exception:
        return ""


def scan(loc_name, kind, path):
    if kind == "file":
        return read_text(path)
    if kind == "prefdir":
        out = []
        try:
            for fn in sorted(os.listdir(path)):
                if fn.startswith("PREF-") and fn.endswith(".md"):
                    out.append(read_text(os.path.join(path, fn)))
        except FileNotFoundError:
            pass
        return "\n".join(out)
    if kind == "logdir":
        out = []
        try:
            files = [f for f in os.listdir(path) if re.match(r"2026-\d\d-\d\d\.md$", f)]
            files.sort(reverse=True)
            for fn in files[:5]:  # 仅最近 5 份日志，控量
                out.append(read_text(os.path.join(path, fn)))
        except FileNotFoundError:
            pass
        return "\n".join(out)
    return ""


def main():
    print(f"[sync] 老强用户偏好漂移校验 · {datetime.date.today()}")
    print("[sync] 五处落点扫描：")
    loc_texts = {}
    for name, kind, path in LOCATIONS:
        t = scan(name, kind, path)
        loc_texts[name] = t
        print(f"  - {name:18s}: {'OK' if t else '⚠️ 空/缺失'} ({len(t)} 字符)")

    print("\n=== 覆盖矩阵（✅=该落点覆盖此键）===")
    shorts = [n.split("_")[0] for n, _, _ in LOCATIONS]
    print("偏好键".ljust(20) + "".join(s.ljust(9) for s in shorts))
    drift_missing_ssot = []
    drift_ssot_only = []
    for key, probes in CANONICAL_KEYS.items():
        row = key[:18].ljust(20)
        covered = {}
        for (name, _, _), s in zip(LOCATIONS, shorts):
            hit = any(re.search(re.escape(p), loc_texts[name], re.I) for p in probes)
            covered[name] = hit
            row += ("✅" if hit else "·").ljust(9)
        print(row)
        l2 = covered.get("L2_USER-PROFILE")
        others = [v for k, v in covered.items() if k != "L2_USER-PROFILE"]
        if (not l2) and any(others):
            drift_missing_ssot.append(key)
        if l2 and not any(others):
            drift_ssot_only.append(key)

    print("\n=== 漂移诊断 ===")
    if drift_missing_ssot:
        print("🔴 SSOT 缺失但别处有（SSOT 未收口，需补进 USER-PROFILE 或 PREF）：")
        for k in drift_missing_ssot:
            print(f"   - {k}")
    else:
        print("✅ 所有关键偏好键均已被 SSOT(USER-PROFILE) 收口")
    if drift_ssot_only:
        print("🟡 仅 SSOT 有、别处无（可能其他落点过期，需同步）：")
        for k in drift_ssot_only:
            print(f"   - {k}")

    print("\n[sync] 完成。建议：每月跑一次；SSOT 缺失项补进 USER-PROFILE.md 或对应 PREF 卡；")
    print("       矛盾（同键多落点取值相反）需人工核对，本脚本仅报告覆盖度。")


if __name__ == "__main__":
    main()
