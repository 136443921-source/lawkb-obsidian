# 自动化执行记忆：9655 每日评分对齐校验

## 最近执行
- 2026-09-28 09:48 (GMT+8) 由定时自动化触发，无人值守，报告 3 块注入失败。
- 2026-09-28 10:32 (GMT+8) 老强指令「立即处理」→ 已对 clm(C4)/xiaode(C5)/lti(C8) 精准注入 data-cno + override 引用；备份 /tmp/9655-reinject-20260928-103209/；复核 13/13 全过。

## 结论速览
- 注入完整性：根部 `subapp_score_override.js` 存在且 `node --check` 通过 ✅；13 块子屏中 10/13 通过（含 data-cno 且恰好 1 处 /subapp_score_override.js 引用）。
- ⚠️ 3 块真失败：`clm`(C4)、`xiaode`(C5)、`lti`(C8) 为裸 `<body>` 标签、无 data-cno、0 处 override 引用 → 评分对齐机制断开。
- 注：`decision`(C2)/`flywheel`(C3)/`mock`(C6) 的 data-cno 位于 data-page-node-id 之后，属性仍生效，按功能判为 OK（非字面 `<body data-cno>` 顺序）。
- 注：全树未找到任何 9360 字节副本文件；实际子屏为 subapps/<name>/index.html（40KB~400KB），"9360 字节副本"描述已与实际不符，疑机制变更，待老强确认。
- 漂移守护 drift_count=0、exit 0 ✅
- 真源新鲜度：generated_at 2026-09-28 08:24:50，age≈1.77h <24h ✅；C1=100.0 / C8=30.0 / D1=64.9；total=64.0 grade=C 合格
- 门禁守护 lti-gate-daemon 运行中（PID 67918）✅
- 服务可达 127.0.0.1:9655/subapp_score_override.js → HTTP 200 ✅

## 处置结果（2026-09-28 10:32 已执行）
- ✅ 已对 clm(C4)/xiaode(C5)/lti(C8) 精准注入：`<body data-cno="Cx">` + 1 处 `<script src="/subapp_score_override.js?v=20260919b"></script>`（置于 `</body>` 前，与 10 块 OK 子屏版本号一致）。
- 备份原件：`/tmp/9655-reinject-20260928-103209/`（clm/xiaode/lti 各一份 .bak）。
- 复核：重新跑注入校验 → **13/13 ALL_OK**（body_OK + ovr_refs=1 全部满足）。
- 注：scan_9655.py / gen_subapps.py 均无 override 注入例程，故走精准注入而非重跑脚本；若后续有夜间重新生成，需关注这 3 块是否再次被覆盖。
- 遗留待老强确认："9360 字节副本"描述与实际 subapps/<name>/index.html（40KB~400KB）不符，疑机制变更——注入校验对象以实际 index.html 为准。

## 2026-09-29 09:08 (GMT+8) 定时自动化触发，无人值守
- 注入完整性 ⚠️ 10/13：clm(C4)/xiaode(C5)/lti(C8) 再次变为裸 `<body>`、0 处 override 引用（09-28 已注入，疑夜间 gen_subapps 重生覆盖）。根部 override.js 存在且 node --check PASS ✅。
- 漂移守护 drift_count=0、exit 0 ✅
- 真源新鲜度 ✅ generated_at 2026-09-29 09:08:31（age≈0.03h）；C1=100.0 / C8=60.0 / D1=64.5；total=69.0 grade=C 合格
- 门禁守护 ⚠️ lti-gate-daemon 未运行（pgrep 无结果）
- 服务可达 ✅ 127.0.0.1:9655/subapp_score_override.js → HTTP 200
- 全程只读校验，未修改任何文件。建议：① C4/C5/C8 重新精准注入 + 排查重生覆盖根因；② 本机真实 Terminal 执行 launchctl load 门禁 plist。

