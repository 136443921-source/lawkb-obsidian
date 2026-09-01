# -*- coding: utf-8 -*-
"""
概念页自动关联块清理器 v1.0（2026-08-30）
============================================================================
背景：resolve_broken_links.py v1.0/v1.1 生成概念页时，会在正文塞入自动关联块：
  - 「## 关联（知识飞轮断链消解 · 概念页自动关联）」  ← 689 个概念页全有
  - 「## 相关笔记」  ← 403 个（条目均带"(共现关键词: ...)"标注）
  - 「## 反向链接」  ← 28 个（混合：部分带共现标注=噪声，部分为真实反向链接）
这些块造成：
  ① 约 152 个概念页互刷引用 → 图谱 top10 失真 40%
  ② 共现关键词误挂（MEMORY 铁律：宁可少挂不可错挂）
  ③ 全库 21.8% 的链接（11695 条）是概念页自动生成的互链噪声

策略（依 MEMORY「共现笔记锚点污染」铁律）：
  - 「关联」「相关笔记」 → 整块删除
  - 「反向链接」         → 只删带"(共现关键词:"标注的行，保留真实条目
  - 概念页文件本身保留（移走会造成 188 处断链，已验证）

安全性：
  - 幂等（已清理的文件检测到无目标块即跳过）
  - dry-run 为默认，须显式 --apply 才落盘
  - 只删概念页**发出**的链接，不影响任何其他笔记
  - 备份：~/WorkBuddy/Backups/2026-08-30_概念页清理前/（689 文件 / 965708 字节）
"""
import os
import re
import sys
import io

CP = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/03-连接/概念页"

FM_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.S)
# 需要整块删除的标题（含可能的括号说明）
DROP_HEADS = ("关联", "相关笔记")
BACKLINK_HEAD = "反向链接"
COOC_RE = re.compile(r"\(共现关键词[:：].*?\)")
HEAD_RE = re.compile(r"(?m)^(#{1,6})\s*(.+?)\s*$")


def split_blocks(body):
    """把正文按标题切成 [(level, title, content), ...]，保留前置无标题部分。"""
    blocks = []
    last = 0
    heads = list(HEAD_RE.finditer(body))
    if not heads:
        return [(0, "", body)]
    pre = body[:heads[0].start()]
    if pre.strip():
        blocks.append((0, "", pre))
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(body)
        blocks.append((len(m.group(1)), m.group(2).strip(), body[m.end():end]))
    return blocks


def clean_text(text):
    """返回 (新文本, 删除块数, 删除共现行数)；若无需清理则返回 None。"""
    m = FM_RE.match(text)
    fm = m.group(0) if m else ""
    body = text[m.end():] if m else text

    blocks = split_blocks(body)
    out = []
    dropped_blocks = 0
    dropped_lines = 0

    for level, title, content in blocks:
        bare = re.sub(r"[（(].*?[)）]", "", title).strip()
        if bare in DROP_HEADS and level >= 2:
            dropped_blocks += 1
            continue
        if bare == BACKLINK_HEAD and level >= 2:
            # 只删共现标注行，保留真实条目
            keep = []
            for line in content.splitlines():
                if COOC_RE.search(line):
                    dropped_lines += 1
                    continue
                keep.append(line)
            new_content = "\n".join(keep)
            if not new_content.strip():
                dropped_blocks += 1
                continue
            out.append(("#" * level) + " " + title + new_content)
            continue
        if level == 0:
            out.append(content)
        else:
            out.append(("#" * level) + " " + title + content)

    if dropped_blocks == 0 and dropped_lines == 0:
        return None

    new_body = "\n".join(out)
    # 收尾：去掉多余空行，保证单换行结尾
    new_body = re.sub(r"\n{3,}", "\n\n", new_body).rstrip() + "\n"
    return fm + new_body, dropped_blocks, dropped_lines


def main():
    apply = "--apply" in sys.argv
    files = sorted(f for f in os.listdir(CP) if f.endswith(".md"))
    stat = {"changed": 0, "skipped": 0, "blocks": 0, "lines": 0, "links_removed": 0}
    link_re = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]*)?(?:\|[^\]]*)?\]\]")

    for f in files:
        p = os.path.join(CP, f)
        text = io.open(p, encoding="utf-8", errors="ignore").read()
        res = clean_text(text)
        if res is None:
            stat["skipped"] += 1
            continue
        new_text, db, dl = res
        stat["changed"] += 1
        stat["blocks"] += db
        stat["lines"] += dl
        stat["links_removed"] += (len(link_re.findall(text)) - len(link_re.findall(new_text)))
        if apply:
            io.open(p, "w", encoding="utf-8").write(new_text)

    mode = "APPLY 已落盘" if apply else "DRY-RUN 未改动"
    print("=== 概念页关联块清理 v1.0 | %s ===" % mode)
    print("  概念页总数     : %d" % len(files))
    print("  需清理         : %d" % stat["changed"])
    print("  无需清理(幂等) : %d" % stat["skipped"])
    print("  删除块         : %d" % stat["blocks"])
    print("  删除共现行     : %d" % stat["lines"])
    print("  移除链接总数   : %d" % stat["links_removed"])
    if not apply:
        print("\n  确认无误后加 --apply 执行落盘")


if __name__ == "__main__":
    main()
