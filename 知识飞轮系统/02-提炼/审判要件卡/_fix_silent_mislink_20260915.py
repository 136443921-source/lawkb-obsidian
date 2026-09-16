#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沉默错链修复器 v1 / 2026-09-15

🔴 只修「同域唯一命中 + 案由名完全一致（仅编号不同）」的高置信度项，
  取自 沉默错链候选映射-20260915.json 中 candidate 非空者。

安全：
  · 改前 cp -n 双形态备份（basename + 扁平，防坑 34 回滚白名单漏排）
  · 同文件多处修改 → 一次原子写入（六-B）
  · 并发保护：跳过近 30 分钟内被改的文件（坑 61）
用法：python _fix_silent_mislink_20260915.py [--apply]
"""
import os, re, json, sys, shutil, time, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
SRC = os.path.join(HERE, "沉默错链候选映射-20260915.json")

APPLY = "--apply" in sys.argv
RECENT_SEC = 1800
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
BK = f"/tmp/存量卡巡检沉默错链修复_{STAMP}"


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    jobs = [x for x in data if x.get("candidate")]
    print(f"高置信度待修：{len(jobs)} 类")

    now = time.time()
    by_file = {}
    for x in jobs:
        old = f"{x['rule_id']}-{x['link_title']}"
        new = x["candidate"]
        for rel in x["files"]:
            by_file.setdefault(rel, []).append((old, new))

    total = 0
    skipped = []
    for rel, pairs in sorted(by_file.items()):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            print(f"  ⚠️  不存在：{rel}")
            continue
        if now - os.path.getmtime(p) < RECENT_SEC:
            skipped.append(rel)
            print(f"  ⏭  并发保护跳过：{rel}")
            continue
        t = open(p, encoding="utf-8").read()
        orig = t
        cnt = 0
        for old, new in pairs:             # 同文件多处 → 累积后一次写入
            c = t.count(old)
            if c:
                t = t.replace(old, new)
                cnt += c
                print(f"  · {rel}\n      {old}\n   →  {new}  ({c} 处)")
        if cnt == 0 or t == orig:
            continue
        total += cnt
        if APPLY:
            os.makedirs(BK, exist_ok=True)
            shutil.copy2(p, os.path.join(BK, os.path.basename(p)))
            shutil.copy2(p, os.path.join(BK, rel.replace("/", "__")))
            open(p, "w", encoding="utf-8").write(t)

    print(f"\n{'[APPLY]' if APPLY else '[DRY-RUN]'} 替换 {total} 处，涉及文件 {len(by_file)-len(skipped)} 个"
          + (f"，并发保护跳过 {len(skipped)} 个" if skipped else ""))
    if APPLY and total:
        print(f"备份 → {BK}（{len(os.listdir(BK))} 份）")


if __name__ == "__main__":
    main()
