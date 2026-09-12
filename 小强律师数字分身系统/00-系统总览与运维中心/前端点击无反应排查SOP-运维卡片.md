---
tags:
  - SOP
  - 运维排查
  - 前端
  - 浏览器缓存
  - jsdom
created: 2026-09-12
updated: 2026-09-12
source: ~/.workbuddy/skills/frontend-click-cache-debug-sop/SKILL.md
---

# 前端静态站点「点击无反应」排查 SOP 卡片

> **真身（单一事实源）**：本卡与 user-level skill `~/.workbuddy/skills/frontend-click-cache-debug-sop/SKILL.md` 同步。本卡为 LawKB 内可读副本；改 SOP 优先改 skill，再回填本卡。
> **触发词**：点击无反应 / 按钮点了没反应 / 静态站点交互失效 / jsdom 复现 / 浏览器缓存旧 JS / 门禁点击不弹框。

## 何时用
- 前端静态站点（如 WorkBuddy 托管的 `*.app.workbuddy.host` app）部署新交互后，用户在浏览器**点击按钮/角色卡无反应**，不弹出预期的下一步 UI（如账号密码框、弹层）。
- 你看到新界面（HTML 已更新），但点了没效果。
- 自动化/脚本改了 JS 后，线上表现与本地测试不一致。

## 关键事实（2026-09-12 实测）
- **代码逻辑正确但点击无反应，最高频根因是浏览器缓存了旧 JS**：静态托管对 `.js` 响应头常只回 `Last-Modified`、无 `Cache-Control`/`ETag` → 浏览器走**启发式缓存** → 复用改造前旧 `auth.js`（旧版没有角色按钮的 click 绑定）→ 看到新 HTML 的按钮、点了却没反应。
- **切勿一上来就改代码**：先按下面五步确凿排除「缓存旧 JS」与「源站/CDN 缓存」，确定不是运行时 bug 后再动手。
- jsdom 真实 DOM 复现是**确凿判定**代码是否真有 bug 的金标准（能复现则代码 OK、问题在缓存；不能复现则代码真有运行时错误）。

## 五步排查流程

### Step 1 · 读源码确认事件绑定逻辑（排除代码 bug）
- 读 `index.html` 的交互浮层 DOM（按钮 id、class、hidden 元素）。
- 读对应 JS（如 `auth.js`）：确认按钮 click 绑定存在、`handler` 逻辑正确（如 `roleGrid.querySelectorAll('.roleCard').forEach(b=>b.addEventListener('click',...))` → `showCredStep(role)` → `credStep.classList.remove('hide')`）。
- 读配置 JS（如 `rbac.js`）：确认 `window.COCKPIT_CONFIG` 已定义、roles/accounts 结构匹配 handler 取值路径（如 `CFG.roles[role]`）。
- 若逻辑本身有错（取值路径 undefined 抛错）→ 直接修代码；若逻辑正确 → 进入 Step 2。

### Step 2 · curl 抓线上 JS：普通版 vs cache-busting 版（排除源站/CDN 缓存）
- 普通访问（模拟浏览器，可能命中 CDN 缓存）：`curl -fsSL "$BASE/auth.js" -o /tmp/auth_plain.js`
- cache-busting（看源站真实最新）：`curl -fsSL "$BASE/auth.js?_=$(date +%s)" -o /tmp/auth_bust.js`
- 比对关键符号命中数：`grep -c 'showCredStep' /tmp/auth_plain.js` 与 `/tmp/auth_bust.js`。
- **若两者均含新代码（命中数一致且 >0）→ 排除源站/CDN 缓存，代码已上线** → 进入 Step 3 确认运行时。

### Step 3 · jsdom 真实 DOM 复现点击（确凿判定代码是否真有 bug）
- 在隔离 workspace 装 jsdom（⚠️ 见踩坑：须 `jsdom@22.1.0` 避 ESM 冲突）。
- 测试脚本：读 `index.html` → 抽取 `<script>` 顺序 → 建 JSDOM（`runScripts:'outside-only'`）→ 把 rbac.js/auth.js 内容 `window.eval` 注入 → `document.getElementById('roleGrid').querySelector('.roleCard').dispatchEvent(new window.Event('click'))` → 检查 `credStep.classList.contains('hide')` 应为 false、`credRoleName.textContent` 应为角色名 → 捕获 `window.onerror`/try-catch 里的运行时异常。
- **若点击后目标元素正确显示、零运行时错误 → 代码 100% 正确，问题必在浏览器缓存（Step 4）**。
- **若复现失败/抛错 → 代码真有运行时 bug → 据报错修代码后重发**。

