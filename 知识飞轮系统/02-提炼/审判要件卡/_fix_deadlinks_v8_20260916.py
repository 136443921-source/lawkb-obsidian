#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_fix_deadlinks_v8_20260916.py  v1.0
存量卡质量巡检第 6 轮 · 死链修复（严格白名单版）

设计原则（本轮实证教训）：
  🔴 坑 63 / 坑 45：「同编号唯一候选」≠ 语义同一。
     实证：R-LN-022 引用要「人格否认」，同编号唯一卡实为「公司对外担保」（历史同号冲突，
     带描述卡只存在于 .backup）；R-CF-052 引用要「税前扣除双比例」，实为「定向捐赠」；
     R-HT-250 引用要「网络推广服务合同」，实为「买卖合同价款支付」。
     → 这些若自动补全即制造「沉默错链」，比死链更危险。
  ✅ 本轮白名单只收两类「首尾增删」型（坑 45 判据第三条）：
     A. 引用名 ⊂ 目标名，差异仅为已知后缀追加（`_提炼索引`）
     B. 引用为裸编号 `R-XX-NNN`，目标为同编号唯一全名（编号语义唯一确定）
     以及 1 条仅插入「的」的极小差异。

安全：cp -n 备份到 /tmp；dry-run 先行；RECENT_SEC=1800 并发保护（坑 62）；
      判定顺序＝先查 inner 是否已在门禁基名集中，命中即不动（坑 34）。
"""
import importlib.util
import os
import re
import shutil
import sys
import time

# 🔴 坑 52：APPLY 必须早于任何 sys.argv 改写
APPLY = "--apply" in sys.argv
_ARGV_BACKUP = list(sys.argv)

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
GATE = os.path.join(ROOT, "02-提炼/审判要件卡/_check_deadlinks.py")
BACKUP = f"/tmp/存量卡巡检死链修复_20260916-{time.strftime('%H%M%S')}"
RECENT_SEC = 1800   # 坑 62：并发写入保护

# 严格白名单：旧引用名 -> 目标真实基名（已 ls 核实物理存在）
WHITELIST = {
    # A 类：引用名 + 已知后缀
    "R-LN-046_同案同被告双轨并行模式识别": "R-LN-046_同案同被告双轨并行模式识别_提炼索引",
    "R-LN-047_实际买受人穿透模式识别": "R-LN-047_实际买受人穿透模式识别_提炼索引",
    "R-LN-048_原告主体瑕疵程序战模式识别": "R-LN-048_原告主体瑕疵程序战模式识别_提炼索引",
    "R-LN-049_关联案撤诉应对模式识别": "R-LN-049_关联案撤诉应对模式识别_提炼索引",
    "R-LN-050_跨案录音证据复用模式识别": "R-LN-050_跨案录音证据复用模式识别_提炼索引",
    # B 类：裸编号补全
    "R-PR-178": "R-PR-178-诉讼代理授权委托书形式要件与委托人可识别性",
    "R-PR-179": "R-PR-179-授权瑕疵的法律效果层级权限限缩与起诉无效",
    "R-PR-180": "R-PR-180-无权代理起诉的追认规则与催告要件",
    "R-PR-181": "R-PR-181-借用他人名义起诉与起诉条件的程序层含义",
    "R-PR-182": "R-PR-182-程序战中的自认边界与反向自认债务防范",
    # 极小差异：仅插入「的」
    "R-PI-240-医疗事故罪严重不负责任的认定与鉴定意见证据地位":
        "R-PI-240-医疗事故罪严重不负责任的认定与鉴定意见的证据地位",
}

WIKI = re.compile(r"\[\[([^\[\]]+?)\]\]")


def split_fm(text):
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end < 0:
        return None, text
    return text[:end + 4], text[end + 4:]


def main():
    import yaml
    spec = importlib.util.spec_from_file_location("gate", GATE)
    gate = importlib.util.module_from_spec(spec)
    sys.argv = [GATE, "--help"]          # 防门禁 main 误触发
    spec.loader.exec_module(gate)
    sys.argv = _ARGV_BACKUP              # 用完立即还原

    names = gate.build_basename_set()
    print(f"门禁基名集：{len(names)}（坑 34：与门禁完全同款口径）")

    # 白名单目标核验：必须都在门禁集里
    bad = [k for k, v in WHITELIST.items() if v not in names]
    if bad:
        print(f"🔴 白名单目标不在门禁集，拒绝执行：{bad}")
        return 1

    now = time.time()
    total_patch, total_file, skipped_recent = 0, 0, []

    for path in gate.md_files():
        rel = os.path.relpath(path, ROOT)
        try:
            mt = os.path.getmtime(path)
        except OSError:
            continue
        if now - mt < RECENT_SEC:
            # 并发写入中的文件先跳过，但仍要处理其引用
            skipped_recent.append(rel)

        try:
            text = open(path, encoding="utf-8").read()
        except Exception:
            continue

        fm, body = split_fm(text)
        orig = text
        counter = [0]

        # ---- 正文 wikilink ----
        def repl(m):
            raw = m.group(1)
            inner = raw.split("|")[0].split("#")[0]
            inner = inner.split("/")[-1]
            inner_n = gate.normalize(inner)
            if inner_n in names:
                return m.group(0)              # 坑 34：命中即不动
            if inner in WHITELIST:
                tgt = WHITELIST[inner]
                counter[0] += 1
                return "[[" + raw.replace(inner, tgt, 1) + "]]"
            return m.group(0)

        new_body = WIKI.sub(repl, body)

        # ---- frontmatter related_links 裸名（坑：84% 死链藏在 fm）----
        new_fm = fm
        if fm:
            flines = fm.split("\n")
            for i, ln in enumerate(flines):
                m2 = re.match(r"^(\s*-\s*)(.*?)(\s*)$", ln)
                if not m2:
                    continue
                val = m2.group(2).strip().strip('"').strip("'")
                if val in names:
                    continue                    # 坑 34：命中即不动
                if val in WHITELIST:
                    flines[i] = f"{m2.group(1)}{WHITELIST[val]}{m2.group(3)}"
                    counter[0] += 1
            new_fm = "\n".join(flines)

        n_patch = counter[0]
        new_text = (new_fm + new_body) if fm is not None else new_body
        if n_patch == 0 or new_text == orig:
            continue

        # 校验：写入后必须仍能被 yaml 解析
        if fm is not None:
            try:
                yaml.safe_load(new_fm.strip("-").strip("\n"))
            except Exception as e:
                print(f"  [FAIL] YAML 校验失败，跳过 {rel}: {str(e)[:60]}")
                continue

        total_patch += n_patch
        total_file += 1
        print(f"  [PATCH {n_patch}] {rel}")

        if APPLY:
            os.makedirs(BACKUP, exist_ok=True)
            dst = os.path.join(BACKUP, rel.replace("/", "__"))
            shutil.copy2(path, dst)     # 同时存扁平版；basename 版亦存
            os.makedirs(os.path.dirname(dst + ".d"), exist_ok=True) if False else None
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_text)

    print(f"\n({'APPLY' if APPLY else 'DRY-RUN'}) 待修 {total_patch} 处 / {total_file} 文件")
    if skipped_recent:
        print(f"并发保护跳过（mtime < 30min）{len(skipped_recent)} 文件（仍参与扫描）")
    if APPLY:
        print(f"备份：{BACKUP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
