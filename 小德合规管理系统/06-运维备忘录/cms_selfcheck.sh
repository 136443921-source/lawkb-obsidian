#!/bin/bash
# 小德合规管理系统 · 资产指纹自检 v2.1（五模板版）
# 创建: 2026-09-12 (v1.0)  |  升级: 2026-09-12 (v2.0 五模板)
# 用法: bash cms_selfcheck.sh
# 目的: 输出各资产实测值，与《运维手册（五模板版）》【十、资产指纹基线 B1–B24】逐项对比，检测文档漂移
# 铁律: 实测值与基线不一致时，先判『有意变更』还是『文档漂移』
#        有意 → 更新基线 + frontmatter；漂移 → 回滚 + 台账记录
# 教训: v1.0 曾因正则误计把业务表数算成 9（实为 10）——脚本写/改完必须实跑验证

CMS="/Users/chenyouqiang/Documents/LawKB/小德合规管理系统"
SKILL="$HOME/.workbuddy/skills/小德合规管理系统/SKILL.md"
CFG="$CMS/05-系统配置"
CARD="$CMS/03-经验卡片"
LAW="/Users/chenyouqiang/Documents/LawKB/法律法规库"
CHARITY="$LAW/慈善合规类法律法规"
MEDICAL="$LAW/医事法律法规库"

# 比对函数: chk <实测> <基线> <标签>
chk() {
  if [ "$1" = "$2" ]; then echo "  ✅ $3: $1  (基线 $2)"
  else echo "  ⚠️  $3: $1  (基线 $2) ← 与基线不符，判『有意变更』还是『漂移』"; fi
}

echo "══════════ 小德 CMS 资产指纹自检 v2.1（五模板版）══════════"
echo "检测时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo

for p in "$CMS" "$CFG" "$CARD" "$LAW"; do
  [ -d "$p" ] || echo "  ⚠️ 目录不存在: $p"
done
[ -f "$SKILL" ] || echo "  ⚠️ SKILL.md 不存在: $SKILL"
echo

# ─────────── 模板① 慈善 ───────────
echo "───── 模板① 慈善合规管理 ─────"
INST="$CFG/小德慈善组织合规管理系统_制度清单（慈善版）.md"
if [ -f "$INST" ]; then
  chk "$(awk '/^## 一、制度母表/,/^## 二、/' "$INST" | grep -cE '^\| *[0-9]+ *\|')" 30 "B1 制度数"
  chk "$(awk '/^## 一、制度母表/,/^## 二、/' "$INST" | grep -c 'CARD-TODO')" 28 "B2 CARD-TODO"
else echo "  ⚠️ 制度清单缺失"; fi

FLOW="$CFG/小德慈善组织合规管理系统_审批流（慈善版）.md"
if [ -f "$FLOW" ]; then
  chk "$(awk '/^## 一、审批控制节点总表/,/^## 二、/' "$FLOW" | grep -cE '^\| *\*{0,2}N[0-9]+\*{0,2} *\|')" 18 "B3 控制节点"
else echo "  ⚠️ 审批流缺失"; fi

FIELD="$CFG/小德慈善组织合规管理系统_字段配置表（慈善版）.md"
if [ -f "$FIELD" ]; then
  # 只数「一、」~「十、」单字章节（末尾锚「、」排除 十一/十二）
  chk "$(grep -cE '^## [一二三四五六七八九十]、' "$FIELD")" 10 "B4 业务表数"
else echo "  ⚠️ 字段表缺失"; fi

# ─────────── 模板② 医院 ───────────
echo "───── 模板② 医院合规管理 ─────"
chk "$(find "$CARD/医院合规" -name '*.md' ! -name 'README*' 2>/dev/null | wc -l | tr -d ' ')" 13 "B6 医院合规卡"
chk "$(find "$CARD/医疗纠纷章卡" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')" 11 "B7 医疗纠纷章卡"
echo "  ℹ️  B8 ②三件套(制度/审批/字段): 实测 $(ls -1 "$CFG" 2>/dev/null | grep -c 医院) 份（基线 3 = 已建，12制度/8审批/8字段）"

