# 9655 每日评分对齐校验 · 执行记忆

- 首次运行：2026-09-21 09:02（无历史记忆文件）
- 校验结果摘要：
  1. 注入完整性 ⚠️：13块子屏10块通过；clm(C4)/xiaode(C5)/lti(C8) 三块 index.html 缺 `<body data-cno>` 且 0 处 `/subapp_score_override.js` 引用 → 评分对齐断裂。根部 override.js 存在且 node --check 通过 ✅。
  2. 漂移守护 ✅：drift_check_9655.py drift_count=0，退出码 0。
  3. 真源新鲜度 ✅：generated_at 2026-09-21 07:58:53（约1.1h内）；C1=30/C8=30/D1=23，total=64，grade=C 合格。
  4. 门禁守护 ⚠️：lti-gate-daemon 未在跑（pgrep 退出码1）→ 需本机 launchctl load。
  5. 服务可达 ✅：override.js HTTP 200。
- 处置建议：对 C4/C5/C8 重跑 scan_9655.py / 重新注入；门禁在本机真实 Terminal 执行 launchctl load。
- 未修改任何文件（只读校验）。

- 2026-09-25 13:47 运行：
  1. 注入完整性 ⚠️：C4(clm)/C5(xiaode)/C8(lti) 三块 index.html 再断裂——body 无 data-cno 且 0 处 override 引用（疑被 rescan/scan 重生成覆盖，2026-09-21 已修后回退）。其余10块+根部 override.js(node --check 通过) ✅。
  2. 漂移守护 ⚠️：drift_count=1（退出码1）；rbac.js 多出非预期屏 governance(C9) 未入基线 v1.4。
  3. 真源新鲜度 ✅：generated_at 2026-09-25 13:43:41（~0.1h）；C1=100/C8=30/D1=65.2，total=64，grade=C 合格。
  4. 门禁守护 ⚠️：lti-gate-daemon 未跑（pgrep 退出码1）。
  5. 服务可达 ✅：override.js HTTP 200。
  - 处置建议：重跑 scan_9655.py 重注入 C4/C5/C8；将 C9 纳入基线快照；本机 launchctl load 门禁。未改任何文件。

- 2026-09-26 09:11 运行（顺序无关校验，修正此前字面匹配误报）：
  1. 注入完整性 ⚠️：13块10块OK；仅 clm(C4)/xiaode(C5)/lti(C8) 三块裸 `<body>` 且无 override 引用（反复断裂，疑 gen_subapps.py 重生成覆盖）。根部 override.js 存在 + node --check ✅。decision/flywheel/mock 因 body 带 data-page-node-id 前缀，字面串误报已排除，实为OK。
  2. 漂移守护 ✅：drift_count=0，退出码0（基线已升 v1.5，C9 已纳入）。
  3. 真源新鲜度 ✅：generated_at 2026-09-26 06:50:45（~2.4h）；C1=100.0/C8=30.0/D1=65.1，total=64.0，grade=C 合格。
  4. 门禁守护 ⚠️：lti-gate-daemon 未跑（pgrep 退出码1）。
  5. 服务可达 ✅：override.js HTTP 200。
  - 处置建议：重跑 scan_9655.py 重注入 C4/C5/C8（并排查生成脚本覆盖）；本机真实 Terminal launchctl load 门禁。未改任何文件。
