# 人伤法规则包 · 使用说明（v1.0）

> 适用域：人身损害（医疗/工伤/交通/其他）纠纷：过错认定、参与度、赔偿规则
> 生成日期：2026-09-24 ｜ 计费模式：subscription_by_domain ｜ 许可：internal_commercial_unit
> 采集模式：目录（目录 知识飞轮系统/06-沉淀/人伤法域库）

## 一、这个包是什么
本包是把「人伤法」领域的数字资产（规则卡 / 法律法规 / 内规手册 / 经验卡 / 自查清单）**标准化封装**后，
交付给**运营部门**（内部虚构商业化单元）订阅使用的规则集合。本席只负责把包的质量做高，定价与定位由运营部门负责人核定。

## 二、交付物清单
| 资产 | 数量 | 位置 |
|---|---|---|
| 人伤法规则卡 | 427 张 | `assets/rules/personal_injury_rules.json` |
| 法律法规 | 6 部 | `assets/laws/laws_index.json` |
| 内规手册 | 0 条（章节索引） | `assets/internal/internal_index.json` |
| 经验卡 | 0 张 | `assets/cards/` |
| 自查清单 | 2 份 | `assets/checklists/checklists_index.json` |

## 三、使用限制
- 仅限内部虚构商业化单元订阅使用，**非对外公开售卖**。
- 含「待核验源」标记的条目（共 174 条，清单见 `assets/rules/source_pending_list.json`），商用前须由运营/合规负责人复核法源（元典核验）。
- 个案卷宗、当事人隐私**绝不**进入本包。

## 四、更新与订阅
- 本包随源资产迭代；版本号与 `CHANGELOG.md` 同步。
- 计费与订阅档位由运营部门负责人核定（见 `manifest.json › billing`）。