# ─────────── 模板③④⑤ 新建 ───────────
echo "───── 模板③ 合同 / ④ 非诉 / ⑤ 调解 ─────"
chk "$(find "$CARD/合同合规" -name '*.md' ! -name 'README*' 2>/dev/null | wc -l | tr -d ' ')" 6 "B9 ③合同合规卡"
echo "  ℹ️  B10 ③三件套: 基线 3（已建，8制度/10审批/10字段，移植①10表骨架+二维矩阵）"
chk "$(find "$CARD/非诉合规" -name '*.md' ! -name 'README*' 2>/dev/null | wc -l | tr -d ' ')" 6 "B11 ④非诉合规卡"
b12=$(find "$CMS/05-系统配置/非诉交付物模板" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
chk "$b12" 5 "B12 ④交付物模板数"
echo "  ℹ️  B13 ⑤调解经验卡: 基线 1（已建，章卡第十六章重映射）"
chk "$(find "$CARD/医疗纠纷章卡" -name '*第十六章*' 2>/dev/null | wc -l | tr -d ' ')" 1 "B14 ⑤调解章卡(第十六章)"

# ─────────── 法源 ───────────
echo "───── 法源 ─────"
# ⚠️ 统计本地法规一律用 -name：-iname 在中文文件名上会漏匹配（实测漏 8 个）
chk "$(find "$LAW" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')" 72 "B15 本地法规总数"
b16=0
for f in "$LAW/慈善合规类法律法规/中华人民共和国慈善法.md" "$LAW/行政法律规章/基金会管理条例.md" "$LAW/行政法律规章/关于慈善组织开展慈善活动年度支出、管理费用和募捐成本的规定.md" "$LAW/行政法律规章/民间非营利组织会计制度.md" "$LAW/慈善合规类法律法规/境外非政府组织境内活动管理法.md" "$LAW/慈善合规类法律法规/慈善组织信息公开办法（民政部令第81号）.md" "$LAW/慈善合规类法律法规/慈善组织公开募捐管理办法（民政部令第74号）.md" "$LAW/慈善合规类法律法规/慈善组织保值增值投资活动管理暂行办法（民政部令第62号）.md" "$LAW/慈善合规类法律法规/志愿服务条例（国务院令第685号）.md" "$LAW/慈善合规类法律法规/中华人民共和国公益事业捐赠法（主席令第19号）.md" "$LAW/慈善合规类法律法规/社会组织登记管理机关行政处罚程序规定（民政部令第68号）.md"; do [ -f "$f" ] && b16=$((b16+1)); done
chk "$b16" 11 "B16 ①慈善轨本地法源(11部)"
MED=$(find "$MEDICAL" -maxdepth 1 -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
chk "$MED" 10 "B17 ②医院轨法源(医事库 10部)"
echo "  ℹ️  B18 待核验法源: 基线 0 项（②医院轨 H1–H5 + ⑤调解轨 M2/M3 已于 2026-09-14 v1.4.6 补建本地源，本地法源缺口清零）—— 见手册附录 B"

# ─────────── 版本与文档数 ───────────
echo "───── 版本与文档数 ─────"
if [ -f "$SKILL" ]; then
  SV=$(grep -m1 '^version:' "$SKILL" | awk '{print $2}')
  chk "$SV" "1.8.0" "B19 SKILL 版本"
else echo "  ⚠️ SKILL.md 缺失"; fi
chk "$(find "$CMS/01-方案设计" -name '*.md' ! -name '*.bak*' 2>/dev/null | wc -l | tr -d ' ')" 11 "B20 01-方案设计"
chk "$(find "$CFG" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')" 20 "B21 05-系统配置"
chk "$(find "$CMS/06-运维备忘录" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')" 2 "B22 06-运维备忘录(md)"
if [ -f "$CMS/06-运维备忘录/cms_change_guard.sh" ]; then
  GN=$(bash "$CMS/06-运维备忘录/cms_change_guard.sh" list 2>/dev/null | tail -1 | grep -oE '[0-9]+' | head -1)
  chk "$GN" 89 "B23 守卫受控文件数"
else echo "  ⚠️ cms_change_guard.sh 缺失"; fi

echo
echo "───── 变更守卫（系统改了但备忘录没回写，这里会红）─────"
if [ -f "$CMS/06-运维备忘录/cms_change_guard.sh" ]; then
  bash "$CMS/06-运维备忘录/cms_change_guard.sh" check 2>/dev/null | tail -3
fi

echo
echo "⚠️ 提示：实测值与基线不一致时，先判『有意变更』还是『文档漂移』。"
echo "   有意 → 更新【十、资产指纹基线】；漂移 → 回滚 + 台账记录。"
echo "   改完记得：① 填变更台账  ② 刷 frontmatter updated/version  ③ 跑守卫 mark 登记基线"
echo "══════════ 自检结束 ════════"
