#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
governor_maturity.py — 法条银行行长成熟度客观追踪（对标 blue_team_maturity.py）

刷新 PROJ 备忘录 MATURITY / TRAINLOG 区块；计算 D1-D6 六维（100 制，M1-M5）。
客观可回归：每次运行从法条银行实库 + PROJ 备忘录重新计算，不靠手工填分。

用法：
  python3 governor_maturity.py --dry-run    # 只打印，不写回
  python3 governor_maturity.py --refresh    # 重算并写回 PROJ 备忘录 MATURITY/TRAINLOG

计分（权重合计 100）：
  D1 治理场次      20  (真实取证场次数，每场 4 分封顶 20；目标 5 场满)
  D2 弹药可溯率    15  (RULE-038 规范 / SOP-AST-08 / 覆盖台账 三源齐备)
  D3 身份留痕率    15  (persona+PROJ 双建 10 + 有真实 TRAINLOG 留痕 5)
  D4 域覆盖        20  (11 域架构 5 + 合规域数/11×15)
  D5 病灶修复率    20  (schema 合规率 = 符合 RULE-038 两型卡数/总卡数 × 20，直接对应 F1)
  D6 接驳闭环      10  (SOP-AST-07 存在 5 + 库内已有合规卡 5)
"""
import os, re, io, sys, datetime, argparse, shutil

HUB = "/Users/chenyouqiang/Documents/LawKB"
BANK = os.path.join(HUB, "法条银行")
PROJ = os.path.join(BANK, "银行治理层", "法条银行行长心智模型与训练备忘录.md")
ARCHIVE = os.path.join(BANK, "_archive")
WEEKLY = os.path.join(BANK, "法律资讯周报")
RULE038_SPEC = os.path.join(BANK, "银行治理层", "_Schema规范_v1.0.md")
SOP_AST_08 = os.path.join(HUB, "_AI-Memory-Hub/09-OPC/09-2部门治理/数字资产中台/SOP",
                          "SOP-AST-08_法条银行科室CRUD治理.md")
COVER = os.path.join(BANK, "银行治理层", "_本地法条银行_覆盖台账.md")
PERSONA = os.path.join(BANK, "银行治理层", "法条银行行长_persona_v1.md")
SOP_AST_07 = os.path.join(HUB, "_AI-Memory-Hub/09-OPC/09-2部门治理/数字资产中台/SOP",
                          "SOP-AST-07_知识飞轮卡库接线.md")

A_REQ = ["type", "doc_no", "sxx", "source_verify", "statute_text_pending"]
B_REQ = ["type", "source", "status"]
STD_ENUM = {"现行有效", "已废止", "即将生效", "待核验"}


def extract_fm(path):
    try:
        lines = io.open(path, encoding="utf-8").read().splitlines()
    except Exception:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    return None if end is None else lines[1:end]


def parse_fm(fm):
    f = {}
    for ln in fm:
        m = re.match(r'^([\u4e00-\u9fffA-Za-z_]+)\s*:\s*(.*)$', ln)
        if m:
            f[m.group(1)] = m.group(2).strip()
    return f


def scan_bank():
    total = 0
    compliant = 0
    domains = set()
    for d in sorted(os.listdir(BANK)):
        dp = os.path.join(BANK, d)
        if not os.path.isdir(dp) or dp in (ARCHIVE, WEEKLY):
            continue
        if d == "银行治理层":
            continue  # 治理文档（memo/persona/_Schema规范/搭建方案/覆盖台账）非 statute 卡，不计入库分母
        for fn in sorted(os.listdir(dp)):
            if not fn.endswith(".md"):
                continue
            fm = extract_fm(os.path.join(dp, fn))
            if fm is None:
                continue
            total += 1
            fld = parse_fm(fm)
            t = fld.get("type", "")
            # D5 客观标准：schema 正确【且】双证一致，才计合规（避免“字段齐全但待核填”虚高）
            if t == "statute" and fld.get("sxx") in STD_ENUM and all(k in fld for k in A_REQ) \
               and str(fld.get("source_verify", "")).startswith("双证一致"):
                compliant += 1
                domains.add(d)
            elif t in ("digest", "case") and all(k in fld for k in B_REQ):
                compliant += 1
                domains.add(d)
    return total, compliant, domains


def count_trainlog(text):
    m = re.search(r"<!-- TRAINLOG_START -->(.*?)<!-- TRAINLOG_END -->", text, re.DOTALL)
    if not m:
        return 0
    return len(re.findall(r"^\| \d{4}-\d{2}-\d{2}", m.group(1), re.MULTILINE))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    if not args.dry_run and not args.refresh:
        args.dry_run = True

    total, compliant, domains = scan_bank()
    proj_text = io.open(PROJ, encoding="utf-8").read() if os.path.exists(PROJ) else ""
    train = count_trainlog(proj_text)

    # D1 治理场次
    d1 = min(20.0, train * 4.0)
    # D2 弹药可溯
    d2 = 15.0 if (os.path.exists(RULE038_SPEC) and os.path.exists(SOP_AST_08)
                  and os.path.exists(COVER)) else 0.0
    # D3 身份留痕
    d3 = (10.0 if (os.path.exists(PERSONA) and os.path.exists(PROJ)) else 0.0) \
        + (5.0 if train >= 1 else 0.0)
    # D4 域覆盖
    d4 = 5.0 + (len(domains) / 11.0) * 15.0 if total else 5.0
    # D5 病灶修复率（schema 合规率 = F1 客观进度）
    rate = (compliant / total) if total else 0.0
    d5 = rate * 20.0
    # D6 接驳闭环
    d6 = (5.0 if os.path.exists(SOP_AST_07) else 0.0) + (5.0 if compliant >= 1 else 0.0)

    score = int(round(d1 + d2 + d3 + d4 + d5 + d6))
    level = ("M1 萌芽" if score < 50 else "M2 成型" if score < 65 else "M3 熟练"
             if score < 80 else "M4 精熟" if score < 92 else "M5 教练级")
    pct = score
    bar = "▓" * (score // 5) + "░" * (20 - score // 5)

    # WF-046 四判据：职能可辨识/边界可追溯(persona+PROJ) + Schema可落(RULE-038) + 与起草方接口(SOP-AST-07) + 真实取证(>=1)
    wf046 = (os.path.exists(PERSONA) and os.path.exists(PROJ)
             and os.path.exists(RULE038_SPEC) and os.path.exists(SOP_AST_07)
             and train >= 1)
    suggest = "ACTIVE（WF-046 四判据满足，建议转正）" if wf046 else "DRAFT（维持）"

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    block = f"""<!-- MATURITY_START -->
> _本区块由 `governor_maturity.py` 自动刷新（{now}）；手工修改会被覆盖。_
> 数据源：法条银行实库扫描（{total} 卡，合规 {compliant}）+ PROJ 备忘录 TRAINLOG（{train} 场）

