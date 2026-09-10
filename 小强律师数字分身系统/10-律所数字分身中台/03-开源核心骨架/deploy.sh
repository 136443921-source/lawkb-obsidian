#!/usr/bin/env bash
# =============================================================
# digital-avatar-kit 脚手架（中小律所数字分身模板 · 开源核心骨架）
# 用法：./deploy.sh [目标目录]   默认 ./digital-avatar-kit
# =============================================================
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-./digital-avatar-kit}"

echo "▶ 脚手架目标：$TARGET"
mkdir -p "$TARGET"/legal-base \
         "$TARGET"/lawyer-yourself-skill \
         "$TARGET"/LTI文本监控器 \
         "$TARGET"/知识飞轮 \
         "$TARGET"/cockpit-portal/portal \
         "$TARGET"/templates

# —— 复制基座模板（优先用本仓库已验证的 schema） ——
if [ -f "$SCRIPT_DIR/../01-律师画像模板/lawyer-profile-template.schema.yaml" ]; then
  cp "$SCRIPT_DIR/../01-律师画像模板/lawyer-profile-template.schema.yaml" "$TARGET/templates/"
  echo "  ✔ 复制 lawyer-profile-template.schema.yaml"
else
  echo "  ⚠ 未找到基座 schema，请手动放入 templates/lawyer-profile-template.schema.yaml"
fi

# —— legal-base 基座 stub ——
cat > "$TARGET/legal-base/SKILL.md" <<'MD'
---
name: legal-base
extends: null
version: 1.0.0
description: 法律类技能基座——强制提供 LTI 文本输出拦截、幻觉防御（R011-R021）、知识飞轮卡库检索纪律。所有法律子技能 frontmatter 写 extends: legal-base 即生效。
---
# legal-base（法律技能基座）
- 出文前必须经 LTI 文本监控器（R/L/C/T/P 五维 + 六维法理逻辑门禁），REJECT=0 才准交付。
- 法条引用须带条号，且仅可来自 pkulaw / 元典 / 本地法律法规库；未回源标 statute_text_pending。
- 问答前先检索 02-提炼/经验卡片 与 06-沉淀/裁判规则库；任务后必沉淀为卡片。
MD