## 2026-09-30 09:19 (GMT+8) 定时自动化触发，无人值守
- 注入完整性 ⚠️ 10/13：clm(C4)/xiaode(C5)/lti(C8) 再次裸 `<body>`、0 处 override 引用（覆写复发，连续第 3 日）。根部 override.js 存在 + node --check PASS ✅。
- 漂移守护 ✅ drift_count=0、exit 0。
- 真源新鲜度 ✅ generated_at 2026-09-30 09:17:30（age≈0.04h）；C1=100.0 / C8=60.0 / D1=64.5；total=69.0 grade=C 合格。
- 门禁守护 ⚠️ lti-gate-daemon 未运行。
- 服务可达 ✅ HTTP 200。
- 全程只读，未改文件。建议同前：① 根治→将注入固化进 gen_subapps.py 或持久模板，避免夜间重生覆盖；② 真实 Terminal 执行 launchctl load 门禁 plist。

## 2026-10-01 11:15 (GMT+8) 定时自动化触发，无人值守
- 注入完整性 ⚠️ 10/13：clm(C4)/xiaode(C5)/lti(C8) 再次裸 `<body>`、0 处 override 引用（覆写复发，连续第 4 日）。根部 override.js 存在 + node --check PASS ✅。
- 漂移守护 ✅ drift_count=0、exit 0。
- 真源新鲜度 ✅ generated_at 2026-10-01 11:12:12（age≈0.06h）；C1=100.0 / C8=60.0 / D1=64.4；total=69.0 grade=C 合格。
- 门禁守护 ⚠️ lti-gate-daemon 未运行（连续第 3 日）。
- 服务可达 ✅ HTTP 200。
- 全程只读，未改文件。建议同前：① 根治→将注入固化进 gen_subapps.py 或持久模板，避免夜间重生覆盖；② 真实 Terminal 执行 launchctl load 门禁 plist。

## 2026-10-02 22:31 (GMT+8) 定时自动化触发，无人值守
- 注入完整性 ⚠️ 10/13（功能判）：clm(C4)/xiaode(C5)/lti(C8) 再次裸 `<body>`、无 data-cno、0 处 override 引用（覆写复发，连续第 5 日）；根部 override.js 存在 + node --check PASS ✅。
- 注：字面 `<body data-cno="Cx">` 仅 7 块精确匹配（C1/C7/D1/D2/D4/D5/D6）；C2/C3/C6 data-cno 在后续属性、功能仍 OK。
- 漂移守护 ✅ drift_count=0、exit 0。
- 真源新鲜度 ✅ generated_at 2026-10-02 22:27:26（age≈0.07h）；C1=100.0 / C8=60.0 / D1=64.4；total=69.0 grade=C 合格。
- 门禁守护 ⚠️ lti-gate-daemon 未运行（pgrep 无结果，连续第 4 日）。
- 服务可达 ✅ HTTP 200。
- 全程只读，未改文件。建议同前：① 根治→将注入固化进 gen_subapps.py 或持久模板；② 真实 Terminal 执行 launchctl load 门禁 plist。

## 2026-10-04 11:27 (GMT+8) 定时自动化触发，无人值守
- 注入完整性 ⚠️ 根部 override.js 存在 + node --check PASS ✅；13 块子屏字面 `<body data-cno>` 仅 7/13，功能 data-cno 10/13、override 引用 10/13。clm(C4)/xiaode(C5)/lti(C8) 仍裸 `<body>`、无 data-cno、0 处引用（覆写复发，连续第 7 日）；C2/C3/C6 仅属性顺序不符、功能 OK。
- 漂移守护 ✅ drift_count=0、exit 0。
- 真源新鲜度 ✅ generated_at 2026-10-04 10:43:49（age≈0.74h<24h）；C1=100.0 / C8=60.0 / D1=64.4；total=69.0 grade=C 合格。
- 门禁守护 ⚠️ pgrep 无 lti-gate-daemon（连续多日未跑）；scorecard 面板标"运行中"为假阳性。
- 服务可达 ✅ HTTP 200。
- 全程只读，未改文件。注：未找到"9360 字节副本"文件，按实际 subapps/<name>/index.html 校验。建议同前：① C4/C5/C8 重新精准注入 + 固化进 gen_subapps.py；② 真实 Terminal launchctl load 门禁 plist。

