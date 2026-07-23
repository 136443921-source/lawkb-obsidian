#!/usr/bin/env python3
# _refresh_health_dashboard.py
# 扫描知识飞轮六层目录 + CaseDrop，重算 KPI，写回飞轮健康度仪表盘 HTML 的 DATA 块。
# 重建时会完整重写 DATA 对象（含 metrics），并输出合法 JS（数组元素带逗号、结尾缩进无关）。
import re
from pathlib import Path
from datetime import date

ROOT = Path("/Users/chenyouqiang/Documents/LawKB/知识飞轮系统")
DASH = ROOT / "飞轮健康度仪表盘.html"
CASEDROP = Path("/Users/chenyouqiang/Documents/CaseDrop")


def count_md(d):
    if not d.exists():
        return 0
    return sum(1 for p in d.rglob("*.md") if p.is_file())


layers = {
    "01-采集": count_md(ROOT / "01-采集"),
    "02-提炼": count_md(ROOT / "02-提炼"),
    "03-连接": count_md(ROOT / "03-连接"),
    "04-巩固": count_md(ROOT / "04-巩固"),
    "05-调用": count_md(ROOT / "05-调用"),
    "06-沉淀": count_md(ROOT / "06-沉淀"),
}

cards_dir = ROOT / "02-提炼/经验卡片"
card_files = list(cards_dir.glob("*.md")) if cards_dir.exists() else []
experience_cards = len(card_files)
sim_cards = sum(
    1 for p in card_files
    if "is_simulation: true" in p.read_text(encoding="utf-8", errors="ignore")
)
real_cards = experience_cards - sim_cards

rules_dir = ROOT / "06-沉淀/裁判规则库"
rule_files = sum(1 for p in rules_dir.rglob("*") if p.is_file()) if rules_dir.exists() else 0

processed = CASEDROP / "processed"
case_notes = (
    sum(1 for p in processed.iterdir() if p.name != "README.md" and not p.name.startswith("."))
    if processed.exists() else 0
)

ongoing = 0
today = date.today().isoformat()

html = DASH.read_text(encoding="utf-8")
# 缩进无关：允许 DATA 块结尾 "};" 前出现任意空白
m = re.search(r"const DATA = \{[\s\S]*?\n\s*\};", html)
if not m:
    raise SystemExit("未找到 DATA 块")

block = m.group(0)
gm = re.search(r"cardGrowth: \[([\s\S]*?)\]", block)
growth = []
if gm:
    for item in re.finditer(r'\{date:"([\d-]+)",\s*cum:(\d+)\}', gm.group(1)):
        growth.append({"date": item.group(1), "cum": int(item.group(2))})
growth = [g for g in growth if g["date"] != today]
growth.append({"date": today, "cum": experience_cards})
growth.sort(key=lambda g: g["date"])

lines = []
lines.append("const DATA = {")
lines.append('  updated: "%s",' % today)
lines.append(
    "  kpi: { experienceCards:%d, ruleFiles:%d, caseNotes:%d, ongoingCases:%d },"
    % (experience_cards, rule_files, case_notes, ongoing)
)
lines.append("  cardGrowth: [")
for g in growth:
    lines.append('    {date:"%s", cum:%d},' % (g["date"], g["cum"]))
lines.append("  ],")
lines.append("  metrics: [")
lines.append(
    '    {name:"协同效果命中率", value:"待采集", desc:"分身问答埋点日志积累中，每月28日协同效果月报将出首值"},'
)
lines.append(
    '    {name:"经验卡片（真实/演练）", value:"%d/%d", desc:"凤仪村为预测型无裁判结果；罗江辉为演练卡"},'
    % (real_cards, experience_cards)
)
lines.append(
    '    {name:"裁判规则库成熟度", value:"🌿幼苗", desc:"主库 R001-R015 + 人伤子库 R016-R023，共 23 条；元数据已对齐"},'
)
lines.append(
    '    {name:"案件-卡片-规则三维索引", value:"已建", desc:"2026-07-18 连接层加厚（P2），覆盖 18 案件/6 卡片/23 规则"}'
)
lines.append("  ]")
lines.append("};")
new_block = "\n".join(lines)

html = html[: m.start()] + new_block + html[m.end():]
DASH.write_text(html, encoding="utf-8")
print(
    "[refresh] %s 经验卡片=%d(真实%d) 规则库文件=%d CaseDrop归档=%d 六层=%s"
    % (today, experience_cards, real_cards, rule_files, case_notes, layers)
)
