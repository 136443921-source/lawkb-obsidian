#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知识盲区扫描 v1.3：扫描 LawKB 知识覆盖度，按案件领域判定盲区。"""
import os, re, json, datetime

ROOT = "/Users/chenyouqiang/Documents/LawKB"
TODAY = datetime.date(2026, 7, 19)
EXCLUDE_DIRS = [".workbuddy", "scripts", "Clippings", "05-调用", "知识飞轮系统/logs", "知识飞轮系统/.workbuddy",
                 "法律法规库", "workbuddy 使用技巧", "Obsidian插件启用极简教程.md",
                 "Obsidian极简安装指南.md", "Obsidian配置指南.md", "未整理文章",
                 "更新基金会值得收藏的133部常用法律法规政策速查汇编目录.md",
                 "审计署通报一批社会组织和基金会违规社会组织应如何加强内审内控.md"]

# 案件领域 -> 关键词（用于匹配知识库笔记）
DOMAINS = {
    "合同纠纷(民法·合同)": ["合同", "违约", "协议解除", "附条件", "债权", "买卖"],
    "股东知情权纠纷(公司法)": ["股东知情权", "知情权", "会计账簿", "股东", "公司法", "出资"],
    "婚姻家庭纠纷(民法·婚姻)": ["离婚", "婚姻", "抚养", "夫妻共同财产", "财产分割", "家事"],
}

def has_frontmatter(text):
    return text.lstrip().startswith("---")

def extract_frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm

def count_wikilinks(text):
    return len(re.findall(r"\[\[([^\]]+)\]\]", text))

def note_quality(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except:
        return None
    if not text.strip():
        return None
    fm = extract_frontmatter(text) if has_frontmatter(text) else {}
    # frontmatter 0.2
    s_front = 0.2 if fm else 0.0
    # 双向链接 0.2
    nlinks = count_wikilinks(text)
    s_link = 0.2 if nlinks > 0 else 0.0
    # 标签 0.1
    s_tag = 0.1 if fm.get("tags") else 0.0
    # 更新 0.2（90天内更新过）
    s_update = 0.0
    upd = fm.get("updated") or fm.get("date") or fm.get("created") or fm.get("last_review")
    if upd:
        m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", upd)
        if m:
            try:
                d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                if (TODAY - d).days <= 90:
                    s_update = 0.2
            except:
                pass
    # 长度 0.3（>=800字满分，线性）
    length = len(re.sub(r"\s", "", text))
    s_len = min(1.0, length / 800.0) * 0.3
    total = s_front + s_link + s_tag + s_update + s_len
    return {
        "path": path,
        "len": length,
        "links": nlinks,
        "tags": bool(fm.get("tags")),
        "updated": bool(s_update),
        "score": round(total, 3),
    }

def walk_md(root):
    out = []
    for dp, dn, fn in os.walk(root):
        # 排除
        rel = os.path.relpath(dp, ROOT)
        if any(rel == e or rel.startswith(e + os.sep) or ("/" + e + "/") in ("/" + rel + "/") for e in EXCLUDE_DIRS):
            continue
        for f in fn:
            if f.endswith(".md"):
                out.append(os.path.join(dp, f))
    return out

# 关键词按"文件名优先"分组：filename_kws 强信号，content_kws 弱信号(需配合领域目录)
DOMAINS = {
    "合同纠纷(民法·合同)": {
        "fname": ["合同", "买卖", "租赁", "借款", "保证", "担保", "承揽", "违约"],
        "content": ["合同编", "违约责任", "合同解除", "要约承诺", "双务合同"],
    },
    "股东知情权纠纷(公司法)": {
        "fname": ["股东知情权", "知情权", "会计账簿", "股东", "公司决议", "股权"],
        "content": ["股东知情权纠纷", "查阅会计账簿", "公司法解释", "股东知情权诉讼"],
    },
    "婚姻家庭纠纷(民法·婚姻)": {
        "fname": ["离婚", "婚姻", "抚养", "扶养", "继承", "夫妻共同", "家事", "赡养"],
        "content": ["离婚纠纷", "夫妻共同财产", "子女抚养权", "婚姻家事"],
    },
}

# 领域相关目录（在此目录内的 content 命中才算数）
DOMAIN_DIRS = ["知识库", "学习笔记", "执业技能库", "笔记助手", "案例库", "合同类法律文书",
                "人伤专业领域", "知识飞轮系统", "法律文书模板", "提示词库"]

all_md = walk_md(ROOT)
print(f"扫描笔记总数: {len(all_md)}")

results = {}
for domain, kws in DOMAINS.items():
    matched = []
    for p in all_md:
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
        except:
            continue
        fname = os.path.basename(p)
        rel = os.path.relpath(p, ROOT)
        # 强信号：文件名含关键词
        fname_hit = any(kw in fname for kw in kws["fname"])
        # 弱信号：内容含关键词 且 处于领域相关目录
        in_domain_dir = any(rel.startswith(d + os.sep) or rel == d for d in DOMAIN_DIRS)
        content_hit = any(kw in txt[:1500] for kw in kws["content"]) and in_domain_dir
        if fname_hit or content_hit:
            q = note_quality(p)
            if q:
                matched.append(q)
    count = len(matched)
    avg_q = round(sum(m["score"] for m in matched) / count, 3) if count else 0.0
    # 覆盖度 = 平均质量 * 数量因子(1~2)
    qty_factor = 1.0 + min(1.0, count / 10.0)
    coverage = round(avg_q * qty_factor, 3) if count else 0.0
    if coverage < 0.5:
        level = "严重盲区"
    elif coverage <= 1.0:
        level = "中度盲区"
    else:
        level = "良好"
    results[domain] = {
        "count": count,
        "avg_quality": avg_q,
        "coverage": coverage,
        "level": level,
        "sample": [os.path.relpath(m["path"], ROOT) for m in matched[:8]],
    }

print(json.dumps(results, ensure_ascii=False, indent=2))
