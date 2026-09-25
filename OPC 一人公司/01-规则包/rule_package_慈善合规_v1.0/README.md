---
created: 2026-09-23T22:34
updated: 2026-09-24T00:01
---
# 慈善合规规则包 · 使用说明（v1.0）

> 适用域：慈善组织（基金会、慈善总会、社会服务机构）合规运营
> 生成日期：2026-09-24 ｜ 计费模式：subscription_by_domain ｜ 许可：internal_commercial_unit
> 采集模式：目录（目录 知识飞轮系统/06-沉淀/慈善合规域库）

## 一、这个包是什么
本包是把「慈善合规」领域的数字资产（规则卡 / 法律法规 / 内规手册 / 经验卡 / 自查清单）**标准化封装**后，
交付给**运营部门**（内部虚构商业化单元）订阅使用的规则集合。本席只负责把包的质量做高，定价与定位由运营部门负责人核定。

## 二、交付物清单
| 资产 | 数量 | 位置 |
|---|---|---|
| 慈善合规规则卡 | 188 张 | `assets/rules/charity_rules.json` |
| 法律法规 | 11 部 | `assets/laws/laws_index.json` |
| 内规手册 | 135 条（章节索引） | `assets/internal/internal_index.json` |
| 经验卡 | 6 张 | `assets/cards/` |
| 自查清单 | 2 份 | `assets/checklists/checklists_index.json` |

## 三、使用限制
- 仅限内部虚构商业化单元订阅使用，**非对外公开售卖**。
- 含「待核验源」标记的条目（共 95 条，清单见 `assets/rules/source_pending_list.json`），商用前须由运营/合规负责人复核法源（元典核验）。
- 个案卷宗、当事人隐私**绝不**进入本包。

## 四、更新与订阅
- 本包随源资产迭代；版本号与 `CHANGELOG.md` 同步。
- 计费与订阅档位由运营部门负责人核定（见 `manifest.json › billing`）。
