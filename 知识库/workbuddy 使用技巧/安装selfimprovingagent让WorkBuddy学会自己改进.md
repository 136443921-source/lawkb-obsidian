---
created: 2026-06-25T15:22
updated: 2026-08-14T00:10
title: 安装selfimprovingagent让WorkBuddy学会自己改进
tags: []
maturity: 🌱种子
source: ""
related: []
last_review: ""
review_interval: 7
difficulty: 3
importance: 3
status: draft
---

https://mp.weixin.qq.com/s/VaJ1j4pbwYo1J8g2SJQGcg

# 安装self-improving-agent：让WorkBuddy学会自己改进

很多人用 AI时会遇到这个问题：AI 犯了同样的错，下次还会再犯。有没有办法让它记住错误、自动改进？

有。安装 self-improving-agent 技能 + 配置自动 Hook，就能让你的 AI 助手WorkBuddy 具备持续学习能力。

## 📋 整体流程

只有3步很简单：

1安装 self-improving-agent 技能2安装 Hook，设置自动响应3运行每日升级计划，闭环改进## 第一步：安装 self-improving-agent

方法一：在 WorkBuddy 对话框中直接输入：安装 self-improving-agent 技能

AI 会自动完成安装，完成后显示安装成功提示。

![](wechat_img_1782372169897_160.jpg)

方法二：打开WorkBuddy，进入技能商店，搜索“self-improving-agent ”，点击安装

到这一步，技能装好了，但 AI 还不会自动学习——需要第二步。

## 第二步：安装 Hook，实现自动响应

Hook 的作用：每次工具调用结束后，自动触发学习和纠错流程，无需手动干预。

在对话框中输入：

> 安装hook：self-improving-agent，自动响应，执行自动的升级计划

![](wechat_img_1782372170106_889.jpg)



AI 会自动完成三件事：

✅ 开启自动纠错：每次工具调用后自动检查是否有错误

✅ 启用自动学习：检测到可改进的内容时自动记录

✅ 全程无需手动确认，后台静默运行

配置完成后，你的 AI 助手就开始「默默学习」了。

**什么是 Hook？** 简单说就是一个触发器。你给 AI 设定一个规则："每次你用完工具之后，检查一下有没有犯什么值得记住的错。" AI 就会在每次操作后自动执行这个检查。

## 第三步：执行每日升级计划

安装和配置都搞定了，但 AI 的学习还只是"记在脑子里"，没有变成"肌肉记忆"。

每天（或定期）AI会自动在对话框中触发一次升级检查：

> 执行每日自我改进检查：运行 daily-upgrade-check.sh 脚本，检查待升级的学习条目，生成报告，并根据报告建议处理高优先级问题。

AI 会自动完成：

1读取 ```
.learnings/
```

 中的学习记录2分析哪些内容值得升级为「项目内存」3生成优先级报告保存到 ```
reports/
```

 目录4处理高优先级问题，完成知识沉淀![](wechat_img_1782372170308_472.jpg)

## 总结

![](wechat_img_1782372170452_480.jpg)



三步完成配置，AI 助手从此具备持续自我改进能力：

**安装技能 → 配置 Hook → 定期运行升级**

WorkBuddy就可以学会自我改进啦！



---
*Source: [WeChat Article](https://mp.weixin.qq.com/s/VaJ1j4pbwYo1J8g2SJQGcg)*

## 相关笔记
- [[小强律师AI助手自我进化报告-20260624]] (共现关键词: 改进, AI)
- [[如何用AI构建自己的案件管理系统-2026-07-24]] (共现关键词: ##, 自己, AI)
- [[工具之外法律人研究AI和Skill研究的是自己的新位置]] (共现关键词: 自己, AI)
- [[我花了两小时用WorkBuddyObsidian搭了一个会自己进化的个人知识库wiki]] (共现关键词: 自己, WorkBuddy, AI)
- [[知识飞轮系统复盘报告-20260713]] (共现关键词: ##, 自动)
- [[WorkBuddy这15个功能一个比一个香建议收藏]] (共现关键词: ##, 自动, WorkBuddy)
- [[装上这7个Skills你的WorkBuddy直接起飞]] (共现关键词: ##, 自动, WorkBuddy)
- [[用ObsidianCodex搭一个会主动思考的个人知识库]] (共现关键词: ##, 自动)
- [[memory]] (共现关键词: ##, self)
- [[设备采购安装合同模板-审查要点-2026-08-05]] (共现关键词: 安装, ##)
- [[Obsidian极简安装指南]] (共现关键词: 安装, ##)
