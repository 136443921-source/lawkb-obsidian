# AGENTS.md — LawKB 库内作业的 AI 共同规则

> 本文件是 Obsidian LawKB 库的**入口规则**。任何在本库内工作的 AI（WorkBuddy / Claude Code / Codex / Gemini / Cursor / 其它）必须先读 **大脑**再动手。

---

## 🧠 第一优先：装载共享记忆中枢

**在库内做任何实质性工作之前，必须执行：**

```bash
cd /Users/chenyouqiang/Documents/LawKB/_AI-Memory-Hub
python3 99-脚本/read_hub.py --brief
```

这会装载：全局规则 → 用户偏好 → 活跃项目 → 近期决策 → 昨日日志。

**跳过的例外**：纯寒暄、一句话查词。

**违反后果**：产出视为草稿，不得交付客户。

---

## ⚖️ 第二优先：冲突仲裁

记忆中枢 = `/Users/chenyouqiang/Documents/LawKB/_AI-Memory-Hub/`，是**唯一永久事实源**。

| 位置 | 角色 |
|---|---|
| `_AI-Memory-Hub/**` | **最终事实源** |
| `LawKB/.workbuddy/memory/` | ⛔ 只读归档（见其 `_00-只读归档声明.md`） |
| `~/.workbuddy/MEMORY.md` 等平台原生 memory | 辅助缓存 |
| 聊天记录 / 临时上下文 | 临时，**不算事实** |

冲突时以中枢 **`status: active` 且 `updated` 最新**者为准，详见 `00-全局规则/冲突仲裁规则.md`。

---

## 📝 第三优先：工作结束后写回

任务完成时必须把新增事实写回中枢：

```bash
python3 99-脚本/write_back.py --type preference --title "..." --body "..." --dry-run  # 先看
python3 99-脚本/write_back.py --type preference --title "..." --body "..."             # 再写
```

类型：`rule` / `preference` / `project-fact` / `decision` / `workflow`

---

## 🚫 库内红线

1. **个案卷宗不得入库**：当事人隐私、身份证、银行卡、证据原件内容，只提炼方法论。
2. **法条不得凭记忆写**：必须查本地 `法律法规库/` 或 pkulaw，找不到标 `statute_text_pending` 且不作为依据。
3. **绝不硬删**：任何文件删除前先 `cp -n` 备份到 `/tmp`。
4. **批量前先 dry-run**，改完确认幂等。
5. **`06-沉淀/裁判规则库/` 的卡片文件名不得重命名** ——300+ 条全名链接依赖它，编号冲突只改 frontmatter。
6. 涉及厚德基金会等慈善组织，决策须引《贵州省厚德公益基金会合规管理手册（试行）（2025版）》第 X 条。

---

## 🔗 快速入口

- 中枢 README：`_AI-Memory-Hub/README.md`
- 共享协议：`_AI-Memory-Hub/00-全局规则/共享记忆协议-v1.0.md`
- 用户偏好索引：`_AI-Memory-Hub/01-用户偏好/_索引.md`
- 活跃项目：`_AI-Memory-Hub/02-当前项目/_活跃项目.md`
- 近期决策：`_AI-Memory-Hub/03-决策档案/_近期决策.md`