## 2026-10-03 09:02 (GMT+8) 定时自动化触发，无人值守
- 注入完整性 ⚠️ 根部 override.js 存在 + node --check PASS ✅；13 块子屏字面 `<body data-cno>` 仅 7/13，功能 data-cno 10/13、override 引用 10/13。C4(clm)/C5(xiaode)/C8(lti) 仍裸 `<body>`、无 data-cno、0 处引用（覆写复发，连续第 6 日）；C2/C3/C6 仅属性顺序不符、功能 OK。
- 漂移守护 ✅ drift_count=0、exit 0。
- 真源新鲜度 ✅ generated_at 2026-10-03 09:01:33（age≈0.02h）；C1=88.0 / C8=60.0 / D1=64.3；total=69.0 grade=C 合格。注：C1 由 100.0 降至 88.0（主机 CPU85.9%/负载11.67 拉低），属真值变化。
- 门禁守护 ⚠️ pgrep 无 lti-gate-daemon（连续第 5+ 日未跑）；scorecard 面板却标"✅运行中/plist已装"，与实际不符→仪表盘门禁状态为假阳性。
- 服务可达 ✅ HTTP 200。
- 全程只读，未改文件。建议：① C4/C5/C8 重新精准注入 + 固化进 gen_subapps.py 防重生覆盖；② 真实 Terminal 执行 launchctl load 门禁 plist；③ 核实 scorecard 门禁状态为何显示"运行中"而 pgrep 无进程。

## 2026-10-07 10:29 (GMT+8) 定时自动化触发，无人值守
- 注入完整性 ⚠️ 根部 override.js 存在 + node --check PASS ✅；13 块功能判 10/13 OK（ev/C2/C3/C6/C7/D1/D2/D4/D5/D6），字面 `<body data-cno>` 8/13（C2/C3/C6 属性顺序不符、功能 OK）。clm(C4)/xiaode(C5)/lti(C8) 仍裸 `<body>`、无 data-cno、0 处 override 引用（覆写复发，连续第 9+ 日）。
- 漂移守护 ✅ drift_count=0、exit 0。
- 真源新鲜度 ✅ generated_at 2026-10-07 10:27:25（age≈0.05h<24h）；C1=100.0 / C8=60.0 / D1=64.3；total=69.0 grade=C 合格（scorecard 结构改为 screens[] 用 cno 字段）。
- 门禁守护 ⚠️ pgrep 无 lti-gate-daemon（连续多日未跑）；面板标"运行中"为假阳性。
- 服务可达 ✅ HTTP 200。
- 全程只读，未改文件。未找到"9360 字节副本"文件，按实际 subapps/<name>/index.html 校验。建议同前：① C4/C5/C8 重新精准注入 + 固化进 gen_subapps.py 持久模板防覆盖；② 真实 Terminal launchctl load 门禁 plist。

## 2026-10-06 11:58 (GMT+8) 定时自动化触发，无人值守
- 注入完整性 ⚠️ 根部 override.js 存在 + node --check PASS ✅；13 块子屏功能判 10/13 OK（含 data-cno 且恰好 1 处 override 引用），字面 `<body data-cno>` 仅 7/13（C2/C3/C6 属性顺序不符、功能 OK）。C4(clm)/C5(xiaode)/C8(lti) 仍裸 `<body>`、无 data-cno、0 处引用（覆写复发，连续第 8+ 日）。
- 漂移守护 ✅ drift_count=0、exit 0。
- 真源新鲜度 ✅ generated_at 2026-10-06 11:58:48（age≈0h<24h）；C1=100.0 / C8=60.0 / D1=64.3；total=69.0 grade=C 合格。
- 门禁守护 ⚠️ pgrep 无 lti-gate-daemon（连续多日未跑）；scorecard 面板标"运行中/plist已装"为假阳性。
- 服务可达 ✅ HTTP 200。
- 全程只读，未改文件。未找到"9360 字节副本"文件，按实际 subapps/<name>/index.html 校验。建议同前：① C4/C5/C8 重新精准注入 + 固化进 gen_subapps.py 防重生覆盖；② 真实 Terminal launchctl load 门禁 plist。
