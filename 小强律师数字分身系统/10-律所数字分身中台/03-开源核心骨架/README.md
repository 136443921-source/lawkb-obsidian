---
created: 2026-09-10T16:26
updated: 2026-09-10T18:08
---
# 中小律所数字分身模板 · 开源核心骨架

> 本目录是可复制骨架的最小集：**跑通四件套（EV 架构 + 飞轮 + LTI + 四模板联动）** 即止。
> 运行 `./deploy.sh` 即可在本机脚手架出一套 `digital-avatar-kit/`，按 `combine.sh` 由
> 律师画像模板生成各席位 `self.md`。

## 目录约定（脚手架产物）

```
digital-avatar-kit/
├── legal-base/SKILL.md          # 法律类技能基座（LTI 拦截 + 幻觉防御 + 飞轮检索纪律）
├── lawyer-yourself-skill/       # 数字分身创建器
│   ├── SKILL.md
│   └── self.md                  # ⚠️ 由 combine.sh 生成，勿手改
├── LTI文本监控器/SKILL.md        # 出文门禁（R/L/C/T/P + 六维）
├── 知识飞轮/                     # 六层挂载 + 扫描/回填脚本（占位，接用户 LawKB）
├── cockpit-portal/              # 统一工作台（RBAC + SSO 骨架）
│   └── portal/{index.html, rbac.js, auth.js}
├── templates/
│   ├── lawyer-profile-template.schema.yaml   # 基座模板（来自 01-律师画像模板/）
│   └── example.lawyer.profile.yaml           # 实例样例
├── combine.sh                   # 模板 → self.md 生成器
└── README.md
```

## 最小技能集（刻意不做重）

| 组件 | 是否必须 | 说明 |
|------|----------|------|
| `legal-base` | ✅ | 所有法律子技能 `extends: legal-base`，门禁/纪律唯一来源 |
| `lawyer-yourself-skill` | ✅ | 消费 profile 蒸馏分身 |
| `LTI文本监控器` | ✅ | 防幻觉质量闸 |
| `知识飞轮` | ✅（增强） | 问答前检索 + 任务后沉淀 |
| `cockpit-portal` | ◯（增强） | 权限中台，对标 Harvey Command Center |
| 模拟法庭 / 积分监测 | ❌ | 增强项，按需加装 |

## 使用

```bash
./deploy.sh ~/my-firm-avatar      # 脚手架到指定目录
cd ~/my-firm-avatar
cp templates/example.lawyer.profile.yaml templates/zhang.profile.yaml
# 编辑 zhang.profile.yaml 的 seat_role / practice_areas / title
./combine.sh templates/zhang.profile.yaml   # 生成 lawyer-yourself-skill/self.md
```

## 许可证

核心骨架以 **Apache-2.0** 开源（带专利授权条款，防 clone 后申请专利反咬）。

商业化走**「开源内核 + 私有化部署 + 蒸馏服务 + 行业规则包」**，**不做公有云 SaaS**——
数据不出所是本方案最锋利的差异化，上云即自我摧毁，且额外触发备案与安全评估义务。
`cockpit-portal` 权限层为增强组件，交付方式是**私有化部署**，非订阅制。

口径依据见方法论白皮书 `02-中小律所数字分身模板方法论.md`（§七 可复制骨架 / §八 License 与合规红线）；
定价与交付细节见 `04-商业化方法论-服务变现实施报告-v1.0.md`（内部手册，对外前须脱敏）。

> v2.0 口径修正：本段原写"MIT 开源 + 轻 SaaS 收费"，与白皮书 §5.2 / §8.1 及 04 报告冲突，已统一。
