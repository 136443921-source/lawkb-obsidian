---
created: 2026-05-28T10:51
updated: 2026-08-21T18:55
title: LTI-文本监察官系统配置说明
tags:
  - 诉讼
  - 合同
maturity: 🌱种子
source: ""
related: []
last_review: ""
review_interval: 7
difficulty: 3
importance: 3
status: draft
---

请按以下要求，帮我设置一下文本监察官系统，用于监测workbuddy 输出文本前的监测，严格实行“未通过文本监察官系统不出文本”的输出原则。
# 系统架构概览

本系统采用 **“防火墙式”**​ 拦截机制。所有 WorkBuddy 生成的文本在写入本地存储前，必须经过 LTI 系统的管道清洗。
## 2. 核心角色配置 (System Prompt)

请在您的 Multi-Agent 框架中配置以下三个“监察官”角色。**建议将以下 Prompt 设置为 System Role。**

### 2.1 角色一：法条真实性核查员 (The Verifier)

**职责**：消灭“幻觉法条”，确保所有引用的法律法规、司法解释、判例真实存在且版本有效。

- **Prompt 配置：**
    
    > “你是一名资深法院书记员，精通中国法律法规数据库。你的任务是核对文本中的法律引用。
    > 
    > **核查清单：**
    > 
    > 1. **时效性**：引用的法条是否已被废止（如《民法典》生效后，《合同法》已废止）。
    >     
    > 2. **准确性**：条、款、项编号是否准确（例如：核对《民法典》第584条是否存在）。
    >     
    > 3. **来源**：禁止引用非官方来源（如自媒体、未认证的法律咨询网站）。
    >     
    >     **输出要求**：仅标记错误，提供正确的法条原文或官方链接（基于挂载的知识库）。”
    >     
    

### 2.2 角色二：逻辑与合规审计员 (The Auditor)

**职责**：消灭逻辑混乱，确保法律推理符合“大前提-小前提-结论”的三段论结构。

- **Prompt 配置：**
    
    > “你是一名红圈所风控合伙人。你的任务是审查法律推理的严密性。
    > 
    > **核查清单：**
    > 
    > 1. **因果倒置**：是否存在‘因为A，所以B’，但A与B无法律上的因果关系？
    >     
    > 2. **遗漏要件**：在判断违约责任时，是否遗漏了‘违约行为’、‘损害结果’、‘因果关系’、‘过错’四个构成要件？
    >     
    > 3. **自相矛盾**：前文认定的事实是否与后文得出的结论冲突。
    >     
    >     **输出要求**：指出逻辑断裂点，并给出重构论证路径的建议。”
    >     
    

### 2.3 角色三：语言净化与格式官 (The Editor)

**职责**：消灭错别字、标点错误及非法律专业用语。

- **Prompt 配置：**
    
    > “你是一名法律出版社的终审编辑。你的任务是标准化法律文本。
    > 
    > **核查清单：**
    > 
    > 1. **术语规范**：必须使用‘法定代表人’而非‘法人代表’；使用‘诉讼时效’而非‘追诉期’（刑法除外）。
    >     
    > 2. **标点符号**：法律条文引用应使用六角括号〔〕，而非方括号[]；引号使用直角引号「」或标准中文引号“”。
    >     
    > 3. **数字与单位**：涉及金额、刑期，必须使用中文数字大写或阿拉伯数字规范格式。
    >     
    >     **输出要求**：直接输出修正后的段落，并标注修改原因。”
    
## 3. 知识库挂载与自检规则 (Knowledge Base)

为了保证监察官的敏锐度，挂载一个动态更新的知识库（可以是本地 JSON/CSV 文件，或向量数据库），挂载知识库位置：obsidian-lawkb-知识库-文本监察官系统。

### 3.1 知识库结构示例 (`legal_inspector_rules.json`)

json

json

```
{
  "version": "2026.05",
  "rules": [
    {
      "rule_id": "R001",
      "category": "时效禁令",
      "description": "禁止引用已废止法律",
      "blacklist": ["中华人民共和国合同法", "中华人民共和国物权法"],
      "replacement": "中华人民共和国民法典"
    },
    {
      "rule_id": "R002",
      "category": "术语规范",
      "wrong_terms": ["罚金", "罚款"],
      "context_rules": "刑法中用‘罚金’，行政法/民法中用‘罚款’"
    },
    {
      "rule_id": "R003",
      "category": "引用格式",
      "pattern": "《.*?》第[0-9]+条",
      "correction": "必须核对该法条在2026年是否有效"
    }
  ]
}
```

