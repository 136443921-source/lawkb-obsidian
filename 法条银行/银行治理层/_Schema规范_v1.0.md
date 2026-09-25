---
title: 法条银行 Schema 规范
type: schema-spec
version: v1.0
status: active
created: 2026-09-22
updated: 2026-09-25T20:41
author: 小强
---

# 法条银行 Schema 规范（v1.0 · 2026-09-22）

> 本规范为法条银行所有文件的 frontmatter 与命名统一标准，由《法条银行搭建建议方案_v1.0_2026-09-22.md》落地。LTI 门禁与管线检索依赖本规范字段，新增/修订文件必须遵循。

## 一、文件命名规范（强制）
```
<法规全称>（<发文字号>）[·<版本指纹>][·<节选范围>].md
```
- 示例：`中华人民共和国慈善法（主席令第19号）·2023修正.md`
- 示例：`中华人民共和国道路交通安全法（主席令第47号）·节选·事故责任与赔偿专题.md`
- 禁止：无发文字号、无版本指纹、纯描述性命名。

## 二、A 型 · 权威法规卡（本地权威源）
```yaml
title: <法规全称>
type: statute
doc_no: <发文字号>            # 主席令第19号 / 法释〔2015〕17号 / 国务院令第701号
effect_rank: 法律|行政法规|司法解释|部门规章|地方性法规
org: <制定机关>
effective_date: <YYYY-MM-DD>
sxx: 现行有效|已废止|即将生效|待核验   # 统一枚举，替换 version_mismatch 文案
source: <权威源URL或核填通道>
source_verify: 双证一致|待核验   # pkulaw/qcc 远程指纹 与 本地末条施行日期一致性
retrieved_date: <YYYY-MM-DD>
scope: 全文|节选·<专题>          # 节选必须标范围
statute_text_pending: false       # LTI 门禁联动字段
aliases: [<常用简称>]
updated: <YYYY-MM-DD>
```

## 三、B 型 · 资讯 / 案例卡
```yaml
title: <标题>
type: digest|case
source: <官方链接>
maturity: 🌱种子|🌿成长|🌳核心
review_interval: 30
status: draft|active
updated: <YYYY-MM-DD>
```
> 指导案例索引统一使用英文键（title/tags/type/...），**废弃中文键**（标题/创建日期/更新日期/标签）。

## 四、版本治理铁律
1. **双证一致**：`source_verify` 须 pkulaw/qcc 远程指纹 与 本地末条施行日期一致，否则 `sxx: 待核验` + `statute_text_pending: true`。
2. **旧版处置**：发现旧版（如慈善法 2016）→ 现行版另存为 `·<版本指纹>` 置顶；旧版移 `法条银行/_archive/` **不删**，frontmatter 标 `superseded_by`。
3. **禁疑本回填**：`sxx: 待核验` 副本，LTI 与管线一律不得引用。
4. **公众号源禁条号级引用**：`mp.weixin.qq.com` 转载法规仅作内容备份，文件名标 `·内容备份·禁条号级引用`，`statute_text_pending: true`，禁止条号级引用。

## 五、引用与回源规则（本地源引证铁律）
- 文书 / 卡片引用法条 → 优先命中 `法条银行/` 本地文件；命中不到 → 标 `statute_text_pending` 走 pkulaw / 元典 / qcc 核填，核填完 verbatim 回填本地并置 false。
- 民法典后条号重排 → 引用同时给新旧条号。
- 公众号转载法规 → 仅作线索，禁条号级引用。

## 六、与 LTI / 管线接口
- `statute_text_pending` 字段双向联动 LTI 门禁（true 即拦截）。
- 覆盖台账 `_本地法条银行_覆盖台账.md` 登记版本指纹，供 LTI 与管线检索。
- 取号不冲突（六-A 门禁）。

---

*本规范为方案落地件，字段调整须经老强确认后版本号 +1。*

## 相关笔记
- [[RULE-038---T1-落-`法条银行_Schema规范_v1.0.md`（两型统一-fron]] (共现关键词: 规范, Schema, v1.0)
