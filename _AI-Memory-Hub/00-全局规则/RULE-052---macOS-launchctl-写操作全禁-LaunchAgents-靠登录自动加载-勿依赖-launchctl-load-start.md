---
title: "RULE-052 macOS launchctl 写操作全禁·LaunchAgents 靠登录自动加载·勿依赖 launchctl load/start"
status: active
updated: 2026-09-28
source: AI
tags: [macOS, launchd, LaunchAgents, 运维铁律, OPC, 一人公司]
---

# RULE-052 · macOS launchctl 本机写操作全禁，LaunchAgents 靠登录自动加载

## 铁律（一句话）
**本机 `launchctl` 的写/控制类操作（`load` / `unload` / `bootstrap` / `start`）全部返回 `5: Input/output error`，不可用；`~/Library/LaunchAgents/*.plist` 由 launchd 在用户登录时自动加载，勿依赖 `launchctl load`/`start` 显式触发。**

## 踩坑经过（2026-09-28，连踩两轮）
1. **第一轮误判**：从 WorkBuddy Bash 沙箱跑 `launchctl load` 报 I/O error 5，AI 误判为"WorkBuddy 沙箱无用户 GUI launchd 域权限"，让老强去真实 Terminal.app 跑。
2. **第二轮纠正**：老强在真实终端（ttys002）跑同样的 3 条 `launchctl load` **依然全报 `Load failed: 5: Input/output error`**；`launchctl start` 同样无效（lti-gate 仍 `- 2`）。
   ⇒ 根因不是沙箱，是**本机 launchd 提交/控制域的机器级限制**——真实终端也无 submit 权限。

## 事实（实测）
- `launchctl load` / `unload` / `bootstrap` / `start` → 均 `5: Input/output error`（写/控制全禁）。
- `launchctl list` → 读正常，能返回已加载的 job（证明 LaunchAgents 已被自动加载）。
- `~/Library/LaunchAgents/*.plist`：**launchd 在用户登录时自动加载**，无需 `launchctl load`。
- 该机 3 条 plist：`com.xiaoqiang.flywheel-sync` / `com.xiaoqiang.lawtwin-probes`（每日定时，RunAtLoad=false）/`com.xiaoqiang.lti-gate`（RunAtLoad=true, KeepAlive）。

## 正确处置（替代 launchctl load/start）
- **要常驻**：把 plist 放 `~/Library/LaunchAgents/` 即可；下次注销/重启登录，launchd 自动 `RunAtLoad` 拉起，无需任何命令。
- **本会话就要让守护活起来**：从 WorkBuddy 后台直跑脚本本身（等价于 plist 的 `ProgramArguments`），例如
  `/Users/chenyouqiang/.workbuddy/binaries/python/versions/3.13.12/bin/python3 ".../lti-gate-daemon.py" --socket /tmp/lti-gate.sock`
  （实测可活 2h33m+；重启后 launchd 自动接管，无冲突）。
- **验证是否常驻**：`launchctl list | grep xiaoqiang` 能看到三项即已自动加载（PID=- 对定时任务属正常）；O1 审计探针 `overall=OK` 证门禁活。

## 边界 / 注意
- **陈旧 sock 冲突（含 AI 手动直跑自冲突·2026-09-28 实测）**：若 `/tmp/lti-gate.sock` 被占用——含 AI 为过 O1 探针从 WorkBuddy 后台直跑的 lti-gate 实例（该实例占 sock 至 11:17，期间把 launchd 的 `RunAtLoad` 自动拉起挡在门外→ExitStatus=2）——launchd 绑定失败。处置：真实终端 `rm -f /tmp/lti-gate.sock` 清掉再重启即可。**⚠️ 严禁重复直跑**：实例若已由 `~/Library/LaunchAgents/` 托管（RunAtLoad），AI 勿再手动直跑同 sock 实例，否则与自动加载抢 sock 自冲突、反把门禁挡死。
- **沙箱视图隔离**：WorkBuddy 沙箱里 `launchctl list` 读不到用户域项，与真实磁盘不一致，**以老强真实终端输出为唯一权威**。
- 关联：O1 运维可审计支柱、lti-gate 守护、9655 驾驶舱探针链、H3 pending 清零。

