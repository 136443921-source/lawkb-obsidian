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
