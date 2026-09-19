---
id: LAWYER-AVATAR-LTI-GATE
title: 律师分身·单机密文版 · LTI 门禁独立进程（G2）
status: active
living_doc: true
related:
  - 小强律师数字分身系统/00-系统总览与运维中心/LTI文本监控系统运维手册-v2.md
  - WorkBuddy/2026-08-08-15-48-47/lti_gate.py
scope: lawyer-avatar-only
updated: 2026-09-18T20:19
tags:
  - LTI
  - lti
  - gate
  - 
  - py
created: 2026-09-18T20:19
---

# LTI 门禁 · 独立进程化（G2 交付物）

> **范围声明**：本目录及本说明**仅引用律师分身（小强律师数字分身系统）资产**，不含「律所分身」相关内容。

## 一、要解决的问题

LTI 文本监控器（v4.8.6，131 测试全绿）原本作为 WorkBuddy skill 内部流程运行，
交付门禁 `lti_gate.py` 只能由特定会话脚本直接调用。在「单机密文版」里，我们需要把
这道门禁**独立成常驻进程**，让 M1 推理、docx 导出流水线、人工交付前校验等任意上游
都能通过本地 socket 调用它，拿到结构化 PASS / REJECT 判定，而不必耦合 LTI 内部的
26 个脚本与缓存体系。

## 二、交付物清单（本目录）

| 文件 | 作用 |
|------|------|
| `lti-gate-daemon.py` | Unix socket 守护进程：接收 `{path}`，subprocess 调用 `lti_gate.py`，回写 `{status,exit,report,ts}` |
| `lti-gate-client.py` | 客户端 CLI：把 docx 递交给守护进程并打印判定；支持 `--ping` 健康检查 |
| `com.xiaoqiang.lti-gate.plist` | macOS launchd 服务定义（开机自启 + 崩溃自愈 `KeepAlive`） |
| `README.md` | 本说明 |

> 被封装的成熟代码 `lti_gate.py` **原样调用、零修改**——本目录只是它的「进程级门面」。

## 三、单机密文版安全铁律

1. **airgap 默认开启**：守护进程派生子进程时主动剥离 `YD_API_KEY` 等环境变量，
   使 `api_key_ready()` 恒为 `False`，**不触发元典 REST 自动核验**（运维手册 §4.2.1
   Level3）。T502 案例存在性核验退化为「提取案号→比对本地缓存→写 pending_verify.json→
   提示会话协办回填」，**绝不偷偷连公网**。
2. **只校验不落正文**：门禁不写文档正文；`pending_verify.json` 仅存案号指纹。
3. **超时熔断**：单份文档硬超时（默认 300s），防止个别大文档卡死拖垮上游。

## 四、运维 SOP

### 前台启动（调试）
```bash
cd "律师分身系统（单机密文版）/05-门禁"
python3 lti-gate-daemon.py --foreground
# 监听 /tmp/lti-gate.sock
```

### 作为 macOS 服务常驻（推荐）
```bash
# 1) 安装 plist 到 LaunchAgents
cp com.xiaoqiang.lti-gate.plist ~/Library/LaunchAgents/
# 2) 加载（开机自启 + 崩溃自愈）
launchctl load ~/Library/LaunchAgents/com.xiaoqiang.lti-gate.plist
# 查看状态
launchctl list | grep lti-gate
# 卸载
launchctl unload ~/Library/LaunchAgents/com.xiaoqiang.lti-gate.plist
```
> 注：本环境不代点 UI。是否真正 `launchctl load` 由老强在终端执行。

### 调用（任意上游）
```bash
# 校验一份文书
python3 lti-gate-client.py /abs/待交付文书.docx
#   PASS  → exit 0，可交付
#   REJECT → exit 1，须修正后重跑
# 健康检查
python3 lti-gate-client.py --ping
```

## 五、协议（行分隔 JSON over Unix socket）

请求：`{"ping":true}` | `{"path":"/abs/x.docx"}` | `{"path":"/abs/x.docx","timeout":300}`
响应：`{"pong":true,"ts":...}` |
      `{"status":"PASS|REJECT|USAGE_ERR|ERROR","exit":0|1|2|-1,"report":"...","ts":...,"elapsed_s":...}`

## 六、验收记录（2026-09-17 实测）

- [x] 守护进程启动并监听 `/tmp/lti-gate.sock`
- [x] `--ping` 返回 `pong`
- [x] 良性 docx 经门禁返回 `PASS`（exit 0）
- [x] 不存在的路径返回 `ERROR`（exit 2），不崩溃

## 七、变更日志

- 2026-09-17 初建（G2）。解耦封装，airgap 默认开，零修改被封装 LTI 代码。

## 相关笔记
- [[律师27SOP复盘与数字分身借鉴方案-v1.0]] (共现关键词: 分身, gate)
- [[修复备忘录-20260914-8139工作流测试-越界转交]] (共现关键词: py, LTI, lti)
- [[2026-09-18-初版部署记录]] (共现关键词: lti, gate, ##)
- [[WF-001-法律文书docx双轨交付流水线]] (共现关键词: ##, LTI, docx)
