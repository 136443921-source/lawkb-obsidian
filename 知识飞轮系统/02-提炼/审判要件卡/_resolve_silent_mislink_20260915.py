#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
沉默错链 → 候选正确编号 解析器 v1 / 2026-09-15

🔴 坑 51 第二代：AY 域 related_links 用「案由序号」构造链接，
  而物理文件用「rule_id 序号」命名，两者**偏移分段不恒定**（实证 68 / 18 两种）。
  → 不能靠算术偏移批量修，只能按「案由名反查实际卡文件名」。

解法：抽链接里的「案由名」（去掉编号与「单案由路由卡」等后缀），
      到案由路由目录反查唯一命中的物理卡；唯一命中才给候选。

只读，不写任何文件。输出 沉默错链候选映射-20260915.json
"""
import os, re, json

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
AY_DIR = os.path.join(ROOT, "06-沉淀/裁判规则库/案由路由")
SRC = os.path.join(HERE, "沉默错链审计-20260915.json")

SUFFIX = re.compile(r"(单案由路由卡|定性分野卡|定性分野|卡)$")


def core(title):
    """从链接标题里抽出核心案由名"""
    t = SUFFIX.sub("", title).strip("-· ")
    t = re.sub(r"[（(].*?[)）]", "", t)
    return t.strip("-· ")


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    # 全库所有 R-* 卡（不只 AY），便于跨域反查
    allcards = []
    for dp, dn, fn in os.walk(os.path.join(ROOT, "06-沉淀/裁判规则库")):
        for f in fn:
            if f.startswith("R-") and f.endswith(".md"):
                allcards.append(os.path.splitext(f)[0])

    out = []
    for o in data:
        c = core(o["link_title"])
        if len(c) < 3:
            out.append({**o, "candidate": None, "confidence": "跳过（核心名过短）"})
            continue
        # 🔴 归一化：忽略连字符/顿号差异（实证「著作权权属侵权」vs「著作权权属-侵权」）
        cn = re.sub(r"[-–—、·\s]", "", c)
        hits = [x for x in allcards
                if c in x or cn in re.sub(r"[-–—、·\s]", "", x)]
        # 优先同域
        dom = o["rule_id"].split("-")[1]
        same = [x for x in hits if x.startswith("R-%s-" % dom)]
        pool = same or hits
        uniq = sorted(set(pool))
        if len(uniq) == 1:
            out.append({**o, "core": c, "candidate": uniq[0],
                        "confidence": "唯一命中（同域）" if same else "唯一命中（跨域）",
                        "hits": len(hits)})
        elif len(uniq) == 0:
            out.append({**o, "core": c, "candidate": None,
                        "confidence": "无命中（疑似卡未建或案由名已更名）", "hits": 0})
        else:
            out.append({**o, "core": c, "candidate": None,
                        "confidence": "多命中 %d，须人工" % len(uniq),
                        "hits": len(hits), "options": uniq[:5]})

    op = os.path.join(HERE, "沉默错链候选映射-20260915.json")
    json.dump(out, open(op, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    n_fix = sum(1 for x in out if x.get("candidate"))
    print(f"沉默错链 {len(out)} 类 → 唯一命中可给候选 {n_fix} 类\n")
    for x in out:
        mark = "✅" if x.get("candidate") else "⏳"
        print(f"{mark} {x['rule_id']}-{x['link_title']}")
        print(f"    核心名：{x.get('core','-')}")
        if x.get("candidate"):
            print(f"    → 候选：{x['candidate']}   [{x['confidence']}]")
        else:
            print(f"    → {x['confidence']}")
            if x.get("options"):
                print(f"       备选：{x['options']}")
        print(f"    出现文件 {len(x['files'])}：{x['files'][:2]}")
    print(f"\n报告 → {op}")


if __name__ == "__main__":
    main()
