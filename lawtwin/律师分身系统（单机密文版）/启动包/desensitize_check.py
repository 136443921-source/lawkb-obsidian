#!/usr/bin/env python3
# =============================================================================
# 律师分身·单机密文版 —— 脱敏门禁
# 扫描指定目录下的文本文件，发现敏感信息（身份证/手机号/银行卡/法院案号）则
# 以非零退出码拦截；退出码 0 表示通过（可放行对外交付）。
# 注意：图片/PDF 等二进制扫描件检测不到，开仓前须人工过一遍。
#
# 用法：
#   python3 desensitize_check.py <目录> [--strict]
# =============================================================================
import sys
import os
import re
import argparse

PATTERNS = {
    "身份证": re.compile(r"\b\d{17}[\dXx]\b"),
    "手机号": re.compile(r"\b1[3-9]\d{9}\b"),
    "银行卡": re.compile(r"\b\d{16,19}\b"),
    "法院案号": re.compile(r"\(?\d{4}\)?[\u4e00-\u9fa5]+?\d+号"),
}

SKIP_EXT = {".enc", ".png", ".jpg", ".jpeg", ".pdf", ".zip", ".gz"}


def scan(path: str):
    hits = []
    for root, _, files in os.walk(path):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in SKIP_EXT:
                continue
            fp = os.path.join(root, f)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        for label, pat in PATTERNS.items():
                            if pat.search(line):
                                hits.append((fp, i, label, line.strip()[:60]))
            except Exception:
                pass
    return hits


def main():
    ap = argparse.ArgumentParser(description="律师分身·单机密文版 脱敏门禁")
    ap.add_argument("path", help="待扫描目录")
    ap.add_argument("--strict", action="store_true", help="严格模式（仅影响提示文案）")
    args = ap.parse_args()

    if not os.path.isdir(args.path):
        print(f"❌ 目录不存在: {args.path}", file=sys.stderr)
        sys.exit(2)

    hits = scan(args.path)
    if hits:
        print(f"❌ 脱敏门禁拦截 {len(hits)} 处（{'严格' if args.strict else '普通'}模式）：")
        for fp, i, label, snippet in hits[:50]:
            print(f"  [{label}] {fp}:{i} {snippet}")
        sys.exit(1)
    print("✅ 脱敏门禁通过（退出码 0）")
    sys.exit(0)


if __name__ == "__main__":
    main()