### 3.2 自检规则更新机制 (Update Mechanism)

- **自动更新**：设置定时任务（Cron Job），每日爬取“北大法宝”或“最高人民法院”官网，抓取最新的司法解释废止公告，自动更新 `blacklist`。
    
- **人工反馈**：当您发现 WorkBuddy 绕过监察官产生错误时，手动向知识库添加一条新规则（Rule），下次运行即生效。
    

## 4. 联动工作流配置 (Workflow Config)

在您的代码或自动化工具（如 n8n, Dify, Coze）中配置如下流程：

### Step 1: 拦截 Hook

在 WorkBuddy 的输出节点（Output Node）后插入一个 **“代码执行器”**​ 或 **“HTTP 请求”**​ 节点，调用 LTI 控制器。

### Step 2: 并行校验 (Parallel Inspection)

将文本同时发送给上述 3 个智能体（Verifier, Auditor, Editor）。

### Step 3: 裁决逻辑 (Adjudication Logic)

编写一段 Python 脚本作为“总控开关”：

python

python

```
def lti_controller(original_text, inspection_reports):
    """
    original_text: WorkBuddy 生成的原文
    inspection_reports: 三个监察官返回的字典
    """
    error_count = 0
    critical_errors = [] # 致命错误（如法条不存在）

    for report in inspection_reports:
        if report['status'] == 'FAIL':
            error_count += 1
            if report['level'] == 'CRITICAL': # 例如：引用了废止的法条
                critical_errors.append(report['message'])

    # 规则：如果有致命错误，拒绝保存并回炉重造
    if len(critical_errors) > 0:
        return {
            "action": "REJECT",
            "reason": critical_errors,
            "revised_text": None
        }
    # 规则：如果是轻微错误（如错别字），自动修正
    elif error_count > 0:
        return {
            "action": "AUTO_FIX",
            "reason": "Minor edits applied",
            "revised_text": apply_fixes(original_text, inspection_reports)
        }
    else:
        return {
            "action": "APPROVE",
            "reason": "Passed all checks",
            "revised_text": original_text
        }
```

## 5. 输出示例

**WorkBuddy 原输出：**

> “根据《合同法》第52条，定金不得超过主合同标的额的百分之30。”

**LTI 拦截后返回：**

> ❌ **[监察官警报] 拒绝保存**
> 
> **错误类型：**​ 法条引用失效 + 计算错误
> 
> **详情：**
> 
> 1. **时效错误**：《合同法》已于2021年废止，应引用《民法典》第586条。
>     
> 2. **数值错误**：定金不得超过主合同标的额的 **20%**（非30%）。
>     
> 
> **建议修正文本：**
> 
> “根据《中华人民共和国民法典》第五百八十六条，定金的数额由当事人约定；但是，不得超过主合同标的额的百分之二十，超过部分不产生定金的效力。”
> 
> **状态：**​ 已阻止写入本地。请确认修正后重试。配置能最大程度地利用 AI 的“谨慎”特质来对抗 AI 的“幻觉”特质

---
## 一、目录结构

text

text

```
lti/
├── main.py                  # 主入口
├── config.py                # 全局配置
├── rules/
│   └── legal_inspector_rules.json
├── inspectors/
│   ├── verifier.py          # 法条真实性
│   ├── auditor.py           # 逻辑与合规
│   ├── editor.py            # 语言与格式
│   └── knowledge_base.py   # 知识库加载
├── controller.py            # 裁决门
└── utils/
    └── logger.py
```

---

## 二、核心脚本（单文件最小可用版）

> ✅ **你可以直接复制这一段，保存为 `lti.py`立刻跑起来**

python

python

