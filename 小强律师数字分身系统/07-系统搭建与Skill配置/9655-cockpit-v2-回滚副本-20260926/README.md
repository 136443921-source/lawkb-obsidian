# 小强总驾驶舱 · 内部操作版（公网原版 1:1 还原）

> 本目录 = 公网 `xiaoqiang-cockpit-hub.app.workbuddy.host`（wbapp_8oxQaImtlGQF5gmODMx19W）的 **1:1 本地还原**。  
> 源：`/Users/chenyouqiang/WorkBuddy/2026-09-05-03-33-49/cockpit-portal/portal`（`.genie` 标定的 localDir）。

## 与公网版的关系

- **门户 6 文件原样复制**：`index.html` / `auth.js` / `rbac.js` / `scorecard_data.json` / `workbench.html` / `rescan_scorecard.py`
- **登录机制 1:1 原版**：令牌粘贴 + 演示角色按钮（Web Crypto HMAC 签发），未改逻辑
- **评分数据 1:1 原版**：`scorecard_data.json` 实扫值 总分 **81.0 / 良好 B / 2026-09-12 17:51:54**
- **唯一改动**：原版 9 屏里 7 个指向已下线 sandbox 的外链（404/离线），改为指向本地 `subapps/` 下的**官方原生子屏文件**（见下表），使内部操作版真正可用。cardfamily / cloud 仍指向在线外链（原样保留，本就在跑）。

## 子屏本地化对照

| 屏               | 原外链状态      | 内部版来源                                         |
| --------------- | ---------- | --------------------------------------------- |
| 模拟法庭 mock       | 离线 link    | `mock-trial-center/index.html`                |
| 车机 ev           | 离线 sandbox | `cheji/index.html`                            |
| 知识飞轮 flywheel   | 离线 sandbox | `feilun/index.html`                           |
| 决策思维树 decision  | 离线 sandbox | `juesi/index.html`                            |
| 积分监测 credits    | 离线 sandbox | `jifen/index.html`                            |
| AI 幻觉监控 lti     | 404        | `lti/index.html`                              |
| 案件生命周期 clm      | 404        | `Claw/case-lifecycle/dashboard/案件生命周期大屏.html` |
| 系统卡族 cardfamily | ✅在线        | 保留外链                                          |
| 云服务监控 cloud     | ✅在线        | 保留外链                                          |

## 运行方式（必须用本地 http 服务，勿 file:// 双击）

原版登录用 Web Crypto、首页用 `fetch()` 拉 JSON，**仅在安全上下文可用**，故需本地服务：

```bash
cd /Users/chenyouqiang/WorkBuddy/2026-09-12-01-29-05/outputs/cockpit-hub-ops
python3 -m http.server 9360
# 浏览器打开 http://127.0.0.1:9360/
```

登录页点「执业律师 / 律所主任」等演示席位即可进入（签发本地令牌）。

## &#x20;⚠️ 红线

含真实案号/当事人/额度/评分，**严禁外发**。与已上线脱敏演示版 `cockpit-hub-demo.app.workbuddy.host` 严格区分。

## 重建脚本

`build_restore.py`：一键从官方源重新 1:1 拉取并本地化（改 rbac 链接），可复现。

## 本地预览（保活一键启动）

`./start_cockpit_hub_ops.sh` 启动并保活本地服务（采用 `os.setsid()` 脱离进程组，命令结束不被回收）；`--restart` 杀旧进程并重启为受管进程（pidfile `.cockpit_ops.pid` + 日志 `.cockpit_ops.log`）。访问 `http://127.0.0.1:9360/`（令牌登录，账号见上「运行方式」）。
