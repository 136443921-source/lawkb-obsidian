#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_fix_yaml_colon_20260916.py  v1.0
修复「frontmatter 值内含半角 `: ` 被 YAML 解析为嵌套 mapping」导致的门禁 FAIL。

病征：yaml.safe_load 报 "mapping values are not allowed here"
根因：plain scalar 值里出现 ASCII 冒号+空格（如 `cloud: 前缀`、`for user: a4204ed9`）
修法：整值用双引号包裹（值内无 ASCII 双引号时安全；有则先替换为中文引号）

用法：
  python _fix_yaml_colon_20260916.py            # dry-run
  python _fix_yaml_colon_20260916.py --apply    # 落盘
"""
import os
import re
import sys

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"

# 🔴 坑 52：APPLY 必须早于任何 sys.argv 改写
APPLY = "--apply" in sys.argv

TARGETS = [
    ("02-提炼/经验卡片/思维轨迹/轨迹卡-北大法宝连接器90001排查的认知纠偏路径-20260916.md",
     "fact_directions"),
    ("02-提炼/经验卡片/飞轮运维/经验卡-归因处方前反向实证与cloud前缀只读-治理席位审计双坑-20260915.md",
     "title"),
]


def split_fm(text):
    """切出 frontmatter 与正文；无 frontmatter 返回 (None, text)"""
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end < 0:
        return None, text
    return text[:end + 4], text[end + 4:]


def quote_value(line, key):
    """把 `key: 值` 整值用双引号包裹"""
    m = re.match(rf"^({re.escape(key)}):\s*(.*)$", line)
    if not m:
        return None
    k, v = m.group(1), m.group(2).strip()
    if v.startswith('"') and v.endswith('"'):
        return None  # 已包裹
    if '"' in v:
        v = v.replace('"', "\u201c", 1)
        # 配对替换：偶数次出现交替左右引号
        out, open_q = [], True
        for ch in v:
            if ch == '"':
                out.append("\u201c" if open_q else "\u201d")
                open_q = not open_q
            else:
                out.append(ch)
        v = "".join(out)
    return f'{k}: "{v}"'


def main():
    import yaml
    changed = 0
    for rel, key in TARGETS:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            print(f"[MISS] {rel}")
            continue
        text = open(path, encoding="utf-8").read()
        fm, body = split_fm(text)
        if fm is None:
            print(f"[SKIP] 无 frontmatter: {rel}")
            continue

        lines = fm.split("\n")
        hit = False
        for i, ln in enumerate(lines):
            if re.match(rf"^{re.escape(key)}:\s*\S", ln):
                new = quote_value(ln, key)
                if new:
                    print(f"  [PATCH] {key}")
                    print(f"    - {ln[:90]}")
                    print(f"    + {new[:90]}")
                    lines[i] = new
                    hit = True
                break
        if not hit:
            print(f"[SKIP] 未命中 {key}: {rel}")
            continue

        new_fm = "\n".join(lines)
        # 先验证
        try:
            yaml.safe_load(new_fm.strip("-").strip("\n"))
        except Exception as e:
            print(f"[FAIL] 修复后仍解析失败 {rel}: {e}")
            continue

        if APPLY:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_fm + body)
            # 复验
            chk = open(path, encoding="utf-8").read()
            f2, _ = split_fm(chk)
            yaml.safe_load(f2.strip("-").strip("\n"))
            changed += 1
            print(f"  [OK] 已写入并复验通过")
        else:
            changed += 1

    print(f"\n({'APPLY' if APPLY else 'DRY-RUN'}) 处理 {changed}/{len(TARGETS)} 个文件")


if __name__ == "__main__":
    main()
