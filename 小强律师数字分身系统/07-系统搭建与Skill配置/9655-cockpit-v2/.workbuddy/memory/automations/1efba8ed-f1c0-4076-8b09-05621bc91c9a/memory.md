# 9655 手册口径漂移比对 · 执行记忆

## 2026-11-23 09:29 运行（首次记录）

- **结果：❌ 比对无法执行（工具链断供），非"无漂移"**
- 指定路径 `9655-cockpit-v2/drift_check_9655.py` 不存在；全盘搜索唯一副本在废弃归档目录 `~/WorkBuddy/_归档/2026-09/2026-09-17-16-22-53/outputs/9655-cockpit-v2/`（prompt 明令严禁引用）
- 实车目录（长期资产位）launchd 探针活着（7 个 JSON 今日 09:25 更新），但：
  - 🔴 `scan_9655.py` 缺失 → `com.xiaoqiang.cockpit9655.scan` 每 300 秒报错（.9655_scan.err 持续堆积），scorecard 无法再生成
  - 🔴 `rbac.js`、`drift_check_9655.py`、`scorecard_data.json` 均不在实车目录
- `_AI-Memory-Hub` 镜像 scorecard_data.json 停更于 **2026-10-02 22:03**（19 屏，total 69.0 / C 合格）——已过期 52 天，不可作真源
- **处置：未用旧数据强行比对（避免假阴性"对齐"结论）；未擅自迁移/修改任何文件（RULE-011）**；报告对话呈现，给 A/B/C 修复建议待老强确认
- 待办：老强确认方案后补迁三件套（scan_9655.py / rbac.js / drift_check_9655.py）至长期资产位并重跑
