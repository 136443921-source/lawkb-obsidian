/* 由 gen_mind_panels.py 自动生成 · 勿手改（改席位配置 JSON 后重跑脚本） */
window.MIND_PANELS={
 "generated": "2026-10-01 10:25",
 "source": "/Users/chenyouqiang/Documents/LawKB/模拟法庭管理系统/模拟法庭席位绑定配置.json",
 "configVersion": "1.4.5",
 "roles": [
  {
   "key": "judge",
   "order": 0,
   "emoji": "⚖️",
   "seat": "审判长",
   "role": "审",
   "name": "ai-mock-court-judge",
   "skill": "ai-mock-court-judge v3.1.0",
   "status": "ACTIVE",
   "criteria": "",
   "activated": "2026-09-14",
   "maturity": "~98/100",
   "grade": "—",
   "kpi": "让老强在庭上心里有底——不替老强判案",
   "redLines": [
    "R2不下终局",
    "LTI必过",
    "审判要件卡矩阵校准",
    "本地源引证",
    "不预断结果"
   ],
   "profileSpec": "心证四步法（R2 不下终局）",
   "trace": "72→74→76→78→80→84→87→90→93→95→96→98（2026-09-08 起）",
   "latest": "judge_mind.js 推演裁决内核接入 JUDGE_CARDS 审判要件卡矩阵（正向 support +0.5／踩坑 pitfall -0.7）；eval_suite 51/51 全绿",
   "battles": "",
   "short": "元典账户计费额度不足 → 双源实时核条未通（pkulaw 单源可用）",
   "dataSource": "LawKB/_AI-Memory-Hub/02-当前项目/PROJ-模拟法官心智成熟度备忘录.md",
   "script": "无独立脚本（以 eval_suite.js 30→51 项客观断言回归度量）",
   "statuteBasis": []
  },
  {
   "key": "red",
   "order": 1,
   "emoji": "🔴",
   "seat": "对方代理人",
   "role": "攻",
   "name": "红队出庭律师",
   "skill": "红队出庭律师 v2.6.0",
   "status": "ACTIVE",
   "criteria": "4/4",
   "activated": "2026-09-15",
   "maturity": "91/100",
   "grade": "M5 教练级",
   "kpi": "把蓝队打疼——弱化攻击＝失职",
   "redLines": [
    "不弱化攻击",
    "不越界裁判",
    "不编造案号",
    "LTI必过",
    "攻击点必沉淀"
   ],
   "profileSpec": "{tier: L1|L2|L3|L4, weights: default|evidence_heavy|law_heavy|procedure_heavy}",
   "trace": "56(M3)→63(M4)→76→81→89(M5)",
   "latest": "人格卡转正实战第1场：6658号31号庭后代理词v5版 · L3 绞杀 × 蓝队 D3 回应；打出 S 级 3 条（民法典171条第2款催告要件缺失 / 民诉法解释89条第1款权限限缩后果 / 自认2780元反噬主轴），法条全部自本地法律法规库核验原文",
   "battles": "10 场（含本场）｜产出 36 号红队战报 + 37 号蓝队 v2 回应",
   "short": "D1 训练场次 9 场（脚本口径）18/20；D4 案由覆盖 4 案 16/20；弹药一级位在授权瑕疵域无对口卡",
   "dataSource": "LawKB/知识飞轮系统/05-调用/红队心智模型与训练备忘录-2026-09-14.md",
   "script": "/Users/chenyouqiang/.workbuddy/skills/_common/scripts/red_team_maturity.py",
   "statuteBasis": [],
   "ammo": {
    "name": "授权瑕疵程序战卡族",
    "built": "2026-09-15",
    "cards": [
     {
      "id": "R-PR-178",
      "name": "诉讼代理授权委托书的形式要件与委托人可识别性",
      "desc": "委托人栏空白+印章盖于空白签字栏＝委托人不可识别，属授权成立层面缺失，非权限范围问题"
     },
     {
      "id": "R-PR-179",
      "name": "授权瑕疵的法律效果层级（权限限缩 vs 起诉无效）",
      "desc": "民诉法解释89条1款：授权不明的法定后果是权限限缩；从瑕疵直跳驳回起诉＝跳级，法院不跟"
     },
     {
      "id": "R-PR-180",
      "name": "无权代理起诉的追认规则与催告要件",
      "desc": "民法典171条2款「视为拒绝追认」以催告+30日为触发前提；未催告即援引＝引用未激活之后果"
     },
     {
      "id": "R-PR-181",
      "name": "借用他人名义起诉与起诉条件的程序层含义（含补正应对预案）",
      "desc": "122条1项含实体+程序两层；含补正应对预案5步（110条本人到庭签保证书为最有力武器）"
     },
     {
      "id": "R-PR-182",
      "name": "程序战中的自认边界与反向自认债务防范",
      "desc": "民诉法解释92条1款自认限于「对己不利」；程序战阶段不得碰实体数字，须用假定性表述"
     }
    ],
    "existing": [
     {
      "id": "R-PR-085",
      "name": "起诉签名身份不符时授权意思表示真实的审查",
      "desc": "本族第 0 环：民法典143条「意思表示真实」教义路径（吊顶案办案教义蒸馏）"
     },
     {
      "id": "R-PR-049",
      "name": "原告主体资格的正面范围与九类不适格情形",
      "desc": "与 R-PR-181 互补：主体资格 vs 起诉条件程序层"
     },
     {
      "id": "R-PR-109",
      "name": "撤销自认",
      "desc": "证据规则域；与 R-PR-182 互补：自认的边界 vs 自认的撤销"
     }
    ],
    "note": "五卡均含 negative_note（红队攻击清单）+ 抗辩与但书（蓝队防御要点），攻防两面同卡"
   },
   "battleLog": [
    {
     "date": "2026-09-15",
     "场次": "红队人格卡转正实战第1场",
     "案源": "（2026）黔0330民初6658号 · 丁戊祥诉刘九零等买卖合同纠纷",
     "标的": "31_庭后代理词_起诉未经合法授权应裁定驳回起诉v5版（蓝队 v4.6.2 出品）",
     "红队档位": "{tier: L3, weights: procedure_heavy}",
     "蓝队档位": "{tier: D3, weights: procedure_heavy}",
     "产物": [
      "36_红队致命漏洞战报_针对31号庭后代理词v5版_人格卡转正实战.md（S级3 / A级4 / B级2）",
      "37_蓝队v2回应_针对36号红队战报_2026-09-15.md（接受8 / 部分接受2 / 反驳2）"
     ],
     "S级破绽": [
      "【法条硬伤】焦点四援引民法典第171条第2款「视为拒绝追认」，但该款以「相对人催告+三十日」为触发前提，v5 全篇未主张亦未证明催告 → 建议改走第1款消极路径 + 三次积极否认",
      "【法律效果跳级】民诉法解释第89条第1款对授权瑕疵的法定后果是「权限限缩」而非「起诉无效」，v5 从瑕疵直跳驳回起诉，缺层级论证",
      "【自认反噬】第104段自认 2780 元，与同段「不得扩大为对欠款数额的认可」自我消解，且削弱「借名发动」主轴说服力"
     ]
    }
   ]
  },
  {
   "key": "blue",
   "order": 2,
   "emoji": "🔵",
   "seat": "我方代理人",
   "role": "防",
   "name": "蓝队出庭律师",
   "skill": "蓝队出庭律师 v4.6.2",
   "status": "ACTIVE",
   "criteria": "",
   "activated": "2026-09-14",
   "maturity": "88/100",
   "grade": "M5 教练级",
   "kpi": "法官需要听到什么才会支持我",
   "redLines": [
    "不自我打分",
    "不掩盖薄弱点",
    "不编造案号",
    "LTI必过",
    "要件逐项举证"
   ],
   "profileSpec": "{tier: D1|D2|D3|D4, weights: default|evidence_heavy|law_heavy|procedure_heavy}",
   "trace": "66(M4)→75→77→81→86→88（2026-09-14 单日演进）",
   "latest": "心智卡实战转正 + 输出模板补齐（九类产物 + 法官三问）",
   "battles": "8 场对抗确认／3 案（厚德、6658、6660）",
   "short": "D4 案由覆盖 12/20",
   "dataSource": "LawKB/_AI-Memory-Hub/02-当前项目/PROJ-001-蓝队出庭律师训练项目状态.md",
   "script": "/Users/chenyouqiang/.workbuddy/skills/_common/scripts/blue_team_maturity.py",
   "statuteBasis": []
  },
  {
   "key": "clerk",
   "order": 3,
   "emoji": "📝",
   "seat": "书记员",
   "role": "录",
   "name": "模拟法庭书记员",
   "skill": "模拟法庭书记员 v1.0.2",
   "status": "ACTIVE",
   "criteria": "4/4",
   "activated": "2026-09-15",
   "maturity": "64/100",
   "grade": "M4 精熟",
   "kpi": "只对「发生了什么」负责——法官可以判错，笔录不能错",
   "redLines": [
    "不评判",
    "不越权填认证结论",
    "不跳级",
    "不润色口语",
    "不补白",
    "不与QC合并",
    "不拿追认充实战"
   ],
   "profileSpec": "{tier: R2, weights: default}  （三件套头部必带）",
   "trace": "首版 → 64/100 M4（2026-09-15）",
   "latest": "人格卡补齐 record_profile 字段规范 + 记录失误标本库骨架（9 标本），激活判据 4/4 达成并转正",
   "battles": "2 场（6658 吊顶案 / 6660 雅菲案），跨案稳定性 98/100 持平",
   "short": "D4 案件覆盖 8/20（同案重跑不加分，需扩案）；D2 台账留痕率 7.1/25",
   "dataSource": "LawKB/_AI-Memory-Hub/02-当前项目/PROJ-002-模拟法庭书记员训练项目状态.md",
   "script": "/Users/chenyouqiang/.workbuddy/skills/_common/scripts/clerk_maturity.py（--refresh --hub-sync）",
   "statuteBasis": []
  }
 ]
};