### Step 4 · curl -sI 查响应头，定位启发式缓存根因
- `curl -sI "$BASE/auth.js" | grep -iE 'HTTP/|cache-control|etag|last-modified|expires'`
- **若只有 `Last-Modified`、无 `Cache-Control`/`ETag`/`Expires`** → 确诊**启发式缓存**：浏览器据 Last-Modified 估算过期时间，复用旧 JS → 这就是点击无反应的根因。

### Step 5 · 修复（强制失效旧 JS）
- `index.html` 三处脚本引用加版本号：`rbac.js`→`rbac.js?v=YYYYMMDDb`、`auth.js`→`auth.js?v=YYYYMMDDb`、`reachprobe.js`→`reachprobe.js?v=YYYYMMDDb`（每次改 JS 递增版本号）。
- `auth.js` 顶部加版本指纹：`console.log('[sso-gate] auth.js v20260912b loaded')`，便于以后一眼看出加载的是哪版。
- 六-B 备份后重发门户（保留原域名）。
- 告知用户：**硬刷新**（Mac `Cmd+Shift+R` / Win `Ctrl+Shift+R`）一次即可拉到新 JS。

## 线上验证（修复后）
- `curl -fsSL "$BASE/?_=$TS" | grep 'v=YYYYMMDDb'` → 确认 HTML 引用了版本号脚本（应 3 处）。
- `curl -fsSL "$BASE/auth.js?v=YYYYMMDDb" -o /tmp/auth_vb.js` → **静态托管须能正确处理带 query 的资源**（返回新 JS + 版本指纹 + 新符号）。若返回 404/旧版 → 改用「文件名版本化」方案（`auth.v2.js` 复制 + 引用改名）。
- 重跑 Step 3 jsdom 复测 → 点击仍正常。

## 关键踩坑
- ⚠️ **jsdom 新版 ESM/CJS 冲突**：直接 `npm i jsdom` 拉到的最新版在 node20 下 `require` 报 ESM 错误 → 降级 `npm install jsdom@22.1.0` 解决。
- ⚠️ **BSD grep 转义**：`grep -E 'a\|b'` / `{n}` 在 macOS BSD grep 下易漏匹配 → 用 `python3` 做校验（`re.search` / 直接 `in` 判断）更可靠。
- ⚠️ **同文件并行 Edit 不落盘**：对同一文件连续多次 Edit 可能后者报成功但文件未变 → 改用 Python 单线程 `s.replace()` 一次可靠替换。
- ⚠️ **急于改代码是最大浪费**：本类问题 80% 是缓存旧 JS，先 Step 2/3/4 确凿定位再动代码。

## 红线
- 六-B 铁律：改前先 `cp` 备份到 `/tmp` 时间戳目录。
- 不擅改用户凭据明文（`rbac.js` 的 `accounts` 强密码）。
- 不代 git commit（若涉及 git 仓库，仅更新备忘录单文件，由用户决定提交）。
- 修复后同步运维备忘录红线/快速访问区（门户改动必同步单一事实源）。

## 一句话口诀
> **按钮点了没反应？先别改代码——Step2 抓线上 JS 看是否真上线、Step3 jsdom 复现看代码是否真有 bug、Step4 查响应头看是不是旧 JS 被缓存。三者都排除不掉缓存，就给脚本加 `?v=` 版本号 + 顶部版本指纹，让用户硬刷新。**

## 变更日志
### v1.0.0（2026-09-12）
- 创建并同步进 LawKB 运维知识体系（可读副本，真身见 user-level skill `frontend-click-cache-debug-sop`）。基于 2026-09-12 小强总驾驶舱门户「选角色不弹账号密码框」实战：代码逻辑正确（jsdom 复现点击成功、零报错）→ 线上 `.js` 仅回 `Last-Modified` 无 `Cache-Control`/`ETag` → 浏览器启发式缓存旧 `auth.js` → 加 `?v=20260912b` 版本号修复并上线验证通过。固化五步排查法 + 踩坑（jsdom@22.1.0 降级）+ 红线。
