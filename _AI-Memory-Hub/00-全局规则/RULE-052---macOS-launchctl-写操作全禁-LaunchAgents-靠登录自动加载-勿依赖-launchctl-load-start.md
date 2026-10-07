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
- [[医疗纠纷诉讼实务全流程操作指引]] (共现关键词: 操作, 公司)
- [[PREF-003-安全操作铁律]] (共现关键词: ---, 操作)
