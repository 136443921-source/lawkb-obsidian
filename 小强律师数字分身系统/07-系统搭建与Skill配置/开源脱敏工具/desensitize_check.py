#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
desensitize_check.py —— LawTwin 开源脱敏门禁（阶段 0 硬前置工具）

用途
    在代码/文档提交到公开仓库前，扫描其中是否残留身份标识类敏感信息。
    未通过本脚本的目录，不得开仓库。

设计原则（对应老强安全铁律）
    1. 默认 dry-run：只报告，绝不修改任何文件。
    2. 批量前先 dry-run：--redact 必须显式指定目标，且 --in-place 强制要求 --backup-dir。
    3. 宁可误报不可漏报：HIGH/MEDIUM 一律阻断，LOW 仅提示（--strict 下也阻断）。

覆盖的检测项
    HIGH   身份证号（18位，含 MOD 11-2 校验位验证）/ 15位老式身份证
    HIGH   统一社会信用代码（18位，含校验位验证）
    HIGH   银行卡号（16-19位，含 Luhn 校验）
    HIGH   已知当事人姓名（--names-file 载入，本地私有名单，不入库）
    MEDIUM 手机号
    MEDIUM 法院案号（带年份括号 / 无括号两种写法）
    MEDIUM 车牌号
    LOW    邮箱地址

用法
    # 只扫描报告（推荐第一步）
    python3 desensitize_check.py /path/to/repo

    # 载入当事人姓名名单（v1.0.1 起不传也会自动读默认名单 ~/.lawtwin/names.txt）
    python3 desensitize_check.py /path/to/repo --names-file ~/.lawtwin/names.txt

    # 严格模式：LOW 也阻断（pre-commit 推荐）
    python3 desensitize_check.py . --strict

    # JSON 输出
    python3 desensitize_check.py . --json

    # 生成脱敏副本（不碰原文件）
    python3 desensitize_check.py . --redact --out-dir ./_redacted

    # 原地脱敏（强制要求备份目录）
    python3 desensitize_check.py . --redact --in-place --backup-dir /tmp/backup_$(date +%s)

    # 内置自检
    python3 desensitize_check.py --self-test

退出码
    0  干净，可提交
    1  发现需处置项（HIGH/MEDIUM，或 --strict 下的 LOW）
    3  运行错误