```
#!/usr/bin/env python3
"""
法律文本监察官（Legal Text Inspector, LTI）
用于拦截 AI 生成文本中的：
- 幻觉法条
- 逻辑断裂
- 错别字 / 格式错误
"""

import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import List


# =======================
# 枚举 & 数据结构
# =======================

class Verdict(Enum):
    PASS = "PASS"
    REJECT = "REJECT"


@dataclass
class ErrorItem:
    rule_id: str
    level: str          # CRITICAL | WARNING
    kind: str
    location: str
    reason: str
    fix_suggestion: str


@dataclass
class InspectionReport:
    inspector: str
    verdict: Verdict
    errors: List[ErrorItem]


@dataclass
class LTIResult:
    action: str                 # PASS | AUTO_FIX | REJECT
    final_text: str
    reports: List[InspectionReport]
    summary: str


# =======================
# 知识库（自检规则）
# =======================

class KnowledgeBase:
    def __init__(self, path: str = "rules/legal_inspector_rules.json"):
        self.path = path
        self.rules = []
        self.load()

    def load(self):
        if not os.path.exists(self.path):
            return
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.rules = data.get("rules", [])

    def match(self, text: str) -> List[ErrorItem]:
        errors = []
        for rule in self.rules:
            if rule["category"] == "时效禁令":
                for bad in rule.get("blacklist", []):
                    if bad in text:
                        errors.append(ErrorItem(
                            rule_id=rule["rule_id"],
                            level="CRITICAL",
                            kind="citation_obsolete",
                            location=bad,
                            reason=f"引用已废止法律：{bad}",
                            fix_suggestion=rule.get("replacement", "请替换为现行有效法律")
                        ))
        return errors


# =======================
# 检查器（Inspectors）
# =======================

class Verifier:
    """法条真实性核查员"""

    def inspect(self, text: str, kb: KnowledgeBase) -> InspectionReport:
        errors = kb.match(text)

        # 示例规则：禁止虚构条款
        if "第999条" in text:
            errors.append(ErrorItem(
                rule_id="V001",
                level="CRITICAL",
                kind="hallucinated_article",
                location="第999条",
                reason="《民法典》不存在第999条",
                fix_suggestion="核实并更正具体条款编号"
            ))

        verdict = Verdict.REJECT if any(e.level == "CRITICAL" for e in errors) else Verdict.PASS
        return InspectionReport("Verifier", verdict, errors)


class Auditor:
    """逻辑与合规审计员"""

    def inspect(self, text: str) -> InspectionReport:
        errors = []

        # 示例规则：主张违约责任却未提违约行为
        if "违约责任" in text and "违约行为" not in text:
            errors.append(ErrorItem(
                rule_id="A001",
                level="WARNING",
                kind="missing_elements",
                location="违约责任",
                reason="主张违约责任但未说明违约行为",
                fix_suggestion="补充违约行为的事实描述"
            ))

        verdict = Verdict.REJECT if any(e.level == "CRITICAL" for e in errors) else Verdict.PASS
        return InspectionReport("Auditor", verdict, errors)


class Editor:
    """语言净化与格式官"""

    def inspect(self, text: str) -> InspectionReport:
        errors = []

        if "签定合同" in text:
            errors.append(ErrorItem(
                rule_id="E001",
                level="WARNING",
                kind="terminology",
                location="签定合同",
                reason="术语错误：应为“签订合同”",
                fix_suggestion="将“签定”改为“签订”"
            ))

        verdict = Verdict.REJECT if any(e.level == "CRITICAL" for e in errors) else Verdict.PASS
        return InspectionReport("Editor", verdict, errors)


# =======================
# 裁决门（Controller）
# =======================

class LTIController:
    def __init__(self):
        self.kb = KnowledgeBase()
        self.verifier = Verifier()
        self.auditor = Auditor()
        self.editor = Editor()

    def run(self, draft_text: str) -> LTIResult:
        reports = [
            self.verifier.inspect(draft_text, self.kb),
            self.auditor.inspect(draft_text),
            self.editor.inspect(draft_text),
        ]

        critical_errors = sum(
            1 for r in reports for e in r.errors if e.level == "CRITICAL"
        )
        reject = any(r.verdict == Verdict.REJECT for r in reports)

        if critical_errors > 0 or reject:
            action = "REJECT"
        elif any(e.level == "WARNING" for r in reports for e in r.errors):
            action = "AUTO_FIX"
        else:
            action = "PASS"

        summary_lines = []
        for r in reports:
            summary_lines.append(f"{r.inspector}: {r.verdict.value}")
            for e in r.errors:
                summary_lines.append(f"  - [{e.level}] {e.reason}")

        return LTIResult(
            action=action,
            final_text=draft_text,
            reports=reports,
            summary="\n".join(summary_lines)
        )


# =======================
# CLI 入口
# =======================

if __name__ == "__main__":
    draft = input("请输入待保存法律文本：\n")

    controller = LTIController()
    result = controller.run(draft)

    print("\n======== LTI 裁决结果 ========")
    print(f"Action: {result.action}")
    print("\nDetails:")
    print(result.summary)

    if result.action == "REJECT":
        print("\n❌ 已阻止写入本地")
    elif result.action == "AUTO_FIX":
        print("\n⚠️ 建议自动修正后写入")
    else:
        print("\n✅ 允许写入本地")
```

