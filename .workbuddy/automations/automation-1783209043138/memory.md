# Spaced Repetition 复习提醒 - 执行记录

## 2026-07-07

- 扫描文件数：429 个 .md 文件
- 今日待复习笔记：5 篇
- 逾期笔记：5 篇（全部逾期 2 天）
- 今日到期：0 篇
- 输出文件：`/Users/chenyouqiang/Documents/LawKB/task-tracker/今日待复习笔记-2026-07-07.json`
- 企微推送：失败。原因：当前企业暂不支持授权机器人「消息」使用权限，同时「通讯录」权限也未授权，无法获取发送对象 userid。
- 待处理：需要用户在企业微信管理后台为应用开启「消息」和「通讯录」权限，或提供其他通知渠道。

## 2026-07-13

- 扫描文件数：471 个 .md 文件
- 今日待复习笔记：5 篇
- 逾期笔记：5 篇（全部逾期 8 天，review_date 均为 2026-07-05）
- 今日到期：0 篇
- 输出文件：`/Users/chenyouqiang/Documents/LawKB/task-tracker/今日待复习笔记-2026-07-13.json`
- 企微推送：失败。原因：`wecom-cli contact get_userlist` 与 `wecom-cli msg get_msg_chat_list` 均返回「当前企业暂不支持授权机器人「通讯录」/「消息」使用权限」。企业微信连接器虽显示 connected，但「消息」和「通讯录」权限仍未被授权。
- 待处理：需用户在企业微信管理后台为应用开启「消息」和「通讯录」权限，或改用其他通知渠道（如邮件、iMA 消息、金山文档/腾讯文档通知）。

## 2026-07-14

- 扫描文件数：417 个 .md 文件
- 今日待复习笔记：5 篇
- 逾期笔记：5 篇（全部逾期 9 天，review_date 均为 2026-07-05）
- 今日到期：0 篇
- 输出文件：`/Users/chenyouqiang/Documents/LawKB/task-tracker/今日待复习笔记-2026-07-14.json`
- 企微推送：失败。原因：`wecom-cli contact get_userlist` 与 `wecom-cli msg get_msg_chat_list` 均返回「当前企业暂不支持授权机器人「通讯录」/「消息」使用权限」。
- 与 7/7 和 7/13 相比，逾期天数从 2 天增长到 8 天再到 9 天，5 篇笔记仍未复习。
- 待处理：需用户在企业微信管理后台为应用开启「消息」和「通讯录」权限。

## 2026-07-15

- 扫描范围已迁移至 `知识飞轮系统/` 目录（72 个 .md 文件；此前统计的是全 LawKB 的更大范围，自 7/14 起任务口径收窄到知识飞轮系统）。
- 今日待复习笔记：5 篇
- 逾期笔记：5 篇（全部逾期 10 天，review_date 均为 2026-07-05）
- 今日到期：0 篇
- 输出文件：`/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/04-巩固/今日待复习笔记-2026-07-15.json`（已迁移到新路径）
- 微信 clawbot 推送：未执行。当前环境无任何 clawbot 工具/CLI/连接器（确认无 `clawbot` 命令、无 clawbot connector）。
- 企业微信兜底推送：仍未执行。`wecom-cli msg --help` 返回「当前企业暂不支持授权机器人「消息」使用权限」，权限问题依旧。
- 交付方式：通过 deliver_attachments 将 JSON 附件交付用户；提醒正文在助手回复中完整呈现。
- 待处理：需用户配置 clawbot 推送渠道，或授予企业微信「消息」权限，否则提醒长期无法主动触达。

## 2026-07-15（续：设置微信 ClawBot 推送）

- 用户确认微信 ClawBot 已绑定（settings.json 中 weixinClawBot enabled=true，channelId a8ecf8750d51@im.bot）。
- 新建推送脚本 `~/.workbuddy/skills/wechat-clawbot-push/send.py`（iLink API，纯标准库）+ SKILL.md。
- 推送测试：脚本返回 `errcode -14 session timeout`。根因：WorkBuddy 网关持有 iLink 会话（经微信 WeChatAppEx 的 ILinkServiceHost），独立脚本无法并发建会话；cursor 文件证实网关活跃轮询（a8ecf8750d51 cursor 11:20 更新）。试过 getupdates 取 token、直接用 cursor token 作 context_token，均 session timeout。
- 结论：后台自动化暂无法主动推送微信 ClawBot（session 被网关独占）；但"对话式回复"可达微信（用户此刻正经 ClawBot 对话，回复即直达微信）。
- 已更新自动化 prompt：第3步改为「脚本主推送 + session timeout 兜底（JSON+日志，待用户微信对话时补推）」。
- 今日实际交付：在对话回复中直接呈现提醒正文（经 ClawBot 送达微信），JSON 已生成并 deliver_attachments。
- 待处理：真·每日 08:00 主动推送需 WorkBuddy 原生 ClawBot 主动发送 API，或用户每日在微信给 ClawBot 发触发词（如"复习"）由助手补推。

## 2026-07-16

- 扫描文件数：98 个 .md 文件（知识飞轮系统/）
- 今日待复习笔记：6 篇
- 逾期笔记：6 篇（其中 4 篇逾期 11 天、2 篇逾期 2 天）
- 今日到期：0 篇
- **新增**：较 7/15 多了 2 篇新逾期笔记（review_date=2026-07-14，案件库/承办案件下的两个文件）
- 输出文件：`/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/04-巩固/今日待复习笔记-2026-07-16.json`
- 微信 ClawBot 推送：失败（session timeout, errcode=-14），与 7/15 一致。独立脚本无法在网关持有 iLink 会话时主动推送。
- 兜底：JSON 已 deliver_attachments 交付；提醒正文已在助手回复中呈现。
- 待处理：4 篇逾期 11 天的笔记自 7/5 起一直未复习，需用户关注。

## 2026-07-17

- 扫描文件数：97 个 .md 文件（知识飞轮系统/）
- 今日待复习笔记：10 篇（较昨天 +4 篇）
- 逾期笔记：6 篇（4 篇逾期 12 天、2 篇逾期 3 天）
- 今日到期：4 篇（均为 7/14-15 日新增提炼笔记，首次到期）
- **变化亮点**：工伤认定意见三、人体损伤程度鉴定、技术咨询合同、首席合规官签字 4 篇笔记首次进入复习周期（均为 IMA 7/14-15 日提炼笔记）
- 输出文件：`/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/04-巩固/今日待复习笔记-2026-07-17.json`
- 微信 ClawBot 推送：失败（session timeout, errcode=-14），与之前一致
- 兜底：JSON 已 deliver_attachments 交付；提醒正文在助手回复中呈现
- ⚠️ 预警：7/29 将有 5 篇人身损害赔偿相关笔记集中到期（批量复习节点），需提前准备
- 待处理：4 篇逾期 12 天的笔记自 7/5 起连续 13 天未复习，风险持续累积
