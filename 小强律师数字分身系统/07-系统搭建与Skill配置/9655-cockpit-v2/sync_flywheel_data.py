"""把 9655 驾驶舱 C3 屏数据源 flywheel-data.js 与主源 Desktop/飞轮中台.html 对齐。

背景（2026-09-27 排查）：
  C3 屏 subapps/flywheel/index.html 的几乎全部可视化都吃 DATA（本文件的全局对象），
  但 9655 这份 flywheel-data.js 停在 2026-09-25 20:05（正本那次批量重建的同一时刻），
  而主源 ~/Desktop/飞轮中台.html 已更新到 2026-09-26 ⇒ 屏上"数据更新"停在 25 日、26 日无数据。

合并口径（2026-09-27 改为择优合并，避免"全量覆盖"造成倒退）：
  默认取主源（Desktop 是权威主源）；以下两类例外保留 9655 原值：
    · dailyGrowth —— 9655 独有字段；且 gen_flywheel_daily.py 的 2741 跟踪起点假象待老强定夺，不擅自改；
    · cardFamily  —— 9655 独有字段，主源无。
  逐字段择优：
    · kg     —— 按 generated 字符串取较新者。主源停在 09-21 23:00，全量覆盖会让知识图谱倒退 4 天。
    · intake —— 按 cases7 取较大者。主源 cases7=0/level=watch 系陈旧快照。
  其余字段（kpi / cardGrowth / rules / layerInc / metrics / alerts / autos / cardFamily）一律取主源。

用法：python3 sync_flywheel_data.py [--dry-run]
"""
import re, json, sys, os, datetime
from pathlib import Path

DST = Path("/Users/chenyouqiang/Documents/LawKB/小强律师数字分身系统/07-系统搭建与Skill配置/9655-cockpit-v2/flywheel-data.js")
SRC = Path.home() / "Desktop" / "飞轮中台.html"
KEEP_9655 = ("dailyGrowth", "cardFamily")   # 9655 独有，必须保留，不得被主源 null 覆盖
DRY = "--dry-run" in sys.argv


def extract_data_block(txt):
    m = re.search(r"const\s+DATA\s*=\s*\{", txt)
    if not m:
        raise SystemExit("✗ 主源未找到 const DATA 块")
    i = txt.index("{", m.start())
    depth = 0
    for j in range(i, len(txt)):
        if txt[j] == "{":
            depth += 1
        elif txt[j] == "}":
            depth -= 1
            if depth == 0:
                return i, j + 1          # 返回 [起, 止) 区间
    raise SystemExit("✗ DATA 块括号未闭合")


def js_to_obj(block):
    s = re.sub(r'([{,]\s*)([A-Za-z_]\w*)\s*:', r'\1"\2":', block)
    s = re.sub(r',(\s*[}\]])', r'\1', s)
    return json.loads(s)


def js_key(k):
    """键名是否可裸写。JS 标识符允许 Unicode（如中文「experienceCards」没问题），
    但不允许全角标点——原文里「卡段模板（可复用）」这类键是带引号的。
    2026-09-27 实测：只按 [A-Za-z_]\\w* 判断会漏掉全角括号键，写出 SyntaxError。"""
    return k if re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", k) else json.dumps(k, ensure_ascii=False)


def js_literal(o, indent=2, level=1):
    """JS 对象字面量序列化：键名裸写、2 空格缩进，与 flywheel-data.js 原文及其它脚本的正则兼容。"""
    pad = " " * (indent * level)
    close = " " * (indent * (level - 1))
    if isinstance(o, dict):
        if not o:
            return "{}"
        return "{\n" + ",\n".join(
            f"{pad}{js_key(k)}: " + js_literal(v, indent, level + 1) for k, v in o.items()
        ) + "\n" + close + "}"
    if isinstance(o, list):
        if not o:
            return "[]"
        return "[\n" + ",\n".join(
            pad + js_literal(v, indent, level + 1) for v in o
        ) + "\n" + close + "]"
    if isinstance(o, bool):
        return "true" if o else "false"
    if o is None:
        return "null"
    return json.dumps(o, ensure_ascii=False)


def choose(field, sv, dv):
    """返回 (采用值, 说明)。sv=主源值, dv=9655 现值。"""
    if field in KEEP_9655 and dv is not None:
        return dv, f"保留 9655 原值（主源无此键或为 null 占位）"
    if field == "kg" and sv and dv:
        sg, dg = str(dv.get("generated") or ""), str(sv.get("generated") or "")
        if sg > dg:
            return dv, f"主源 generated={dg} 更旧，取 9655（{sg}）"
    if field == "intake" and sv and dv:
        if (dv.get("cases7") or -1) > (sv.get("cases7") or -1):
            return dv, f"主源 cases7={sv.get('cases7')}/{sv.get('level')} 陈旧，取 9655（{dv.get('cases7')}/{dv.get('level')}）"
    return sv, "取主源"


src_txt = SRC.read_text(encoding="utf-8")
dst_txt = DST.read_text(encoding="utf-8")

s0, s1 = extract_data_block(src_txt)
d0, d1 = extract_data_block(dst_txt)
sd, dd = js_to_obj(src_txt[s0:s1]), js_to_obj(dst_txt[d0:d1])

print("主源 updated =", sd.get("updated"), "｜ 9655 现 updated =", dd.get("updated"))
print("主源 DATA 顶层字段:", list(sd.keys()))
print("9655  DATA 顶层字段:", list(dd.keys()))