# 输出文本质量控制器检查表（LTI–QC Checklist）

> 适用场景：WorkBuddy -所有法律AI智能体 生成文本在**落盘、外发、归档前**的统一质控门槛
> 
> 使用方式：每篇输出必须**逐项勾选**；任一「阻断项」未通过 → 整体 verdict = REJECT

---

## 一、基础合规与材料安全

|#|检查维度|检查要点|检查方式|通过标准|备注|
|---|---|---|---|---|---|
|1|**材料脱敏**​|是否残留身份证号、手机号、银行卡号、车牌、住址、病历、商业秘密|正则 + 人工抽查|无任何直接标识符；间接标识符已泛化|☐|
|2|**审查立场**​|AI 是否越位作出“终局判断”（如定罪、裁决、处罚决定）|Prompt 回溯|AI 仅作分析/参考，立场为“辅助审查”|☐|
|3|**合同类型识别**​|是否正确识别合同性质（买卖/租赁/服务/技术/联营等）|对照文本要素|类型标签与正文一致，且影响后续规则选择|☐|

---

## 二、风险识别与插件联动

|#|检查维度|检查要点|检查方式|通过标准|备注|
|---|---|---|---|---|---|
|4|**专项插件调用**​|是否启用必选插件（法条效力校验 / 案例检索 / 主体资信查询）|日志检查|高风险场景必须调用对应插件并有记录|☐|
|5|**重大风险来源绑定**​|是否将风险点绑定到具体法条、判例或监管文件|溯源检查|每一处“高风险”均有明确外部依据|☐|
|6|**反向质疑完成**​|是否完成“反方论证”（即假设对方抗辩时的反驳力）|结构化阅读|至少包含 1 轮反向质疑与回应|☐|

---

## 三、人工介入与外部依赖

|#|检查维度|检查要点|检查方式|通过标准|备注|
|---|---|---|---|---|---|
|7|**人工复核事项单列**​|是否单独列出必须由人类律师确认的事项|清单检查|所有不可完全自动化决策事项均单列|☐|
|8|**外部检索披露降级**​|是否如实披露“未检索到权威来源 / 检索降级”的情况|文本扫描|无来源或低置信度时明确标注“仅供参考”|☐|

---

## 四、输出结构与AI参与边界

|#|输出类型|必须包含要素|格式要求|是否区分|备注|
|---|---|---|---|---|---|
|9|**批注（Annotation）**​|行内注释、风险提示、术语解释|行号 + 颜色/标签|✅ 独立区块|☐|
|10|**概要（Summary）**​|核心结论、风险等级、处置建议|≤ 300 字|✅ 置顶|☐|
|11|**意见（Opinion）**​|法律分析、推理链条、替代方案|三段论结构|✅ 明确区分 AI 分析与引用|☐|
|12|**流程图（Flowchart）**​|关键流程、审批路径、救济路径|Mermaid / PlantUML|✅ 可视化|☐|
|13|**说明（Disclosure）**​|AI 参与范围、局限、责任边界|固定声明模板|✅ 文末|☐|

---

## 五、AI参与范围说明（固定模板）

> 以下内容**必须**出现在每一份对外/正式文本的末尾：

text

text

```
【AI参与说明】
1. 本文件由人工智能辅助生成，仅供内部参考，不构成正式法律意见。
2. AI 参与范围：<勾选适用的项>
   □ 法条检索与效力校验
   □ 合同结构梳理与风险提示
   □ 文书草拟与语言润色
   □ 案例检索与类案比对
   □ 其他：______________
3. 未覆盖事项：<必须人工复核的内容>
4. 责任声明：最终决策由执业律师/合规负责人作出。
```

---

## 六、质控结论汇总（单页速判）

|项目|结果|
|---|---|
|材料脱敏|☐ 通过 ☐ 不通过|
|审查立场|☐ 通过 ☐ 越位|
|合同类型|☐ 已识别 ☐ 存疑|
|插件调用|☐ 完整 ☐ 缺失|
|风险绑定|☐ 完整 ☐ 不完整|
|反向质疑|☐ 完成 ☐ 未完成|
|人工事项|☐ 单列 ☐ 缺失|
|外部检索|☐ 正常 ☐ 降级披露|
|输出结构|☐ 完整 ☐ 不完整|
|AI说明|☐ 已附 ☐ 缺失|

**最终质控 verdict：**​

☐ PASS ☐ AUTO_FIX ☐ REJECT




