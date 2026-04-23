#!/bin/bash
# Obsidian 插件一键下载脚本
# 使用 ghproxy 镜像加速（国内可用）
# 执行: bash /Users/chenyouqiang/Documents/LawKB/download_plugins.sh

echo "🔧 开始下载 Obsidian 插件..."
echo "======================================"

# 确保目录存在
mkdir -p "/Users/chenyouqiang/Documents/LawKB/.obsidian/plugins/dataview"
mkdir -p "/Users/chenyouqiang/Documents/LawKB/.obsidian/plugins/templater-obsidian"

# 设置镜像地址
MIRROR="https://mirror.ghproxy.com/https://github.com"

# 1. 下载 Dataview 插件 (版本 0.5.70)
echo "📦 下载 Dataview 插件..."
curl -L -s -f -o "/Users/chenyouqiang/Documents/LawKB/.obsidian/plugins/dataview/main.js" \
  "${MIRROR}/blacksmithgu/obsidian-dataview/releases/download/0.5.70/main.js"

if [ $? -eq 0 ]; then
    echo "  ✅ main.js 下载成功"
else
    echo "  ❌ main.js 下载失败，尝试备用链接..."
    curl -L -s -o "/Users/chenyouqiang/Documents/LawKB/.obsidian/plugins/dataview/main.js" \
      "https://github.com/blacksmithgu/obsidian-dataview/releases/download/0.5.70/main.js" || echo "  ❌ 备用链接也失败"
fi

curl -L -s -f -o "/Users/chenyouqiang/Documents/LawKB/.obsidian/plugins/dataview/manifest.json" \
  "${MIRROR}/blacksmithgu/obsidian-dataview/releases/download/0.5.70/manifest.json"

if [ $? -eq 0 ]; then
    echo "  ✅ manifest.json 下载成功"
else
    curl -L -s -o "/Users/chenyouqiang/Documents/LawKB/.obsidian/plugins/dataview/manifest.json" \
      "https://github.com/blacksmithgu/obsidian-dataview/releases/download/0.5.70/manifest.json" || echo "  ❌ 备用链接也失败"
fi

# 2. 下载 Templater 插件 (版本 1.18.2)
echo "📦 下载 Templater 插件..."
curl -L -s -f -o "/Users/chenyouqiang/Documents/LawKB/.obsidian/plugins/templater-obsidian/main.js" \
  "${MIRROR}/SilentVoid13/Templater/releases/download/1.18.2/main.js"

if [ $? -eq 0 ]; then
    echo "  ✅ main.js 下载成功"
else
    echo "  ❌ main.js 下载失败，尝试备用链接..."
    curl -L -s -o "/Users/chenyouqiang/Documents/LawKB/.obsidian/plugins/templater-obsidian/main.js" \
      "https://github.com/SilentVoid13/Templater/releases/download/1.18.2/main.js" || echo "  ❌ 备用链接也失败"
fi

curl -L -s -f -o "/Users/chenyouqiang/Documents/LawKB/.obsidian/plugins/templater-obsidian/manifest.json" \
  "${MIRROR}/SilentVoid13/Templater/releases/download/1.18.2/manifest.json"

if [ $? -eq 0 ]; then
    echo "  ✅ manifest.json 下载成功"
else
    curl -L -s -o "/Users/chenyouqiang/Documents/LawKB/.obsidian/plugins/templater-obsidian/manifest.json" \
      "https://github.com/SilentVoid13/Templater/releases/download/1.18.2/manifest.json" || echo "  ❌ 备用链接也失败"
fi

echo "======================================"
echo "📁 检查下载结果:"
ls -la "/Users/chenyouqiang/Documents/LawKB/.obsidian/plugins/dataview/" 2>/dev/null || echo "Dataview 目录不存在"
ls -la "/Users/chenyouqiang/Documents/LawKB/.obsidian/plugins/templater-obsidian/" 2>/dev/null || echo "Templater 目录不存在"

echo ""
echo "✅ 脚本执行完成！"
echo ""
echo "下一步："
echo "1. 安装 Obsidian 应用（如果还没安装）"
echo "2. 打开 Obsidian，选择 /Users/chenyouqiang/Documents/LawKB 作为笔记库"
echo "3. 进入设置 → 社区插件 → 开启 Dataview 和 Templater 插件开关"