---
created: 2026-06-23T18:31
updated: 2026-06-23T18:33
---
https://mp.weixin.qq.com/s/zmrIPFHKnOj-rVWR6va_7Q

# 用WorkBuddy搞定PDF四件套：解读、转PPT、转Excel、转Word，一个AI全包


你电脑里是不是躺着几十个PDF，想改改不了、想转格式要充会员、想找关键数据翻半天？今天教你用WorkBuddy，一句话搞定。

**先说结论：**WorkBuddy内置4个Skill，覆盖PDF最痛的4个场景——


📄 markitdown → PDF智能解读，30秒提炼80页报告
📊 pptx-generator → PDF一键转PPT，不用重做
📈 minimax-xlsx → PDF表格提取到Excel，数据可直接算
📝 minimax-docx → PDF转Word可编辑，格式还不乱




![WorkBuddy PDF四件套](wechat_img_1782210677083_188.jpg)





## 一、PDF智能解读：80页报告，30秒出摘要



你收到一份80页的行业报告PDF，领导说"下午开会用"——你是从头翻到尾，还是让AI帮你先提炼？



**WorkBuddy怎么操作：**

你对WorkBuddy说：

"帮我把这份行业报告PDF读一下，提炼出3个核心观点和5个关键数据"

WorkBuddy会自动调用 markitdown Skill：

① 识别PDF格式，提取全部文本和结构
② 保留标题层级、表格、列表等格式
③ AI理解内容后生成摘要+关键数据
④ 你还能追问："第三章节的具体建议是什么？"

markitdown用的是微软开源的MarkItDown引擎，**支持PDF、Word、PPT、Excel、图片OCR、音频转写**，可以说是个"万能文档翻译器"。




💡 **进阶用法：**批量解读。把多个PDF丢给WorkBuddy，让它提取每份的核心结论，再生成一份"竞品分析汇总报告"。




## 二、PDF转PPT：不用一页一页重做了



最常见的场景：收到一份PDF方案，领导说"把这个做成PPT，下午汇报"——以前只能对着PDF重新排版，现在呢？



**WorkBuddy两步搞定：**


第一步，提取内容：


"帮我把这个PDF的内容提取出来，按照PPT的逻辑重新组织大纲"


WorkBuddy调用 markitdown 提取文本 → AI理解后重新组织成PPT大纲


第二步，生成PPT：


"按照这个大纲，帮我生成一份12页的PPT，风格要商务简洁"


WorkBuddy调用 pptx-generator Skill → 自动生成封面、目录、章节页、内容页、总结页 → 输出.pptx文件，打开就能用




pptx-generator用的是PptxGenJS引擎，**支持6种配色方案、4种设计风格、5种页面类型**，不是那种丑到不敢拿出来的AI PPT。




💡 **省时技巧：**先让WorkBuddy生成大纲，你确认逻辑没问题再让它做PPT。比直接一步到位更可控，改起来也快。




![PDF转换流程](wechat_img_1782210677210_963.jpg)





## 三、PDF表格提取到Excel：数据终于能算了



PDF里的表格是最烦的——看得见摸不着，想算个合计都得手动敲。有了WorkBuddy：




你对WorkBuddy说：


"这个PDF里的销售数据表格，帮我提取到Excel里，加上合计行"


WorkBuddy会这样操作：
① markitdown提取PDF中的表格文本
② AI识别表头和数据结构
③ minimax-xlsx生成标准Excel文件
④ 自动加上SUM公式，数据可以直接计算




minimax-xlsx的Excel生成能力很强：

- ✅ 支持多Sheet、合并单元格、条件格式
- ✅ 所有计算结果用Excel公式，不是硬编码数字
- ✅ 自动应用财务配色标准（输入蓝色、公式黑色、跨表引用绿色）
- ✅ 支持后续编辑已有Excel文件，零格式丢失




💡 **真实场景：**每月把供应商发来的PDF报价单提取到Excel，自动算出最低价、平均价，再生成比价表。以前2小时的活，5分钟搞定。