"""

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable

VERSION = "1.0.1"

# 默认脱敏名单路径。不传 --names-file 时自动加载，
# 避免"忘了传参就静默漏检"——门禁场景漏检代价远高于误报。
NAMES_FILE_DEFAULT = "~/.lawtwin/names.txt"

# ---------------------------------------------------------------- 常量

SCAN_EXT = {
    ".md", ".txt", ".markdown", ".json", ".yaml", ".yml",
    ".py", ".js", ".ts", ".html", ".htm", ".css", ".sh", ".csv",
}

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".obsidian", ".idea", ".vscode", "dist", "build", "_redacted",
}

SKIP_FILES = {"desensitize_check.py", ".desensitizeignore"}

IGNORE_MARK = "desensitize:ignore"

# 严重级别
HIGH, MEDIUM, LOW = "HIGH", "MEDIUM", "LOW"

SEVERITY_ORDER = {HIGH: 0, MEDIUM: 1, LOW: 2}


# ---------------------------------------------------------------- 校验算法

def _id_card_ok(s: str) -> bool:
    """18 位身份证 MOD 11-2 校验位验证（GB 11643-1999）。"""
    if len(s) != 18:
        return False
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    codes = "10X98765432"
    try:
        total = sum(int(s[i]) * weights[i] for i in range(17))
    except ValueError:
        return False
    return codes[total % 11] == s[17].upper()


def _uscc_ok(s: str) -> bool:
    """统一社会信用代码校验位验证（GB 32100-2015）。"""
    if len(s) != 18:
        return False
    charset = "0123456789ABCDEFGHJKLMNPQRTUWXY"
    weights = [1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]
    try:
        total = sum(charset.index(s[i]) * weights[i] for i in range(17))
    except ValueError:
        return False
    check = 31 - (total % 31)
    if check == 31:
        check = 0
    return charset[check] == s[17]


def _luhn_ok(s: str) -> bool:
    """银行卡号 Luhn 校验。"""
    if not (16 <= len(s) <= 19) or not s.isdigit():
        return False
    total = 0
    for i, ch in enumerate(reversed(s)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


# ---------------------------------------------------------------- 正则

# 18 位身份证：6位地址 + 8位生日 + 3位顺序 + 1位校验
RE_ID18 = re.compile(
    r"(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)"
)
# 15 位老式身份证
RE_ID15 = re.compile(
    r"(?<!\d)[1-9]\d{7}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}(?!\d)"
)
# 统一社会信用代码
RE_USCC = re.compile(r"(?<![0-9A-Z])[0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10}(?![0-9A-Z])")
# 银行卡：连续 16-19 位数字（再由 Luhn 与身份证规则过滤）
RE_BANK = re.compile(r"(?<!\d)\d{16,19}(?!\d)")
# 手机号
RE_PHONE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
# 案号（带年份括号）：（2026）黔0330民初6658号
RE_CASE_BRACKET = re.compile(
    r"[\(（]\s*(?:19|20)\d{2}\s*[\)）]"
    r"[\u4e00-\u9fa5]{0,8}\d{0,6}\s*"
    r"[民刑行执赔破保再辖仲监特督请认]"
    r"[\u4e00-\u9fa5]{0,4}\s*\d{1,6}\s*号"
)
# 案号（无括号）：2026黔0330民初6658号
RE_CASE_PLAIN = re.compile(
    r"(?:19|20)\d{2}\s*[\u4e00-\u9fa5]{1,6}\d{0,6}\s*"
    r"[民刑行执赔破保再辖仲监特督请认]"
    r"[\u4e00-\u9fa5]{0,4}\s*\d{1,6}\s*号"
)
# 车牌：贵C09782D
RE_PLATE = re.compile(r"(?<![0-9A-Z])[\u4e00-\u9fa5][A-HJ-NP-Z][A-HJ-NP-Z0-9]{4,6}(?![0-9A-Z])")
# 邮箱
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


# ---------------------------------------------------------------- 数据结构

@dataclass
class Finding:
    file: str
    line: int
    severity: str
    kind: str
    value: str
    context: str


@dataclass
class ScanResult:
    scanned_files: int = 0
    skipped_files: int = 0
    findings: list = field(default_factory=list)

    def add(self, f: Finding):
        self.findings.append(f)

    def count_by_severity(self):
        c = {HIGH: 0, MEDIUM: 0, LOW: 0}
        for f in self.findings:
            c[f.severity] += 1
        return c


# ---------------------------------------------------------------- 检测器

def _ctx(line: str, start: int, end: int, width: int = 24) -> str:
    a = max(0, start - width)
    b = min(len(line), end + width)
    seg = line[a:b].replace("\n", " ").strip()
    return ("..." if a > 0 else "") + seg + ("..." if b < len(line) else "")


def detect_line(line: str, names: list, path: str, lineno: int, result: ScanResult):
    """对单行执行全部检测。"""
    raw_spans = []  # (start, end, severity, kind, value)

    # 身份证 18 位（带校验位验证，误报极低）
    for m in RE_ID18.finditer(line):
        if _id_card_ok(m.group(0)):
            raw_spans.append((m.start(), m.end(), HIGH, "身份证号(18位)", m.group(0)))

    # 身份证 15 位
    for m in RE_ID15.finditer(line):
        raw_spans.append((m.start(), m.end(), HIGH, "身份证号(15位)", m.group(0)))

    # 统一社会信用代码（排除已被身份证覆盖的区间）
    id_spans = {(s, e) for s, e, sev, _, _ in raw_spans if sev == HIGH}
    for m in RE_USCC.finditer(line):
        if any(not (m.end() <= s or m.start() >= e) for s, e in id_spans):
            continue
        if _uscc_ok(m.group(0)):
            raw_spans.append((m.start(), m.end(), HIGH, "统一社会信用代码", m.group(0)))

    # 银行卡（排除身份证区间 + 排除纯重复数字）
    # 双级策略：Luhn 通过 -> HIGH；未通过但首位落在常见卡 BIN -> LOW 提示人工复核。
    # 理由：门禁场景漏报代价远高于误报，不能因 Luhn 不通过就完全静默。
    for m in RE_BANK.finditer(line):
        v = m.group(0)
        # 仅排除"全部位同字符"（如 0000000000000000）；
        # 不能按字符种类数 <=2 排除，否则 4111111111111111 这类合法卡号会被误杀。
        if len(set(v)) <= 1:
            continue
        if any(not (m.end() <= s or m.start() >= e) for s, e in id_spans):
            continue
        if _luhn_ok(v):
            raw_spans.append((m.start(), m.end(), HIGH, "银行卡号", v))
        elif v[0] in "3456":
            raw_spans.append((m.start(), m.end(), LOW, "疑似卡号(未过Luhn)", v))

    # 手机号
    for m in RE_PHONE.finditer(line):
        raw_spans.append((m.start(), m.end(), MEDIUM, "手机号", m.group(0)))

    # 案号（优先匹配带括号的完整写法）
    bracket_spans = [m.span() for m in RE_CASE_BRACKET.finditer(line)]
    for m in RE_CASE_BRACKET.finditer(line):
        raw_spans.append((m.start(), m.end(), MEDIUM, "法院案号", m.group(0)))
    for m in RE_CASE_PLAIN.finditer(line):
        if any(not (m.end() <= s or m.start() >= e) for s, e in bracket_spans):
            continue
        raw_spans.append((m.start(), m.end(), MEDIUM, "法院案号(无括号)", m.group(0)))

    # 车牌
    for m in RE_PLATE.finditer(line):
        raw_spans.append((m.start(), m.end(), MEDIUM, "车牌号", m.group(0)))

    # 邮箱
    for m in RE_EMAIL.finditer(line):
        raw_spans.append((m.start(), m.end(), LOW, "邮箱地址", m.group(0)))

    # 当事人姓名（名单驱动，最高优先）
    for name in names:
        if not name:
            continue
        for m in re.finditer(re.escape(name), line):
            raw_spans.append((m.start(), m.end(), HIGH, "当事人姓名", m.group(0)))

    # 重叠消解：优先 HIGH，其次更长的匹配
    raw_spans.sort(key=lambda x: (SEVERITY_ORDER[x[2]], -(x[1] - x[0]), x[0]))
    taken = []
    for s, e, sev, kind, value in raw_spans:
        if any(not (e <= ts or s >= te) for ts, te in taken):
            continue
        taken.append((s, e))
        result.add(Finding(
            file=str(path), line=lineno, severity=sev,
            kind=kind, value=value, context=_ctx(line, s, e),
        ))


# ---------------------------------------------------------------- 文件遍历

def load_ignore_file(root: Path) -> list:
    p = root / ".desensitizeignore"
    if not p.exists():
        return []
    return [ln.strip() for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


def should_skip(path: Path, root: Path, ignore_patterns: list) -> bool:
    if path.name in SKIP_FILES:
        return True
    rel = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
    for pat in ignore_patterns:
        if rel == pat or rel.startswith(pat.rstrip("/") + "/") or Path(rel).match(pat):
            return True
    return False


def iter_files(target: Path, root: Path, ignore_patterns: list) -> Iterable[Path]:
    if target.is_file():
        yield target
        return
    for dirpath, dirnames, filenames in os.walk(target):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() not in SCAN_EXT:
                continue
            if should_skip(p, root, ignore_patterns):
                continue
            yield p


# ---------------------------------------------------------------- 主扫描

def scan(target: Path, names: list) -> ScanResult:
    root = target if target.is_dir() else target.parent
    ignore_patterns = load_ignore_file(root)
    result = ScanResult()

    for p in iter_files(target, root, ignore_patterns):
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            result.skipped_files += 1
            continue

        result.scanned_files += 1
        lines = text.splitlines()

        for i, line in enumerate(lines, 1):
            if IGNORE_MARK in line:
                continue
            if i > 1 and IGNORE_MARK in lines[i - 2]:
                continue
            detect_line(line, names, p, i, result)

    return result


# ---------------------------------------------------------------- 脱敏

def build_redactor(names: list):
    name_map = {}
    for idx, n in enumerate(names):
        if n:
            name_map[n] = "当事人%s" % chr(ord("A") + idx) if idx < 26 else "当事人%d" % (idx + 1)

    def redact_line(line: str) -> str:
        # 姓名优先（避免部分替换导致漏网）
        for n, token in sorted(name_map.items(), key=lambda x: -len(x[0])):
            line = line.replace(n, "[%s]" % token)

        def _sub(pattern, repl, s, need=None):
            out, last = [], 0
            for m in pattern.finditer(s):
                v = m.group(0)
                if need and not need(v):
                    continue
                out.append(s[last:m.start()])
                out.append(repl)
                last = m.end()
            out.append(s[last:])
            return "".join(out)

        line = _sub(RE_ID18, "[身份证已脱敏]", line, _id_card_ok)
        line = _sub(RE_ID15, "[身份证已脱敏]", line)
        line = _sub(RE_USCC, "[信用代码已脱敏]", line, _uscc_ok)
        line = _sub(RE_BANK, "[银行卡已脱敏]", line, _luhn_ok)
        line = _sub(RE_BANK, "[疑似卡号已脱敏]", line,
                    lambda v: v[0] in "3456" and len(set(v)) > 1)
        line = _sub(RE_PHONE, "[手机号已脱敏]", line)
        line = _sub(RE_CASE_BRACKET, "[案号已脱敏]", line)
        line = _sub(RE_CASE_PLAIN, "[案号已脱敏]", line)
        line = _sub(RE_PLATE, "[车牌已脱敏]", line)
        line = _sub(RE_EMAIL, "[邮箱已脱敏]", line)
        return line

    return redact_line


def do_redact(target: Path, names: list, out_dir: Path = None,
              in_place: bool = False, backup_dir: Path = None):
    root = target if target.is_dir() else target.parent
    ignore_patterns = load_ignore_file(root)
    redact = build_redactor(names)
    changed = []

    for p in iter_files(target, root, ignore_patterns):
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        new_lines = []
        hit = False
        for line in text.splitlines(keepends=True):
            if IGNORE_MARK in line:
                new_lines.append(line)
                continue
            nl = redact(line.rstrip("\n")) + ("\n" if line.endswith("\n") else "")
            if nl != line:
                hit = True
            new_lines.append(nl)

        if not hit:
            continue

        new_text = "".join(new_lines)

        if in_place:
            if backup_dir is None:
                print("[ERROR] --in-place 必须同时指定 --backup-dir（安全铁律：改前先备份）",
                      file=sys.stderr)
                return 3
            rel = p.relative_to(root) if p.is_relative_to(root) else Path(p.name)
            bak = backup_dir / rel
            bak.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, bak)
            p.write_text(new_text, encoding="utf-8")
            changed.append(str(p))
        else:
            rel = p.relative_to(root) if p.is_relative_to(root) else Path(p.name)
            dst = out_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(new_text, encoding="utf-8")
            changed.append(str(dst))

    mode = "原地脱敏（已备份至 %s）" % backup_dir if in_place else "输出脱敏副本至 %s" % out_dir
    print("\n[%s] 共处理 %d 个文件" % (mode, len(changed)))
    for c in changed[:20]:
        print("  - %s" % c)
    if len(changed) > 20:
        print("  ... 其余 %d 个省略" % (len(changed) - 20))
    return 0


# ---------------------------------------------------------------- 自检

SELF_TEST_CASES = [
    ("身份证18位", "当事人身份证号 522132197804302816，住贵州省。", HIGH, "身份证号"),
    ("身份证15位", "旧证号码 522132780430281 已失效。", HIGH, "身份证号"),
    ("手机号", "联系电话 13644392100 可接通。", MEDIUM, "手机号"),
    ("案号带括号", "本院受理的（2026）黔0330民初6658号一案。", MEDIUM, "法院案号"),
    ("案号无括号", "参见 2026黔0330民初6658号民事判决。", MEDIUM, "法院案号(无括号)"),
    ("银行卡", "收款账户 4111111111111111 请核对。", HIGH, "银行卡号"),
    ("疑似卡号", "收款账户 6222021234567890123 请核对。", LOW, "疑似卡号"),
    ("车牌", "事故车辆贵C09782D由南向北行驶。", MEDIUM, "车牌号"),
    ("邮箱", "联系方式 laoqiang@example.com 长期有效。", LOW, "邮箱地址"),
]


def self_test() -> int:
    print("=== desensitize_check.py 自检 v%s ===" % VERSION)
    print("说明：验证各检测规则能否命中构造样本（样本为随机生成，非真实数据）\n")
    ok = fail = 0
    for name, sample, want_sev, want_kind in SELF_TEST_CASES:
        r = ScanResult()
        detect_line(sample, [], Path("<self-test>"), 1, r)
        matched = [f for f in r.findings if f.severity == want_sev and f.kind.startswith(want_kind)]
        if matched:
            print("  [PASS] %-12s -> %-8s %s" % (name, matched[0].severity, matched[0].value))
            ok += 1
        else:
            got = ", ".join("%s/%s" % (f.severity, f.kind) for f in r.findings) or "无命中"
            print("  [FAIL] %-12s -> 期望 %s/%s，实际：%s" % (name, want_sev, want_kind, got))
            fail += 1

    print("\n=== 校验位算法验证 ===")
    print("  身份证 MOD11-2 正确样本通过: %s" % _id_card_ok("522132197804302816"))
    print("  身份证 篡改样本被拒:         %s" % (not _id_card_ok("522132197804302817")))
    print("  Luhn 正确样本通过:           %s" % _luhn_ok("4111111111111111"))
    print("  Luhn 错误样本被拒:           %s" % (not _luhn_ok("6222021234567890123")))
    print("  未过Luhn但符合卡BIN -> LOW:  %s" % ("6222021234567890123"[0] in "3456"))

    print("\n结果：%d 通过 / %d 失败" % (ok, fail))
    return 0 if fail == 0 else 1


# ---------------------------------------------------------------- 报告

def print_report(result: ScanResult, target: Path, strict: bool) -> int:
    c = result.count_by_severity()
    print("\n" + "=" * 62)
    print("LawTwin 脱敏门禁 v%s  扫描目标：%s" % (VERSION, target))
    print("=" * 62)
    print("扫描文件 %d 个，跳过 %d 个" % (result.scanned_files, result.skipped_files))
    print("命中：HIGH %d / MEDIUM %d / LOW %d" % (c[HIGH], c[MEDIUM], c[LOW]))

    if not result.findings:
        print("\n[PASS] 未发现敏感信息，可以提交。")
        return 0

    print("\n" + "-" * 62)
    by_file = {}
    for f in result.findings:
        by_file.setdefault(f.file, []).append(f)

    for path, items in sorted(by_file.items()):
        print("\n%s" % path)
        for f in sorted(items, key=lambda x: (x.line, SEVERITY_ORDER[x.severity])):
            print("  L%-5d [%s] %s" % (f.line, f.severity, f.kind))
            print("         值：%s" % f.value)
            print("         上下文：%s" % f.context)

    print("\n" + "-" * 62)
    blocking = c[HIGH] + c[MEDIUM]
    if strict:
        blocking += c[LOW]

    if blocking:
        print("[BLOCK] 发现 %d 项需处置，禁止提交。" % blocking)
        print("        提示：确属样例可在该行或上一行加  %s  豁免" % IGNORE_MARK)
        return 1
    print("[WARN] 仅发现 LOW 级提示项，非严格模式下放行。")
    return 0


# ---------------------------------------------------------------- CLI

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="LawTwin 开源脱敏门禁 —— 阶段 0 硬前置工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("target", nargs="?", help="待扫描的文件或目录")
    ap.add_argument("--names-file", help="当事人姓名名单（每行一个，本地私有，切勿入库）")
    ap.add_argument("--strict", action="store_true", help="LOW 级也阻断（pre-commit 推荐）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    ap.add_argument("--redact", action="store_true", help="执行脱敏（默认仅报告）")
    ap.add_argument("--out-dir", help="脱敏副本输出目录（与 --redact 配合）")
    ap.add_argument("--in-place", action="store_true", help="原地脱敏（强制要求 --backup-dir）")
    ap.add_argument("--backup-dir", help="原地脱敏前的备份目录")
    ap.add_argument("--self-test", action="store_true", help="运行内置自检")
    ap.add_argument("--version", action="version", version="desensitize_check %s" % VERSION)

    args = ap.parse_args(argv)

    if args.self_test:
        return self_test()

    if not args.target:
        ap.print_help()
        return 3

    target = Path(args.target).expanduser().resolve()
    if not target.exists():
        print("[ERROR] 路径不存在：%s" % target, file=sys.stderr)
        return 3

    # 未显式指定时回落到默认名单，防止漏检。
    # 必须跳过 # 注释行：否则 README 式的说明行会被整体当作"姓名"去匹配。
    names = []
    nf = Path(args.names_file).expanduser() if args.names_file \
        else Path(NAMES_FILE_DEFAULT).expanduser()
    if nf.exists():
        names = [ln.strip() for ln in nf.read_text(encoding="utf-8").splitlines()
                 if ln.strip() and not ln.strip().startswith("#")]
        # 必须走 stderr：--json 模式下 stdout 只允许输出 JSON，否则 CI 解析会崩
        print("[INFO] 已载入脱敏名单 %d 条（%s）" % (len(names), nf), file=sys.stderr)
    elif args.names_file:
        # 显式指定却读不到：多半是路径写错，必须报错，不能静默放行
        print("[ERROR] 指定的名单文件不存在：%s" % nf, file=sys.stderr)
        return 3
    else:
        print("[WARN] 默认名单不存在，跳过姓名检测：%s" % nf, file=sys.stderr)

    if args.redact:
        if args.in_place:
            if not args.backup_dir:
                print("[ERROR] --in-place 必须同时指定 --backup-dir", file=sys.stderr)
                return 3
            return do_redact(target, names, in_place=True,
                             backup_dir=Path(args.backup_dir).expanduser().resolve())
        if not args.out_dir:
            print("[ERROR] --redact 需指定 --out-dir（或改用 --in-place + --backup-dir）",
                  file=sys.stderr)
            return 3
        return do_redact(target, names, out_dir=Path(args.out_dir).expanduser().resolve())

    result = scan(target, names)

    if args.json:
        print(json.dumps({
            "version": VERSION,
            "target": str(target),
            "scanned_files": result.scanned_files,
            "skipped_files": result.skipped_files,
            "counts": result.count_by_severity(),
            "findings": [asdict(f) for f in result.findings],
        }, ensure_ascii=False, indent=2))
        c = result.count_by_severity()
        blocking = c[HIGH] + c[MEDIUM] + (c[LOW] if args.strict else 0)
        return 1 if blocking else 0

    return print_report(result, target, args.strict)


if __name__ == "__main__":
    sys.exit(main())
