# 9655  cockpit-v2 项目长期记忆

## 运维铁律 / 已知坑
- **LTI 门禁守护(com.xiaoqiang.lti-gate)必须在真实 GUI 会话拉起**：launchctl 用户域 LaunchAgent 须注入 `gui/501`；WorkBuddy 沙箱 / SSH 无 GUI 会话会因 launchd 域不可达稳定报 `I/O error 5`（Bootstrap failed / Load failed），属**预期边界**非故障。一键脚本 `start_lti_gate.sh`（终端）/ `start_lti_gate.command`（Finder 双击）已封装双路径加载 + 诚实失败检测（I/O error5 时退出码1，不再误报"加载成功"）。详见 9655 运维手册 §6.1。
- **每日评分对齐校验**：13 块 9360 副本子屏须含 `<body data-cno="Cx">` + 1 处 `/subapp_score_override.js` 引用；**已于 2026-09-21 补齐 clm(C4)/xiaode(C5)/lti(C8) 三块缺失注入（统一串 `<script src="/subapp_score_override.js?v=20260919b"></script>`，备份在 /tmp/9655-subapp-inject-20260921-105250），现 13 块全过**。根 `subapp_score_override.js` 经 `node --check` 通过。drift_check_9655.py 退出码 0=对齐。
- 脚本坑：bash 内置 `UID` 为只读变量，接收 `id -u` 须用小写 `uid`；`launchctl load` 在 I/O error5 时退出码仍 0，须查 stderr "load failed" 判定。

## 关键路径
- 9655 运维手册：LawKB/小强律师数字分身系统/00-系统总览与运维中心/9655 驾驶舱运维手册.md（v1.4，只读运维层）
- 基线快照：同目录 9655_驾驶舱基线快照.json（drift_check 比对真源）
- 门禁 plist：~/Library/LaunchAgents/com.xiaoqiang.lti-gate.plist
