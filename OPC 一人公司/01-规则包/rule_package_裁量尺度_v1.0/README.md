# 裁量尺度规则包 · 使用说明（v1.0）

> 适用域：跨域横切：处罚/赔偿/量刑裁量基准（card_type=裁量尺度 或 标题含'裁量'）
> 生成日期：2026-09-23 ｜ 计费模式：subscription_by_domain ｜ 许可：internal_commercial_unit
> 采集模式：横切标签（card_type=裁量尺度 / title_contains=['裁量']）

## 一、这个包是什么
本包是把「裁量尺度」领域的数字资产（规则卡 / 法律法规 / 内规手册 / 经验卡 / 自查清单）**标准化封装**后，
交付给**运营部门**（内部虚构商业化单元）订阅使用的规则集合。本席只负责把包的质量做高，定价与定位由运营部门负责人核定。

## 二、交付物清单
| 资产 | 数量 | 位置 |
|---|---|---|
| 裁量尺度规则卡 | 49 张 | `assets/rules/discretion_rules.json` |
| 法律法规 | 0 部 | `assets/laws/laws_index.json` |
| 内规手册 | 0 条（章节索引） | `assets/internal/internal_index.json` |
| 经验卡 | 0 张 | `assets/cards/` |
| 自查清单 | 0 份 | `assets/checklists/checklists_index.json` |

## 三、使用限制
- 仅限内部虚构商业化单元订阅使用，**非对外公开售卖**。
- 含「待核验源」标记的条目（共 33 条，清单见 `assets/rules/source_pending_list.json`），商用前须由运营/合规负责人复核法源（元典核验）。
- 个案卷宗、当事人隐私**绝不**进入本包。

## 四、更新与订阅
- 本包随源资产迭代；版本号与 `CHANGELOG.md` 同步。
- 计费与订阅档位由运营部门负责人核定（见 `manifest.json › billing`）。
