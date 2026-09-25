#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fix_fatiao_schema.py — 法条银行 schema 治理双模式脚本

========================================================================
模式 A：G2 schema 整治（对标 fix_updated_format.py 范式）
------------------------------------------------------------------------
把法条银行旧 schema（version_* 系列 + Obsidian 渲染字段）收敛为
RULE-038 两型 A 型权威法规卡。
策略：「重建干净 A 型 frontmatter」——丢弃 Obsidian 渲染字段，保留
title / superseded_by / comments / aliases / source 原值，补齐必需字段。
--dry-run 列出计划；--apply 执行（改前自动备份 /tmp，幂等可反复跑）；
--file <名> 单卡试点。

模式 B：G1 联网双证核填（--g1 开关）
------------------------------------------------------------------------
针对「需要联网核填」的卡（sxx:待核验/待远程核验、version_mismatch、
source_verify 非「双证一致」），由 agent 先用官方源（qcc-legal/WebSearch
官方站）取远程指纹，写入 --g1-data <json> 后，本脚本做：
  1) 本地施行日期提取（frontmatter 优先：施行日期/effective_date/
     version_effective_date/version_local → 兜底正文 YYYY-MM-DD，跳过元数据行）；
  2) 远程指纹 ↔ 本地日期 比对 → source_verify: 双证一致 | 待核验；
  3) sxx / statute_text_pending / retrieved_date 核填；
  4) 重建/归一为 A 型 frontmatter（兼容 version_* 与 CMS 母本同义词字段，
     透传所有非 A 型字段，零字段丢失）。

⚠️ 架构边界（不降级到记忆、不越权）：
  - 脚本本身不联网；联网核填由 agent 经官方源完成，结果经 --g1-data JSON 传入。
  - RULE-038 字段契约未变（retrieved_date 本就是 A 型字段），故本脚本
    不触发「字段调整须经老强确认后版本号+1」；若日后改契约须走确认流程。

范围（守 R-3 边界）：
  G2 仅处理含 version_* 旧字段的卡；G1 处理「待核填」标记卡。
  「无 type / 无 frontmatter」卡均不自动处理，单独报告待老强分类。