---
## 一、你的思路评价：**方向完全正确，但单点防御不够**

输出拦截器（LTI）是**必要的最后一道防线**，但法律AI防幻觉必须是**四层防御体系**：

```
<font color="#ff0000">Layer 1: 提示词层  → 从根源减少幻觉（few-shot、强制引用格式）</font>
<font color="#ff0000">Layer 2: 推理层   → CoT + 自一致性校验</font>
<font color="#ff0000">Layer 3: 输出拦截  → LTI（你现在的重点）← 我们今天讨论的</font>
<font color="#ff0000">Layer 4: 人工复核  → 高风险提示必须人工确认</font>
```

只做Layer 3，AI会不断生成垃圾然后被拦截，效率低下。四层一起建才稳。

---

## 二、现有 LTI 技能的**三个核心漏洞**

### 🔴 漏洞1：你发现的两类问题**完全没有规则覆盖**

当前LTI内置规则（R001-R010）只覆盖：

- 已废止法律（合同法/物权法/担保法）
- 定金≤20%
- 术语规范（罚金/罚款）

**缺失的规则**（你需要立即补充）：

|应新增规则|检查逻辑|
|---|---|
|R011-裁判文书写法|"判决书"仅用于实体判决；"裁定书"用于程序裁定；禁止混用|
|R012-或裁或诉条款|引用《仲裁法》第5、9、16、17、18条校验；禁止输出"或裁或诉条款有效"|
|R013-案号格式校验|案号必须符合（年份）法院代字+案件类型代字+编号 格式|
|R014-法条序号现实性|引用法条必须是该国法条实际存在的条文号（可对接LawKB校验）|

### 🟠 漏洞2：路径硬编码，技能无法移植

技能描述中的路径是：

```
/Users/chenyouqiang/WorkBuddy/2026-05-16-task-36/lti/
```

当前工作目录已经是 `task-39`，路径失效。**所有路径应改为相对路径或配置化**。

### 🟡 漏洞3：Verifier 只检查"废止法律"，不检查"法条内容幻觉"

AI最常见的幻觉不是引用废止法律，而是：

- 引用真实存在但**内容完全错误**的法条（如"民法典第586条"存在，但内容描述错误）
- 编造**根本不存在的法条序号**（如"民法典第1234条"）

现有LTI对此**完全无能为力**。

---

## 三、完善方案：**LTI v2.0 升级建议**

- 已废止法律（合同法/物权法/担保法）
- 定金≤20%
- 术语规范（罚金/罚款）

**缺失的规则**（你需要立即补充）：

|应新增规则|检查逻辑|
|---|---|
|R011-裁判文书写法|"判决书"仅用于实体判决；"裁定书"用于程序裁定；禁止混用|
|R012-或裁或诉条款|引用《仲裁法》第5、9、16、17、18条校验；禁止输出"或裁或诉条款有效"|
|R013-案号格式校验|案号必须符合（年份）法院代字+案件类型代字+编号 格式|
|R014-法条序号现实性|引用法条必须是该国法条实际存在的条文号（可对接LawKB校验）|


---

## 📋 交付物清单

|文档名称|内容概述|字数|
|---|---|---|
|**LTI-v2.0-架构设计.md**|核心架构、组件设计、技术选型、实施路线图|~4万字|
|**LTI-v2.0-数据库设计.md**|关系型+向量+缓存三层存储设计|~1.6万字|
|**LTI-v2.0-API设计.md**|RESTful API + WebSocket + SDK设计|~1.2万字|
|**LTI-v2.0-安全与部署设计.md**|四层安全架构 + 生产部署方案|~3.2万字|

---

## 🔑 核心升级特性

### 1. 插件化架构

- **检查官作为插件**：Verifier、Auditor、Editor等作为独立插件
- **动态加载/卸载**：支持运行时启用/禁用插件
- **插件市场**：社区共享检查官插件
- **沙箱执行**：插件在沙箱中执行，确保安全

### 2. 语义理解引擎

- **Legal-BERT模型**：使用法律领域预训练模型
- **向量数据库**：ChromaDB存储法律知识的向量表示
- **语义匹配**：不再是简单的关键词匹配，而是语义层面的法律概念匹配
- **幻觉法条检测**：通过向量相似度检测幻觉法条

### 3. 智能裁决控制器

- **机器学习裁决**：基于历史数据预测可能的错误
- **自适应阈值**：根据文档类型、用户偏好动态调整裁决阈值
- **错误优先级排序**：基于多因素计算错误的严重程度
- **A/B测试**：对新规则进行A/B测试，选择最优配置

