/* ============================================================================
 * subsumption_engine.js — 要件涵摄引擎（Path A 真涵摄 · 命门升级版）
 * ----------------------------------------------------------------------------
 * 定位：把 judge_reviewer 的「检索相似卡」（judgeReviewA 关键词匹配）升级为
 *      「按要件拆解 → 逐要件涵摄 → 输出推理链」的候选推理实体。
 *
 * 设计原则（继承 judge_reviewer_entity_design.md 红线）：
 *   1. R2 只给候选：所有输出带【候选·待人工确认】，禁止 verdict/win_prob。
 *   2. 离线可用：纯 JS，不依赖外部 LLM / 不联网（核条走桥接另算）。
 *   3. 要件模型教义化：构成要件取自通说与本地源，不凭记忆编造。
 *   4. 只读：不写回 LawKB / statute_cache。
 *
 * 双形态：Node(module.exports) + 浏览器(window.SUBSUMPTION)。
 * ========================================================================== */

(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined') window.SUBSUMPTION = api;
})(this, function () {

  /* ----------------------------- 要件模型库 ----------------------------- *
   * 每个 statuteKey 对应 statute_cache.json 中的同 key（权威文本已北大法宝核填）。
   * elements: 构成要件（教义拆解）；satisfiedBy: 该要件可由哪些事实标签涵摄；
   * hint: 涵摄指引（含本案情境锚点）；burden: 举证责任归属方。
   * legalEffect: 全满足 / 任一不满足 / 存疑未认定 三种结论候选。
   * ---------------------------------------------------------------------- */
  const ELEMENT_MODELS = {
    civ_143: {
      statuteKey: 'civ_143',
      law: '中华人民共和国民法典',
      article: '第143条',
      title: '民事法律行为有效要件',
      pkulawUrl: 'https://pkulaw.com/chl/aa00daaeb5a4fe4ebdfb.html',
      elements: [
        { id: 'e1', text: '行为人具有相应的民事行为能力',
          satisfiedBy: ['完全民事行为能力', '自然人成年且精神健康', '法人依法登记且在经营范围'],
          hint: '涵摄指引：查明当事人身份、年龄、精神状态、法人登记与经营范围。',
          burden: '主张法律行为有效方' },
        { id: 'e2', text: '意思表示真实',
          satisfiedBy: ['本人真实作出', '授权委托真实', '无欺诈胁迫', '无重大误解', '无冒名'],
          hint: '涵摄指引：查明签名/印鉴是否本人作出；有无冒名、虚假授权、欺诈胁迫、重大误解。' +
                '【本案锚点·6658吊顶案】起诉状署名"丁茂祥"与营业执照"丁戊祥"（第14位为5）姓名不一致，' +
                '授权意思表示是否真实系核心争点——143条"意思表示真实"要件是否满足，直接决定起诉主体行为效力。',
          burden: '主张法律行为有效方' },
        { id: 'e3', text: '不违反法律、行政法规的强制性规定，不违背公序良俗',
          satisfiedBy: ['标的合法', '目的合法', '不违背公序良俗'],
          hint: '涵摄指引：审查合同标的/目的是否违法或违背公序良俗（反向见民法典153条）。',
          burden: '主张法律行为有效方' }
      ],
      legalEffect: {
        allSatisfied: '民事法律行为有效，产生当事人预期的法律约束力。',
        anyNotSatisfied: '反向推论：任一有效要件缺失 → 该民事法律行为不生效（无效或可撤销）。',
        someDoubt: '要件真伪不明时，依举证责任（民诉法第67条）由主张有效方承担不利后果。'
      }
    },

    civ_153: {
      statuteKey: 'civ_153',
      law: '中华人民共和国民法典',
      article: '第153条',
      title: '无效情形（违反强制性规定/违背公序良俗）',
      pkulawUrl: 'https://pkulaw.com/chl/aa00daaeb5a4fe4ebdfb.html',
      elements: [
        { id: 'e1', text: '违反法律、行政法规的强制性规定（且该规定致行为无效）',
          satisfiedBy: ['违反效力性强制规定', '非管理性规定'],
          hint: '涵摄指引：区分"效力性"与"管理性"强制规定；仅前者致无效（但书）。',
          burden: '主张无效方' },
        { id: 'e2', text: '违背公序良俗',
          satisfiedBy: ['损害公共秩序', '违背善良风俗'],
          hint: '涵摄指引：审查行为是否损害公共秩序或善良风俗。',
          burden: '主张无效方' }
      ],
      legalEffect: {
        allSatisfied: '民事法律行为无效（153条）：违反效力性强制规定 或 违背公序良俗，二者任一即无效。',
        anyNotSatisfied: '未落入153条无效情形，行为不因本条无效（效力另依143等判断）。',
        someDoubt: '是否违反效力性强制规定/违背公序良俗真伪不明 → 由主张无效方举证，不能证成则不成立无效。'
      }
    },

    civ_577: {
      statuteKey: 'civ_577',
      law: '中华人民共和国民法典',
      article: '第577条',
      title: '违约责任',
      pkulawUrl: 'https://pkulaw.com/chl/aa00daaeb5a4fe4ebdfb.html',
      elements: [
        { id: 'e1', text: '存在合法有效的合同关系',
          satisfiedBy: ['合同依法成立', '合同有效', '双方合意'],
          hint: '涵摄指引：先决于合同成立与效力（可衔接 civ_143/civ_465）。',
          burden: '主张违约责任方' },
        { id: 'e2', text: '当事人一方不履行合同义务或履行不符合约定',
          satisfiedBy: ['未按约履行', '履行迟延', '瑕疵履行', '拒绝履行'],
          hint: '涵摄指引：查明履约事实、约定期限、瑕疵证据（举证质证环节固定）。',
          burden: '主张违约责任方' },
        { id: 'e3', text: '无免责事由',
          satisfiedBy: ['无不可抗力', '无约定免责', '无免责条款生效'],
          hint: '涵摄指引：审查是否存在不可抗力（180条）或约定/法定免责。',
          burden: '抗辩免责方' }
      ],
      legalEffect: {
        allSatisfied: '违约方应承担继续履行、采取补救措施或赔偿损失等违约责任（577条）。',
        anyNotSatisfied: '任一要件缺失（尤无有效合同/无违约/有免责）→ 违约责任不成立。',
        someDoubt: '违约或免责真伪不明 → 由主张方举证，真伪不明承担不利后果。'
      }
    },

    civ_465: {
      statuteKey: 'civ_465',
      law: '中华人民共和国民法典',
      article: '第465条',
      title: '合同相对性（仅对当事人具有法律约束力）',
      pkulawUrl: 'https://pkulaw.com/chl/aa00daaeb5a4fe4ebdfb.html',
      elements: [
        { id: 'e1', text: '合同依法成立',
          satisfiedBy: ['双方合意', '形式合规'],
          hint: '涵摄指引：合同成立要件。',
          burden: '主张约束方' },
        { id: 'e2', text: '主张约束非合同当事人',
          satisfiedBy: ['突破相对性', '第三人承担责任', '实际买受人'],
          hint: '涵摄指引：审查是否向非当事人主张权利。' +
                '【本案锚点·雅菲窗帘案6660/吊顶案6658】黄茂姣涉嫌实际买受人，' +
                '相对性抗辩核心：合同仅约束署名当事人，非经法定情形不得扩及第三人。',
          burden: '主张约束方' }
      ],
      legalEffect: {
        allSatisfied: '依法成立的合同仅对当事人具有法律约束力，非当事人不受其约束（但法律另有规定除外）。',
        anyNotSatisfied: '不存在相对性约束基础 → 对非当事人主张缺乏合同依据。',
        someDoubt: '是否构成突破相对性（如买卖挂靠/债务加入）真伪不明 → 由主张方举证。'
      }
    },

    civ_770: {
      statuteKey: 'civ_770',
      law: '中华人民共和国民法典',
      article: '第770条',
      title: '承揽合同定义',
      pkulawUrl: 'https://pkulaw.com/chl/aa00daaeb5a4fe4ebdfb.html',
      elements: [
        { id: 'e1', text: '承揽人按定作人要求完成工作',
          satisfiedBy: ['按指示作业', '完成特定工作'],
          hint: '涵摄指引：审查工作内容是否"按定作人要求"。',
          burden: '主张承揽关系方' },
        { id: 'e2', text: '交付工作成果',
          satisfiedBy: ['交付成果', '成果可验收'],
          hint: '涵摄指引：是否以"成果交付"为对价核心（区别于劳务/买卖）。',
          burden: '主张承揽关系方' },
        { id: 'e3', text: '定作人支付报酬',
          satisfiedBy: ['报酬约定', '应付款'],
          hint: '涵摄指引：报酬支付义务。',
          burden: '主张承揽关系方' }
      ],
      legalEffect: {
        allSatisfied: '构成承揽合同，适用承揽有关规定（含 770-787）。',
        anyNotSatisfied: '要件缺失 → 不构成承揽合同（可能系买卖/劳务/建设工程）。',
        someDoubt: '合同性质真伪不明 → 由主张方举证，并可能触发证据规定53条释明。'
      }
    },

    civ_787: {
      statuteKey: 'civ_787',
      law: '中华人民共和国民法典',
      article: '第787条',
      title: '定作人任意解除权',
      pkulawUrl: 'https://pkulaw.com/chl/aa00daaeb5a4fe4ebdfb.html',
      elements: [
        { id: 'e1', text: '承揽合同依法成立',
          satisfiedBy: ['承揽关系成立'],
          hint: '涵摄指引：先决于 civ_770 承揽关系成立。',
          burden: '解除权行使方' },
        { id: 'e2', text: '承揽人完成工作前',
          satisfiedBy: ['工作未完成', '成果未交付'],
          hint: '涵摄指引：时间节点须在"完成工作前"，完成后不享任意解除。',
          burden: '解除权行使方' }
      ],
      legalEffect: {
        allSatisfied: '定作人可随时解除合同；造成承揽人损失的，应赔偿损失。',
        anyNotSatisfied: '不满足（如已完成工作）→ 不享有任意解除权。',
        someDoubt: '是否"完成前"真伪不明 → 由行使方举证。'
      }
    },

    civ_793: {
      statuteKey: 'civ_793',
      law: '中华人民共和国民法典',
      article: '第793条',
      title: '建工合同无效折价补偿',
      pkulawUrl: 'https://pkulaw.com/chl/aa00daaeb5a4fe4ebdfb.html',
      elements: [
        { id: 'e1', text: '建设工程施工合同无效',
          satisfiedBy: ['无资质', '应招未招', '串标', '违反强制规定'],
          hint: '涵摄指引：审查施工资质、招投标合规性（建工解释一第1条）。',
          burden: '主张无效/折价方' },
        { id: 'e2', text: '建设工程经验收合格',
          satisfiedBy: ['验收合格', '发包人擅自使用视为合格'],
          hint: '涵摄指引：验收合格为折价补偿前提；不合格则进入 e2b 分支。',
          burden: '主张折价方' },
        { id: 'e2b', text: '验收不合格之处理（修复后合格/仍不合格）',
          satisfiedBy: ['修复后合格', '修复后仍不合格'],
          hint: '涵摄指引：不合格时，修复合格→发包人可请求承包人承担修复费；仍不合格→承包人无权请求折价补偿。',
          burden: '视情形分配' },
        { id: 'e3', text: '发包人对不合格损失有过错',
          satisfiedBy: ['发包人提供错误图纸', '发包人指令违规'],
          hint: '涵摄指引：发包人过错 → 承担相应责任（与承包人过错相抵）。',
          burden: '主张发包人责任方' }
      ],
      legalEffect: {
        allSatisfied: '无效但验收合格 → 可参照合同关于工程价款的约定折价补偿承包人。',
        anyNotSatisfied: '无效且验收不合格且修复仍不合格 → 承包人无权请求折价补偿。',
        someDoubt: '验收/过错真伪不明 → 由主张方举证，依举证责任分配后果。'
      }
    },

    ms2023_67: {
      statuteKey: 'ms2023_67',
      law: '中华人民共和国民事诉讼法（2023修正）',
      article: '第67条',
      title: '举证责任（谁主张谁举证）',
      pkulawUrl: 'https://pkulaw.com/chl/55ada7bc4fc9d8ccbdfb.html',
      elements: [
        { id: 'e1', text: '当事人提出具体主张',
          satisfiedBy: ['诉请', '抗辩', '事实主张'],
          hint: '涵摄指引：识别主张内容与主张方。',
          burden: '主张方' },
        { id: 'e2', text: '该主张所依据的事实处于真伪不明需证状态',
          satisfiedBy: ['待证事实', '对方不自认'],
          hint: '涵摄指引：对方自认或免证事实不触发举证负担。',
          burden: '主张方' }
      ],
      legalEffect: {
        allSatisfied: '主张方对自己提出的主张有责任提供证据；真伪不明时承担不利后果。',
        anyNotSatisfied: '主张方无须举证之情形（对方自认/免证事实）→ 不触发本条负担。',
        someDoubt: '事实真伪不明 → 由主张方承担举证不能的不利后果。'
      }
    },

    ms2023_68: {
      statuteKey: 'ms2023_68',
      law: '中华人民共和国民事诉讼法（2023修正）',
      article: '第68条',
      title: '及时举证·举证期限与逾期后果',
      pkulawUrl: 'https://pkulaw.com/chl/55ada7bc4fc9d8ccbdfb.html',
      elements: [
        { id: 'e1', text: '法院确定举证期限（或当事人协商）',
          satisfiedBy: ['举证通知书', '期限指定'],
          hint: '涵摄指引：审查举证期限是否已指定及期限长度。',
          burden: '法院/当事人' },
        { id: 'e2', text: '当事人逾期提供证据',
          satisfiedBy: ['超期提交', '未在期限内提供'],
          hint: '涵摄指引：判断逾期事实。',
          burden: '逾期提供方' },
        { id: 'e3', text: '逾期理由不成立或拒不说明',
          satisfiedBy: ['理由不成立', '拒不说明'],
          hint: '涵摄指引：法院责令说明理由，理由不成立方可处罚。',
          burden: '逾期提供方' }
      ],
      legalEffect: {
        allSatisfied: '法院可不予采纳该证据，或采纳但予以训诫、罚款。',
        anyNotSatisfied: '理由成立/已延期 → 不发生逾期不利后果。',
        someDoubt: '理由是否成立真伪不明 → 由提供方说明，不能说明则推定为不成立。'
      }
    },

    ms2023_71: {
      statuteKey: 'ms2023_71',
      law: '中华人民共和国民事诉讼法（2023修正）',
      article: '第71条',
      title: '证据出示与互相质证',
      pkulawUrl: 'https://pkulaw.com/chl/55ada7bc4fc9d8ccbdfb.html',
      elements: [
        { id: 'e1', text: '证据在法庭上出示',
          satisfiedBy: ['当庭出示', '物证书证展示'],
          hint: '涵摄指引：证据须经出示程序。',
          burden: '举证方' },
        { id: 'e2', text: '当事人互相质证',
          satisfiedBy: ['对方质证意见', '质辩交锋'],
          hint: '涵摄指引：未经质证不得作为定案依据（证据规定第68条精神）。',
          burden: '双方' }
      ],
      legalEffect: {
        allSatisfied: '证据经出示并互相质证，具备作为定案依据的程序资格。',
        anyNotSatisfied: '未经质证 → 不得作为认定案件事实的根据。',
        someDoubt: '质证是否充分真伪不明 → 影响证明力认定。'
      }
    },

    evid_53: {
      statuteKey: 'evid_53',
      law: '最高人民法院关于民事诉讼证据的若干规定（2019修正）',
      article: '第53条',
      title: '释明与焦点审理（法律关系性质/行为效力认定不一致）',
      pkulawUrl: 'https://pkulaw.com/chl/e2cef8c231095c1bbdfb.html',
      elements: [
        { id: 'e1', text: '当事人主张的法律关系性质或民事行为效力',
          satisfiedBy: ['主张性质', '主张效力'],
          hint: '涵摄指引：识别当事人主张的定性。',
          burden: '当事人' },
        { id: 'e2', text: '与人民法院根据案件事实作出的认定不一致',
          satisfiedBy: ['定性分歧', '效力分歧'],
          hint: '涵摄指引：法院心证与当事人主张出现分歧即触发。' +
                '【本案锚点】6658案若法院认为"起诉主体/授权意思表示"与原告主张不一致，应作为焦点审理并释明。',
          burden: '法院释明' },
        { id: 'e3', text: '非已充分辩论 且 对裁判理由及结果有影响',
          satisfiedBy: ['未充分辩论', '有影响'],
          hint: '涵摄指引：已充分辩论或无影响者不触发。',
          burden: '法院' }
      ],
      legalEffect: {
        allSatisfied: '法院应将前述性质/效力作为焦点问题审理并释明；当事人据此变更诉请的，法院准许并可重新指定举证期限。',
        anyNotSatisfied: '无分歧或已充分辩论/无影响 → 不触发释明与焦点转换。',
        someDoubt: '是否"有影响"真伪不明 → 由法院裁量，倾向于保护当事人辩论权。'
      }
    }
  };

  /* ------------------- Path B：动态要件模型合并（任意规范自动拆解后落盘） ------------------- *
   * 加载顺序：浏览器侧先载 dynamic_models.js（设 window.SUBSUMPTION_DYNAMIC），
   *          Node 侧直接读同目录 dynamic_models.json；二者合并进 ELEMENT_MODELS。
   * 新增任意法条：agent 用北大法宝/元典 live 抓原文 → 教义拆解 → 同步写
   *          dynamic_models.json 与 dynamic_models.js → 引擎自动收录，widget 立即可用。
   * ----------------------------------------------------------------------------------- */
  (function mergeDynamicModels() {
    let dyn = null;
    try {
      if (typeof window !== 'undefined' && window.SUBSUMPTION_DYNAMIC) {
        dyn = window.SUBSUMPTION_DYNAMIC;
      } else if (typeof require !== 'undefined') {
        const fs = require('fs'), path = require('path');
        const p = path.join(__dirname, 'dynamic_models.json');
        dyn = JSON.parse(fs.readFileSync(p, 'utf8'));
      }
    } catch (e) { dyn = null; }
    if (dyn && typeof dyn === 'object') {
      Object.keys(dyn).forEach(k => { ELEMENT_MODELS[k] = dyn[k]; });
    }
  })();

  /* ----------------------------- 核心函数 ----------------------------- */

  // 列出全部可用法条 key + 标题（供 UI 下拉）
  function listStatutes() {
    return Object.keys(ELEMENT_MODELS).map(k => ({
      key: k,
      label: `${ELEMENT_MODELS[k].law} ${ELEMENT_MODELS[k].article} · ${ELEMENT_MODELS[k].title}`
    }));
  }

  // 取单条要件模型
  function getModel(key) { return ELEMENT_MODELS[key] || null; }

  const STATUS = {
    SAT:  '满足',
    NOT:  '不满足',
    DOUBT:'存疑',
    UND:  '未认定'
  };

  /* --------------------- 证据类型分类器（证据清单联动·离线） ---------------------
   * 依要件文本关键词，推荐应举证据类型；不满足(NOT)情形给补强/转换路径建议。
   * 证明标准统一引用《民诉法解释》第108条「高度盖然性」。 */
  const EVIDENCE_KEYWORDS = [
    { kw: ['意思表示', '授权', '委托', '合意', '订立'], ev: ['书面授权/委托文件', '录音录像', '微信/短信等沟通记录', '合同原件'] },
    { kw: ['行为能力', '成年', '精神', '登记', '资格'], ev: ['身份证明', '营业执照/登记信息', '行为能力鉴定意见'] },
    { kw: ['因果关系', '原因', '导致', '造成'], ev: ['鉴定意见', '事故认定书', '医疗/损失记录', '现场勘验笔录'] },
    { kw: ['损害', '损失', '后果'], ev: ['医疗费/票据', '损失评估报告', '损失清单', '鉴定意见'] },
    { kw: ['过错', '违法', '不当', '违反'], ev: ['过错行为记录', '行政处罚决定书', '证人证言', '视听资料'] },
    { kw: ['欺诈', '虚假', '隐瞒', '误导'], ev: ['虚假陈述证据', '隐瞒事实证据', '第三人证言'] },
    { kw: ['错误', '认识', '误解'], ev: ['作出意思表示时的沟通记录', '认知状态证据'] },
    { kw: ['加害', '行为', '侵权'], ev: ['加害行为记录', '现场证据', '证人证言'] }
  ];

  function classifyEvidence(text, status) {
    if (status === STATUS.NOT) {
      return {
        evs: ['补强证据（指向该要件成立）', '或评估转换诉讼/抗辩路径'],
        standard: '本证需达高度盖然性；若属反驳，则反证只需动摇法官心证（《民诉法解释》第108条）'
      };
    }
    const out = [];
    EVIDENCE_KEYWORDS.forEach(k => { if (k.kw.some(w => (text || '').includes(w))) out.push(...k.ev); });
    if (!out.length) out.push('书证', '物证', '证人证言', '视听资料', '鉴定意见（依待证事实具体确定）');
    return {
      evs: Array.from(new Set(out)),
      standard: '民事诉讼一般证明标准：高度盖然性（《最高人民法院关于适用〈民事诉讼法〉的解释》第108条）'
    };
  }

  /* --------------------- 心证层（judge_reviewer 心智 · 候选 · 纯离线） ---------------------
   * 生成两类候选推理：
   *   ① 本院倾向于认为…（心证适度开示，依结论类型给倾向 + 理由 + 归责）
   *   ② 证据采信说理（对已有已证事实的要件逐一认证，禁写"显然/当然"）
   * 全程【候选·待人工确认】，无 verdict，纯离线零 live 消耗。 */
  function buildXinZheng(m, rows, conclusionType) {
    const req = rows.filter(r => !r.optional);

    // ① 证据采信说理：仅对已有已证事实的要件逐一认证
    const admission = [];
    rows.forEach(r => {
      if (!r.fact) return;
      let verdict, reason;
      if (r.status === STATUS.SAT) {
        verdict = '采信';
        reason = `该已证事实「${r.fact}」经法庭出示、当事人互相质证，形式合法、来源真实、与待证事实具有关联性，本院予以采信，作为认定要件「${r.text}」满足之依据，证明力足以达到高度盖然性。`;
      } else if (r.status === STATUS.NOT) {
        verdict = '采纳·证明方向反';
        reason = `该已证事实「${r.fact}」本院予以采纳，但其证明方向指向要件「${r.text}」不成立（或不足以证明要件满足），故该要件不予认定满足。`;
      } else if (r.status === STATUS.DOUBT) {
        verdict = '初步采纳·待认证';
        reason = `该已证事实「${r.fact}」本院予以初步采纳，但证明力尚未充分（未达高度盖然性，或存在反证可能），要件「${r.text}」处于存疑状态，待进一步质证、补证后认定。`;
      } else {
        verdict = '暂不予认证';
        reason = `要件「${r.text}」处于未认定状态，已证事实「${r.fact}」尚不足以独立支撑要件涵摄，需结合其他证据综合判断。`;
      }
      admission.push({ id: r.id, text: r.text, status: r.status, verdict, reason });
    });

    // ② 心证倾向段：本院倾向于认为…
    const unsat = req.filter(r => r.status === STATUS.NOT);
    const doubtUnd = req.filter(r => r.status === STATUS.DOUBT || r.status === STATUS.UND);
    let leanType, leanText;
    if (conclusionType === 'effect-established') {
      leanType = '成立倾向';
      const satReq = req.filter(r => r.status === STATUS.SAT);
      leanText = `本院倾向于认为，依现有证据，该法律效果成立之可能性较高。理由：${m.title}所列各项要件（${satReq.map(r => '「' + r.text + '」').join('、')}）均经已证事实涵摄满足，且无明显反证足以推翻，故暂作成立之认定准备。`;
    } else if (conclusionType === 'effect-not-established') {
      leanType = '不成立倾向';
      leanText = `本院倾向于认为，该法律效果难以成立。理由：强制要件${unsat.map(u => '「' + u.text + '」').join('、')}不满足（${unsat.map(u => u.burden + '所主张/抗辩之该要件不能成立').join('；')}），依${m.law}${m.article}之构成要件，该法律效果欠缺成立基础。`;
    } else {
      leanType = '真伪不明·待举证';
      const burdenSet = Array.from(new Set(doubtUnd.map(u => u.burden)));
      leanText = `本院倾向于认为，要件${doubtUnd.map(u => '「' + u.text + '」').join('、')}事实真伪不明。依举证责任分配（民事诉讼法第67条），由${burdenSet.join('、')}承担举证不能之不利后果；在补证前，本院暂不能形成该法律效果成立之心证。`;
    }
    const optNote = rows.filter(r => r.optional)
      .map(r => `（可选要件「${r.text}」当前状态：${r.status}，不阻断主结论，仅作补充审查维度）`).join('');
    return { lean: { type: leanType, text: leanText + (optNote ? optNote : '') }, admission };
  }

  /* --------------------- §F 数额预判门控（与要件成立联动） ---------------------
   * 设计铁律：数额预判（违约金 / 损失赔偿 / 折价补偿等）必须以"基础责任要件成立"为前提。
   *   - statuteKey 属"责任 / 赔偿型" 且 conclusionType==='effect-established' → 解锁 §F
   *   - 否则（未成立 / 真伪不明 / 非责任型）→ 锁定 §F，并给候选理由（不自动裁量）
   * 全链路【候选·待人工确认】，不输出任何数额结论。 */
  const AMOUNT_RELEVANT = {
    civ_577:  { label: '违约责任',
      scale: ['违约金（民法典第585条：约定过分高于损失可请求酌减，一般以超损30%为参考）',
              '实际损失赔偿（可预见规则·第584条）', '继续履行 / 补救措施（第577条）'] },
    civ_793:  { label: '建工折价补偿',
      scale: ['折价补偿额（参照合同工程价款约定·第793条）', '修复费用（验收不合格时）'] },
    civ_1165: { label: '过错侵权赔偿责任',
      scale: ['人身损害赔偿（医疗费 / 误工 / 护理 / 残疾赔偿金等）', '财产损失赔偿', '精神损害抚慰金（第1183条）'] },
    civ_148:  { label: '欺诈撤销后果 / 赔偿',
      scale: ['返还财产 / 折价补偿（第157条）', '信赖利益损失赔偿'] },
    civ_1182: { label: '侵害人身权益财产损失赔偿',
      scale: ['财产损失赔偿（按损失发生时市场价格等·第1182条）'] }
  };

  function computeAmountGate(m, conclusionType) {
    const rel = AMOUNT_RELEVANT[m.statuteKey];
    if (!rel) {
      return {
        enabled: false, relevant: false, label: null,
        reason: `本案要件「${m.title}」非直接责任 / 赔偿型，数额预判须以基础责任要件成立为前提；` +
                `请就违约责任、过错侵权赔偿、建工折价等责任要件完成涵摄且结论为"成立"后，再进入具体数额预估。`
      };
    }
    const cl = conclusionTypeLabel(conclusionType);
    if (conclusionType === 'effect-established') {
      return {
        enabled: true, relevant: true, label: rel.label, scales: rel.scale,
        reason: `「${m.title}」成立（${m.article}），责任基础已确立，可进入数额预判：` +
                `依该条与裁量尺度卡确定违约金 / 损失赔偿 / 折价补偿等具体数额（须结合举证与第585条等调整规则，机器仅给候选）。`
      };
    }
    if (conclusionType === 'pending-burden') {
      return {
        enabled: false, relevant: true, label: rel.label,
        reason: `「${m.title}」真伪不明（待举证），责任基础未确立，暂不进入数额预判；` +
                `待要件补全、结论转为"成立"后再行预估。`
      };
    }
    return {
      enabled: false, relevant: true, label: rel.label,
      reason: `「${m.title}」不成立（${cl}），责任基础欠缺，不进入数额预判。`
    };
  }

  function amountScaleHints(statuteKey) {
    const rel = AMOUNT_RELEVANT[statuteKey];
    return rel ? rel.scale : [];
  }

  /**
   * 构建要件涵摄推理链
   * @param {string} statuteKey
   * @param {Object} findings  形如 { e1:'满足'|'不满足'|'存疑'|'未认定', ... }
   * @param {Object} opts      可选 { facts:{e1:'事实表述',...}, note:'的补充说明确认' }
   * @returns {Object} 结构化推理链（全带 R2 候选标注）
   */
  function buildSubsumption(statuteKey, findings, opts) {
    opts = opts || {};
    const m = ELEMENT_MODELS[statuteKey];
    if (!m) return { error: '未找到要件模型：' + statuteKey, tag: STATUS_UND ? '' : '【候选·待人工确认】' };

    const f = findings || {};
    const facts = opts.facts || {};
    const rows = m.elements.map(el => {
      const st = f[el.id] || STATUS.UND;
      return {
        id: el.id,
        text: el.text,
        status: st,
        fact: facts[el.id] || '',
        hint: el.hint,
        burden: el.burden,
        optional: !!el.optional
      };
    });

    // 结论类型判定（optional 要件不成立/未认定不阻断主结论，仅作补充审查维度）
    const reqRows = rows.filter(r => !r.optional);
    const hasNot = reqRows.some(r => r.status === STATUS.NOT);
    const hasDoubtOrUnd = reqRows.some(r => r.status === STATUS.DOUBT || r.status === STATUS.UND);
    let conclusionType, conclusionText;
    if (hasNot) {
      conclusionType = 'effect-not-established';
      conclusionText = m.legalEffect.anyNotSatisfied;
    } else if (hasDoubtOrUnd) {
      conclusionType = 'pending-burden';
      conclusionText = m.legalEffect.someDoubt;
    } else {
      conclusionType = 'effect-established';
      conclusionText = m.legalEffect.allSatisfied;
    }

    // —— 证据缺口自主识别（Path B 第二阶段·离线逻辑·零 live 消耗）——
    // 扫描：状态为 未认定/存疑/不满足 且 缺乏已证事实 的要件 → 自动归责举证方
    const GAP_STATUS = {};
    GAP_STATUS[STATUS.UND] = true; GAP_STATUS[STATUS.DOUBT] = true; GAP_STATUS[STATUS.NOT] = true;
    const gaps = rows.filter(r => {
      if (r.fact) return false;                                   // 已有已证事实 → 非缺口
      if (r.status === STATUS.SAT) return false;                  // 满足 → 非缺口
      if (r.optional) {
        // 可选要件：仅在被明确标注为 存疑/不满足 时才列为补充缺口，
        // 避免"从未评估的默认未认定"每次运行都产生噪声。
        return r.status === STATUS.DOUBT || r.status === STATUS.NOT;
      }
      return !!GAP_STATUS[r.status];                              // 强制要件：未认定/存疑/不满足 皆列缺口
    }).map(r => {
      let suggestion;
      if (r.status === STATUS.UND) {
        suggestion = `由 ${r.burden} 举证证明；若未举证，该要件处于未认定状态，将依举证责任分配承担不利后果。`;
      } else if (r.status === STATUS.DOUBT) {
        suggestion = `事实真伪不明，依举证规则由 ${r.burden} 承担不利后果（待证事实不成立）。`;
      } else {
        suggestion = `${r.burden} 所主张/抗辩之该要件不成立，需补强证据或转换诉讼/抗辩路径；当前缺已证事实支撑。`;
      }
      if (r.optional) suggestion = '（可选要件·不阻断主结论）' + suggestion;
      const ce = classifyEvidence(r.text, r.status);
      return { id: r.id, text: r.text, status: r.status, burden: r.burden, optional: r.optional, suggestion,
               suggestedEvidence: ce.evs, proofStandard: ce.standard };
    });

    // —— §F 数额预判门控（与要件成立联动·候选·待人工确认）——
    const amountGate = computeAmountGate(m, conclusionType);

    // —— 心证层（judge_reviewer 心智·候选·待人工确认·纯离线）——
    const xz = buildXinZheng(m, rows, conclusionType);

    // 推理链步骤（大前提→小前提逐要件→结论）
    const chain = [];
    chain.push(`【大前提】${m.law}${m.article}（${m.title}）：` +
      m.elements.map(e => e.text).join('；') + '。');
    rows.forEach(r => {
      const mark = ({ '满足':'✓', '不满足':'✗', '存疑':'?', '未认定':'·' })[r.status];
      chain.push(`【小前提·涵摄】要件(${r.id}) ${r.text}： [${mark} ${r.status}]` +
        (r.fact ? ` — 已证事实：${r.fact}` : '') +
        (r.status === STATUS.UND ? `（${r.burden}待证）` : ''));
    });
    // 逻辑串接
    const marks = rows.map(r => ({ '满足':'✓', '不满足':'✗', '存疑':'?', '未认定':'·' })[r.status]).join('');
    chain.push(`【涵摄串接】${marks} → ${conclusionTypeLabel(conclusionType)}`);
    chain.push(`【结论候选·待人工确认】${conclusionText}`);
    if (gaps.length) {
      chain.push(`【证据缺口·自主识别·待人工确认】共识别 ${gaps.length} 处证据缺口（下列要件缺已证事实，自动归责举证方）：`);
      gaps.forEach((g, i) => {
        chain.push(`  ${i + 1}. 要件(${g.id}) ${g.text} · [${g.status}] · 举证方：${g.burden}` +
          (g.optional ? '（可选）' : '') + ` → ${g.suggestion}`);
      });
    }

    // 心证层写入推理链（供复制/留痕）
    if (xz.lean && xz.lean.text) {
      chain.push(`【心证·候选·待人工确认·${xz.lean.type}】${xz.lean.text}`);
    }
    if (xz.admission && xz.admission.length) {
      chain.push(`【证据采信说理·候选·待人工确认】共对 ${xz.admission.length} 项已证事实作认证说理：`);
      xz.admission.forEach((a, i) => {
        chain.push(`  ${i + 1}. 要件(${a.id})「${a.text}」[${a.status}] → 【${a.verdict}】${a.reason}`);
      });
    }

    // —— §F 数额预判门控写入推理链（供复制 / 留痕）——
    if (amountGate.relevant) {
      chain.push(`【§F 数额预判门控·候选·待人工确认】${amountGate.enabled ? '✅ 解锁' : '⛔ 锁定'}（${amountGate.label}）：${amountGate.reason}`);
    }

    return {
      statuteKey,
      law: m.law,
      article: m.article,
      title: m.title,
      pkulawUrl: m.pkulawUrl,
      rows,
      conclusionType,
      conclusionText,
      chain,
      gaps,
      amountGate,
      xinZheng: xz,
      tag: '【候选·待人工确认】'
    };
  }

  function conclusionTypeLabel(t) {
    return ({
      'effect-established': '全部要件满足 → 法律效果成立（候选）',
      'effect-not-established': '存在要件不满足 → 法律效果不成立（候选）',
      'pending-burden': '要件存疑/未认定 → 真伪不明，依举证责任分配（候选）'
    })[t] || t;
  }

  // 6658 吊顶案·冒名诉讼主轴 预设（civ_143 e2 存疑）
  function preset_6658() {
    return buildSubsumption('civ_143',
      { e1: STATUS.SAT, e2: STATUS.DOUBT, e3: STATUS.SAT },
      { facts: {
          e1: '刘九零、刘维为完全民事行为能力人；丁戊祥（营业执照92520330MACJE5T94X）系登记经营者',
          e2: '起诉状署名"丁茂祥"，与营业执照"丁戊祥"姓名不一致（第14位身份证号为5），授权委托意思表示是否真实存争点；2026-07-14/08-24通话录音已在庭上播放待采信',
          e3: '标的为吊顶采购，不违反强制性规定及公序良俗'
        },
        note: '6658吊顶案·冒名诉讼程序战主轴：143条"意思表示真实"要件涵摄'
      });
  }

  /* --------------------- 争议焦点 → 要件选择（③ disputeFocus 驱动） ---------------------
   * 给定一段争议焦点/事实描述，自动解析出候选法条 key（短关键词命中打分），返回候选与首选。
   * 全链路【候选·待人工确认】，不替用户拍板诉求性质。 */
  const FOCUS_KEYWORDS = {
    civ_143:  ['效力', '有效', '无效', '意思表示', '欺诈', '胁迫', '重大误解', '冒名', '撤销'],
    civ_153:  ['无效', '强制规定', '公序良俗', '违背'],
    civ_577:  ['违约', '不履行', '逾期', '迟延', '瑕疵履行', '违约金', '赔偿', '继续履行'],
    civ_465:  ['相对性', '第三人', '实际买受人', '挂靠', '非当事人'],
    civ_770:  ['承揽', '定作', '加工', '交付成果', '任意解除'],
    civ_787:  ['任意解除', '承揽', '定作人'],
    civ_793:  ['建工', '施工', '资质', '招投标', '折价补偿', '验收'],
    civ_1165: ['侵权', '过错', '损害', '医疗', '交通事故', '精神损害', '加害'],
    ms2023_67: ['举证', '谁主张', '真伪不明'],
    ms2023_68: ['举证期限', '逾期', '训诫'],
    ms2023_71: ['质证', '出示', '证据'],
    evid_53:  ['释明', '焦点', '法律关系性质', '效力认定不一致']
  };

  function focusKeywordsFor(key, m) {
    if (FOCUS_KEYWORDS[key]) return FOCUS_KEYWORDS[key];
    // 动态模型兜底：取标题 + 各要件 satisfiedBy 作为关键词
    const set = new Set([m.title]);
    (m.elements || []).forEach(el => (el.satisfiedBy || []).forEach(s => set.add(s)));
    return Array.from(set);
  }

  function resolveDisputeFocus(focusText, opts) {
    opts = opts || {};
    const t = (focusText || '').toLowerCase();
    const cands = [];
    Object.keys(ELEMENT_MODELS).forEach(key => {
      const m = ELEMENT_MODELS[key];
      const kws = focusKeywordsFor(key, m);
      let score = 0; const hits = [];
      kws.forEach(k => {
        const w = (k || '').toLowerCase();
        if (w && t.includes(w)) { score++; if (hits.indexOf(k) < 0) hits.push(k); }
      });
      if (score > 0) cands.push({
        key,
        label: m.law + ' ' + m.article + ' · ' + m.title,
        score,
        hits: hits.slice(0, 6),
        domain: m.title
      });
    });
    cands.sort((a, b) => b.score - a.score);
    const primary = cands[0] || null;
    return { input: focusText, candidates: cands, primaryKey: primary ? primary.key : null, primary };
  }

  // 高层入口：争议焦点 → 解析首选法条 → 直接生成要件涵摄推理链
  function buildFromDisputeFocus(focusText, findings, opts) {
    opts = opts || {};
    const res = resolveDisputeFocus(focusText, opts);
    if (!res.primaryKey) {
      return { error: '未能从争议焦点解析出可用要件模型：' + focusText, tag: '【候选·待人工确认】' };
    }
    const d = buildSubsumption(res.primaryKey, findings || {}, opts);
    d.disputeFocus = focusText;
    d.focusResolution = { primaryKey: res.primaryKey, candidates: res.candidates.map(c => c.key) };
    return d;
  }

  return {
    ELEMENT_MODELS,
    listStatutes,
    getModel,
    buildSubsumption,
    buildXinZheng,
    STATUS,
    classifyEvidence,
    conclusionTypeLabel,
    computeAmountGate,
    amountScaleHints,
    AMOUNT_RELEVANT,
    resolveDisputeFocus,
    buildFromDisputeFocus,
    preset_6658
  };
});
