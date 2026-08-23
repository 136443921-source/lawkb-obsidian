#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CaseDrop 投递即处理监听器（由 launchd WatchPaths 触发）

将 /Users/chenyouqiang/Documents/CaseDrop 根目录下新投递的案件材料即时归档到
LawKB 知识飞轮系统，消除"19:00 定时"带来的时态差：
  - 生成案件笔记 → LawKB/案件库/承办案件/<案由>/
  - 生成经验卡片占位 → LawKB/知识飞轮系统/02-提炼/经验卡片/
  - 原文件移至 CaseDrop/processed/
  - 本地通知（clawbot 推送机制待接入时替换为对应调用）

并发安全：文件锁防止 launchd 重复触发叠加执行。
"""
import os
import sys
import re
import time
import json
import shutil
import fcntl
import datetime

CASEDROP = "/Users/chenyouqiang/Documents/CaseDrop"
LAWKB_CASES = "/Users/chenyouqiang/Documents/LawKB/案件库/承办案件"
LAWKB_CARDS = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/经验卡片"
LOG = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/casedrop_watch.log"
LOCK = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/casedrop_watch.lock"


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def notify(title, body):
    # clawbot 推送机制待接入；此处用 macOS 本地通知作兜底可见提示
    try:
        os.system('osascript -e \'display notification "%s" with title "%s"\' >/dev/null 2>&1'
                  % (body.replace('"', "'"), title.replace('"', "'")))
    except Exception:
        pass
    log(f"NOTIFY {title}: {body}")


def read_docx(path):
    try:
        import zipfile
        z = zipfile.ZipFile(path)
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
        texts = re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml)
        return "".join(texts)
    except Exception as e:
        return f"[docx 解析失败: {e}]"


def extract_text(path):
    if path.lower().endswith(".docx"):
        return read_docx(path)
    for enc in ("utf-8", "gbk"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except Exception:
            continue
    return f"[读取失败: {path}]"


def first_heading(text):
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()
    t = text.strip().replace("\n", " ")
    return (t[:40] if t else "未命名案件")


def case_type_of(text, name):
    blob = (text + name)
    if "担保" in blob:
        return "担保合同纠纷"
    if "租赁" in blob:
        return "租赁纠纷"
    if "劳务" in blob or "工伤" in blob or "损害" in blob:
        return "侵权纠纷"
    if "合同" in blob:
        return "合同纠纷"
    return "其他纠纷"


def safe_name(s):
    return re.sub(r"[^\w一-龥-]", "_", s)[:40] or "case"


def process_item(item_path, name):
    files = []
    if os.path.isdir(item_path):
        for root, _, fs in os.walk(item_path):
            for fn in fs:
                if fn.lower().endswith((".md", ".docx", ".txt", ".pdf")):
                    files.append(os.path.join(root, fn))
    else:
        files = [item_path]
    if not files:
        return None, None

    combined = []
    for fp in files:
        combined.append(f"# 文件: {os.path.basename(fp)}\n\n" + extract_text(fp))
    text = "\n\n---\n\n".join(combined)

    title = first_heading(extract_text(files[0])) or name
    ctype = case_type_of(text, name)
    today = datetime.date.today().isoformat()
    sname = safe_name(title)

    # 案件笔记
    note_dir = os.path.join(LAWKB_CASES, ctype)
    os.makedirs(note_dir, exist_ok=True)
    note_path = os.path.join(note_dir, f"{sname}.md")
    note = f"""---
created: {today}
updated: {today}
tags: [案件, {ctype}]
case_type: {ctype}
status: 待提炼
result: 进行中
case_no: 待补充
source: CaseDrop投递即处理
review_date: {today}
---

# 案件笔记：{title}

> 由 CaseDrop 投递即处理监听器自动归档（{today}），待「案件材料自动归档」任务或人工补全经验卡片提炼。

## 来源文件
""" + "\n".join(f"- {os.path.basename(fp)}" for fp in files) + f"""

## 原始材料摘要（自动提取前 1500 字）
{text[:1500]}
"""
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(note)

    # 经验卡片占位（待提炼）
    os.makedirs(LAWKB_CARDS, exist_ok=True)
    card_path = os.path.join(LAWKB_CARDS, f"经验卡片-{sname}.md")
    card = f"""---
created: {today}
is_simulation: false
status: 待提炼
case_type: {ctype}
result: 进行中
case_no: 待补充
source: CaseDrop投递即处理（自动占位，待补提炼）
trigger: "（待从案件笔记提炼）"
do: "（待提炼）"
dont: "（待提炼）"
confidence: 0.3
tags: [经验卡片, 待提炼, {ctype}]
---

# 经验卡片（占位）：{title}

> ⚠️ 本卡片由 CaseDrop 投递即处理监听器生成占位，待「案件材料自动归档」任务或人工提炼 `trigger/do/dont/裁判规则`。
"""
    with open(card_path, "w", encoding="utf-8") as f:
        f.write(card)

    return title, note_path


def main():
    try:
        lf = open(LOCK, "w")
        fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception:
        log("另一个实例正在运行，退出")
        sys.exit(0)

    log("=== CaseDrop 监听器触发 ===")
    if not os.path.isdir(CASEDROP):
        log("CaseDrop 目录不存在")
        sys.exit(0)

    os.makedirs(os.path.join(CASEDROP, "processed"), exist_ok=True)

    processed = 0
    items = [d for d in os.listdir(CASEDROP)
             if d != "processed" and not d.startswith(".")]
    for name in items:
        ip = os.path.join(CASEDROP, name)
        try:
            title, note_path = process_item(ip, name)
            if not title:
                continue
            dest = os.path.join(CASEDROP, "processed", name)
            if os.path.exists(dest):
                dest = f"{dest}_{int(time.time())}"
            shutil.move(ip, dest)
            processed += 1
            log(f"已归档: {name} → {note_path}")
        except Exception as e:
            log(f"处理失败 {name}: {e}")

    if processed > 0:
        notify("CaseDrop 即时归档", f"本次自动归档 {processed} 个案件，已移至 processed/")
        log(f"本次共归档 {processed} 个案件")
    else:
        log("无新投递，退出")
    log("=== 结束 ===")


if __name__ == "__main__":
    main()
