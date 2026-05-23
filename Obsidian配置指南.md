---
tags:
  - 指导案例
  - ###
  - 合同
  - 知识库
  - 案件
  - 证据
  - 插件
  - 答辩状
  - 起诉状
  - 法律
  - 代理词
  - obsidian
  - git
  - 侵权责任
  - LawKB
  - 模板
  - 关系图
---

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

## 三、社区插件安装指南（已预配置）

### 当前已启用的插件
本知识库已在 `.obsidian/community-plugins.json` 中预配置以下插件：
- **dataview** – 数据查询与自动表格生成
- **templater-obsidian** – 高级模板引擎

### 安装步骤（通过 Obsidian 图形界面）
1. **打开 Obsidian** 并加载 `LawKB` 笔记库
2. 进入 **设置** → **社区插件**
3. 确保 **安全模式** 已关闭（允许加载社区插件）
4. 点击 **浏览**，搜索以下插件并安装：
   - **Dataview**（作者：Blacksmith）
   - **Templater**（作者：SilentVoid）

5. **启用插件**：
   - 安装后，返回 **社区插件** 列表
   - 分别开启 **Dataview** 和 **Templater** 的开关
   - 根据提示重启 Obsidian 生效

### 验证安装
- 左侧边栏应出现 **Dataview** 图标（表格形状）
- 命令面板（Cmd+P）输入 `Templater` 显示相关命令
- 新建笔记，输入 ````dataview` 看是否高亮

### 备用安装方案（手动下载）
如果网络问题无法通过应用内安装，可手动下载插件文件：
1. 访问 GitHub 发布页面：
   - Dataview: https://github.com/blacksmithgu/obsidian-dataview/releases
   - Templater: https://github.com/SilentVoid13/Templater/releases
2. 下载最新版本的 `main.js` 和 `manifest.json`
3. 解压到对应文件夹：
   - Dataview: `.obsidian/plugins/dataview/`
   - Templater: `.obsidian/plugins/templater-obsidian/`
4. 重启 Obsidian

## 四、Git 同步配置（已初始化）

### 本地仓库状态
- ✅ Git 仓库已初始化（`/Users/chenyouqiang/Documents/LawKB/.git`）
- ✅ 初始提交已完成（包含目录结构、案例模板、配置指南）
- ✅ .gitignore 已配置（忽略临时文件、隐私数据）

### 连接远程仓库（GitHub / Gitee）
#### 选项一：GitHub（国际）
1. **创建新仓库**：登录 GitHub → New Repository → 名称 `LawKB`（公有/私有自选）
2. **获取远程地址**：`https://github.com/你的用户名/LawKB.git`
3. **本地添加远程**：
   ```bash
   cd ~/Documents/LawKB
   git remote add origin https://github.com/你的用户名/LawKB.git
   git push -u origin main
   ```
4. **输入凭据**：根据提示输入 GitHub 用户名和密码（或 Personal Access Token）

#### 选项二：Gitee（国内加速）
1. **创建新仓库**：登录 Gitee → 新建仓库 → 名称 `LawKB`
2. **获取远程地址**：`https://gitee.com/你的用户名/LawKB.git`
3. **本地添加远程**：
   ```bash
   cd ~/Documents/LawKB
   git remote add origin https://gitee.com/你的用户名/LawKB.git
   git push -u origin main
   ```

#### 选项三：本地备份（无需网络）
```bash
# 创建压缩备份到指定位置（如移动硬盘）
tar -czf ~/Desktop/LawKB-备份-$(date +%Y%m%d).tar.gz -C ~/Documents/LawKB .
```

### 日常同步命令
```bash
# 1. 查看状态
git status

# 2. 添加更改
git add .

# 3. 提交
git commit -m "更新：添加新案件/笔记"

# 4. 推送到远程
git push

# 5. 拉取远程更新（多人协作时）
git pull
```

## 五、判例索引建立（已创建）

### [[最高人民法院指导案例索引]]
- 文件位置：`判例索引/最高人民法院指导案例索引.md`
- 内容：前 10 个指导案例的详细索引（案号、标题、关键词、官方链接）
- 使用：点击表格中的链接直接访问最高人民法院官方页面