### 当前成熟度（100 制）：**{level}** · **{score} / 100**

`{bar}` {pct}%

> 客观回归：schema 合规率 {compliant}/{total} = {rate*100:.1f}%（对应 F1 真实修复进度）；真实治理取证 {train} 场。

| 维度 | 得分 | 实测 |
|---|---|---|
| D1 治理场次 | **{d1:.1f}** / 20 | {train} 场真实取证（每场 4 分，目标 5 场满） |
| D2 弹药可溯率 | **{d2:.1f}** / 15 | RULE-038/SOP-AST-08/覆盖台账 三源{'齐备' if d2 else '缺'} |
| D3 身份留痕率 | **{d3:.1f}** / 15 | persona+PROJ 双建 {10 if os.path.exists(PERSONA) and os.path.exists(PROJ) else 0} + 留痕 {5 if train>=1 else 0} |
| D4 域覆盖 | **{d4:.1f}** / 20 | 11 域架构 + 合规域 {len(domains)}/11 |
| D5 病灶修复率 | **{d5:.1f}** / 20 | schema 合规率 {rate*100:.1f}%（F1 客观进度） |
| D6 接驳闭环 | **{d6:.1f}** / 10 | SOP-AST-07 {'存在' if os.path.exists(SOP_AST_07) else '缺'} + 合规卡 {compliant} |

**等级阶梯**：M1 萌芽 → M2 成型 → M3 熟练 → M4 精熟 → M5 教练级
**WF-046 四判据**：{'✅ 满足' if wf046 else '⏳ 待满足'} → 状态建议 **{suggest}**
<!-- MATURITY_END -->"""

    if args.refresh:
        new = re.sub(r"<!-- MATURITY_START -->.*?<!-- MATURITY_END -->", block,
                     proj_text, flags=re.DOTALL)
        if new == proj_text:
            print("ℹ️ PROJ MATURITY 区块已是最新，无需改写")
        else:
            io.open(PROJ, "w", encoding="utf-8").write(new)
            # frontmatter 同步
            new_fm = re.sub(r"maturity_score:.*", f"maturity_score: {score}/100", new)
            new_fm = re.sub(r"maturity_level:.*", f"maturity_level: {level}", new_fm)
            if wf046:
                new_fm = re.sub(r"status: DRAFT.*", "status: ACTIVE", new_fm)
            if new_fm != new:
                io.open(PROJ, "w", encoding="utf-8").write(new_fm)
            print(f"✅ 已刷新 PROJ 备忘录：{level} · {score}/100 · 状态建议 {suggest}")
            if wf046:
                print("⚠️ 状态变更 DRAFT→ACTIVE（WF-046 四判据满足，已落 PROJ frontmatter）")
        # 双目录同步：刷新后无条件以 PROJ 工作态最新版覆盖中枢主存副本。
        # 修复缺陷：原同步逻辑嵌套在「MATURITY 块变化」分支内，导致 PROJ 其他变动（frontmatter/章节）时中枢滞后。
        # 现改为每次 --refresh 均同步，落实「系统有变动，文档随之更新」。防覆盖先备份至 /tmp/opc_hub_sync_<ts>。
        _ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        MID = os.path.join(HUB, "_AI-Memory-Hub/09-OPC/09-2部门治理/数字资产中台",
                           "法条银行行长心智模型与训练备忘录.md")
        try:
            if os.path.exists(MID):
                _bk = f"/tmp/opc_hub_sync_{_ts}"; os.makedirs(_bk, exist_ok=True)
                shutil.copy2(MID, os.path.join(_bk, "行长备忘录_中枢旧版.md"))
            shutil.copy2(PROJ, MID)
            print(f"📡 已同步共享中枢主存：{MID}")
        except Exception as _e:
            print(f"⚠️ 中枢同步失败（不影响本地刷新）：{_e}")
    else:
        print(block)
        print("\n📝 DRY-RUN：未写回。确认后加 --refresh。")


if __name__ == "__main__":
    main()