# ⚠️ 键序必须显式钉死：dailyGrowth 必须排在 metrics 之前。
#    gen_flywheel_daily.py 的替换正则是 `dailyGrowth:\s*\[[\s\S]*?\],\s*\n\s*metrics:`，
#    顺序一旦颠倒正则就匹配不上，fallback 的 js_text.replace("  metrics: [", ...) 会在 metrics 前
#    再插一段 → 文件里出现两个 dailyGrowth 同名键（JS 后者覆盖前者，看着能用实则很脏）。
#    2026-09-27 实测踩到：用 json.dumps 重排后键序变成 metrics→...→dailyGrowth。
#    故不用 dict 自然键序，显式按 KEY_ORDER 排，未列出的键按 主源→9655 追加到末尾。
KEY_ORDER = ["updated", "kpi", "cardGrowth", "dailyGrowth", "metrics",
             "layerInc", "kg", "rules", "autos", "intake", "alerts", "cardFamily"]

merged, notes = {}, []
_pick_cache = {}
for k in KEY_ORDER:
    if k in sd or k in dd:
        v, why = choose(k, sd.get(k), dd.get(k))
        merged[k] = v
        notes.append((k, why))
for k in list(sd) + [k for k in dd if k not in sd]:   # KEY_ORDER 未覆盖的键补在末尾
    if k not in merged and sd.get(k) is not None:
        merged[k] = sd[k]
        notes.append((k, "非约定键·主源补回"))
    elif k not in merged and dd.get(k) is not None:
        merged[k] = dd[k]
        notes.append((k, "非约定键·9655补回"))
merged = {k: v for k, v in merged.items() if v is not None}

print("\n合并后字段:", list(merged.keys()))
print("保留的", [k for k in KEEP_9655 if k in merged], "末点:", merged.get("dailyGrowth", [])[-1:])

print("\n=== 逐字段采用说明 ===")
for k, why in notes:
    print(f"  · {k}: {why}")

print("\n=== 本次变更字段（9655旧 → 合并后）===")
changed = 0
for k in sorted(set(sd) | set(dd) | set(merged)):
    a, b = dd.get(k), merged.get(k)
    if json.dumps(a, ensure_ascii=False, sort_keys=True) != json.dumps(b, ensure_ascii=False, sort_keys=True):
        changed += 1
        print(f"  {k}:\n    旧 {json.dumps(a, ensure_ascii=False)[:110]}\n    新 {json.dumps(b, ensure_ascii=False)[:110]}")
print(f"\n共 {changed} 个字段变更")

if DRY:
    print("\n🟡 DRY-RUN 未写入")
    sys.exit(0)

# 拼接口径（2026-09-27 修正：初版在此连踩两坑，两次都被 node 实跑抓出）
#   坑1：d0 是 "{" 的索引而非 "const DATA = " 的起点 → 写出 "const DATA = const DATA = {"
#   坑2：d1 是 "}" 之后一位（即 ";"）。首版给 new_block 又补了 ";" → 尾部每跑一次叠一个分号（}",";";";）。
# 正确：前缀切到 d0（保留 "const DATA = "），新块只出 "{...}" 不带分号，后缀从 d1 起（自带那个 ";"）。
# 幂等性：重复跑在同一份正确文件上不会再加分号。
# 另：输出用 JS 字面量风格（键名裸写，非 json.dumps 的"带引号"），与原文及其它脚本的正则保持一致。
new_block = js_literal(merged)
out_txt = dst_txt[:d0] + new_block + dst_txt[d1:]
tmp = DST.with_suffix(".js.tmp_" + datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"))
tmp.write_text(out_txt, encoding="utf-8")
os.replace(tmp, DST)
print("\n✅ 已同步 ->", DST)

# ---- 写入后自检（2026-09-27 加：初版连写坏两次却"报告成功"，靠外部 node 才抓到）----
# 注意：vm 中脚本顶层 const 只进词法环境，不会挂到 context object 上，
#      必须显式 "globalThis.__D__ = DATA" 才能从外部读取（首版自检就栽在这，误报"已回滚"实为没回滚）。
import subprocess, shutil
BACKUP = Path("/tmp/flywheel-data.js.备份_0927同步前.js")
head = DST.read_text(encoding="utf-8")[:60]
if head.count("const DATA = ") > 1 or "const DATA = const DATA" in head:
    shutil.copy(BACKUP, DST)
    raise SystemExit("✗ 自检失败：文件头重复 const DATA = ，已真回滚")
chk = subprocess.run(
    ["node", "-e",
     "const fs=require('fs'),vm=require('vm');"
     "const c=fs.readFileSync(process.argv[1],'utf8');"
     "const x={window:{},document:{}};vm.createContext(x);"
     # 顶层 const 不挂 ctx，必须显式导出；末尾加分号是防原文无换行时拼接失效
     "vm.runInContext(c+';globalThis.__D__=DATA;',x);"
     "const D=x.__D__;if(!D||!D.updated)throw new Error('DATA 未挂载');"
     "console.log('✅ 自检通过: DATA.updated='+D.updated+' 顶层字段'+Object.keys(D).length+'个');"
     "console.log('   cardGrowth 末点='+JSON.stringify(D.cardGrowth.slice(-1))"
     "+' ｜ kg.total_notes='+D.kg.total_notes+' ｜ intake.cases7='+D.intake.cases7);"
     "console.log('   dailyGrowth 末点='+JSON.stringify(D.dailyGrowth.slice(-1))"
     "+' ｜ cardFamily='+(D.cardFamily&&typeof D.cardFamily==='object'?"
     "JSON.stringify(D.cardFamily.total)+'张/规则族'+D.cardFamily.card_type_count+'类':'缺失'));",
     DST],
    capture_output=True, text=True)
print(chk.stdout.strip() or chk.stderr.strip()[:600])
if chk.returncode != 0:
    shutil.copy(BACKUP, DST)          # 真回滚，别再口头撒谎
    raise SystemExit("✗ 自检失败（node 报错），已真回滚备份 " + str(BACKUP))