## 来源
- 2026-09-28 实测（老强真实终端 I/O error 5 + WorkBuddy 直跑兜底复活 lti-gate，O1 探针 overall=OK）。AI 落卡防复发。

## 相关笔记
- [[安装selfimprovingagent让WorkBuddy学会自己改进]] (共现关键词: 医疗, 自动, 合同)
- [[2026-09-14-价值复盘]] (共现关键词: ---, 自动, 合同)
- [[lti_semantic_rules.json]] (共现关键词: 医疗, lti, 合同)
- [[律师27SOP复盘与数字分身借鉴方案-v1.0]] (共现关键词: gate, 合同)
- [[2026-10-08]] (共现关键词: gate, 合同)
- [[国际贸易合同出口业务操作指引-2026-07-22]] (共现关键词: 公司, 操作, 共现)
- [[律师签发律师函业务操作指引2021-2026-07-21]] (共现关键词: 公司, 操作)
- [[R-PI-271-后续治疗费与医疗依赖计算康复费整容费]] (共现关键词: 公司, 共现, 依赖)
- [[R-PI-246-护理费的计算口径与护理依赖]] (共现关键词: 诉讼, 依赖)
- [[R-GS-052-所有权保留买卖合同解除与继续履行的共益债务]] (共现关键词: 052, 公司, 诉讼)
- [[R-SH-052-惩罚性赔偿倍数的确定规则]] (共现关键词: 052, ##, 诉讼)
- [[R-CF-052]] (共现关键词: 052, 慈善, 共现)
- [[轨迹卡-北大法宝连接器90001排查的认知纠偏路径-20260916]] (共现关键词: 加载, 共现)
- [[lti_element_cards.json]] (共现关键词: 共现, lti)
- [[MEMORY]] (共现关键词: 共现, gate, lti)
- [[2026-09-21]] (共现关键词: gate, lti)
- [[RULE-050---不动-gate-config.md，符合非破坏性扩展铁律]] (共现关键词: RULE, ---, 共现)
- [[小德慈善组织合规管理系统_字段配置表（慈善版）]] (共现关键词: ---, 诉讼, 慈善)
- [[连接枢纽-商事]] (共现关键词: ##, ---, 自动)
- [[连接枢纽-慈善法]] (共现关键词: ##, ---, 自动)
- [[2026-09-21-小强律师数字分身系统（单机密文版）]] (共现关键词: ---, 自动)
- [[DEC-2026-001-技能黑名单自动启用]] (共现关键词: ##, ---, 自动)
- [[（二）告别依赖鉴定主动拆解诊疗核心过错的实战方法]] (共现关键词: ##, 依赖)
- [[RULE-013---点火条件仍依赖用户在连接器页对-ima-mcp-重新信任授权+重启（不代点U]] (共现关键词: ---, RULE, 依赖)
- [[WF-038---当前阻塞：运行会话-MCP-工具索引为启动快照，配置修复后须再重启一次方加载]] (共现关键词: ---, 加载)
- [[2026-09-18-初版部署记录]] (共现关键词: ##, lti)
- [[README]] (共现关键词: ##, lti)
- [[WF-052-QQ-摘要已发送（SMTP-兜底，主题标注撤销外部消耗误报）]] (共现关键词: ---, 052)
- [[经验卡-删源前必验服务真在目标位-观察期满不等于风险窗口关闭-20260926]] (共现关键词: ---, launchd, 公司)
- [[经验卡-9655真源位迁移未完成-launchd仍指旧会话目录-20260926]] (共现关键词: ---, launchd)
- [[操作指南_验证最高法院判例_20260527]] (共现关键词: 操作, 公司)
- [[操作指南_查询对方代理人情况_20260527]] (共现关键词: 操作, 公司)
- [[经验卡-9655心跳断流-fresh_h38h-扫描任务launchd未加载-20260927]] (共现关键词: launchctl, load, ---)
- [[CRT-20260927-01]] (共现关键词: launchctl, ---, 公司)
- [[医疗纠纷诉讼实务全流程操作指引]] (共现关键词: 操作, 公司)
- [[PREF-003-安全操作铁律]] (共现关键词: ---, 操作)
