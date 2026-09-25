#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""遗留项修复（immediate）：5 张 LN 指针 canonical 重写 + 1 张 CF 重编号 + 2 张 CF 孤儿隔离
铁律：先备份命中文件 → 再改 → 写报告。全部可回滚。
"""
import os, re, shutil, datetime

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
TS = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
RID_RE = re.compile(r"^rule_id:\s*(\S+)", re.M)
SKIP = [".backup", ".trash", "_quarantine", ".backup_link", "__pycache__"]

# ---------- 双维度取空闲号 ----------
def get_free_rid(domain):
    maxn = 0
    for dp, dn, fn in os.walk(os.path.join(ROOT, "06-沉淀")):
        if any(x in dp for x in SKIP):
            continue
        for f in fn:
            if not f.endswith(".md"):
                continue
            m = re.match(rf"R-{domain}-(\d+)\.md$", f)
            if m:
                maxn = max(maxn, int(m.group(1)))
            h = open(os.path.join(dp, f), encoding="utf-8", errors="ignore").read(2500)
            mr = RID_RE.search(h)
            if mr and re.match(rf"^R-{domain}-(\d+)$", mr.group(1)):
                maxn = max(maxn, int(re.search(r"(\d+)$", mr.group(1)).group(1)))
    return f"R-{domain}-{maxn+1:03d}"

# ---------- 清理 malformed rule_id 块并写入新号 + alias ----------
def set_rid_clean(p, new, old):
    txt = open(p, encoding="utf-8", errors="ignore").read()
    # 去掉原有（可能 malformed 的）rule_id 块：rule_id: 后跟可选换行+缩进列表
    txt2 = re.sub(r"^rule_id:(?:\s*\n(?:\s*-.*\n?)*)?",
                  f"rule_id: {new}\naliases:\n  - {old}\n", txt, count=1, flags=re.M)
    open(p, "w", encoding="utf-8").write(txt2)
    # 校验：恰好一个 rule_id 且等于 new
    rid = RID_RE.search(open(p, encoding="utf-8", errors="ignore").read(2500))
    assert rid and rid.group(1) == new, f"rule_id 写入校验失败: {p}"
    return new

def backup_files(files, tag):
    bak = f"/tmp/leftover_fix_{TS}_{tag}"
    os.makedirs(bak, exist_ok=True)
    for p in files:
        rel = os.path.relpath(p, ROOT)
        dst = os.path.join(bak, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(p, dst)
    return bak

def main():
    print(f"[时间] {TS}")
    # ===== 受影响文件清单 =====
    cf_lib = os.path.join(ROOT, "06-沉淀", "慈善合规域库")
    cf076 = os.path.join(cf_lib, "R-CF-076-慈善合规数值红线速查-LTI映射桥.md")
    cf052 = os.path.join(cf_lib, "R-CF-052-税前扣除资格双比例红线公益支出公募70非公募8管理费10-12.md")
    cf053 = os.path.join(cf_lib, "R-CF-053-基金会互捐核心真实最终受益人执行方公开遴选募捐资金非自有资金.md")

    pdir = os.path.join(ROOT, "02-提炼", "经验卡片", "跨案模式识别")
    ln_map = {  # 指针文件名(不含.md) : 正确 canonical 目标
        "R-LN-046_同案同被告双轨并行模式识别_提炼索引": "06-沉淀/裁判规则库/学习笔记/R-LN-097_同案同被告双轨并行模式识别.md",
        "R-LN-047_实际买受人穿透模式识别_提炼索引": "06-沉淀/裁判规则库/学习笔记/R-LN-098_实际买受人穿透模式识别.md",
        "R-LN-048_原告主体瑕疵程序战模式识别_提炼索引": "06-沉淀/裁判规则库/学习笔记/R-LN-099_原告主体瑕疵程序战模式识别.md",
        "R-LN-049_关联案撤诉应对模式识别_提炼索引": "06-沉淀/裁判规则库/学习笔记/R-LN-100_关联案撤诉应对模式识别.md",
        "R-LN-050_跨案录音证据复用模式识别_提炼索引": "06-沉淀/裁判规则库/学习笔记/R-LN-101_跨案录音证据复用模式识别.md",
    }
    ln_files = [os.path.join(pdir, f + ".md") for f in ln_map]

    # ===== 备份 =====
    bak_cf = backup_files([cf076, cf052, cf053], "cf")
    bak_ln = backup_files(ln_files, "ln")
    print(f"[备份] CF: {bak_cf}")
    print(f"[备份] LN: {bak_ln}")

    # ===== ① CF-076 重编号（distinct 卡，补合法号）=====
    new_cf = get_free_rid("CF")
    set_rid_clean(cf076, new_cf, "R-CF-076")
    print(f"[CF重编号] R-CF-076-数值红线 → {new_cf} (alias R-CF-076)")

    # ===== ② CF-052 / CF-053 孤儿隔离（malformed 副本，canonical R-CF-115/116 已存在）=====
    trash = os.path.join(cf_lib, ".trash_cf")
    os.makedirs(trash, exist_ok=True)
    for p in [cf052, cf053]:
        shutil.move(p, os.path.join(trash, os.path.basename(p)))
        print(f"[CF隔离] {os.path.basename(p)} → .trash_cf (canonical 已为 R-CF-115/116)")

    # ===== ③ 5 张 LN 指针 canonical 重写 =====
    cnt = 0
    for f, target in ln_map.items():
        p = os.path.join(pdir, f + ".md")
        txt = open(p, encoding="utf-8", errors="ignore").read()
        txt2 = re.sub(r"^canonical:\s*.*$", f"canonical: {target}", txt, flags=re.M)
        if txt2 != txt:
            open(p, "w", encoding="utf-8").write(txt2)
            cnt += 1
            print(f"[LN修复] {f}.md → {target}")
    print(f"[LN修复] 完成 {cnt} 张（R-LN-045 目标本就存在，未动）")

    # ===== 报告 =====
    rep = os.path.join(ROOT, "_outputs", f"遗留项修复报告-{TS}.md")
    L = ["# 遗留项修复报告", "", f"> {TS} | 备份 {bak_cf} / {bak_ln}", "",
         "## 处理明细",
         f"1. CF-076-数值红线-LTI映射桥：重编号 → **{new_cf}**（alias R-CF-076，文件名不动）",
         "2. CF-052-税前扣除 / CF-053-基金会互捐：malformed 孤儿，已隔离至 慈善合规域库/.trash_cf（canonical R-CF-115/R-CF-116 已存在，内容已保留）",
         "3. LN 指针 5 张（046~050）canonical 重写至真实主卡 R-LN-097~101_*.md（学习笔记，下划线命名）",
         "4. R-LN-045 指针 canonical 目标本就存在，未改动",
         "", "## 回滚", f"- CF：恢复 {bak_cf} 至 06-沉淀/慈善合规域库",
         f"- LN：恢复 {bak_ln} 至 02-提炼/经验卡片/跨案模式识别",
         "- 隔离卡：从 慈善合规域库/.trash_cf 移回"]
    open(rep, "w", encoding="utf-8").write("\n".join(L))
    print(f"[报告] {rep}")

if __name__ == "__main__":
    main()
