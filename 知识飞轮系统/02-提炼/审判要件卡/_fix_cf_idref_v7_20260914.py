#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合规审查卡「规划号段 → 落地号段」死链修复器  v7 / 2026-09-14

🔴 病根（坑 8 新形态：规划号段 ≠ 落地号段）：
   合规审查卡建卡流水线在规划阶段分配 R-CF-179~188，经验卡/案例摘要/连接枢纽/
   入库索引按**规划号**写了引用；而卡片实际落盘时取的是 **R-CF-143~152**
   （见 `02-提炼/合规审查卡/合规审查卡-入库索引-2026-09-13-P1.md`）。
   → 10 个编号**从未存在**，产生 10 条真死链 / 约 70 处引用。

🔴 与坑 8 的区别：坑 8 是「号段被并发抢占」，本例是「号段在落地时被整体改号，
   而引用方仍按规划号写链」—— 卡在，号不对，比被抢占更隐蔽（卡确实存在，只是号不同）。

映射依据（人工逐条核对，1:1 顺序对应，主题完全一致）：
   入库索引「一、本批 10 张卡」表 vs 死链名，逐条语义对齐后确认。

用法：python _fix_cf_idref_v7_20260914.py [--apply]
"""
import os, re, sys, shutil, datetime, glob

ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
APPLY = "--apply" in sys.argv
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
BK = f"/tmp/存量卡巡检CF编号修复_{STAMP}"

# 规划号 → 落地号（人工复核通过，顺序 1:1）
MAP = {
    "R-CF-179-捐赠票据与捐赠人服务合规审查卡":     "R-CF-143-公益事业捐赠票据开具与交付合规审查卡",
    "R-CF-180-项目发起方资质与立项合规审查卡":      "R-CF-144-项目立项与发起方资质合规审查卡",
    "R-CF-181-项目运营全生命周期合规审查卡":        "R-CF-145-项目全生命周期管理合规审查卡",
    "R-CF-182-进展反馈与财务披露合规审查卡":        "R-CF-146-项目进展反馈合规审查卡",
    "R-CF-183-民非会计科目设置合规审查卡":          "R-CF-147-民间非营利组织会计制度科目设置与核算合规审查卡",
    "R-CF-184-凭证编制与审核内控合规审查卡":        "R-CF-148-会计凭证编制与内部控制合规审查卡",
    "R-CF-185-财务会计报告披露合规审查卡":          "R-CF-149-财务报表编制与年度披露合规审查卡",
    "R-CF-186-商户号捐赠资金核算合规审查卡":        "R-CF-150-平台商户号捐赠资金管理与核算合规审查卡",
    "R-CF-187-受益人隐私与影像授权合规审查卡":      "R-CF-151-受益人与捐赠人个人信息保护合规审查卡",
    "R-CF-188-月捐管理合规审查卡":                  "R-CF-152-月捐与持续捐赠合规审查卡",
}


def main():
    # ① 目标存在性校验（坑 34）
    bn = {os.path.splitext(os.path.basename(p))[0]
          for p in glob.glob(os.path.join(ROOT, "**/*.md"), recursive=True)}
    miss = [v for v in MAP.values() if v not in bn]
    if miss:
        print("🔴 目标不存在，终止：", miss)
        return
    print(f"目标存在性校验：{len(MAP)}/{len(MAP)} 全部在库 ✅")

    # ② 一次性正则（坑 37：长名优先，避免二次替换）
    pat = re.compile("|".join(sorted((re.escape(k) for k in MAP), key=len, reverse=True)))

    files = []
    for p in ("06-沉淀/**/*.md", "02-提炼/**/*.md", "03-连接/**/*.md", "05-调用/**/*.md"):
        files += glob.glob(os.path.join(ROOT, p), recursive=True)
    files = [f for f in files if "_隔离_" not in f and "/.backup" not in f]

    if APPLY:
        os.makedirs(BK, exist_ok=True)

    total, touched = 0, []
    for p in files:
        try:
            t = open(p, encoding="utf-8").read()
        except Exception:
            continue
        if not pat.search(t):
            continue
        n = len(pat.findall(t))
        nt = pat.sub(lambda m: MAP[m.group(0)], t)
        total += n
        touched.append((p, n))
        if APPLY:
            shutil.copy2(p, os.path.join(BK, os.path.relpath(p, ROOT).replace("/", "__")))
            open(p, "w", encoding="utf-8").write(nt)

    print(f'{"[APPLY]" if APPLY else "[DRY-RUN]"} 映射 {len(MAP)} 条 | 命中文件 {len(touched)} | 替换 {total} 处')
    for p, n in sorted(touched, key=lambda x: -x[1]):
        print(f"   {n:3d} 处  {os.path.relpath(p, ROOT)}")
    if APPLY and touched:
        print(f"\n备份：{BK}（{len(os.listdir(BK))} 份）")


if __name__ == "__main__":
    main()