### 4. 知识库 v2.0

- **向量数据库**：使用ChromaDB/Pinecone存储法律知识的向量表示
- **语义搜索**：基于语义相似度的规则匹配
- **自动学习**：从每次检查中学习新模式，自动生成规则建议
- **规则版本ing**：支持规则版本管理和A/B测试

### 5. 可视化报告系统

- **交互式报告**：基于Plotly/ECharts的可视化报告
- **错误分布饼图**：直观展示错误类型分布
- **检查官性能条形图**：对比各检查官的性能
- **错误趋势折线图**：跨时间、跨文档类型的错误趋势
- **风险热力图**：直观展示文档中的高风险区域

### 6. 性能优化

- **并行检查**：多个检查官并行执行
- **智能缓存**：Redis缓存检查结果，避免重复计算
- **增量检查**：仅检查文档中修改的部分
- **异步处理**：大文档异步检查，实时推送进度

---

## 🗺️ 实施路线图

|阶段|时间|核心任务|
|---|---|---|
|**Phase 1**|第1-2周|基础架构升级（插件框架 + 事件总线）|
|**Phase 2**|第3-4周|知识库 v2.0（向量数据库 + 语义搜索）|
|**Phase 3**|第5-6周|智能裁决控制器（机器学习 + 自适应阈值）|
|**Phase 4**|第7-8周|Verifier v2.0（语义理解 + 幻觉法条检测）|
|**Phase 5**|第9-10周|报告与可视化（可视化报告 + 趋势分析）|
|**Phase 6**|第11-12周|性能优化（并行检查 + 智能缓存）|

**预计总实施时间**：12周（3个月）

---

## 💡 技术亮点

1. **混合存储架构**：PostgreSQL（关系型） + ChromaDB（向量） + Redis（缓存）
2. **事件驱动架构**：检查流程由事件触发，支持异步处理
3. **四层安全防护**：网络边界 → 应用 → 数据 → 基础设施
4. **JWT + RBAC**：完善的认证与授权体系
5. **Docker + K8s**：容器化部署，支持水平扩展
6. **Prometheus + Grafana**：全面的监控与告警


### 测试结果：

- ✅ **5个插件全部注册成功**：
    
    - VerifierV2 v2.0.0-enhanced [✓ 启用]
    - AuditorV2 v2.0.0 [✓ 启用]
    - EditorV2 v2.0.0 [✓ 启用]
    - PlagiarismChecker v1.0.0 [✓ 启用]
    - CitationChecker v1.0.0 [✓ 启用]
- ✅ **智能裁决控制器工作正常**：
    
    - 裁决结果：REJECT（驳回）
    - 通过概率：0.303（低于0.7阈值）
    - 置信度：0.9
    - 处理时间：0.002秒
- ✅ **检测到6个错误**：
    
    - 2个严重错误（CRITICAL）：幻觉法条、引用已废止法律
    - 4个警告（WARNING）：标点符号错误、潜在抄袭风险
- ✅ **事件系统正常**：产生了13个事件，所有事件处理器正常工作
    

### LTI v2.0 系统架构（最终版）：

```
LTI v2.0 系统
├── 核心组件
│   ├── EventBus（事件总线）
│   ├── IntelligentController（智能裁决控制器，ML驱动）
│   ├── FeatureExtractor（特征提取器，14+维特征）
│   └── AdjudicatorML（ML裁决器，RandomForest）
│
├── 检查官插件（5个）
│   ├── VerifierV2 - 语义法条核查员
│   ├── AuditorV2 - 格式审计员
│   ├── EditorV2 - 文字编辑器
│   ├── PlagiarismChecker - 抄袭检查员
│   └── CitationChecker - 引用检查员
│
└── 支持模块
    ├── Web界面（HTML+JS，无需依赖）
    ├── 模型训练脚本（准确率86.5%）
    └── 测试套件（100%通过）
```

## 实施路线图

### **Phase 1：基础集成（1-2周）**

- ✅ 创建LTI v2.0 API接口
- ✅ 在法律检索助手中集成LTI检查
- ✅ 建立统一错误编码

### **Phase 2：全面集成（2-4周）**

- ⏳ 在庭审准备助手中集成LTI检查
- ⏳ 在合同审查系统中集成LTI检查
- ⏳ 创建质量监控仪表盘

### **Phase 3：智能优化（4-8周）**

- ⏳ 建立反馈循环机制
- ⏳ 训练专门的错误预测模型
- ⏳ 实现自动修正建议