# —— lawyer-yourself-skill stub ——
cat > "$TARGET/lawyer-yourself-skill/SKILL.md" <<'MD'
---
name: lawyer-yourself-skill
extends: legal-base
version: 1.0.0
description: 法律职业特化数字分身创建器。消费律师画像模板（*.profile.yaml），经 combine 生成 self.md。
---
# lawyer-yourself-skill
- self.md 由 combine.sh 从 templates/*.profile.yaml 生成，禁止手改。
- 改模板/实例后必须重跑 combine，否则刷新被覆盖（Fix-the-source 铁律）。
MD
cat > "$TARGET/lawyer-yourself-skill/self.md" <<'MD'
<!-- 此文件由 combine.sh 生成，请勿手改 -->
MD

# —— LTI 文本监控器 stub ——
cat > "$TARGET/LTI文本监控器/SKILL.md" <<'MD'
---
name: LTI文本监控器
extends: legal-base
version: 1.0.0
description: 法律文本输出门禁。R/L/C/T/P 五维 QC + 六维法理逻辑门禁；R101 条号越界、C301 金额硬矛盾可阻断。
---
# LTI 文本监控器
- wrap_output() 在所有法律文本输出前调用，未通过绝不输出。
- 维度：R 法条真实 / L 法理逻辑 / C 一致性（含 301 金额、302 名称、304 案号）/ T 溯源 / P 程序。
MD

# —— 示例席位实例 ——
cat > "$TARGET/templates/example.lawyer.profile.yaml" <<'YAML'
schema_version: "1.0"
profile:
  display_name: "示例律师（张三）"
  seat_role: "lawyer"
  firm: "示例律师事务所"
  title: "执业律师"
  avatar_handle: "小X"
thinking_chain:
  response_depth:
    level: "doctrinal"
    cite_precise: true
    forbid_popularizing: true
    allow_neutral_balance: false
    require_viewpoint: true
  legal_verification:
    forbid_memory_citation: true
    allowed_sources: ["pkulaw", "yuandian-mcp", "local_law_lib"]
    pending_marker: "statute_text_pending"
    require_article_number: true
review_gates:
  redblue_review: true
  lti_qc: true
  lti_dimensions: ["R", "L", "C", "T", "P"]
  gate_levels: 6
  reject_threshold: 0
  block_rules: ["R101", "C301"]
knowledge_flywheel:
  retrieve_before_answer: true
  retrieve_paths: ["02-提炼/经验卡片", "06-沉淀/裁判规则库"]
  deposit_after_task: true
  nonlitigation_trace: true
delivery:
  docx_dual_track: true
  tencent_doc: true
  desktop_archive: true
  doc_format_law:
    font_body: "仿宋"; font_size: 16; font_title: "宋体"; font_title_size: 22
    line_spacing: 28; margin_top: 3.3; margin_bottom: 3.2; margin_left: 2.7; margin_right: 2.4
  forbid_thesis_style: true
language_style:
  structured_markdown: true
  emoji_titles: true
  one_line_conclusion: true
  formal_doc_no_emoji: true
safety:
  six_b: true
  backup_first: true
  cp_backup: true
  never_fabricate_token: true
seat_overrides:
  practice_areas: ["民商事诉讼", "合同法"]
  legal_question_priority:
    first: "lawyer-yourself-skill"
    charity_only: "小德慈善组织合规专家"
YAML

# —— combine.sh 生成器 ——
cat > "$TARGET/combine.sh" <<'SH'
#!/usr/bin/env bash
# 由律师画像实例生成 lawyer-yourself-skill/self.md
set -euo pipefail
PROFILE="${1:?用法: ./combine.sh templates/xxx.profile.yaml}"
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$KIT_DIR/lawyer-yourself-skill/self.md"
PY="$KIT_DIR/.combine_gen.py"
cat > "$PY" <<'PYEOF'
import sys, re, pathlib
p = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
name = re.search(r'display_name:\s*"?([^"\n]+)"?', p)
role = re.search(r'seat_role:\s*"?([^"\n]+)"?', p)
lvl  = re.search(r'level:\s*"?([^"\n]+)"?', p)
out = ["<!-- 此文件由 combine.sh 自动生成，请勿手改 -->", ""]
if name: out.append(f"# 数字分身 · {name.group(1).strip()}")
if role: out.append(f"席位角色：{role.group(1).strip()}")
if lvl:  out.append(f"回答深度：{lvl.group(1).strip()}（法教义学直给 / 不科普 / 引精准条号）")
out += ["", "## 强制纪律（源自 legal-base + LTI）",
        "- 出文前过 LTI 五维 QC + 六维门禁，REJECT=0 才交付",
        "- 法条仅引 pkulaw/元典/本地库，未回源标 statute_text_pending",
        "- 问答前检索经验卡+裁判规则库，任务后必沉淀为卡",
        "- 安全铁律：六-B / 先备份 / cp 备份 / 不代点 UI"]
pathlib.Path(sys.argv[2]).write_text("\n".join(out), encoding="utf-8")
print("✔ 已生成", sys.argv[2])
PYEOF
python3 "$PY" "$PROFILE" "$OUT"
rm -f "$PY"
SH

cat > "$TARGET/README.md" <<'MD'
# digital-avatar-kit（中小律所数字分身模板 · 开源核心骨架）
运行 `./deploy.sh` 脚手架；`combine.sh` 由律师画像模板生成各席位 self.md。
核心四件套：EV 架构 + 知识飞轮 + LTI 文本监控器 + 四模板联动。
核心骨架以 Apache-2.0 开源（专利授权条款，防 clone 后申请专利反咬）。
商业化走「开源内核 + 私有化部署 + 蒸馏服务 + 行业规则包」，不做公有云 SaaS ——
数据不出所是本方案最锋利的差异化，上云即自我摧毁，且额外触发备案与安全评估义务。
cockpit 权限层为增强组件，交付方式是私有化部署，非订阅制。
口径依据见 02-中小律所数字分身模板方法论.md（§七 / §八）。
MD

chmod +x "$TARGET/combine.sh"
echo "✔ 脚手架完成。下一步："
echo "   cd $TARGET && ./combine.sh templates/example.lawyer.profile.yaml"
