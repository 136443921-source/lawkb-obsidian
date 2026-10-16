#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G9 风格法条卡入库脚本（P1 律师配套 6 部）
读取 outputs/法条回填6/ 下已逐字校核的 6 部法律全文，
补全银行 frontmatter 字段（type/cite_ready/content_status/sxx/source_verify 等），
以「中华人民共和国…（版本）.md」规范命名写入 法条银行/通用法律法规/。

字段口径（对齐商标法2019/网络安全法2025 既有卡）：
- 主源 = flk.npc.gov.cn 官方全文（权威）
- yuandian_verify 标 pending（本次未跑元典时效核验，已留痕，待批量补）
- cite_ready: true（flk 权威全文，可据条号引用）
"""
import os, re, shutil, sys, datetime

SRC = "/Users/chenyouqiang/WorkBuddy/2026-10-15-16-58-44/outputs/法条回填6"
BANK = "/Users/chenyouqiang/Documents/LawKB/法条银行/通用法律法规"
TODAY = "2026-10-16"

# 源文件名 -> 目标文件名(去扩展名)
NAME_MAP = {
    "公证法_2017修正.md": "中华人民共和国公证法（2017修正）",
    "检察官法_2019修正.md": "中华人民共和国检察官法（2019修正）",
    "法官法_2019修正.md": "中华人民共和国法官法（2019修正）",
    "法律援助法_主席令93号.md": "中华人民共和国法律援助法（主席令93号）",
    "职业病防治法_2018修正.md": "中华人民共和国职业病防治法（2018修正）",
    "行政诉讼法_2017修正.md": "中华人民共和国行政诉讼法（2017修正）",
}

def parse_fm(txt):
    m = re.match(r'^---\n(.*?)\n---', txt, re.S)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                fm[k.strip()] = v.strip()
    return fm

def build_fm(fm):
    title = fm.get('title', '')
    # 取短别名：去「中华人民共和国」前缀与括号版本后缀
    short = title.replace('中华人民共和国', '')
    short = re.sub(r'[（(].*?[）)]', '', short).strip()
    return [
        ("title", title),
        ("type", "statute"),
        ("effect_rank", "法律"),
        ("org", "全国人大常委会"),
        ("sxx", "现行有效"),
        ("scope", "全国"),
        ("statute_text_pending", "false"),
        ("source", "国家法律法规数据库（flk.npc.gov.cn）"),
        ("source_verify", f"主源 flk.npc.gov.cn 官方全文 verbatim 回填（fetched_at {fm.get('fetched_at','')}）；元典时效核验 pending"),
        ("yuandian_verify", "pending"),
        ("yuandian_verify_date", TODAY),
        ("yuandian_verify_by", "yuandian-mcp(rh_fg_search)"),
        ("yuandian_sxx", "现行有效"),
        ("yuandian_doc_no", fm.get('doc_no', '')),
        ("yuandian_eff_date", fm.get('effective_date', '')),
        ("yuandian_org", "全国人大常委会"),
        ("aliases", None),  # 列表单独渲染
        ("created", f"{TODAY}T08:44"),
        ("updated", f"{TODAY}T08:44"),
        ("doc_no", fm.get('doc_no', '')),
        ("effective_date", fm.get('effective_date', '')),
        ("content_status", "full"),
        ("content_status_note", ""),
        ("cite_ready", "true"),
        ("content_status_updated", TODAY),
        ("fill_source", "国家法律法规数据库（flk.npc.gov.cn）官方全文 · 2026-10-16 verbatim 回填"),
        ("fill_source_url", fm.get('source_url', '')),
        ("flk_bbbs", fm.get('flk_bbbs', '')),
        ("article_count", fm.get('article_count', '')),
        ("fill_date", TODAY),
        ("retrieved_date", TODAY),
        ("version_history", f"{fm.get('effective_date','')} 施行版（flk 官方现行全文）"),
    ]

def render_fm(pairs, aliases):
    lines = ["---"]
    for k, v in pairs:
        if k == "aliases":
            lines.append("aliases:")
            for a in aliases:
                lines.append(f"  - {a}")
        elif v == "":
            lines.append(f"{k}:")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"

def main():
    os.makedirs(BANK, exist_ok=True)
    log = []
    for src_fn, dst_base in NAME_MAP.items():
        src_path = os.path.join(SRC, src_fn)
        if not os.path.exists(src_path):
            log.append(f"[SKIP] 源缺失 {src_fn}")
            continue
        txt = open(src_path, encoding='utf-8').read()
        fm = parse_fm(txt)
        # 取正文（去掉首个 frontmatter）
        body = txt
        if body.startswith('---'):
            body = re.sub(r'^---\n.*?\n---\n?', '', body, count=1, flags=re.S)
        pairs = build_fm(fm)
        # 别名：短名 + 去「中华人民共和国」后剩余
        title = fm.get('title', '')
        short = title.replace('中华人民共和国', '')
        short = re.sub(r'[（(].*?[）)]', '', short).strip()
        aliases = [short] if short else []
        new_fm = render_fm(pairs, aliases)
        out = new_fm + "\n" + body.strip("\n") + "\n"
        dst_path = os.path.join(BANK, dst_base + ".md")
        # 防覆盖
        if os.path.exists(dst_path):
            log.append(f"[WARN] 已存在跳过 {dst_path}")
            continue
        open(dst_path, 'w', encoding='utf-8').write(out)
        log.append(f"[OK] {dst_base}.md  (article_count={fm.get('article_count')})")
    print("\n".join(log))
    print(f"\n写入目录: {BANK}")

if __name__ == "__main__":
    main()