### 建议3个月内启动）

**4. 实现插件化架构** - 支持社区贡献插件（3-4周） **5. 可视化报告系统** - 交互式图表、趋势分析（2-3周） **6. 实现自适应阈值调整** - 基于历史数据动态调整（2-3周） **7. 完善反馈循环机制** - 自动创建GitHub Issue（2-3周）

### 🟢 低优先级（建议6个月内启动）

**8. 性能优化** - 并行检查、智能缓存（3-4周） **9. Docker容器化部署** - 简化部署流程（1-2周） **10. 监控和日志系统** - Prometheus + Grafana（2-3周）

## Word 中律师看到的效果

|元素|表现|
|---|---|
|封面|明确写出 `Verdict: REJECT / AUTO_FIX / PASS`|
|右侧栏|每一条 LTI Checklist 错误|
|正文|黄色高亮 + `[LTI-WARNING]`前缀|
|文档属性|可追溯质控结论|

✅ **完全符合律师日常 Word 审阅习惯**

---

# 二、一页纸 Risk Dashboard（红绿灯规则）

## 1️⃣ 设计原则

- **只给合伙人看**
    
- **30 秒内判断要不要往下审**
    
- **红 / 黄 / 绿 三色语义不可歧义**


LTI（Legal Text Inspector）规则覆盖太窄的问题，这是一个法律AI系统建设中的核心挑战。我给你一个系统性的解决方案：

## 一、问题诊断：规则覆盖窄的根本原因

从你的LTI v2.0架构看，规则覆盖窄通常源于：

1. **规则来源单一**：仅依赖少数法规或模板
2. **规则抽象层级不够**：缺乏从具体案例到通用规则的抽象
3. **规则更新滞后**：未能及时纳入新法规、新司法解释
4. **规则分类维度单一**：缺乏多维度、多层次的规则组织

## 二、丰富规则库的系统方法

### **方法1：多源规则采集体系**

建立"四纵四横"规则采集网络：

**四纵（规则来源）**：

- **法律法规库**：人大法工委、国务院、部委规章
- **司法案例库**：最高法指导案例、公报案例、典型案例
- **行业规范库**：各行业主管部门的规范性文件
- **合同模板库**：标准合同、行业示范文本

**四横（采集方式）**：

- **自动爬取**：通过API对接"北大法宝"、"威科先行"等数据库
- **人工整理**：资深律师整理实务经验
- **案例反哺**：从审查案例中自动提取新规则
- **用户反馈**：建立规则缺失反馈机制

### **方法2：规则结构化建模**

将规则分解为可计算的结构化对象：

**python**

复制

```python
{
  "rule_id": "contract_review_001",
  "rule_type": "mandatory",  # 强制性/建议性/风险提示
  "rule_category": "contract_formation",  # 规则分类
  "applicable_scenarios": ["purchase_contract", "service_contract"],
  "rule_content": "合同必须包含标的条款",
  "legal_basis": ["民法典第470条"],
  "risk_level": "high",  # 高/中/低
  "detection_pattern": "regex或NLP模式",
  "remedy_suggestion": "建议补充标的条款",
  "effective_date": "2021-01-01",
  "expiry_date": None,
  "related_rules": ["rule_002", "rule_003"]
}
```

### **方法3：规则自动发现与生成**

利用AI技术从案例中自动提取规则：

1. **案例说理提取**：用NLP从判决书"法院认为"部分提取裁判规则
2. **争议焦点聚类**：对大量案件的争议焦点进行聚类分析，发现高频风险点
3. **规则冲突检测**：自动发现新旧规则、不同层级规则间的冲突
4. **规则效果评估**：通过历史案例验证规则的有效性

### **方法4：规则库动态更新机制**

建立"OODA循环"式更新机制：

- **Observe（观察）**：监控系统运行中的规则命中率、漏报率
- **Orient（定位）**：分析未命中案例，定位规则缺失
- **Decide（决策）**：确定新规则或规则调整方案
- **Act（行动）**：更新规则库，重新训练模型

## 三、针对LTI v2.0的具体实施建议

### **短期（1-2周）：快速扩容**

1. **导入现有规则集**：
    
    - 将你已整理的90条风险规则导入结构化规则库
    - 补充《民法典》《合同法》《司法解释》的强制性规定
2. **建立规则分类体系**：
    
    - 按合同类型分类：买卖、服务、借款、租赁等
    - 按审查维度分类：主体、标的、价款、履行、违约等
    - 按风险等级分类：🔴高风险、🟡中风险、🟢低风险

