---
id: WF-034
title: jsdom 无头校验替代浏览器手点（前端交互回归法）
type: workflow
status: active
updated: 2026-09-14
source_ai: workbuddy
scope: global
confidence: high
tags:
  - 前端校验
  - 无头测试
  - 回归
  - jsdom
  - 可复用方法论
---

# jsdom 无头校验替代浏览器手点（前端交互回归法）

> 来源：2026-09-14 模拟法官中台建设实践。老强原建议"浏览器手动点一遍 confirm 交互"，改为 jsdom 无头 harness 挂载真实 HTML 跑全链路，由 AI 全权处理验证。
> 本条只沉淀方法论，个案交互细节不入中枢。

## 适用场景

任何含前端交互（抽屉、表单、事件绑定、localStorage 持久化）的 HTML 产物，需要验证"点击→状态→渲染→持久化"链路，但又不想依赖人工点验或 playwright 重武器时。核心价值：**把"老强手点"变成可回归、可累积的资产**。

## 一、标准 harness 骨架

1. **剥离脚本挂载**：`const htmlNoScript = html.replace(/<script[\s\S]*?<\/script>/g, "")`，用 `new JSDOM(htmlNoScript, { runScripts:'outside-only', pretendToBeVisual:true, url:'https://localhost/' })` 挂载。**`url` 是启用 `localStorage` 的开关**——缺它 localStorage 为 undefined，证据持久化等测试直接崩。
2. **依赖注入**：把被测模块挂到 `window`：`window.SUBSUMPTION = require('./subsumption_engine.js')` 等；`window.toast = ()=>{}` 等 stub 兜底。
3. **只 eval 需要的函数，不跑整 app init()**：整 app 的 `init()` 依赖大量 DOM 元素，缺一个就 `Cannot set properties of null` 崩。用 `html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)` 取 inline blocks，再用 `blocks.find(b => /function renderChain/.test(b))` **精确匹配定义段**（避免抓到调用段）。
4. **getElementById stub 兜底**：`window.document.getElementById = (orig => id => orig.call(window.document,id) || {value:'',innerHTML:'',onclick:null,classList:{add(){},remove(){}},style:{}})(window.document.getElementById)`，防 null 崩。
5. **触发交互**：`el.value = '...'; el.click()` 或 `dispatchEvent`，再断言 `output.innerHTML` 含关键标记。

## 二、多套件分工（避免一锅烩）

- **回归 harness**（如 15/15）：验证既有交互不破，每次改动必跑。
- **eval 断言套件**（如 39 项）：纯函数/引擎层机器可断言（结论类型、§F 门控、REJECT=0、竞合识别），不依赖 DOM。
- **专项 e2e**（如 10/10）：针对新接入模块做端到端渲染+回写验证。

三者分工：eval 管"逻辑对不对"，harness 管"交互没破"，e2e 管"新模块真接进去了"。

## 三、两个必踩的坑（复用必看）

1. **Node 全局 vs window 标识符**：UMD 模块在 jsdom eval 中，`const X = require(...)` 的裸标识符 `X` 不在 Node `global` 作用域 → 改为 `global.X = require(...)` + `window.X = ...` **双轨挂载**，eval 内才能直接用 `X`。
2. **函数提取用「独占换行结尾」正则**：从 HTML 抠真实源码时，用 `blocks.filter(b => /function renderChain/.test(b))` 会同时命中"定义段"和"调用段"；改成精确匹配定义段的标识（如 `window.renderChain = function` 或独占 `\n}` 包裹）才稳。

## 四、红线

- 不 eval 整 app 脚本（init 必崩）。
- 不改被测 HTML 源码来验证（那是假通过）；harness 只挂载、不篡改。
- 断言必须可量化（含某标记 / 计数 > 0），禁"看起来对"。

## 五、价值

把"人工点验"升级为 CI 快通道：每次改完前端，跑 harness+e2e，全绿才交付。换人、换时、换机都不失忆。

## 相关笔记
- [[R-PR-159-物证原物出示规则(动产·不动产·复制件替代)]] (共现关键词: ##, 替代, 证据)
- [[R-PI-396-用人单位工作人员执行工作任务致害替代责任]] (共现关键词: ##, 替代)
- [[WF-050-多副本大屏UI元素全盘清除流水线]] (共现关键词: WF, 证据, HTML)
- [[前端点击无反应排查SOP-运维卡片]] (共现关键词: ##, jsdom, 浏览器)
- [[WF-029-静态看板改版前端三坑排障流水线]] (共现关键词: 证据, 浏览器, ##)
- [[技能卡库挂载普查报告-2026-09-08]] (共现关键词: 证据, 挂载)
- [[WF-026-审判要件卡拆卡流水线]] (共现关键词: WF, 挂载)