### 扩展索引
1. **添加新指导案例**：
   - 访问 [最高人民法院指导案例发布平台](https://www.court.gov.cn/shenpan/gzzd/)
   - 复制案例信息，按表格格式追加到 `最高人民法院指导案例索引.md`
   - 使用 `git commit -m "添加指导案例XX号"` 记录版本

2. **建立专题索引**（例如“民事借款合同纠纷”）：
   - 创建新文件：`判例索引/民事借款合同专题.md`
   - 使用 Dataview 自动汇总相关案例：
     ````markdown
     ```dataview
     TABLE 标题, 关键词, 发布日期
     FROM "判例索引"
     WHERE contains(关键词, "借款合同")
     SORT 发布日期 DESC
     ```
     ````

3. **链接到案件笔记**：
   - 在案件笔记中引用指导案例：`[[最高人民法院指导案例索引#指导案例1号]]`
   - 反向链接自动建立，形成知识网络

## 六、工作流配置

### 每日工作日志模板
在 Obsidian 设置 → 模板 → 指定模板文件夹：`~/Documents/LawKB/文书模板`

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

## 七、常用命令速查

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

## 八、数据备份与同步

### 自动备份脚本（示例）
```bash
#!/bin/bash
# 每天凌晨备份知识库到 iCloud
cd ~/Documents/LawKB
tar -czf ~/Library/Mobile\ Documents/com~apple~CloudDocs/LawKB备份/$(date +%Y%m%d).tar.gz .
echo "备份完成: $(date)" >> ~/Documents/LawKB/备份日志.md
```

### Git 自动同步（crontab）
```bash
# 编辑 crontab: crontab -e
# 每天 22:00 自动提交并推送
0 22 * * * cd /Users/chenyouqiang/Documents/LawKB && git add . && git commit -m "自动备份 $(date)" && git push
```

## 九、故障排除

### 常见问题
1. **Obsidian 无法识别链接**：确保使用 `[[文件名]]` 格式，文件名需精确匹配
2. **搜索不到内容**：检查是否在正确笔记库，重启 Obsidian 重新索引
3. **同步冲突**：使用 Git 或 iCloud 时，手动处理合并冲突
4. **插件不生效**：检查 `社区插件` 列表是否启用，重启 Obsidian

### 获取帮助
- Obsidian 中文社区：https://forum-zh.obsidian.md
- 法律科技交流群：相关微信群/钉钉群

---

**配置状态**：✅ 基础结构就绪 | ✅ Git 初始化 | ✅ 判例索引创建 | ⚠️ 插件待安装  
**下一步操作**：
1. 打开 Obsidian，选择 `~/Documents/LawKB` 作为笔记库
2. 按照 **第三部分** 安装社区插件
3. 按照 **第四部分** 连接远程 Git 仓库
4. 开始记录你的第一个真实案件！

---
*最后更新：2026-04-23*  
*版本：2.0（完整配置版）*

## 标签
#[[指导案例]]
#[[###]]
#[[合同]]
#[[知识库]]
#[[案件]]
#[[证据]]
#[[插件]]
#[[答辩状]]
#[[起诉状]]
#[[法律]]
#[[代理词]]
#[[obsidian]]
#[[git]]
#[[侵权责任]]
#[[LawKB]]
#[[模板]]
#[[关系图]]

## 相关笔记
- [[合同审查的五个层次]] (共现关键词: 民法, 关键词)
- [[AI合同审查搭建思路流程提示词从入门到进阶]] (共现关键词: 侵权, 起诉, 民法)
- [[法律检索助手 skill 配置说明书]] (共现关键词: 配置, 民法)
- [[案件关系图示例]] (共现关键词: 民法, 插件)
- [[法律意见书_接受捐赠协议书标准版]] (共现关键词: 起诉, 民法)
- [[律师常用的12组提示词合同审查文书写作案件分析]] (共现关键词: 起诉, 知识产权, 关键词)
- [[关于审理道路交通事故损害赔偿案件适用法律若干问题的解释（二）]] (共现关键词: 民法, 侵权, 关键词)
- [[ClaudeCodeObsidian个人知识库从工具到思维的完整指南]] (共现关键词: Obsidian, 指南)
- [[郭某与某甲公司等财产损害补偿纠纷案 - 中华人民共和国最高人民法院公报]] (共现关键词: 民法, 答辩)
- [[律师AI提效的7套黄金提示词]] (共现关键词: 民法, 答辩)
- [[律师AI提示词使用指南从入门到精通]] (共现关键词: 民法, 答辩)
- [[法律备忘录 skill 配置说明书]] (共现关键词: 合同, 配置, 民法)
- [[证据目录的编排逻辑]] (共现关键词: 合同, 起诉, 民法)
- [[代理词_罗江辉诉易思立达]] (共现关键词: 合同, 起诉, 民法)
- [[Templater快速配置指南]] (共现关键词: 指南, 合同, 配置)
- [[Obsidian插件启用极简教程]] (共现关键词: 合同, 起诉, Obsidian)
- [[侵权纠纷-模板]] (共现关键词: 合同, 民法, 答辩)
- [[知识产权案件-模板]] (共现关键词: 合同, 民法, 答辩)
- [[民事案件-通用模板]] (共现关键词: 合同, 民法, 答辩)
- [[中华人民共和国仲裁法]] (共现关键词: 合同, 民法, 答辩)
- [[起诉状撰写要点]] (共现关键词: 合同, 民法, 答辩)
- [[Obsidian极简安装指南]] (共现关键词: 指南, 民法, Obsidian)
- [[检查模板路径]] (共现关键词: LawKB, 合同, Obsidian)
- [[合同纠纷-模板 1]] (共现关键词: 合同, 民法, 答辩)
- [[合同纠纷-模板]] (共现关键词: 合同, 民法, 答辩)
- [[法律合同审查助手skill 配置说明书]] (共现关键词: 合同, 配置, 民法)
- [[法律文书写作助手skill 配置说明书v2.0]] (共现关键词: 合同, 配置, 民法)
- [[案件执行助手skill 配置说明书]] (共现关键词: 合同, 配置, 民法)
- [[庭审红队律师配置]] (共现关键词: 合同, 起诉, 民法)
- [[README]] (共现关键词: 合同, 起诉, 答辩)
- [[文书红队推演配置]] (共现关键词: 合同, 配置, 民法)