## 四、PDF转Word可编辑：格式还不会乱



PDF转Word的痛点是啥？**格式全乱。**表格变了、图片丢了、标题变成普通文字。用WorkBuddy就不一样了：




你对WorkBuddy说：


"帮我把这个PDF转成Word文档，保留原来的标题层级和表格格式"


WorkBuddy的操作流程：
① markitdown提取PDF完整结构和文本
② AI分析标题层级、段落、表格、列表
③ minimax-docx按原始结构重新生成Word文档
④ 标题→标题样式、表格→表格样式、列表→列表样式




minimax-docx基于OpenXML SDK，不是那种简单粗暴的文本粘贴：

- ✅ 13种文档风格模板（商务/学术/公文/HBR等）
- ✅ 支持页眉页脚、目录、脚注、批注
- ✅ 中英文排版标准（GB/T 9704公文、APA/MLA学术论文）
- ✅ 生成后还能继续编辑，格式零丢失




💡 **最骚的操作：**PDF转Word后，让WorkBuddy"按公司模板重新排版"，自动套用你们公司的Word模板，标题字体、页边距、Logo一键对齐。




![组合技](wechat_img_1782210677353_503.jpg)





## 四件套速查表：场景→操作，照做就行


你想干啥
用的Skill
对WorkBuddy说什么
耗时




读懂80页报告
markitdown
"提炼核心观点和关键数据"
30秒


PDF方案转PPT
markitdown + pptx-generator
"提取内容并生成PPT"
3分钟


PDF表格变Excel
markitdown + minimax-xlsx
"提取表格到Excel加公式"
1分钟


PDF转Word可编辑
markitdown + minimax-docx
"转Word保留原格式"
2分钟


多PDF对比分析
markitdown（批量）
"对比这3份报告的核心差异"
2分钟


PDF报价单比价
markitdown + minimax-xlsx
"提取报价生成比价表"
3分钟





## 3个踩坑提醒




**❌ 坑1：扫描件PDF直接丢给AI**


扫描件PDF本质是图片，markitdown可以OCR提取，但准确率取决于扫描质量。**建议：**先用"帮我把这个扫描件做OCR"测试一下提取效果，再决定是否需要人工校对。





**❌ 坑2：以为一步到位就完美**


PDF转PPT/Excel/Word，建议**分两步走**：先提取内容，确认无误后再生成目标格式。一步到位虽然快，但中间环节出了错你都不知道。**建议：**让WorkBuddy先展示提取结果，你确认后再生。





**❌ 坑3：复杂排版PDF期望100%还原**


图文混排、分栏、特殊字体的PDF，转换后可能有细节差异。**建议：**把重点放在**内容准确性**上，排版微调比从头做快10倍。




## 组合技：PDF的终极玩法



单个Skill好用，组合起来才是真正降维打击：




**🚀 组合1：PDF → PPT + 演讲备注**


转PPT的同时，让WorkBuddy给每页生成演讲备注。汇报时打开PPT的备注视图，你就像有了提词器。





**🚀 组合2：多PDF → 对比报告 → Word**


3份供应商PDF报价单 → 提取数据对比 → 生成Word比价报告。以前要1天，现在10分钟。





**🚀 组合3：PDF → Excel → 可视化图表**


PDF里的年度数据 → 提取到Excel → 加上SUM/AVERAGE公式和条件格式 → 领导要的报表直接交。




说到底，PDF从来不是问题，**问题是你有没有一个能读懂PDF、还能帮你干活的AI助手**。WorkBuddy的4个Skill就像4个专业小弟，你一句话指挥，它们各司其职。




**还没装这4个Skill？**


打开WorkBuddy → 技能市场搜索：
markitdown / pptx-generator / minimax-xlsx / minimax-docx
一键安装，马上就能用




觉得有用？转发给还在手动复制PDF的同事 👇







---
*Source: [WeChat Article](https://mp.weixin.qq.com/s/zmrIPFHKnOj-rVWR6va_7Q)*