### **中期（1-2个月）：系统化建设**

1. **对接外部数据源**：
    
    - 申请"北大法宝"API接口，自动同步最新法规
    - 爬取"中国裁判文书网"相关案例（注意合规性）
2. **开发规则管理后台**：
    
    - 可视化规则编辑界面
    - 规则版本管理
    - 规则效果分析报告

### **长期（3-6个月）：智能化演进**

1. **规则自动发现引擎**：
    
    - 训练案例说理提取模型
    - 开发规则冲突检测算法
2. **规则众包平台**：
    
    - 允许资深律师贡献规则
    - 建立规则质量评估体系

## 四、技术实现路径

### **阶段1：规则结构化存储**

### **阶段2：规则引擎开发**

### **阶段3：规则效果监控**
## 五、关键成功因素

1. **规则质量 > 规则数量**：每条规则都要经过验证
2. **持续迭代**：规则库不是一次建完，要持续更新
3. **人机协同**：AI发现 + 人工验证
4. **效果闭环**：建立规则效果反馈机制

## 六、下一步行动建议

我建议你按以下顺序推进：

1. **本周**：整理现有90条规则，建立Excel版规则清单
2. **下周**：设计规则库数据结构，开发规则导入脚本
3. **本月**：对接1-2个外部数据源，扩大规则来源
4. **下月**：建立规则效果监控dashboard



## 相关笔记
- [[谈案律师技能设计方案_20260528]] (共现关键词: 合同, 仲裁, text)
- [[文书红队推演配置]] (共现关键词: 民法, 合同, 仲裁)
- [[律师用AI梳理证据链的5个重点附提示词]] (共现关键词: 合同, 仲裁)
- [[LTI-文本监察官系统配置说明]] (共现关键词: 文本, 监察官, 系统配置)
- [[self.md-20260817]] (共现关键词: self, 民法, 合同)
- [[月度回灌日志]] (共现关键词: self, 合同)
- [[最佳实践模板]] (共现关键词: 法条, 合同)
- [[小强律师人伤法自学每日报告-2026年06月28日]] (共现关键词: 法条, 民法, 合同)
- [[工伤赔偿项目全景表13项6维度建议收藏]] (共现关键词: 法条, 合同)
- [[小强律师人伤法自学每日报告-2026年06月19日]] (共现关键词: 合同, 行政)
- [[工伤认定2026最新裁判与规则]] (共现关键词: 合同, 行政)
- [[工伤保险条例-核心条文摘录]] (共现关键词: 合同, 行政)
- [[法考必考的最新入库案例]] (共现关键词: 裁定, 行政, 民法)
- [[律师数字分身系统技能配置迭代方案 1.0]] (共现关键词: ---, 裁定, 民法)
- [[LTI文本监控器v4.0迁移与调用规范]] (共现关键词: LTI, 文本)
- [[法律检索助手迭代配置说明v2]] (共现关键词: 说明, 行政)
- [[法律文书写作助手 Skill配置说明v1.0]] (共现关键词: 说明, 仲裁)
- [[法随案例库 MCP 集成说明]] (共现关键词: 说明, 行政)
- [[WorkBuddy50个实用提示词]] (共现关键词: 违约, 说明, 行政)
- [[律师AI提效的7套黄金提示词]] (共现关键词: 行政法, 民法, 行政)
- [[律师AI提示词清单（1.0 版）]] (共现关键词: ---, 行政法, 行政)
- [[律师AI提示词使用指南从入门到精通]] (共现关键词: 仲裁, 民法, 法条)
- [[经验卡片-要素式文书实务-示范文本首选率超75%]] (共现关键词: 违约, 文本, 行政)
- [[法律文书防幻觉提示词_LTI校验版]] (共现关键词: 文本, 违约, 法条)
- [[小哲AI 学伴智能体搭建方案]] (共现关键词: 文本, 行政)
- 合同审查报告-简约版-使用说明 
- 律师AI提示词使用指南从入门到精通 
- V1.1输出拦截器——法律文书常见错误案例库 
- [[法律检索助手迭代配置说明v2|法律检索助手迭代配置说明v2]]|法律检索助手迭代配置说明v2|法律检索助手迭代配置说明v2|法律检索助手迭代配置说明v2|法律检索助手迭代配置说明v2|法律检索助手迭代配置说明v2|法律检索助手迭代配置说明v2|法律检索助手迭代配置说明v2 
- 法律文书写作助手skill 配置说明书v2.0 