"""
import os, re, io, sys, json, datetime, argparse, shutil

BANK = "/Users/chenyouqiang/Documents/LawKB/法条银行"
ARCHIVE = os.path.join(BANK, "_archive")
WEEKLY = os.path.join(BANK, "法律资讯周报")
SKIP = {ARCHIVE, WEEKLY}
STD_ENUM = {"现行有效", "已废止", "即将生效", "待核验"}
MAP = {"version_doc_no": "doc_no", "version_effect_rank": "effect_rank",
       "version_org": "org", "version_effective_date": "effective_date",
       "version_verify": "source_verify"}
SRC_FIELDS = ["version_source", "version_basis", "version_ref"]

# 旧 version_* 数据字段白名单（仅这些字段出现才视为 legacy 需整治卡）。
# 注意：排除纯「version: vX」版本标记 与 治理文档字段（如 persona 的 version_anchor）。
LEGACY_VERSION_FIELDS = {
    "version_doc_no", "version_effect_rank", "version_org",
    "version_effective_date", "version_verify", "version_mismatch",
    "version_basis", "version_local", "version_ref", "version_source",
}

# G1 候选判定：sxx 待核验类 / version_mismatch / source_verify 非双证一致
G1_SXX_PENDING = {"待核验", "待远程核验"}
G1_REMOTE_STATUS_MAP = {
    "现行有效": "现行有效",
    "已被修订": "待核验",          # 卡体需人工确认是否为现行修订版
    "部分失效废止": "待核验",
    "失效废止": "已废止",
    "尚未生效": "即将生效",
    "草案": "待核验",
}

# CMS 母本 schema 同义词 → A 型字段名
CMS_SYN = {
    "发文字号": "doc_no",
    "施行日期": "effective_date",
    "时效性": "sxx",
    "效力级别": "effect_rank",
    "制定机关": "org",
}
# 被消费（重命名/替换，不再透传）的字段白名单
CONSUMED = {
    "title", "type", "doc_no", "effect_rank", "org", "effective_date",
    "sxx", "statute_text_pending", "source_verify", "source", "scope",
    "superseded_by", "aliases", "comments", "retrieved_date", "updated",
    "发文字号", "施行日期", "时效性", "效力级别", "制定机关",
    "核验源", "verify_date", "发布日期",
}
CONSUMED_VERSION = ("version",)  # 所有 version* 前缀


def extract_fm(path):
    try:
        lines = io.open(path, encoding="utf-8").read().splitlines()
    except Exception:
        return None, None
    if not lines or lines[0].strip() != "---":
        return None, lines
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    return (None, lines) if end is None else (lines[1:end], lines)


def parse_fm(fm):
    f = {}
    for ln in fm:
        m = re.match(r'^([\u4e00-\u9fffA-Za-z_]+)\s*:\s*(.*)$', ln)
        if m:
            f[m.group(1)] = m.group(2).strip()
    return f


def parse_fm_blocks(path):
    """行级解析 frontmatter：返回 [(key, [raw_lines_incl_key_and_nested]), lines, end]。
    保留多行列表/嵌套块的原始格式，供透传零丢失。"""
    try:
        lines = io.open(path, encoding="utf-8").read().splitlines()
    except Exception:
        return None, None, None
    if not lines or lines[0].strip() != "---":
        return None, lines, None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None, lines, None
    blocks = []
    i = 1
    while i < end:
        ln = lines[i]
        if ln.strip() == "":
            i += 1
            continue
        m = re.match(r'^([\u4e00-\u9fffA-Za-z_]+)\s*:\s*(.*)$', ln)
        if not m:
            i += 1
            continue
        key = m.group(1)
        block = [ln]
        i += 1
        while i < end and (lines[i].startswith(" ") or lines[i].startswith("\t")):
            block.append(lines[i])
            i += 1
        blocks.append((key, block))
    return blocks, lines, end


def docno_from_name(fn):
    m = re.search(r'（([^）]*?第\d+号)）', fn)
    return m.group(1) if m else None


def body_text(path):
    """返回卡体（frontmatter 之后的正文）"""
    fm, lines = extract_fm(path)
    if fm is None:
        return "\n".join(lines) if lines else ""
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return ""
    return "\n".join(lines[end + 1:])


def local_effective_date(path):
    """本地施行日期：frontmatter 明确日期字段优先（施行日期/effective_date/
    version_effective_date/version_local/发布日期），兜底正文 YYYY-MM-DD
    （跳过「来源/发布时间/时间：/公布日期/发布日期/时间:」等元数据行）。"""
    fm, _ = extract_fm(path)
    if fm is None:
        return None
    fld = parse_fm(fm)
    cand = []
    for k in ("施行日期", "effective_date", "version_effective_date",
             "version_effective", "发布日期"):
        v = fld.get(k)
        if v:
            for d in re.findall(r'(\d{4})-(\d{2})-(\d{2})', str(v)):
                cand.append("-".join(d))
    vl = fld.get("version_local")
    if vl:
        for d in re.findall(r'(\d{4})-(\d{2})-(\d{2})', str(vl)):
            cand.append("-".join(d))
    if cand:
        return max(cand)
    txt = body_text(path)
    bcand = []
    for ln in txt.splitlines():
        if re.search(r'来源|发布时间|时间：|公布日期|发布日期|时间:', ln):
            continue
        for d in re.findall(r'(\d{4})-(\d{2})-(\d{2})', ln):
            bcand.append("-".join(d))
    return max(bcand) if bcand else None


# =====================================================================
# G2：version_* → A 型 重建
# =====================================================================
def plan_file(path, fn):
    fm, _ = extract_fm(path)
    if fm is None:
        return None  # 无 frontmatter，不自动处理
    fld = parse_fm(fm)
    if not any(k in LEGACY_VERSION_FIELDS for k in fld):
        return None  # 非旧 version_* 数据卡（纯 version: vX 版本标记/治理文档），不处理

    new = []
    title = fn[:-3]  # 优先用文件名（规范法规名）；原 title 可能是剪切错误/带源后缀噪声，不沿用
    new.append(f"title: {title}")
    new.append("type: statute")
    docno = (fld.get("version_doc_no") or docno_from_name(fn)
             or fld.get("doc_no") or "待核填（pkulaw）")
    new.append(f"doc_no: {docno}")
    if "version_effect_rank" in fld:
        new.append(f"effect_rank: {fld['version_effect_rank']}")
    elif "effect_rank" in fld:
        new.append(f"effect_rank: {fld['effect_rank']}")
    if "version_org" in fld:
        new.append(f"org: {fld['version_org']}")
    elif "org" in fld:
        new.append(f"org: {fld['org']}")
    if "version_effective_date" in fld:
        new.append(f"effective_date: {fld['version_effective_date']}")
    elif "effective_date" in fld:
        new.append(f"effective_date: {fld['effective_date']}")
    mismatch = str(fld.get("version_mismatch", "")).lower().startswith("true")
    sxx_raw = fld.get("sxx")
    if mismatch:
        new.append("sxx: 待核验")
        new.append("statute_text_pending: true")
    elif sxx_raw in STD_ENUM:
        new.append(f"sxx: {sxx_raw}")
        new.append("statute_text_pending: false")
    else:
        new.append("sxx: 待核验")
        new.append("statute_text_pending: true")
    if "version_verify" in fld:
        new.append(f"source_verify: {fld['version_verify']}")
    else:
        new.append("source_verify: 待核验")
    src = fld.get("source") or next((fld[k] for k in SRC_FIELDS if k in fld),
                                    "待核填（pkulaw）")
    new.append(f"source: {src}")
    if "scope" in fld:
        new.append(f"scope: {fld['scope']}")
    else:
        new.append("scope: 全文")
    if "superseded_by" in fld:
        new.append(f"superseded_by: {fld['superseded_by']}")
    if "version_note" in fld:
        new.append(f"comments: {fld['version_note']}")
    if "aliases" in fld:
        new.append(f"aliases: {fld['aliases']}")
    new.append(f"updated: {datetime.date.today().isoformat()}")
    return new


# =====================================================================
# G1：联网双证核填 → A 型（行级、兼容 CMS 同义词、零丢失透传）
# =====================================================================
def is_g1_candidate(fld):
    """判定该卡是否需要联网双证核填。"""
    if "version_mismatch" in fld and str(fld["version_mismatch"]).lower().startswith("true"):
        return True
    sxx = fld.get("sxx")
    if sxx in G1_SXX_PENDING:
        return True
    sv = fld.get("source_verify")
    # 以「双证一致」开头即视为已核填（允许「双证一致（来源…）」带括号说明）
    if sv is None or not str(sv).startswith("双证一致"):
        return True
    return False


def plan_g1_file(path, fn, verify_map):
    """G1 候选 → 重建/归一 A 型（含双证标记 + CMS 同义词兼容 + 透传零丢失）。
    返回：None（无 frontmatter）/ dict（候选无 verify 数据）/ list（inner 行，无 --- 定界）。"""
    blocks, lines, end = parse_fm_blocks(path)
    if blocks is None:
        return None  # 无 frontmatter，不自动处理
    fm_lines = lines[1:end]
    fld = parse_fm(fm_lines)
    if not is_g1_candidate(fld):
        return None  # 已完成双证核填，跳过

    key = fn
    v = verify_map.get(key) or verify_map.get(fn[:-3]) or verify_map.get(fld.get("title", ""))
    local_eff = local_effective_date(path)

    if v is None:
        missing = []
        for k in ("doc_no", "effective_date", "sxx", "source_verify"):
            cur = fld.get(k, fld.get(CMS_SYN.get(k, k), "（缺失）"))
            if cur in ("待核验", "待远程核验", "待核填（pkulaw）", "（缺失）"):
                missing.append(k)
        return {"candidate": True, "missing": missing, "local_eff": local_eff,
                "note": "待 --g1-data 联网核填"}

    # ---- 取值：远程指纹优先，其次 A 型名，其次 CMS 同义词 ----
    docno = (v.get("doc_no") or fld.get("doc_no") or fld.get("发文字号")
             or docno_from_name(fn) or "待核填（pkulaw）")
    eff_rank = (fld.get("effect_rank") or fld.get("效力级别") or v.get("effect_rank")
                or "待核填（pkulaw）")
    org = (fld.get("org") or fld.get("制定机关") or v.get("org") or "待核填（pkulaw）")
    eff_date = (v.get("effective_date") or fld.get("effective_date")
                or fld.get("施行日期") or "待核填（pkulaw）")
    r_status = v.get("effect_status", "现行有效")
    r_source = v.get("source", "官方源（待补）")
    r_url = v.get("source_url", "")

    dual = "双证一致" if (local_eff and eff_date and str(local_eff) == str(eff_date)) else "待核验"
    sxx = G1_REMOTE_STATUS_MAP.get(r_status, "待核验")
    pending = "true" if dual != "双证一致" else "false"

    inner = []
    inner.append(f"title: {fn[:-3]}")
    inner.append("type: statute")
    inner.append(f"doc_no: {docno}")
    inner.append(f"effect_rank: {eff_rank}")
    inner.append(f"org: {org}")
    inner.append(f"effective_date: {eff_date}")
    inner.append(f"sxx: {sxx}")
    inner.append(f"statute_text_pending: {pending}")
    if dual == "双证一致":
        sv_note = f"双证一致（{docno}·{eff_date} ↔ 本地末条/最新日期·{local_eff}）"
    else:
        sv_note = "待核验"
        if local_eff and eff_date and local_eff != eff_date:
            sv_note += f"（本地末条/最新日期·{local_eff} ≠ 远程·{eff_date}，待人工复核）"
        elif local_eff is None:
            sv_note += "（本地卡体无可比 YYYY-MM-DD 施行日期，待人工复核）"
    inner.append(f"source_verify: {sv_note}")

    old_src = fld.get("source")
    src = r_source or old_src or "待核填（pkulaw）"
    if r_url:
        src = f"{src}（{r_url}）"
    inner.append(f"source: {src}")

    # scope（保留原值或默认全文）
    scope = fld.get("scope") or "全文"
    inner.append(f"scope: {scope}")
    if "superseded_by" in fld:
        inner.append(f"superseded_by: {fld['superseded_by']}")

    # comments：合并原 comments + 双证说明 + 旧源/旧核验源/发布日期 留痕
    comments = fld.get("comments", "")
    extra = f"G1双证核填于{datetime.date.today().isoformat()}：{sv_note}"
    if old_src and old_src not in src:
        extra += f"；旧source:{old_src}"
    if fld.get("核验源"):
        extra += f"；旧核验源:{fld['核验源']}"
    if fld.get("发布日期"):
        extra += f"；发布日期:{fld['发布日期']}"
    inner.append(f"comments: {comments + '；' if comments else ''}{extra}")

    if "aliases" in fld:
        inner.append(f"aliases: {fld['aliases']}")

    inner.append(f"retrieved_date: {datetime.date.today().isoformat()}")
    inner.append(f"updated: {datetime.date.today().isoformat()}")

    # ---- 透传：保留所有非 A 型、非被消费字段（tags/maturity/related_cms/note/created...）----
    consumed = set(CONSUMED)
    for k in fld:
        if k.startswith(CONSUMED_VERSION):
            consumed.add(k)
    passthrough = []
    for k, blk in blocks:
        if k in consumed:
            continue
        passthrough.extend(blk)
    inner += passthrough
    return inner


# =====================================================================
# 执行框架（G2 / G1 共用）
# =====================================================================
def collect(mode, args, verify_map):
    targets = []
    for d in sorted(os.listdir(BANK)):
        dp = os.path.join(BANK, d)
        if not os.path.isdir(dp) or dp in SKIP:
            continue
        if d == "银行治理层":
            continue  # 治理文档（memo/persona/_Schema规范/搭建方案/覆盖台账）非 statute 卡，G1/G2 均跳过
        for fn in sorted(os.listdir(dp)):
            if not fn.endswith(".md"):
                continue
            if args.file and fn != args.file:
                continue
            p = os.path.join(dp, fn)
            if mode == "g1":
                nf = plan_g1_file(p, fn, verify_map)
            else:
                nf = plan_file(p, fn)
            if nf is not None:
                targets.append((p, fn, nf))
    return targets


def emit_manifest(targets, out):
    man = {}
    for p, fn, nf in targets:
        if isinstance(nf, dict) and nf.get("candidate"):
            man[fn] = {
                "doc_no": None, "effective_date": None,
                "effect_status": "现行有效",
                "effect_rank": None, "org": None,
                "source": "官方源（qcc-legal/WebSearch 官方站）", "source_url": "",
                "missing": nf.get("missing", []),
                "local_eff": nf.get("local_eff"),
            }
    with io.open(out, "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
    print(f"📤 已生成 G1 核填清单（待 agent 填值）：{out}")


def apply_targets(targets, label):
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bk = f"/tmp/fatiao_{label}_{ts}"
    os.makedirs(bk, exist_ok=True)
    fixed = 0
    for p, fn, nf in targets:
        if isinstance(nf, dict):
            continue  # 仅候选报告，无 verify 数据，跳过
        txt = io.open(p, encoding="utf-8").read()
        lines = txt.splitlines()
        if lines[0].strip() != "---":
            continue
        end = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end = i
                break
        if end is None:
            continue
        # nf 为 inner 行（无定界 ---）；重组为 开定界 + inner + 闭定界 + 正文
        new_lines = [lines[0]] + nf + lines[end:]
        new_txt = "\n".join(new_lines) + ("\n" if not txt.endswith("\n") else "")
        rel = os.path.relpath(p, BANK).replace("/", "__")
        shutil.copy2(p, os.path.join(bk, rel))
        io.open(p, "w", encoding="utf-8").write(new_txt)
        fixed += 1
    print(f"\n✅ [{label}] 已整治 {fixed} 张；备份 {bk}")
    return fixed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--file", default=None, help="单卡试点：只处理指定文件名")
    ap.add_argument("--g1", action="store_true", help="G1 联网双证核填模式（替代默认 G2 version_* 整治）")
    ap.add_argument("--g1-data", default=None, help="G1 模式：agent 经官方源产出的远程指纹 JSON")
    ap.add_argument("--emit-manifest", default=None, help="G1 模式：输出待核填清单 JSON（供 agent 填值）")
    args = ap.parse_args()
    if not args.dry_run and not args.apply:
        args.dry_run = True

    mode = "g1" if args.g1 else "g2"
    verify_map = {}
    if args.g1 and args.g1_data:
        try:
            verify_map = json.load(io.open(args.g1_data, encoding="utf-8"))
        except Exception as e:
            print(f"❌ --g1-data 读取失败：{e}")
            return 1

    targets = collect(mode, args, verify_map)

    if not targets:
        if mode == "g1":
            print("✅ 无 G1 待核填卡（sxx 均已双证一致）。" if not args.file
                  else f"✅ {args.file} 无需 G1 核填。")
        else:
            print("✅ 无 version_* 旧 schema 卡需整治。" if not args.file
                  else f"✅ {args.file} 无需整治（无 version_* 字段）。")
        return 0

    print(f"🔍 [{mode.upper()}] 发现 {len(targets)} 张待处理卡：")
    for p, fn, nf in targets:
        print(f"\n[法条银行/{os.path.relpath(p, BANK)}]")
        if isinstance(nf, dict):  # G1 候选报告（无 verify 数据）
            print(f"    ⏳ 候选：缺失 {nf.get('missing')}；本地末条/最新日期={nf.get('local_eff')}")
        else:
            for ln in nf:
                print(f"    {ln}")

    if args.g1 and args.emit_manifest:
        emit_manifest(targets, args.emit_manifest)
    elif args.g1 and not args.g1_data and args.dry_run:
        print("\n💡 G1 dry-run：以上为待核填候选。请 agent 经官方源取远程指纹，"
              "写入 --g1-data <json> 后加 --apply。可加 --emit-manifest <path> 生成待填清单。")

    if not args.apply:
        print("\n📝 DRY-RUN：未修改。确认映射规则后加 --apply"
              + ("（单卡试点）" if args.file else "（改前自动备份 /tmp）") + "。")
        return 0

    if args.g1 and not verify_map:
        print("\n⚠️ G1 --apply 需要 --g1-data（远程指纹 JSON），否则无可核填数据。已跳过写入。")
        return 0

    apply_targets(targets, mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
