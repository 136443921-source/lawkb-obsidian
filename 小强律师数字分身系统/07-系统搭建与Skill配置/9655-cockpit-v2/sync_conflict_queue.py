#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_conflict_queue.py · 冲突仲裁队列 → 9360 驾驶舱 实时同步
========================================================
把 LawKB「冲突仲裁」目录里最新的 `冲突仲裁队列_*.json`
同步进 9360 驾驶舱的 conflict-arbitration 子屏，作为该屏运行时拉取的数据源。

落点铁律：仅写 cockpit-hub-ops 目录内，不触碰 LawKB 源目录。
单一数据源：LawKB 冲突仲裁扫描产出 冲突仲裁队列_*.json（本脚本只读）。

用法：
  python3 sync_conflict_queue.py            # 同步最新一份
  python3 sync_conflict_queue.py --dry-run  # 仅报告不写
"""
import sys, os, json, glob, shutil, datetime

COCKPIT = "/Users/chenyouqiang/WorkBuddy/2026-09-12-01-29-05/outputs/cockpit-hub-ops"
CONFLICT_DIR = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/03-连接/冲突仲裁"
SUBAPP = os.path.join(COCKPIT, "subapps", "conflict-arbitration")
OUT = os.path.join(SUBAPP, "queue.json")

# 六类冲突中文标签（与 lawkb-conflict-arbitration 一致）
TYPE_LABEL = {
    "KE": "知识演进", "FC": "事实纠正", "VC": "版本冲突",
    "CC": "内容矛盾", "CR": "上下文相关", "MC": "成熟度冲突",
}


def latest_queue():
    files = sorted(glob.glob(os.path.join(CONFLICT_DIR, "冲突仲裁队列_*.json")))
    if not files:
        # 兜底：也认 看板 html（取其内嵌 DATA 不可行，这里仅列文件）
        raise FileNotFoundError("冲突仲裁目录无 冲突仲裁队列_*.json：" + CONFLICT_DIR)
    return files[-1]


def load_resolved_log():
    """读取 _resolved_log.json（apply 真实执行留痕）→ 用于判定「已处置」而非仅 AI 建议。"""
    p = os.path.join(CONFLICT_DIR, "_resolved_log.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            return {}
    return {}


def normalize(path, resolved_log=None):
    d = json.load(open(path, encoding="utf-8"))
    conflicts = d.get("conflicts", [])
    rl = resolved_log or {}
    for c in conflicts:
        # 真实处置状态 = 该 ID 出现在 apply 留痕；队列 decision 仅代表 AI 建议
        c["resolved"] = bool(c.get("id") in rl)
    return {
        "generated": d.get("generated", ""),
        "root": d.get("root", ""),
        "count": d.get("count", len(conflicts)),
        "resolved_count": sum(1 for c in conflicts if c.get("resolved")),
        "synced_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source_file": os.path.basename(path),
        "conflicts": conflicts,
    }


def atomic_write_json(path, data, indent=1):
    """原子写 JSON：先写同目录临时文件并 fsync 落盘，再 os.replace 原子覆盖目标。

    P3 根治（2026-09-16）：原 open(path,'w') 截断写会制造并发读半截竞态
    （rescan 刷新时恰读到半截 queue.json 导致 JSON 解析失败）。改为：
      ① 写 path 同目录的隐藏临时文件（保证 os.replace 同文件系统、原子生效）
      ② flush + fsync 确保数据落盘后再 rename
      ③ os.replace 跨平台原子替换（覆盖既存目标，POSIX/Windows 均保证原子性）
    读方在任何时刻拿到的要么是旧完整版、要么是新完整版，杜绝半截。
    """
    d = os.path.dirname(path) or "."
    tmp = os.path.join(d, "." + os.path.basename(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def main():
    dry = "--dry-run" in sys.argv
    src = latest_queue()
    rl = load_resolved_log()
    data = normalize(src, rl)
    n = len(data["conflicts"])
    # 计数概览（仅报告用）
    by_type = {}
    pending = 0
    resolved = 0
    for c in data["conflicts"]:
        by_type[c.get("type", "?")] = by_type.get(c.get("type", "?"), 0) + 1
        if c.get("resolved"):
            resolved += 1
        else:
            pending += 1
    print(f"[冲突仲裁同步] 源：{os.path.basename(src)}")
    print(f"  候选冲突总数：{n} ｜ 待处理 {pending} ｜ 已处置 {resolved}")
    print(f"  六类分布：", "  ".join(f"{TYPE_LABEL.get(t,t)}={by_type.get(t,0)}" for t in ["KE","FC","VC","CC","CR","MC"]))
    if dry:
        print("  [dry-run] 跳过写入。")
        return
    os.makedirs(SUBAPP, exist_ok=True)
    if os.path.isfile(OUT):
        bk = f"/tmp/conflict-queue-{datetime.datetime.now():%Y%m%d-%H%M%S}.json"
        shutil.copy(OUT, bk)
        print(f"  备份旧 queue.json → {bk}")
    # ★ P3 根治：原子写（临时文件 + fsync + os.replace），消除并发读半截竞态
    atomic_write_json(OUT, data)
    print(f"  ✅ 已原子写入 {OUT}（{os.path.getsize(OUT)//1024} KB）")


if __name__ == "__main__":
    main()
