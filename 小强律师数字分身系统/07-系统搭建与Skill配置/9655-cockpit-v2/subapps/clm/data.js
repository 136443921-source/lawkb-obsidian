window.CLM_DATA = {
  "generatedAt": "2026-09-17 13:20",
  "today": "2026-09-17",
  "stageNames": [
    "①接案建档",
    "②检索研究",
    "③文书起草",
    "④庭审查庭",
    "⑤客户协作",
    "⑥程序执行",
    "⑦风控归档"
  ],
  "gateStatusText": {
    "pass": "通过",
    "active": "进行中",
    "warn": "警示",
    "fail": "未通过",
    "todo": "待办",
    "waived": "免除",
    "skip": "跳过"
  },
  "kpi": {
    "caseCount": 13,
    "p0Count": 3,
    "overdueCount": 2,
    "deadlineCount": 8
  },
  "deadlines": [
    {
      "id": "d1",
      "name": "34 号庭后补充意见（证据⑨强化意见一版）呈递",
      "due": "2026-09-07",
      "type": "约定",
      "level": "P0",
      "state": "done",
      "basis": "2026-09-05 老强拍板呈递时机定为星期一",
      "note": "已于 2026-09-07 呈递法院（与 31/33 号一并归整呈递）；34 号为证据⑨强化意见一版终稿",
      "_caseNo": "(2026)黔0330民初6658号",
      "_caseId": "6658",
      "_daysLeft": -10,
      "_level": "overdue",
      "_rank": 0
    },
    {
      "id": "d2",
      "name": "对撤诉意见（二）[含⑦调查取证、⑧录音刻录附卷、⑨焦联鹏到庭询问] 经当事人核验确认，已于 2026-09-07 前后递交法院",
      "due": "2026-09-07",
      "type": "计划",
      "level": "P0",
      "state": "done",
      "basis": "⑦⑧⑨ 已并入⑪意见（二），不另立申请；2026-09-06 老强确认口径",
      "note": "意见（二）已发当事人核验确认并递交法院（老强 2026-09-16 核实：实际已递交，案卷原 armed 为状态陈旧未更新）；原「未递交前不得视为已提交」约束现已解除",
      "_caseNo": "(2026)黔0330民初6660号",
      "_caseId": "6660",
      "_daysLeft": -10,
      "_level": "overdue",
      "_rank": 0
    },
    {
      "id": "d2",
      "name": "撤诉裁定送达前窗口期处置（19 号备用稿）",
      "due": null,
      "type": "触发型",
      "level": "P1",
      "state": "armed",
      "basis": "原告若申请撤诉即触发",
      "note": "19 号《对原告申请撤诉的意见》备用，撤诉不妨碍审查+保留另诉/投诉/控告权利",
      "_caseNo": "(2026)黔0330民初6658号",
      "_caseId": "6658",
      "_daysLeft": null,
      "_level": "armed",
      "_rank": 4
    },
    {
      "id": "d3",
      "name": "一审判决上诉期",
      "due": null,
      "type": "触发型",
      "level": "P0",
      "state": "armed",
      "basis": "判决书送达之日起十五日（条文序号交付前须经 LTI 核验）",
      "note": "择期宣判中，送达日起算；裁定为十日",
      "_caseNo": "(2026)黔0330民初6658号",
      "_caseId": "6658",
      "_daysLeft": null,
      "_level": "armed",
      "_rank": 4
    },
    {
      "id": "d1",
      "name": "撤诉裁定送达前窗口期（自认钉死+录音附卷已闭环，静候送达）",
      "due": null,
      "type": "触发型",
      "level": "P2",
      "state": "armed",
      "basis": "准许撤诉裁定不可上诉、不可复议，唯一救济为诉讼费院长复核",
      "note": "自认钉死（8.19《情况说明》真卷证据9 / 8.24被告方通话录音说明 / 法院官方8.24电话询问录音笔录已调取归卷）已于裁定送达前闭环；窗口期仍开放，送达即关闭不可补救，故仍须保持可见",
      "_caseNo": "(2026)黔0330民初6660号",
      "_caseId": "6660",
      "_daysLeft": null,
      "_level": "armed",
      "_rank": 4
    },
    {
      "id": "d4",
      "name": "类案 R1-R5 黔2627 以外 3 案庭审引用前原文核验",
      "due": null,
      "type": "内部",
      "level": "P1",
      "state": "pending",
      "basis": "防幻觉铁律：引用前必核原文",
      "note": "未完成 C4 核验不得当庭引用",
      "_caseNo": "(2026)黔0330民初6658号",
      "_caseId": "6658",
      "_daysLeft": null,
      "_level": "pending",
      "_rank": 5
    },
    {
      "id": "d3",
      "name": "封堵原样再诉（民诉法解释第214条第1款）",
      "due": null,
      "type": "持续",
      "level": "P1",
      "state": "pending",
      "basis": "撤诉后可再诉，须以自认钉死+附卷阻断",
      "note": "条文序号交付前须经 LTI 核验",
      "_caseNo": "(2026)黔0330民初6660号",
      "_caseId": "6660",
      "_daysLeft": null,
      "_level": "pending",
      "_rank": 5
    },
    {
      "id": "d4",
      "name": "黄茂姣资金流水调取（另案索赔前置）",
      "due": null,
      "type": "内部",
      "level": "P2",
      "state": "pending",
      "basis": "与 6658 案联动",
      "note": "属另案索赔前置条件，非本案当期必办",
      "_caseNo": "(2026)黔0330民初6660号",
      "_caseId": "6660",
      "_daysLeft": null,
      "_level": "pending",
      "_rank": 5
    }
  ],
  "cases": [
    {
      "schema": "case-state/v1",
      "caseId": "6658",
      "caseNo": "(2026)黔0330民初6658号",
      "title": "丁戊祥诉刘九零、刘维、黄茂姣、习水县欧派木门杉王店吊顶买卖合同纠纷案",
      "court": "贵州省习水县人民法院 · 速裁法庭",
      "judge": "龙雅清（独任审判员）",
      "procedure": "简易程序",
      "partyRole": "被告方",
      "counselRole": "代书（未正式代理）",
      "client": [
        "刘九零",
        "刘维"
      ],
      "domain": "建设工程/买卖合同",
      "status": "进行中",
      "stage": {
        "current": 4,
        "code": "trial",
        "name": "④庭审查庭",
        "enteredAt": "2026-09-01",
        "note": "第一次开庭已毕，择期宣判；34 号庭后补充意见（证据⑨强化意见一版）已于 2026-09-07 呈递法院"
      },
      "gates": {
        "G0": {
          "name": "收案门禁",
          "status": "pass",
          "note": "已建档，案件笔记入 LawKB"
        },
        "G1": {
          "name": "检索门禁",
          "status": "pass",
          "note": "07 法律检索报告、22 类案检索报告已出"
        },
        "G2": {
          "name": "文书门禁",
          "status": "pass",
          "note": "01-05 答辩/举证/质证/发问/代理词已提交"
        },
        "G3": {
          "name": "庭审门禁",
          "status": "active",
          "note": "9/1 开庭已毕，23 号笔录研读已出；择期宣判未结"
        },
        "G4": {
          "name": "客户门禁",
          "status": "pass",
          "note": "34 号已交当事人核验通过，并于 2026-09-07 呈递法院"
        },
        "G5": {
          "name": "程序门禁",
          "status": "active",
          "note": "24/25/26 已提交，33 号调取申请已获准履行"
        },
        "G6": {
          "name": "风控门禁",
          "status": "pass",
          "note": "34/35 号 LTI 校验 PASS（0 REJECT）"
        },
        "G7": {
          "name": "结案回流",
          "status": "todo",
          "note": "待判决生效后启动经验回填"
        }
      },
      "deadlines": [
        {
          "id": "d1",
          "name": "34 号庭后补充意见（证据⑨强化意见一版）呈递",
          "due": "2026-09-07",
          "type": "约定",
          "level": "P0",
          "state": "done",
          "basis": "2026-09-05 老强拍板呈递时机定为星期一",
          "note": "已于 2026-09-07 呈递法院（与 31/33 号一并归整呈递）；34 号为证据⑨强化意见一版终稿"
        },
        {
          "id": "d2",
          "name": "撤诉裁定送达前窗口期处置（19 号备用稿）",
          "due": null,
          "type": "触发型",
          "level": "P1",
          "state": "armed",
          "basis": "原告若申请撤诉即触发",
          "note": "19 号《对原告申请撤诉的意见》备用，撤诉不妨碍审查+保留另诉/投诉/控告权利"
        },
        {
          "id": "d3",
          "name": "一审判决上诉期",
          "due": null,
          "type": "触发型",
          "level": "P0",
          "state": "armed",
          "basis": "判决书送达之日起十五日（条文序号交付前须经 LTI 核验）",
          "note": "择期宣判中，送达日起算；裁定为十日"
        },
        {
          "id": "d4",
          "name": "类案 R1-R5 黔2627 以外 3 案庭审引用前原文核验",
          "due": null,
          "type": "内部",
          "level": "P1",
          "state": "pending",
          "basis": "防幻觉铁律：引用前必核原文",
          "note": "未完成 C4 核验不得当庭引用"
        }
      ],
      "timeline": [
        {
          "date": "2026-07-14",
          "event": "刘维与丁戊祥通话录音（10分50秒，证据⑦）"
        },
        {
          "date": "2026-08-19",
          "event": "丁戊祥《情况说明》，自认黄茂姣带客选货付订金"
        },
        {
          "date": "2026-08-24",
          "event": "刘维与丁戊祥通话（3分13秒，证据⑧）；同日法官电话询问丁戊祥（证据⑨）"
        },
        {
          "date": "2026-08-26",
          "event": "庭前准备报告 v3；类案检索 5 规则"
        },
        {
          "date": "2026-09-01",
          "event": "第一次开庭（速裁法庭 15:00），实体审理至择期宣判",
          "key": true
        },
        {
          "date": "2026-09-02",
          "event": "31 号 v4 纠错、32 号 v2 委托书矛盾分析"
        },
        {
          "date": "2026-09-03",
          "event": "33 号调取法官询问录音笔录申请书定稿"
        },
        {
          "date": "2026-09-05",
          "event": "真卷核验重大重构：冒名诉讼降补强，实体合同相对性升主攻；34 号四轮推翻改写为证据⑨强化意见一版",
          "key": true
        },
        {
          "date": "2026-09-07",
          "event": "34 号庭后补充意见（证据⑨强化意见一版）呈递法院（与 31/33 号一并归整呈递）",
          "key": true
        }
      ],
      "nextActions": [
        "34 号庭后补充意见（证据⑨强化意见一版）已于 2026-09-07 呈递法院，持续跟踪择期宣判节点",
        "呈递清单与 31/33 号一并归整，待老强拍板后执行",
        "跟踪择期宣判时间节点，送达即起算上诉期",
        "持续提示：程序异议属平行备位轨道，不遮蔽实体防御主线（01/05 号）"
      ],
      "risks": [
        "真卷显示丁戊祥委托律师陈宇、妻子盖章、当庭确认授权，冒名诉讼驳回起诉路径被法庭实际否定，程序战成功概率有限",
        "证据⑤《未起诉说明》已被丁戊祥当庭陈述推翻，不得再作程序战核心依据",
        "刘九零/刘维当庭认可 75 元阳角，金额层面存在部分自认，须严守防自认铁律",
        "34 号前后四轮推翻重写，版本混乱风险，呈递前须确认最终版本为证据⑨强化意见一版"
      ],
      "stance": {
        "blue": 20,
        "trend": "flat",
        "reason": "实体防御有当庭自认支撑（刘维自认房子包给黄茂姣仅选货、黄茂姣代付定金及11万），但程序战被法庭否定、金额层面存在部分自认，整体略优于持平"
      },
      "meta": {
        "schema": "case-meta/v1",
        "agents": [
          {
            "stage": "①接案建档",
            "gate": "G0",
            "role": "建档/决策留痕",
            "agent": "CLM case-state.json + decision-capture",
            "status": "已接入",
            "artifacts": [
              "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/丁戊祥诉刘九零吊顶买卖合同纠纷案/丁戊祥诉刘九零吊顶买卖合同纠纷案-案件笔记.md（案情笔录/案件备忘录）"
            ]
          },
          {
            "stage": "②检索研究",
            "gate": "G1",
            "role": "法律检索",
            "agent": "元典MCP(yuandian-mcp) + 北大法宝MCP(pkulaw)",
            "status": "已接入",
            "note": "二源互补",
            "artifacts": [
              "/Users/chenyouqiang/Desktop/小强律师办案系统/庭审10件套_丁戊祥诉刘九零吊顶案（6658）/07_法律检索报告.docx"
            ]
          },
          {
            "stage": "②检索研究",
            "gate": "G1",
            "role": "类案检索",
            "agent": "元典case vector + 北大法宝MCP + 法随案例库MCP",
            "status": "已接入",
            "note": "三源互补",
            "artifacts": [
              "/Users/chenyouqiang/Desktop/小强律师办案系统/庭审10件套_丁戊祥诉刘九零吊顶案（6658）/22_类案检索报告.docx"
            ]
          },
          {
            "stage": "②检索研究",
            "gate": "G1",
            "role": "检索归档",
            "agent": "ima 知识库",
            "status": "已接入",
            "artifacts": [
              "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/丁戊祥诉刘九零吊顶买卖合同纠纷案/丁戊祥诉刘九零吊顶买卖合同纠纷案-案件笔记.md"
            ]
          },
          {
            "stage": "③法律文书起草",
            "gate": "G2",
            "role": "法律文书（庭审六件套）",
            "agent": "法律文书docx交付流水线 + LTI文本监控器",
            "status": "已接入",
            "artifacts": [
              "/Users/chenyouqiang/Desktop/小强律师办案系统/庭审10件套_丁戊祥诉刘九零吊顶案（6658）/01_民事答辩状0810.docx",
              "/Users/chenyouqiang/Desktop/小强律师办案系统/庭审10件套_丁戊祥诉刘九零吊顶案（6658）/02_举证清单.docx",
              "/Users/chenyouqiang/Desktop/小强律师办案系统/庭审10件套_丁戊祥诉刘九零吊顶案（6658）/03_质证意见.docx",
              "/Users/chenyouqiang/Desktop/小强律师办案系统/庭审10件套_丁戊祥诉刘九零吊顶案（6658）/04_庭审发问提纲.docx",
              "/Users/chenyouqiang/Desktop/小强律师办案系统/庭审10件套_丁戊祥诉刘九零吊顶案（6658）/05_代理词.docx",
              "/Users/chenyouqiang/Desktop/小强律师办案系统/庭审10件套_丁戊祥诉刘九零吊顶案（6658）/06_庭审预案.docx"
            ]
          },
          {
            "stage": "④庭审查庭",
            "gate": "G3",
            "role": "模拟法庭/审判要件",
            "agent": "mock-trial-control-center + 审判要件卡拆卡流水线 + 本会话专家",
            "status": "已接入"
          },
          {
            "stage": "⑤客户协作",
            "gate": "G4",
            "role": "汇报/推送",
            "agent": "案件工作汇报 + 调解和解 + CLM send_client_brief + agent-mail",
            "status": "已接入（邮件通道待配webhook）"
          },
          {
            "stage": "⑥程序执行",
            "gate": "G5",
            "role": "程序推进",
            "agent": "案件全生命周期·程序推进包",
            "status": "已建"
          },
          {
            "stage": "⑦风控归档",
            "gate": "G6/G8",
            "role": "合规风控",
            "agent": "LTI + lawkb-legal-consistency-audit + G8非诉专项",
            "status": "已接入"
          },
          {
            "stage": "结案回流",
            "gate": "G7",
            "role": "经验沉淀",
            "agent": "mind-distill + LawKB 知识飞轮",
            "status": "已接入"
          },
          {
            "stage": "运维",
            "gate": "-",
            "role": "入口/监测",
            "agent": "xiaoqiang-cockpit-hub + workbuddy-credit-monitor",
            "status": "已接入"
          }
        ]
      },
      "mockTrial": {
        "prepReportReady": true,
        "prepReportPath": "LawKB/法律文书/模拟法庭/庭前强化稿/庭审准备报告_v3.md",
        "status": "未启动",
        "lastTrialAt": null,
        "trialBriefPath": null
      },
      "publicView": {
        "stageText": "一审已开庭，等待法院宣判",
        "done": [
          "2026-09-01 已参加第一次开庭",
          "已向法院提交答辩状、举证清单、质证意见、代理词等诉讼材料",
          "已提交调取证据申请并获法院准许"
        ],
        "next": "34 号庭后补充意见（证据⑨强化意见一版）已于 2026-09-07 呈递法院，其后等待法院宣判",
        "clientTodo": [
          "核验并签署《庭后补充意见（二）》，确认无误后由我们代为呈递",
          "收到法院判决书后第一时间告知我们，以便计算上诉期限"
        ],
        "contact": "陈友强"
      },
      "updatedAt": "2026-09-14",
      "source": "桌面真卷「小强律师办案系统/丁戊祥诉刘九零吊顶案」+ LawKB 案件笔记（2026-09-05 真卷重构版）",
      "_folder": "丁戊祥诉刘九零吊顶买卖合同纠纷案",
      "_path": "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/丁戊祥诉刘九零吊顶买卖合同纠纷案/case-state.json",
      "evidence": [
        {
          "no": "证据1",
          "name": "黄茂姣装修报价单（黄茂姣.xlsx）",
          "source": "承包方出具（电子数据原始载体）",
          "purpose": "整装总价178,000元；其中“厨房厕所吊顶”项目单独列价4,000元（备注：吕扣板吊顶+两台暖风机）——吊顶属承包方包工包料范围，材料采购义务在承揽人（《民法典》第七百七十条、第七百七十四条）",
        },
        {
          "no": "证据2",
          "name": "2025年6月25日收据（No.6912057）",
          "source": "原件1份",
          "purpose": "2025.6.25收30,000元，付款人刘九零、收款人黄茂姣——装修款向承包方支付",
        },
        {
          "no": "证据3",
          "name": "2025年8月4日收据",
          "source": "原件1份",
          "purpose": "2025.8.4收40,000元，付款人刘九零、收款人黄茂姣，盖“欧派门业习水专卖店”章",
        },
        {
          "no": "证据4",
          "name": "2025年8月20日收据",
          "source": "原件1份",
          "purpose": "2025.8.20收40,000元，累计110,000元，付款人刘九零、收款人黄茂姣，盖“欧派门业习水专卖店”章",
        },
        {
          "no": "证据5",
          "name": "丁戊祥（原告经营者）与刘维微信聊天记录",
          "source": "原始载体刘维手机（电子数据）",
          "purpose": "原告明知向承包方（黄茂姣）结算；刘维明示“尾款找黄茂姣”“定金由黄茂姣打给你”；原告“要得”未否认——真实交易相对方为承包方",
        },
        {
          "no": "证据6",
          "name": "《产品订购协议》NO.1040218",
          "source": "照片/复印件",
          "purpose": "性质为选样确认单据（非买卖合同）；客户名称按房屋权属人刘九零记载，刘维仅受托选样签字；定金2,000元由黄茂姣微信支付",
        },
        {
          "no": "证据7",
          "name": "《关于麒龙习水印象B8-1-21-4房屋装修问题整改的通知》及送达回执",
          "source": "照片+送达凭证",
          "purpose": "承包方2025.6.16整体承包、8项质量问题；刘九零与承包人之间存在尾款结算及整改费用争议；拒收",
        },
        {
          "no": "证据8",
          "name": "《情况说明》（习水县锦绣明天建材店出具，2026.8.19丁戊祥当场书写并手持拍照留存）",
          "source": "照片+原始载体（拍摄手机）",
          "purpose": "原告自认“黄茂姣带着客来我店里选货”“谁选的货：黄茂姣”“订金谁支付的：黄茂姣（微信支付）”——买受人即黄茂姣",
        },
        {
          "no": "证据9",
          "name": "《关于未提起（2026）黔0330民初6658号诉讼的说明》（丁戊祥2026.8.20亲笔签署）及现场照片2张",
          "source": "原件+照片",
          "purpose": "丁戊祥从未提起本案诉讼、未授权任何人以其名义起诉、起诉状署名非本人所签、认可《情况说明》、愿出庭作证并承担法律责任",
        },
        {
          "no": "证据10",
          "name": "原告身份证复印件、个体工商户营业执照",
          "source": "复印件",
          "purpose": "登记姓名“丁戊祥”（身份证号522132197804302816，户籍地二郎乡）；起诉状签名“丁茂祥”与登记姓名不符→冒签；户籍地≠经营地→未实际参与诉讼",
        },
        {
          "no": "证据11",
          "name": "律师费支付凭证（待取得）、丁戊祥关于《授权委托书》盖章背景的补充书面说明（待取得）、法官电话核实录音（2026年8月）及在场见证人证言（待取得）",
          "source": "凭证/录音/说明/证言（部分待取得）",
          "purpose": "①律师费支付主体待查实（丁戊祥未付，依《民诉法》第67条第2款申请法院依职权调查）②《授权委托书》系黄茂姣与律师共同携带上门让丁戊祥盖章取得，丁戊祥无起诉真实意思③委托合同签署主体待查实",
        }
      ],
    },
    {
      "schema": "case-state/v1",
      "caseId": "众志救援",
      "caseNo": "（行政争议·非诉咨询）",
      "title": "众志救援中心场地收回行政补偿案",
      "domain": "行政协议/行政补偿",
      "status": "非诉",
      "stage": {
        "current": 0,
        "code": "calibrated",
        "name": "DTC-CASE-001 校准生成·待人工回填",
        "enteredAt": "2026-09-14",
        "note": "状态字段取自飞轮索引；stage 具体进度待人工回填"
      },
      "gates": {
        "G0": {
          "name": "门禁G0",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G1": {
          "name": "门禁G1",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G2": {
          "name": "门禁G2",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G3": {
          "name": "门禁G3",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G4": {
          "name": "门禁G4",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G5": {
          "name": "门禁G5",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G6": {
          "name": "门禁G6",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G7": {
          "name": "门禁G7",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G8": {
          "name": "门禁G8",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        }
      },
      "calibration": {
        "ticket": "DTC-CASE-001",
        "generatedAt": "2026-09-14",
        "source": "案件-知识映射索引 + 案件笔记存在性",
        "verifiedFields": [
          "caseNo",
          "title",
          "domain",
          "status"
        ],
        "pendingFields": [
          "court",
          "judge",
          "client",
          "deadlines",
          "meta.agents",
          "timeline"
        ],
        "note": "本文件由校准脚本自动生成，仅含索引可证事实；court/judge/client/deadlines/agents 须人工从案件笔记与桌面真卷实地回填，禁止凭记忆完善。"
      },
      "meta": {
        "schema": "case-meta/v1",
        "agents": [
          {
            "stage": "校准占位",
            "role": "DTC-CASE-001",
            "agent": "待回填",
            "status": "todo",
            "note": "meta.agents 待人工按运维手册§3.2 补齐11条路由"
          }
        ]
      },
      "_folder": "众志救援场地使用收回案件",
      "_path": "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/众志救援场地使用收回案件/case-state.json"
    },
    {
      "schema": "case-state/v1",
      "caseId": "冒井",
      "caseNo": "（二审改判·遵义中院2023）",
      "title": "冒井渔业vs厚德渔业合同纠纷（退出补偿协议履行）",
      "domain": "商事合同/退出补偿",
      "status": "已结案",
      "stage": {
        "current": 0,
        "code": "calibrated",
        "name": "DTC-CASE-001 校准生成·待人工回填",
        "enteredAt": "2026-09-14",
        "note": "状态字段取自飞轮索引；stage 具体进度待人工回填"
      },
      "gates": {
        "G0": {
          "name": "门禁G0",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G1": {
          "name": "门禁G1",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G2": {
          "name": "门禁G2",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G3": {
          "name": "门禁G3",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G4": {
          "name": "门禁G4",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G5": {
          "name": "门禁G5",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G6": {
          "name": "门禁G6",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G7": {
          "name": "门禁G7",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G8": {
          "name": "门禁G8",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        }
      },
      "calibration": {
        "ticket": "DTC-CASE-001",
        "generatedAt": "2026-09-14",
        "source": "案件-知识映射索引 + 案件笔记存在性",
        "verifiedFields": [
          "caseNo",
          "title",
          "domain",
          "status"
        ],
        "pendingFields": [
          "court",
          "judge",
          "client",
          "deadlines",
          "meta.agents",
          "timeline"
        ],
        "note": "本文件由校准脚本自动生成，仅含索引可证事实；court/judge/client/deadlines/agents 须人工从案件笔记与桌面真卷实地回填，禁止凭记忆完善。"
      },
      "meta": {
        "schema": "case-meta/v1",
        "agents": [
          {
            "stage": "校准占位",
            "role": "DTC-CASE-001",
            "agent": "待回填",
            "status": "todo",
            "note": "meta.agents 待人工按运维手册§3.2 补齐11条路由"
          }
        ]
      },
      "_folder": "冒井渔业vs厚德渔业合同纠纷",
      "_path": "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/冒井渔业vs厚德渔业合同纠纷/case-state.json"
    },
    {
      "schema": "case-state/v1",
      "caseId": "审计约定",
      "caseNo": "（非诉审查）",
      "title": "厚德基金会审计业务约定书审查",
      "domain": "基金会审计业务合规",
      "status": "非诉",
      "stage": {
        "current": 0,
        "code": "calibrated",
        "name": "DTC-CASE-001 校准生成·待人工回填",
        "enteredAt": "2026-09-14",
        "note": "状态字段取自飞轮索引；stage 具体进度待人工回填"
      },
      "gates": {
        "G0": {
          "name": "门禁G0",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G1": {
          "name": "门禁G1",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G2": {
          "name": "门禁G2",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G3": {
          "name": "门禁G3",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G4": {
          "name": "门禁G4",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G5": {
          "name": "门禁G5",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G6": {
          "name": "门禁G6",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G7": {
          "name": "门禁G7",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G8": {
          "name": "门禁G8",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        }
      },
      "calibration": {
        "ticket": "DTC-CASE-001",
        "generatedAt": "2026-09-14",
        "source": "案件-知识映射索引 + 案件笔记存在性",
        "verifiedFields": [
          "caseNo",
          "title",
          "domain",
          "status"
        ],
        "pendingFields": [
          "court",
          "judge",
          "client",
          "deadlines",
          "meta.agents",
          "timeline"
        ],
        "note": "本文件由校准脚本自动生成，仅含索引可证事实；court/judge/client/deadlines/agents 须人工从案件笔记与桌面真卷实地回填，禁止凭记忆完善。"
      },
      "meta": {
        "schema": "case-meta/v1",
        "agents": [
          {
            "stage": "校准占位",
            "role": "DTC-CASE-001",
            "agent": "待回填",
            "status": "todo",
            "note": "meta.agents 待人工按运维手册§3.2 补齐11条路由"
          }
        ]
      },
      "_folder": "厚德基金会审计业务约定书审查",
      "_path": "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/厚德基金会审计业务约定书审查/case-state.json"
    },
    {
      "schema": "case-state/v1",
      "caseId": "百益上诉",
      "caseNo": "（二审/另案进行中）",
      "title": "厚德基金会诉百益服务中心合同纠纷上诉案",
      "domain": "基金会服务协议",
      "status": "进行中",
      "stage": {
        "current": 0,
        "code": "calibrated",
        "name": "DTC-CASE-001 校准生成·待人工回填",
        "enteredAt": "2026-09-14",
        "note": "状态字段取自飞轮索引；stage 具体进度待人工回填"
      },
      "gates": {
        "G0": {
          "name": "门禁G0",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G1": {
          "name": "门禁G1",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G2": {
          "name": "门禁G2",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G3": {
          "name": "门禁G3",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G4": {
          "name": "门禁G4",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G5": {
          "name": "门禁G5",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G6": {
          "name": "门禁G6",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G7": {
          "name": "门禁G7",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G8": {
          "name": "门禁G8",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        }
      },
      "calibration": {
        "ticket": "DTC-CASE-001",
        "generatedAt": "2026-09-14",
        "source": "案件-知识映射索引 + 案件笔记存在性",
        "verifiedFields": [
          "caseNo",
          "title",
          "domain",
          "status"
        ],
        "pendingFields": [
          "court",
          "judge",
          "client",
          "deadlines",
          "meta.agents",
          "timeline"
        ],
        "note": "本文件由校准脚本自动生成，仅含索引可证事实；court/judge/client/deadlines/agents 须人工从案件笔记与桌面真卷实地回填，禁止凭记忆完善。"
      },
      "meta": {
        "schema": "case-meta/v1",
        "agents": [
          {
            "stage": "校准占位",
            "role": "DTC-CASE-001",
            "agent": "待回填",
            "status": "todo",
            "note": "meta.agents 待人工按运维手册§3.2 补齐11条路由"
          }
        ]
      },
      "_folder": "厚德基金会诉百益服务中心合同纠纷上诉案",
      "_path": "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/厚德基金会诉百益服务中心合同纠纷上诉案/case-state.json"
    },
    {
      "schema": "case-state/v1",
      "caseId": "道真百益",
      "caseNo": "(2025)黔0325民初230号之一",
      "title": "厚德基金会诉道真百益合同纠纷案（公益理财服务协议履行/款项返还）",
      "court": "道真仡佬族苗族自治县人民法院（一审）；二审上诉阶段",
      "partyRole": "上诉人（一审原告）",
      "opposingParty": [
        "道真仡佬族苗族自治县百益社会工作服务中心",
        "李丽",
        "李佳豪"
      ],
      "domain": "合作合同/基金会服务协议",
      "status": "进行中（二审上诉阶段）",
      "client": [
        "贵州省厚德公益基金会"
      ],
      "stage": {
        "current": 0,
        "code": "calibrated",
        "name": "DTC-CASE-001 补建·待人工回填",
        "enteredAt": "2026-09-14",
        "note": "独立夹原无 state；要素取自本夹案件笔记原文(案号/法院/身份/对方)，其余待人工回填"
      },
      "gates": {
        "G0": {
          "name": "门禁G0",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        },
        "G1": {
          "name": "门禁G1",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        },
        "G2": {
          "name": "门禁G2",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        },
        "G3": {
          "name": "门禁G3",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        },
        "G4": {
          "name": "门禁G4",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        },
        "G5": {
          "name": "门禁G5",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        },
        "G6": {
          "name": "门禁G6",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        },
        "G7": {
          "name": "门禁G7",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        },
        "G8": {
          "name": "门禁G8",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        }
      },
      "calibration": {
        "ticket": "DTC-CASE-001",
        "generatedAt": "2026-09-14",
        "source": "本夹案件笔记原文(厚德基金会诉道真百益合同纠纷案-案件笔记.md)",
        "verifiedFields": [
          "caseNo",
          "title",
          "court",
          "partyRole",
          "domain",
          "status",
          "client",
          "opposingParty"
        ],
        "pendingFields": [
          "judge",
          "deadlines",
          "meta.agents",
          "timeline",
          "nextActions",
          "risks"
        ],
        "note": "要素取自笔记原文；judge/deadlines/agents/timeline 须人工从笔记与桌面真卷实地回填，禁止凭记忆完善。"
      },
      "meta": {
        "schema": "case-meta/v1",
        "agents": [
          {
            "stage": "校准占位",
            "role": "DTC-CASE-001",
            "agent": "待回填",
            "status": "todo",
            "note": "meta.agents 待人工按运维手册§3.2 补齐11条路由"
          }
        ]
      },
      "_folder": "厚德基金会诉道真百益合同纠纷案",
      "_path": "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/厚德基金会诉道真百益合同纠纷案/case-state.json"
    },
    {
      "schema": "case-state/v1",
      "caseId": "凤仪村",
      "caseNo": "（无案号·预测阶段尚未起诉）",
      "title": "凤仪村与赤水月亮湖合作合同纠纷案",
      "partyRole": "代理被告/被上诉人（凤仪村委）",
      "opposingParty": [
        "赤水月亮湖"
      ],
      "domain": "合作合同纠纷",
      "status": "准备/预测阶段（尚未起诉）",
      "client": [
        "凤仪村委"
      ],
      "stage": {
        "current": 0,
        "code": "calibrated",
        "name": "DTC-CASE-001 收窄·待人工回填",
        "enteredAt": "2026-09-14",
        "note": "由合作合同夹双案描述收窄为凤仪村案（道真百益已独立成案）；要素取自凤仪村笔记原文"
      },
      "gates": {
        "G0": {
          "name": "门禁G0",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        },
        "G1": {
          "name": "门禁G1",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        },
        "G2": {
          "name": "门禁G2",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        },
        "G3": {
          "name": "门禁G3",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        },
        "G4": {
          "name": "门禁G4",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        },
        "G5": {
          "name": "门禁G5",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        },
        "G6": {
          "name": "门禁G6",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        },
        "G7": {
          "name": "门禁G7",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        },
        "G8": {
          "name": "门禁G8",
          "status": "todo",
          "note": "DTC-CASE-001 补建/收窄·待人工从案件笔记实地回填"
        }
      },
      "calibration": {
        "ticket": "DTC-CASE-001",
        "generatedAt": "2026-09-14",
        "source": "本夹凤仪村与赤水月亮湖合作合同纠纷案-案件笔记.md",
        "verifiedFields": [
          "caseNo",
          "title",
          "partyRole",
          "domain",
          "status",
          "client",
          "opposingParty"
        ],
        "pendingFields": [
          "court",
          "judge",
          "deadlines",
          "meta.agents",
          "timeline"
        ],
        "note": "要素取自笔记原文；court/judge/deadlines/agents/timeline 须人工回填。"
      },
      "meta": {
        "schema": "case-meta/v1",
        "agents": [
          {
            "stage": "校准占位",
            "role": "DTC-CASE-001",
            "agent": "待回填",
            "status": "todo",
            "note": "meta.agents 待人工按运维手册§3.2 补齐11条路由"
          }
        ]
      },
      "_folder": "合作合同",
      "_path": "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/合作合同/case-state.json"
    },
    {
      "schema": "case-state/v1",
      "caseId": "娄山华庭",
      "caseNo": "（非诉审查）",
      "title": "娄山华庭房屋租赁合同审查",
      "domain": "房屋租赁合同",
      "status": "非诉",
      "stage": {
        "current": 0,
        "code": "calibrated",
        "name": "DTC-CASE-001 校准生成·待人工回填",
        "enteredAt": "2026-09-14",
        "note": "状态字段取自飞轮索引；stage 具体进度待人工回填"
      },
      "gates": {
        "G0": {
          "name": "门禁G0",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G1": {
          "name": "门禁G1",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G2": {
          "name": "门禁G2",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G3": {
          "name": "门禁G3",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G4": {
          "name": "门禁G4",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G5": {
          "name": "门禁G5",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G6": {
          "name": "门禁G6",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G7": {
          "name": "门禁G7",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G8": {
          "name": "门禁G8",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        }
      },
      "calibration": {
        "ticket": "DTC-CASE-001",
        "generatedAt": "2026-09-14",
        "source": "案件-知识映射索引 + 案件笔记存在性",
        "verifiedFields": [
          "caseNo",
          "title",
          "domain",
          "status"
        ],
        "pendingFields": [
          "court",
          "judge",
          "client",
          "deadlines",
          "meta.agents",
          "timeline"
        ],
        "note": "本文件由校准脚本自动生成，仅含索引可证事实；court/judge/client/deadlines/agents 须人工从案件笔记与桌面真卷实地回填，禁止凭记忆完善。"
      },
      "meta": {
        "schema": "case-meta/v1",
        "agents": [
          {
            "stage": "校准占位",
            "role": "DTC-CASE-001",
            "agent": "待回填",
            "status": "todo",
            "note": "meta.agents 待人工按运维手册§3.2 补齐11条路由"
          }
        ]
      },
      "_folder": "娄山华庭房屋租赁合同",
      "_path": "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/娄山华庭房屋租赁合同/case-state.json"
    },
    {
      "schema": "case-state/v1",
      "caseId": "1497",
      "caseNo": "(2018)黔0330民初1497号",
      "title": "王德明担保合同签名伪造案",
      "domain": "担保合同/执行异议",
      "status": "进行中",
      "stage": {
        "current": 0,
        "code": "calibrated",
        "name": "DTC-CASE-001 校准生成·待人工回填",
        "enteredAt": "2026-09-14",
        "note": "状态字段取自飞轮索引；stage 具体进度待人工回填"
      },
      "gates": {
        "G0": {
          "name": "门禁G0",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G1": {
          "name": "门禁G1",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G2": {
          "name": "门禁G2",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G3": {
          "name": "门禁G3",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G4": {
          "name": "门禁G4",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G5": {
          "name": "门禁G5",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G6": {
          "name": "门禁G6",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G7": {
          "name": "门禁G7",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G8": {
          "name": "门禁G8",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        }
      },
      "calibration": {
        "ticket": "DTC-CASE-001",
        "generatedAt": "2026-09-14",
        "source": "案件-知识映射索引 + 案件笔记存在性",
        "verifiedFields": [
          "caseNo",
          "title",
          "domain",
          "status"
        ],
        "pendingFields": [
          "court",
          "judge",
          "client",
          "deadlines",
          "meta.agents",
          "timeline"
        ],
        "note": "本文件由校准脚本自动生成，仅含索引可证事实；court/judge/client/deadlines/agents 须人工从案件笔记与桌面真卷实地回填，禁止凭记忆完善。"
      },
      "meta": {
        "schema": "case-meta/v1",
        "agents": [
          {
            "stage": "校准占位",
            "role": "DTC-CASE-001",
            "agent": "待回填",
            "status": "todo",
            "note": "meta.agents 待人工按运维手册§3.2 补齐11条路由"
          }
        ]
      },
      "_folder": "王德明担保合同纠纷案",
      "_path": "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/王德明担保合同纠纷案/case-state.json"
    },
    {
      "schema": "case-state/v1",
      "caseId": "罗江辉",
      "caseNo": "(2026)黔0103民初□□□□号（案号待核实）",
      "title": "罗江辉教育培训合同纠纷（闭店退费）",
      "domain": "教育培训合同/预付式消费",
      "status": "已结案",
      "stage": {
        "current": 0,
        "code": "calibrated",
        "name": "DTC-CASE-001 校准生成·待人工回填",
        "enteredAt": "2026-09-14",
        "note": "状态字段取自飞轮索引；stage 具体进度待人工回填"
      },
      "gates": {
        "G0": {
          "name": "门禁G0",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G1": {
          "name": "门禁G1",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G2": {
          "name": "门禁G2",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G3": {
          "name": "门禁G3",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G4": {
          "name": "门禁G4",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G5": {
          "name": "门禁G5",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G6": {
          "name": "门禁G6",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G7": {
          "name": "门禁G7",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G8": {
          "name": "门禁G8",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        }
      },
      "calibration": {
        "ticket": "DTC-CASE-001",
        "generatedAt": "2026-09-14",
        "source": "案件-知识映射索引 + 案件笔记存在性",
        "verifiedFields": [
          "caseNo",
          "title",
          "domain",
          "status"
        ],
        "pendingFields": [
          "court",
          "judge",
          "client",
          "deadlines",
          "meta.agents",
          "timeline"
        ],
        "note": "本文件由校准脚本自动生成，仅含索引可证事实；court/judge/client/deadlines/agents 须人工从案件笔记与桌面真卷实地回填，禁止凭记忆完善。"
      },
      "meta": {
        "schema": "case-meta/v1",
        "agents": [
          {
            "stage": "校准占位",
            "role": "DTC-CASE-001",
            "agent": "待回填",
            "status": "todo",
            "note": "meta.agents 待人工按运维手册§3.2 补齐11条路由"
          }
        ]
      },
      "_folder": "罗江辉教育合同纠纷案",
      "_path": "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/罗江辉教育合同纠纷案/case-state.json"
    },
    {
      "schema": "case-state/v1",
      "caseId": "陈长卫",
      "caseNo": "（二审改判·黔东南中院2022）",
      "title": "陈长卫劳务致害案（高压电击伤）",
      "domain": "提供劳务受害/建设工程",
      "status": "已结案",
      "stage": {
        "current": 0,
        "code": "calibrated",
        "name": "DTC-CASE-001 校准生成·待人工回填",
        "enteredAt": "2026-09-14",
        "note": "状态字段取自飞轮索引；stage 具体进度待人工回填"
      },
      "gates": {
        "G0": {
          "name": "门禁G0",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G1": {
          "name": "门禁G1",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G2": {
          "name": "门禁G2",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G3": {
          "name": "门禁G3",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G4": {
          "name": "门禁G4",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G5": {
          "name": "门禁G5",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G6": {
          "name": "门禁G6",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G7": {
          "name": "门禁G7",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G8": {
          "name": "门禁G8",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        }
      },
      "calibration": {
        "ticket": "DTC-CASE-001",
        "generatedAt": "2026-09-14",
        "source": "案件-知识映射索引 + 案件笔记存在性",
        "verifiedFields": [
          "caseNo",
          "title",
          "domain",
          "status"
        ],
        "pendingFields": [
          "court",
          "judge",
          "client",
          "deadlines",
          "meta.agents",
          "timeline"
        ],
        "note": "本文件由校准脚本自动生成，仅含索引可证事实；court/judge/client/deadlines/agents 须人工从案件笔记与桌面真卷实地回填，禁止凭记忆完善。"
      },
      "meta": {
        "schema": "case-meta/v1",
        "agents": [
          {
            "stage": "校准占位",
            "role": "DTC-CASE-001",
            "agent": "待回填",
            "status": "todo",
            "note": "meta.agents 待人工按运维手册§3.2 补齐11条路由"
          }
        ]
      },
      "_folder": "陈长卫劳务致害案",
      "_path": "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/陈长卫劳务致害案/case-state.json"
    },
    {
      "schema": "case-state/v1",
      "caseId": "6660",
      "caseNo": "(2026)黔0330民初6660号",
      "title": "焦联鹏（习水县焦鹏雅菲软装经营部）诉刘九零、刘维窗帘买卖合同纠纷案",
      "court": "贵州省习水县人民法院",
      "judge": "龙雅清",
      "procedure": "一审",
      "partyRole": "被告方",
      "counselRole": "代理",
      "client": [
        "刘九零",
        "刘维"
      ],
      "domain": "建设工程/买卖合同",
      "status": "撤诉窗口期",
      "stage": {
        "current": 6,
        "code": "procedure",
        "name": "⑥程序执行",
        "enteredAt": "2026-09-01",
        "note": "原告开庭当日申请撤诉，准许裁定未送达；窗口期处置为主战场"
      },
      "gates": {
        "G0": {
          "name": "收案门禁",
          "status": "pass",
          "note": "已建档，案件笔记入 LawKB"
        },
        "G1": {
          "name": "检索门禁",
          "status": "pass",
          "note": "2026-07-14 法律检索报告、08 号法律检索报告"
        },
        "G2": {
          "name": "文书门禁",
          "status": "pass",
          "note": "01-06 答辩/举证/质证/发问/代理词/庭审预案已备"
        },
        "G3": {
          "name": "庭审门禁",
          "status": "waived",
          "note": "9/1 开庭当日原告申请撤诉，未正式开庭"
        },
        "G4": {
          "name": "客户门禁",
          "status": "pass",
          "note": "意见（二）[含⑦⑧⑨]已发当事人核验确认，待确认后周一（2026-09-07）递交"
        },
        "G5": {
          "name": "程序门禁",
          "status": "active",
          "note": "撤诉裁定送达前窗口期；自认钉死+录音附卷（含8.19说明真卷证据9、8.24被告方通话录音说明、法院官方8.24电话询问录音笔录已调取归卷）已于裁定送达前闭环；当前仅静候法院撤诉裁定送达，送达即窗口关闭"
        },
        "G6": {
          "name": "风控门禁",
          "status": "warn",
          "note": "撤诉法条曾凭记忆写错（误用145条），已实地核验为148条第1款"
        },
        "G7": {
          "name": "结案回流",
          "status": "todo",
          "note": "撤诉裁定送达、再诉封堵完成后启动"
        }
      },
      "deadlines": [
        {
          "id": "d1",
          "name": "撤诉裁定送达前窗口期（自认钉死+录音附卷已闭环，静候送达）",
          "due": null,
          "type": "触发型",
          "level": "P2",
          "state": "armed",
          "basis": "准许撤诉裁定不可上诉、不可复议，唯一救济为诉讼费院长复核",
          "note": "自认钉死（8.19《情况说明》真卷证据9 / 8.24被告方通话录音说明 / 法院官方8.24电话询问录音笔录已调取归卷）已于裁定送达前闭环；窗口期仍开放，送达即关闭不可补救，故仍须保持可见"
        },
        {
          "id": "d2",
          "name": "对撤诉意见（二）[含⑦调查取证、⑧录音刻录附卷、⑨焦联鹏到庭询问] 经当事人核验确认，已于 2026-09-07 前后递交法院",
          "due": "2026-09-07",
          "type": "计划",
          "level": "P0",
          "state": "done",
          "basis": "⑦⑧⑨ 已并入⑪意见（二），不另立申请；2026-09-06 老强确认口径",
          "note": "意见（二）已发当事人核验确认并递交法院（老强 2026-09-16 核实：实际已递交，案卷原 armed 为状态陈旧未更新）；原「未递交前不得视为已提交」约束现已解除"
        },
        {
          "id": "d3",
          "name": "封堵原样再诉（民诉法解释第214条第1款）",
          "due": null,
          "type": "持续",
          "level": "P1",
          "state": "pending",
          "basis": "撤诉后可再诉，须以自认钉死+附卷阻断",
          "note": "条文序号交付前须经 LTI 核验"
        },
        {
          "id": "d4",
          "name": "黄茂姣资金流水调取（另案索赔前置）",
          "due": null,
          "type": "内部",
          "level": "P2",
          "state": "pending",
          "basis": "与 6658 案联动",
          "note": "属另案索赔前置条件，非本案当期必办"
        }
      ],
      "timeline": [
        {
          "date": "2025-06-01",
          "event": "刘九零与欧派门业签装修合同（整装178,000元含窗帘5,000元）"
        },
        {
          "date": "2025-09-25",
          "event": "黄茂姣确定雅菲软装、谈价、下单"
        },
        {
          "date": "2025-11-20",
          "event": "承包方整改通知（质量问题）"
        },
        {
          "date": "2025-11-25",
          "event": "原告制订货单，刘维仅签收"
        },
        {
          "date": "2026-01-22",
          "event": "原告催款，被告指向黄茂姣"
        },
        {
          "date": "2026-07-14",
          "event": "法律检索报告完成（防御型）"
        },
        {
          "date": "2026-08-12",
          "event": "庭审准备报告（追加第三人策略修订版）"
        },
        {
          "date": "2026-08-24",
          "event": "法官电话核实（14-附2 说明）"
        },
        {
          "date": "2026-09-01",
          "event": "原告开庭当日申请撤诉，未正式开庭；13 号撤诉后处置建议报告出具",
          "key": true
        },
        {
          "date": "2026-09-03",
          "event": "9/4 递交底稿就绪（⑦⑪⑧⑨ 四份申请）"
        },
        {
          "date": "2026-09-06",
          "event": "意见（二）发当事人核验确认；⑦调查取证、⑧录音刻录附卷、⑨焦联鹏到庭询问确定并入意见（二），不另立申请；待周一（2026-09-07）递交",
          "key": true
        }
      ],
      "nextActions": [
        "意见（二）[含⑦⑧⑨]已发当事人核验确认，待周一（2026-09-07）递交法院；递交后持续跟踪裁定送达",
        "裁定送达前完成自认钉死（原告亲笔《情况说明》+ 法官电话核实录音附卷）",
        "主张《民诉法解释》第238条第1款：当事人有违法行为需依法处理的，法院可以不准许撤诉",
        "持续跟踪裁定送达状态，送达后立即评估再诉风险"
      ],
      "risks": [
        "撤诉裁定送达即生效且不可上诉不可复议，窗口期一旦关闭再无补救空间",
        "撤诉法条曾凭记忆写错（误用民诉法145条第2款），正确为148条第1款——同类法条引用须实地核验",
        "原告撤诉后可依《民诉法解释》第214条第1款原样再诉，自认钉死不到位则前功尽弃",
        "金额混乱（'295二元'笔误与微信'5000'矛盾），若再诉须咬死原告举证责任"
      ],
      "stance": {
        "blue": 65,
        "trend": "up",
        "reason": "原告开庭当日撤诉，被告方未进入实体对抗即解除主要风险；剩余敞口为再诉封堵，裁定送达前完成自认钉死即可大幅压缩"
      },
      "meta": {
        "schema": "case-meta/v1",
        "agents": [
          {
            "stage": "①接案建档",
            "gate": "G0",
            "role": "建档/决策留痕",
            "agent": "CLM case-state.json + decision-capture",
            "status": "已接入",
            "artifacts": [
              "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/雅菲软装窗帘买卖合同纠纷案/焦联鹏诉刘九零窗帘买卖合同纠纷案-案件笔记.md（案情笔录/案件备忘录）"
            ]
          },
          {
            "stage": "②检索研究",
            "gate": "G1",
            "role": "法律检索",
            "agent": "元典MCP(yuandian-mcp) + 北大法宝MCP(pkulaw)",
            "status": "已接入",
            "note": "二源互补",
            "artifacts": [
              "/Users/chenyouqiang/Desktop/小强律师办案系统/庭审10件套_雅菲软装窗帘案（6660）/08_法律检索报告_雅菲软装窗帘案.docx"
            ]
          },
          {
            "stage": "②检索研究",
            "gate": "G1",
            "role": "类案检索",
            "agent": "元典case vector + 北大法宝MCP + 法随案例库MCP",
            "status": "待补",
            "note": "三源互补；6660 暂未单独成件，或并入法律检索报告",
            "artifacts": []
          },
          {
            "stage": "②检索研究",
            "gate": "G1",
            "role": "检索归档",
            "agent": "ima 知识库",
            "status": "已接入",
            "artifacts": [
              "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/雅菲软装窗帘买卖合同纠纷案/焦联鹏诉刘九零窗帘买卖合同纠纷案-案件笔记.md"
            ]
          },
          {
            "stage": "③法律文书起草",
            "gate": "G2",
            "role": "法律文书（庭审六件套）",
            "agent": "法律文书docx交付流水线 + LTI文本监控器",
            "status": "已接入",
            "artifacts": [
              "/Users/chenyouqiang/Desktop/小强律师办案系统/庭审10件套_雅菲软装窗帘案（6660）/01_民事答辩状_雅菲软装窗帘案_最新版.docx",
              "/Users/chenyouqiang/Desktop/小强律师办案系统/庭审10件套_雅菲软装窗帘案（6660）/02_举证清单_雅菲软装窗帘案_最新版.docx",
              "/Users/chenyouqiang/Desktop/小强律师办案系统/庭审10件套_雅菲软装窗帘案（6660）/03_质证意见_雅菲软装窗帘案_最新版.docx",
              "/Users/chenyouqiang/Desktop/小强律师办案系统/庭审10件套_雅菲软装窗帘案（6660）/04_庭审发问提纲_雅菲软装窗帘案.docx",
              "/Users/chenyouqiang/Desktop/小强律师办案系统/庭审10件套_雅菲软装窗帘案（6660）/05_代理词_雅菲软装窗帘案.docx",
              "/Users/chenyouqiang/Desktop/小强律师办案系统/庭审10件套_雅菲软装窗帘案（6660）/06_庭审预案_法官裁判预判备忘_雅菲软装窗帘案.docx"
            ]
          },
          {
            "stage": "④庭审查庭",
            "gate": "G3",
            "role": "模拟法庭/审判要件",
            "agent": "mock-trial-control-center + 审判要件卡拆卡流水线 + 本会话专家",
            "status": "已接入"
          },
          {
            "stage": "⑤客户协作",
            "gate": "G4",
            "role": "汇报/推送",
            "agent": "案件工作汇报 + 调解和解 + CLM send_client_brief + agent-mail",
            "status": "已接入（邮件通道待配webhook）"
          },
          {
            "stage": "⑥程序执行",
            "gate": "G5",
            "role": "程序推进",
            "agent": "案件全生命周期·程序推进包",
            "status": "已建"
          },
          {
            "stage": "⑦风控归档",
            "gate": "G6/G8",
            "role": "合规风控",
            "agent": "LTI + lawkb-legal-consistency-audit + G8非诉专项",
            "status": "已接入"
          },
          {
            "stage": "结案回流",
            "gate": "G7",
            "role": "经验沉淀",
            "agent": "mind-distill + LawKB 知识飞轮",
            "status": "已接入"
          },
          {
            "stage": "运维",
            "gate": "-",
            "role": "入口/监测",
            "agent": "xiaoqiang-cockpit-hub + workbuddy-credit-monitor",
            "status": "已接入"
          }
        ]
      },
      "mockTrial": {
        "prepReportReady": true,
        "prepReportPath": null,
        "status": "未启动",
        "lastTrialAt": null,
        "trialBriefPath": null
      },
      "publicView": {
        "stageText": "原告已申请撤诉，等待法院裁定送达",
        "done": [
          "已完成答辩状、举证清单、质证意见等应诉材料准备",
          "2026-09-01 已到庭，对方当日申请撤诉",
          "已出具撤诉后处置建议报告并拟递交相关申请"
        ],
        "next": "自认钉死（含8.19《情况说明》真卷证据9、8.24被告方通话录音说明、法院官方8.24电话询问录音笔录已调取归卷）已在裁定送达前闭环；当前仅静候法院撤诉裁定送达，送达后窗口关闭不可补救",
        "clientTodo": [
          "如收到法院任何裁定书或传票，请第一时间拍照告知我们",
          "保留与本案相关的全部微信记录、收据、合同原件，不要删除"
        ],
        "contact": "陈友强"
      },
      "caseStateDetail": {
        "schema": "case-detail/v1",
        "factSummary": "原告习水县焦鹏雅菲软装经营部（个体工商户，经营者焦联鹏）以2025-11-25《雅菲软装订货单》（窗帘等软装产品）为由，诉请被告刘九零、刘维（刘九零之兄，曾用名刘军）支付货款。起诉状OCR识别金额约2,952元，存疑，以法院核定为准。被告抗辩：真交易相对方为房屋装修承包方欧派门业习水专卖店（负责人黄茂娇），被告仅系受承包方指示的收货验收人，与原告无直接买卖合同关系。",
        "disputeFocus": [
          "买卖合同关系是否成立：无书面合同时，被告刘维在订货单上的签收行为性质（数量验收 vs 买受人确认）",
          "合同相对性可否突破：隐名代理（民法典925/926条）、表见代理（172条）、债务加入（552条）是否成立",
          "备位抗辩边界：先履行抗辩权（526条）、法定抵销（568条）以有效买卖债务为前提，须避免自认债务"
        ],
        "legalBasis": [
          {
            "law": "民法典第465条",
            "point": "合同相对性——被告方防御第一道防线根基：无证据证明与原告达成买卖合意，原告只能向真相对方主张"
          },
          {
            "law": "买卖合同纠纷解释第1条",
            "point": "无书面合同买卖关系认定标准：送货单/收货单仅为间接证据，须结合交易方式、交易习惯及其他证据综合认定（本案胜负手规则）"
          },
          {
            "law": "民法典第925/926条",
            "point": "隐名代理——双刃剑：若原告交易时明知相对方为欧派、被告仅收货人，则合同直接约束欧派（有利）；若原告有理由相信被告为买受人则不利"
          },
          {
            "law": "民法典第526条",
            "point": "先履行抗辩权——备位抗辩，以被告对原告负有有效买卖债务为前提"
          },
          {
            "law": "民法典第568条",
            "point": "法定抵销——备位抗辩，互负同种类金钱债务时适用"
          },
          {
            "law": "民诉法解释第90条",
            "point": "举证责任分配：原告须证明其主张的买卖关系事实，证据不足则承担不利后果"
          }
        ],

        "strategy": {
          "blue": "第一道防线咬死合同相对性：原告与欧派门业成立买卖、被告仅收货验收人，引用买卖合同解释第1条+有利类案（宁波北仑'签字收货房主'案）。严防在载明欠款金额的单据上签名被认定为共同买受人（类案4/6/7风险警示）。备位主张装修质量瑕疵抗辩+法定抵销，但避免任何自认债务表述。",
          "red": "原告若证明被告实际参与磋商、选货、结算或付款，或在含金额单据签名，则被告可能被认定为买受人（类案4张签名确认欠款/类案6方某甲签字结算付款/类案7本人签字选货）。金额混乱（'295二元'笔误 vs 微信'5000'矛盾）须由原告举证，被告咬死举证责任。"
        },
        "relatedCases": [
          {
            "case": "(2026)黔0330民初6658号 丁戊祥诉刘九零吊顶买卖合同纠纷案",
            "relation": "平行案件，同涉黄茂姣为涉嫌实际买受人；6660案撤诉后须联动调取黄茂姣资金流水（d4内部前置），封堵原样再诉"
          },
          {
            "case": "宁波北仑'签字收货的房主'案（2014）",
            "relation": "有利类案：签收=收货验收非买受人，二审维持，事实结构高度一致"
          },
          {
            "case": "江西新干(2026)瓷砖买卖案（类案4）",
            "relation": "风险警示：在载明欠款单据签名=共同买受人，本案须严防"
          }
        ],
        "riskLevel": "中风险",
        "windowNote": "撤诉窗口期：原告2026-09-01开庭当日申请撤诉，准许裁定尚未送达。裁定送达即生效且不可上诉、不可复议，唯一救济为诉讼费院长复核。所有动作（自认钉死——原告亲笔《情况说明》+法官电话核实录音附卷）须在送达前完成。撤诉后可依民诉法解释第214条第1款原样再诉，须以自认钉死+附卷阻断。"
      },
      "updatedAt": "2026-09-16",
      "source": "桌面真卷「庭审10件套_雅菲软装窗帘案（6660）」+ LawKB 案件笔记（2026-09-04 蒸馏版）",
      "_folder": "雅菲软装窗帘买卖合同纠纷案",
      "_path": "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/雅菲软装窗帘买卖合同纠纷案/case-state.json",
      "evidence": [
        {
          "no": "1",
          "name": "《装修工程施工合同》（刘九零 与 欧派门业有限公司习水专卖店 / 黄茂娇）",
          "source": "被告持有",
          "purpose": "涉案房屋系包工包料整体发包给欧派门业，窗帘等软装属装修承揽范围；被告与原告之间不存在窗帘买卖关系。与灯具案系同一合同，可相互印证；亦为申请追加黄茂姣、习水县欧派木门杉王店为第三人之事实依据",
        },
        {
          "no": "2",
          "name": "支付欧派装修款收款收据 3 张",
          "source": "被告持有（3张）",
          "purpose": "①2025.6.25付首期款30,000元；②2025.8.4付40,000元（合计收到70,000元）；③2025.8.20付40,000元（合计收到110,000元）。收款人均为黄茂姣并加盖“欧派门业习水专卖店”印章。证明被告已向装修承包方履行付款义务，窗帘款含在整装总价中，原告不应再向被告主张",
        },
        {
          "no": "3",
          "name": "黄茂姣与被告微信聊天记录（原始载体：刘维手机；对方“梵哲门窗黄茂姣 18984285819”）",
          "source": "被告持有（手机原始载体）",
          "purpose": "证明窗帘的磋商、定价、下单均由装修承包方黄茂姣作出。关键内容：“你喜欢那里定都可以，你那里定和我说就可以”；“窗帘谈好5000是不？那我喊他下单开始做了”，被告回复“对”",
        },
        {
          "no": "4",
          "name": "《整改通知》及送达记录",
          "source": "被告持有",
          "purpose": "装修承包方施工存在质量瑕疵且经催告拒不整改，为备位抗辩（先履行抗辩权、法定抵销）之事实基础。与灯具案整改事项同源",
        },
        {
          "no": "5",
          "name": "欧派负责人支付定金/预付款的线索材料（银行或微信转账记录等）",
          "source": "申请法院调取或原告自认",
          "purpose": "涉案窗帘定金/预付款由装修承包方或其负责人支付，印证真实交易相对方为欧派而非被告",
        },
        {
          "no": "6",
          "name": "《雅菲软装订货单》原件（2025.11.25）",
          "source": "原告持有（申请法院调取/当庭质证）",
          "purpose": "核查：①客户栏署名是谁；②刘维/刘九零签名处是否注明“收货人/验收人”；③是否载明欠款金额。签名性质（数量验收vs欠款确认）直接决定本案认定走向，须重点质证",
        },
        {
          "no": "7",
          "name": "被告与“A雅菲软装”微信聊天记录（原始载体：刘维手机）",
          "source": "被告持有（手机原始载体）",
          "purpose": "2026.1.22原告工作人员催款“哥 这边还有款 没结”，被告回复“你们只能问黄茂姣要”，原告回复“这边说问你按”。证明原告明知应向黄茂姣主张货款",
        },
        {
          "no": "8",
          "name": "《装修项目报价单》（黄茂娇.xlsx，电子版+打印件）",
          "source": "被告持有（1份）",
          "purpose": "整装优惠总价178,000元。其中“窗帘”项目5,000元（品牌：曼诗非＋雅菲＋依世兰亭随选；工艺：客厅双层＋卧室单层）。直接证明窗帘属装修承揽范围、价款已含于整装总价。与灯具案报价单同源",
        },
        {
          "no": "9",
          "name": "《情况说明》原件（2026.8.19原告焦联鹏亲笔签署）+签署照片+被告保存事实",
          "source": "被告持有（刘维保存原件+照片原始载体）",
          "purpose": "【核心增量】原告自认：黄茂姣选货、定金3,000元（微信）由黄付、尾款栏亲笔填“黄茂姣已付”→涉案窗帘货款已由真实买受人黄茂姣结清；且原告亲笔签署并拍照、主动交被告刘维保存，证明其明知",
        },
        {
          "no": "10",
          "name": "法官电话核实记录/录音（2026.8.24，焦联鹏自认“黄茂姣代付清货款”）",
          "source": "法院卷宗/录音在卷（申请调取、复制）",
          "purpose": "【核心增量】诉讼中自认：货款已付清系免证事实，原告不得作出相反主张（证据规定§3、民诉法解释§92）；与证据9相互印证",
        },
        {
          "no": "11",
          "name": "《授权委托书》复印件（立案卷宗，仅盖公章、无焦联鹏本人签字）",
          "source": "法院立案卷宗（已查阅，1份）",
          "purpose": "【核心增量】委托手续未经经营者本人确认——起诉及委托真实性存疑，疑由黄茂姣借名操盘；申请核实公章真实性、通知焦联鹏到庭核实",
        }
      ],
    },
    {
      "schema": "case-state/v1",
      "caseId": "韩杰",
      "caseNo": "（刑事申诉·再审辩护）",
      "title": "韩杰医生医疗事故罪申诉/再审辩护",
      "domain": "医疗事故罪/刑事",
      "status": "进行中",
      "stage": {
        "current": 0,
        "code": "calibrated",
        "name": "DTC-CASE-001 校准生成·待人工回填",
        "enteredAt": "2026-09-14",
        "note": "状态字段取自飞轮索引；stage 具体进度待人工回填"
      },
      "gates": {
        "G0": {
          "name": "门禁G0",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G1": {
          "name": "门禁G1",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G2": {
          "name": "门禁G2",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G3": {
          "name": "门禁G3",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G4": {
          "name": "门禁G4",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G5": {
          "name": "门禁G5",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G6": {
          "name": "门禁G6",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G7": {
          "name": "门禁G7",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        },
        "G8": {
          "name": "门禁G8",
          "status": "todo",
          "note": "DTC-CASE-001 校准自动生成·待人工从案件笔记/桌面真卷实地回填核实"
        }
      },
      "calibration": {
        "ticket": "DTC-CASE-001",
        "generatedAt": "2026-09-14",
        "source": "案件-知识映射索引 + 案件笔记存在性",
        "verifiedFields": [
          "caseNo",
          "title",
          "domain",
          "status"
        ],
        "pendingFields": [
          "court",
          "judge",
          "client",
          "deadlines",
          "meta.agents",
          "timeline"
        ],
        "note": "本文件由校准脚本自动生成，仅含索引可证事实；court/judge/client/deadlines/agents 须人工从案件笔记与桌面真卷实地回填，禁止凭记忆完善。"
      },
      "meta": {
        "schema": "case-meta/v1",
        "agents": [
          {
            "stage": "校准占位",
            "role": "DTC-CASE-001",
            "agent": "待回填",
            "status": "todo",
            "note": "meta.agents 待人工按运维手册§3.2 补齐11条路由"
          }
        ]
      },
      "_folder": "韩杰医生医疗事故罪申诉案",
      "_path": "/Users/chenyouqiang/Documents/LawKB/案件生命周期管理系统/韩杰医生医疗事故罪申诉案/case-state.json"
    }
  ]
};
