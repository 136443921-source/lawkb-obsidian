# Obsidian 法律知识库配置指南

## 一、软件准备

### 1. 安装 Obsidian（如未安装）
- 官网下载：https://obsidian.md
- 安装后打开，选择 **"打开文件夹作为笔记库"**
- 路径选择：`/Users/chenyouqiang/Documents/LawKB`

### 2. 安装 obsidian-cli 命令行工具（可选但推荐）

#### 方法A：通过 Homebrew（需要管理员权限）
```bash
# 1. 先安装 Homebrew（如未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 添加 obsidian-cli 仓库
brew tap yakitrak/yakitrak

# 3. 安装 obsidian-cli
brew install obsidian-cli

# 4. 验证安装
obsidian-cli --help
```

#### 方法B：手动下载二进制（无需管理员权限）
1. 访问 https://github.com/yakitrak/obsidian-cli/releases
2. 下载最新版本的 `obsidian-cli-macos`（或对应系统版本）
3. 解压后将可执行文件放到 `~/bin/` 或 `/usr/local/bin/`
4. 添加执行权限：`chmod +x ~/bin/obsidian-cli`

#### 方法C：直接使用文件系统（无需安装）
- Obsidian 会自动索引 `LawKB` 文件夹内的所有 Markdown 文件
- 可使用系统命令进行基本操作：
  ```bash
  # 搜索
  grep -r "借款合同" ~/Documents/LawKB --include="*.md"
  
  # 统计
  find ~/Documents/LawKB -name "*.md" | wc -l
  ```

## 二、Obsidian 基础设置

### 1. 核心插件开启
- **文件恢复**：开启自动保存（防止丢失）
- **模板**：启用模板功能
- **星标**：标记重要笔记
- **大纲**：显示文档结构

### 2. 社区插件推荐（法律工作专用）
1. **Dataview** - 自动生成案件统计表
   ```javascript
   // 示例：列出所有审理中的案件
   TABLE 案由, 当事人, 立案日期, 当前阶段
   FROM "案件"
   WHERE 当前阶段 = "审理中"
   SORT 立案日期 DESC
   ```

2. **Templater** - 智能模板填充
   - 预置：起诉状、答辩状、代理词模板
   - 自动插入日期、案号、当事人信息

3. **Calendar** - 庭审日期追踪
   - 直观显示开庭日期
   - 点击日期快速创建庭审记录

4. **Excalidraw** - 绘制案件关系图
   - 可视化当事人关系
   - 绘制证据链图

## 三、工作流配置

### 每日工作日志模板
在 Obsidian 设置 → 模板 → 指定模板文件夹：`~/Documents/LawKB/模板`

创建 `Daily Log.md`：
```markdown
---
date: {{date:YYYY-MM-DD}}
tags: [daily, log]
---

## {{date:YYYY-MM-DD}} 工作记录

### 已完成
- [ ] 

### 待办事项
- [ ] 

### 案件进展
- 

### 学习收获
- 

### 明日计划
- 
```

### 案件索引自动化
创建 `案件索引.md`，使用 Dataview 插件自动生成：

````markdown
```dataview
TABLE 案由, 当事人, 立案日期, 当前阶段, 标的额
FROM "案件"
SORT 立案日期 DESC
```
````

## 四、常用命令速查

### obsidian-cli 命令示例
```bash
# 1. 搜索
obsidian-cli search "借款合同"          # 按文件名搜索
obsidian-cli search-content "LPR四倍" # 按内容搜索

# 2. 创建
obsidian-cli create "案件/2026-王五-侵权责任纠纷" --content "# 新案件"

# 3. 整理
obsidian-cli move "案件/旧名称" "案件/新名称"  # 重命名并更新链接

# 4. 统计
obsidian-cli search-content "庭审" | wc -l      # 统计含"庭审"的笔记数
```

### 替代方案（无 cli）
```bash
# 1. 使用系统命令搜索
cd ~/Documents/LawKB
grep -r "关键词" --include="*.md" -n

# 2. 批量重命名（谨慎使用）
find . -name "*借款*" -exec rename 's/借款/借贷/' {} \;

# 3. 生成目录树
tree -I '.obsidian|*.canvas' --dirsfirst
```

## 五、数据备份

### 自动备份脚本（示例）
```bash
#!/bin/bash
# 每天凌晨备份知识库到 iCloud
cd ~/Documents/LawKB
tar -czf ~/Library/Mobile\ Documents/com~apple~CloudDocs/LawKB备份/$(date +%Y%m%d).tar.gz .
echo "备份完成: $(date)" >> ~/Documents/LawKB/备份日志.md
```

### Git 版本控制（可选）
```bash
cd ~/Documents/LawKB
git init
git add .
git commit -m "初始提交"
# 关联远程仓库（GitHub/Gitee）
git remote add origin <仓库地址>
```

## 六、故障排除

### 常见问题
1. **Obsidian 无法识别链接**：确保使用 `[[文件名]]` 格式，文件名需精确匹配
2. **搜索不到内容**：检查是否在正确笔记库，重启 Obsidian 重新索引
3. **同步冲突**：使用 Git 或 iCloud 时，手动处理合并冲突

### 获取帮助
- Obsidian 中文社区：https://forum-zh.obsidian.md
- 法律科技交流群：相关微信群/钉钉群

---

**配置状态**：基础结构已就位，Obsidian 应用待关联  
**下一步操作**：打开 Obsidian，选择 `~/Documents/LawKB` 作为笔记库