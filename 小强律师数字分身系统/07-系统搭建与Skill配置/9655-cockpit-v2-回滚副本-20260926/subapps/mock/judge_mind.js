/*
 * judge_mind.js — 法官心智·红蓝推演裁决内核（参与智能体）
 * ---------------------------------------------------------------------------
 * 定位：把"法官心智"从独立的裁判/审查面板，升级为「红蓝对抗推演」的
 *       **参与智能体**——对每一轮红蓝攻防做心证判定、对争点做双方对抗裁决、
 *       推演终局生成「拟裁判要旨（候选·待人工确认）」，并接入 LTI 五维 QC 门禁。
 *
 * 设计原则（继承 R2 安全铁律 + judge_reviewer_entity_design.md 红线）：
 *   ① AI 仅产出候选推理与阶段性心证，绝不下终局裁判结论；
 *   ② 所有输出强制标注【候选·待人工确认】；
 *   ③ 心证须写理由，禁写「显然」「当然」（由 LTI QC P2 门禁兜底）；
 *   ④ 举证负担提示遵循「谁主张谁举证 + 本证高度盖然性/反证动摇心证」（民诉法解释108）。
 *
 * v2（B 方案）：推演裁决内核接入 JUDGE_CARDS 审判要件卡矩阵 ——
 *   以审判要件卡的「正向规则(support/points) + 常见误区(pitfall)」为语义基准，
 *   校准每条攻防的采信度，并使法官心证/拟裁判要旨带卡源可追溯。
 *   分支隔离：未传入 cards（opts.cards 为空）时，完全退回 v1 纯启发式，向后兼容。
 *
 * 该模块为纯函数 UMD：Node(require) 与 浏览器(window.JUDGE_MIND) 双形态可用，
 * 以便被 eval_suite.js 客观断言、被中台 HTML 直接消费。
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.JUDGE_MIND = factory();
})(typeof self !== 'undefined' ? self : this, function () {

  /* ============================ 心证倾向映射 ============================ */
  const XIN_TENDENCY = {
    blue: '倾向蓝队（被告）',
    red: '倾向红队（原告）',
    pending: '待证·真伪不明',
    mixed: '双方各有胜负·需综合评判'
  };

  /* ============================ 卡片索引（缓存） ============================ */
  // 审判要件卡是「正向裁判规则 + 常见误区」基准卡（favor 多为中立），
  // 故不依 favor 定倾向，而依 support/points（正向）/ pitfall（反向）校准采信。
  const _cardIdx = new Map(); // id -> 预切分索引
  function _prep(card) {
    if (_cardIdx.has(card.id)) return _cardIdx.get(card.id);
    const cut = s => (s || '').split(/[。.\n；;]/).map(x => x.replace(/[^一-龥]/g, '')).filter(x => x.length >= 4);
    const idx = {
      sup: cut(card.support).concat(cut(card.points)),        // 正向规则句（≥4字）
      pit: cut(card.pitfall),                                  // 常见误区句（≥4字）
      lawNums: (card.law || '').match(/第\s*(\d+)\s*条/gi) || [],
      nameTok: _tokens(card.name || ''),                       // 名称 3-4 字 token
      domain: (card.domain || '').replace(/[^一-龥]/g, '')
    };
    _cardIdx.set(card.id, idx);
    return idx;
  }
  // 取中文 3-4 字滑窗 token（过滤过短/过宽，作为名称特异性匹配锚）
  function _tokens(s) {
    const clean = (s || '').replace(/[^一-龥]/g, '');
    const out = [];
    for (let n = 4; n >= 3; n--)
      for (let i = 0; i + n <= clean.length; i++) out.push(clean.substr(i, n));
    return out;
  }
  // arg 是否包含某句子的任意连续 4 字片段（语义近似代理，用于相关性入选）
  function _sentHit(arg, sentences) {
    for (const s of (sentences || [])) {
      for (let i = 0; i + 4 <= s.length; i++) {
        if (arg.includes(s.substr(i, 4))) return true;
      }
    }
    return false;
  }
  // 通用 4 字结构词黑名单：出现在绝大多数卡中，不足以表明方向，匹配时跳过
  const COMMON4 = new Set([
    '保险合', '险合同', '投保人', '被保险', '当事人', '合同法', '民法典', '民诉法', '人民法',
    '合同纠', '同纠纷', '营业执', '分支机', '诉讼主', '依据法', '应当依', '对于本', '关于本',
    '以及', '其他', '下列', '本条', '第一', '第二', '可以', '应当', '但是', '如果', '关于', '对于'
  ]);
  // 方向判断：arg 是否复述了某句子的「非通用 4 字规则短语」（防通用词误判为复述规则）
  function _ruleHit(arg, sentences) {
    for (const s of (sentences || [])) {
      const clean = s.replace(/[^一-龥]/g, '');
      for (let i = 0; i + 4 <= clean.length; i++) {
        const w = clean.substr(i, 4);
        if (COMMON4.has(w)) continue;
        if (arg.includes(w)) return true;
      }
    }
    return false;
  }
  // 从卡片 law 中提取「第X条」数字，要求 arg 出现「第X条」才视为命中（防误中裸数字）
  function _lawHit(arg, lawNums) {
    for (const ln of (lawNums || [])) {
      const m = ln.match(/(\d+)/);
      if (m && arg.includes('第' + m[1] + '条')) return true;
    }
    return false;
  }

  /**
   * 文本 → 关联审判要件卡（v2 矩阵接入核心匹配器）。
   * 入选条件：须含「特异性信号」(名称token / 法条号 / 正向规则句) 之一，且综合相关度≥4，
   *           避免仅凭 domain 泛化命中。
   * @returns {array} 命中的卡片对象数组
   */
  function matchCards(text, cards) {
    if (!cards || !cards.length) return [];
    const t = (text || '').replace(/[^一-龥]/g, '');
    if (!t) return [];
    const matched = [];
    for (const c of cards) {
      const idx = _prep(c);
      let rel = 0;
      let specific = false;
      const dom2 = idx.domain.substr(0, 2);
      if (dom2 && t.includes(dom2)) rel += 2;                          // 案由域弱信号
      for (const tok of idx.nameTok) { if (t.includes(tok)) { rel += 3; specific = true; break; } }
      if (_lawHit(t, idx.lawNums)) { rel += 3; specific = true; }
      // 入选仅依「名称/法条」特异性信号，避免通用词(sup/pit)泛化误选；
      // sup/pit 仅用于下方 _cardAdj 的方向校准（_ruleHit 非通用窗）。
      if (specific && rel >= 4) matched.push(c);
    }
    return matched;
  }

  /**
   * 单条攻防命中卡片后的采信校准：正向规则加分、踩坑(pitfall)降权。
   * 方向判定用连续 5 字强匹配；仅明确命中 support/pitfall 才计分，通用词相关不计分。
   * @returns {object} {adj, hitSup, hitPit}
   */
  function _cardAdj(arg, cards) {
    const m = matchCards(arg, cards);
    if (!m.length) return { adj: 0, hitSup: [], hitPit: [] };
    const ac = (arg || '').replace(/[^一-龥]/g, '');
    let adj = 0; const hitSup = [], hitPit = [];
    for (const c of m) {
      const idx = _prep(c);
      const sHit = _ruleHit(ac, idx.sup);   // 复述正向规则短语
      const pHit = _ruleHit(ac, idx.pit);   // 复述常见误区短语
      if (pHit) { adj -= 0.7; hitPit.push(c.id); }             // 踩中误区 → 降权（最高优先级）
      else if (sHit) { adj += 0.5; hitSup.push(c.id); }        // 陈述正向规则 → 强化
      // 仅相关但不复述正/误规则 → 不计分（避免通用词误加成）
    }
    return { adj, hitSup, hitPit };
  }

  /* ============================ 单条攻防心证判定 ============================ */
  /**
   * 法官对一条攻防/主张的心证判定（候选）。
   * v2：若传入 opts.cards，引入审判要件卡矩阵校准。
   * @param {string} arg 攻防/主张文本
   * @param {object} opts {side:'blue'|'red', focus, cards}
   * @returns {object} {arg, verdict, score, reason, tag}
   *   verdict ∈ {采信, 部分采信, 存疑, 不采信}
   */
  function assessArgument(arg, opts) {
    opts = opts || {};
    const t = (arg || '').toLowerCase();
    let score = 0; const signals = [];

    // —— 证据支撑信号（强信号，权重最高）——
    const eviKw = ['证据', '录音', '鉴定', '签字', '收据', '合同', '协议', '微信', '照片', '录像', '判决书', '发票', '笔录', '函', '通知', '对账单'];
    eviKw.forEach(k => { if (t.includes(k)) { score += 1.0; signals.push('有证据指向·' + k); } });

    // —— 法理规范信号（中信号）——
    const lawKw = ['民法典', '民诉法', '第', '条', '相对性', '代理', '授权', '追认', '意思', '要件', '举证', '高度盖然', '过错', '无效', '合同效力', '承揽'];
    lawKw.forEach(k => { if (t.includes(k)) { score += 0.5; signals.push('援引规范·' + k); } });

    // —— 质疑/反证信号（攻击强度，体现"反证只需动摇心证"）——
    const atkKw = ['无', '不', '未', '缺', '矛盾', '不符', '错', '否认', '未闭合', '未提供', '无依据', '无闭合', '未形成'];
    atkKw.forEach(k => { if (t.includes(k)) { score += 0.3; signals.push('质疑点·' + k); } });

    // —— v2：审判要件卡矩阵校准（分支隔离，无 cards 完全退回原启发式）——
    if (opts.cards && opts.cards.length) {
      const ca = _cardAdj(arg, opts.cards);
      if (ca.hitSup.length || ca.hitPit.length) {
        score += ca.adj;
        if (ca.hitPit.length) signals.push('审判要件卡·' + ca.hitPit.join('/') + '（踩坑降权）');
        if (ca.hitSup.length) signals.push('审判要件卡·' + ca.hitSup.join('/') + '（正向规则强化）');
      }
    }

    // —— 心证判定阈值（与 v1 一致，保证向后兼容）——
    let verdict;
    if (score >= 2.6) verdict = '采信';
    else if (score >= 1.6) verdict = '部分采信';
    else if (score >= 0.8) verdict = '存疑';
    else verdict = '不采信';

    return {
      arg: arg,
      verdict,
      score: +score.toFixed(2),
      reason: '信号：' + (signals.join('；') || '无明显证据/规范信号'),
      side: opts.side || null,
      tag: '【候选·待人工确认】'
    };
  }

  /* ============================ 单争点对抗裁决 ============================ */
  /**
   * 对一个争点，综合蓝队立论与红队攻击，给出法官阶段性心证（候选）。
   * v2：传入 cards 时，额外给出焦点关联的审判要件卡与卡片依据叙述。
   * @param {string} focus 争点描述
   * @param {string[]} blueArgs 蓝队（被告）立论/防守
   * @param {string[]} redArgs 红队（原告）攻击/主张
   * @param {object} opts {burden, cards}
   */
  function assessDispute(focus, blueArgs, redArgs, opts) {
    opts = opts || {};
    const cards = opts.cards || null;
    const blue = (blueArgs || []).map(a => assessArgument(a, { side: 'blue', cards }));
    const red = (redArgs || []).map(a => assessArgument(a, { side: 'red', cards }));
    const blueStrong = blue.filter(x => x.verdict === '采信' || x.verdict === '部分采信').length;
    const redStrong = red.filter(x => x.verdict === '采信' || x.verdict === '部分采信').length;

    let tendency;
    if (blueStrong > redStrong) tendency = 'blue';
    else if (redStrong > blueStrong) tendency = 'red';
    else if (blueStrong === 0 && redStrong === 0) tendency = 'pending';
    else tendency = 'mixed';

    const burdenNote = opts.burden ||
      '依"谁主张谁举证"原则分配；本证须达高度盖然性，反证只需动摇法官心证（《民诉法解释》第108条）。';

    // —— v2：焦点关联审判要件卡 + 卡片依据叙述 ——
    let focusCards = [];
    let cardRationale = '';
    let pitfallHits = [];
    if (cards && cards.length) {
      focusCards = matchCards(focus, cards).map(c => ({ id: c.id, name: c.name, domain: c.domain, favor: c.favor }));
      // 汇总双方 arg 踩中的误区卡
      [...blue, ...red].forEach(x => {
        const ca = _cardAdj(x.arg, cards);
        if (ca.hitPit.length) pitfallHits.push({ side: x.side, arg: x.arg, cards: ca.hitPit });
      });
      if (focusCards.length) {
        const names = focusCards.slice(0, 5).map(c => c.id + '《' + (c.name || '') + '》').join('、');
        cardRationale = '【候选·待人工确认】本争点关联审判要件卡 ' + focusCards.length + ' 张（' + names +
          '）。法官应依其要件框架审查，并防范卡片列明的常见误区（pitfall）。';
      }
    }

    return {
      focus,
      blueJudge: blue,
      redJudge: red,
      blueStrong,
      redStrong,
      tendency,
      tendencyLabel: XIN_TENDENCY[tendency],
      burden: burdenNote,
      note: '【候选·待人工确认】法官对本争点的阶段性心证：' + XIN_TENDENCY[tendency] + '。',
      tag: '【候选·待人工确认】',
      focusCards,
      cardRationale,
      pitfallHits
    };
  }

  /* ============================ 拟裁判要旨（候选） ============================ */
  /**
   * 整合多争点评判 + 要件涵摄 + 心证档案，生成拟裁判要旨（候选·待人工确认）。
   * v2：争点评判段引用关联审判要件卡；末尾新增「审判要件卡援引」段。
   * @param {object} opts {disputes[], focusList[], sub, xz[]}
   */
  function renderVerdictDraft(opts) {
    opts = opts || {};
    const disputes = opts.disputes || [];
    const focusList = opts.focusList || [];
    const sub = opts.sub || null;
    const xz = opts.xz || [];

    let txt = '【拟裁判要旨（候选·待人工确认 · R2 · 非终局结论）】\n';

    if (focusList.length) {
      txt += '本案争点归纳：' + focusList.join('；') + '。\n';
    }
    if (disputes.length) {
      txt += '\n一、争点评判（法官心智·候选）\n';
      disputes.forEach((d, i) => {
        const f = d.focus || ('争点' + (i + 1));
        txt += `  （${i + 1}）${f}：本庭阶段性心证${d.tendencyLabel || ''}。\n`;
        txt += `      蓝队立论采信任数 ${d.blueStrong || 0}，红队攻击采信任数 ${d.redStrong || 0}。\n`;
        if (d.burden) txt += `      ${d.burden}\n`;
        // v2：引用关联审判要件卡
        if (d.focusCards && d.focusCards.length) {
          txt += `      关联审判要件卡：${d.focusCards.map(c => c.id).join('、')}（依正向裁判规则·候选）。\n`;
        }
      });
    }
    if (sub && sub.conclusionType) {
      const map = {
        'effect-established': '责任成立',
        'effect-failed': '责任不成立',
        'pending-burden': '举证责任未卸除·待证',
        'some-doubt': '部分要件存疑'
      };
      const gateNote = (sub.amountGate && sub.amountGate.enabled) ? '（已进入 §F 数额研判）' : '';
      txt += '\n二、要件涵摄结论（候选）\n  ' + (map[sub.conclusionType] || sub.conclusionType) + gateNote + '。\n';
    }
    if (xz && xz.length) {
      txt += '\n三、已记录心证档案\n';
      xz.forEach(x => { txt += `  · ${x.tendency || ''}：${x.note || ''}\n`; });
    }
    // v2：审判要件卡援引段（全案去重）
    const allCards = [...new Set(disputes.flatMap(d => (d.focusCards || []).map(c => c.id)))];
    if (allCards.length) {
      txt += '\n四、审判要件卡援引（候选·待人工确认）\n  ' + allCards.join('、') +
        ' —— 以上卡片构成本案推演裁决的「正向裁判规则」基准，仅供老强研判参考。\n';
    }
    txt += '\n⚠️ 以上为 AI 法官心智依"正向裁判规则（审判要件卡矩阵）+ 要件模型 + 心证档案"生成的候选推演结论，仅供老强研判参考，绝不替代终局裁判。\n';
    return txt;
  }

  /* ============================ 整场推演裁决 ============================ */
  /**
   * 消费红蓝推演态势（assault3.rounds），把每轮当作一个争点对抗单元，
   * 逐轮裁决后汇总拟裁判要旨，并接入 LTI 五维 QC 门禁（如有）。
   * v2：自动接入 JUDGE_CARDS 矩阵（opts.cards 或浏览器 window.__JUDGE_CARDS_IMPORT__）。
   * @param {object} opts {rounds[], disputeFocus, sub, xz[], docText, cards}
   * @returns {object} {disputes, draft, tendencySummary, qc, tag}
   */
  function runTrialJudge(opts) {
    opts = opts || {};
    const rounds = opts.rounds || [];
    const disputeFocus = (opts.disputeFocus || '').toString().trim();
    const sub = opts.sub || null;
    const xz = opts.xz || [];
    const docText = opts.docText || '';

    // —— v2：接入审判要件卡矩阵（显式优先，浏览器兜底自动挂载源）——
    let cards = opts.cards || null;
    if (!cards && typeof window !== 'undefined') {
      cards = window.JUDGE_CARDS || window.__JUDGE_CARDS_IMPORT__ || null;
    }

    const disputes = rounds.map(r => {
      const focus = (r.focus) || ('第 ' + (r.round != null ? r.round : '?') + ' 轮对抗');
      const blueArgs = r.blueDef || [];
      const redArgs = r.redAtk || [];
      return assessDispute(focus, blueArgs, redArgs, { burden: r.burden, cards });
    });

    const focusList = [];
    if (disputeFocus) focusList.push(disputeFocus);
    disputes.forEach(d => { if (d.focus && d.focus.indexOf('轮对抗') < 0) focusList.push(d.focus); });

    const draft = renderVerdictDraft({ disputes, focusList: Array.from(new Set(focusList)), sub, xz });

    // —— 接入 LTI 五维 QC 门禁（若前端校验器可用）——
    let qc = null;
    try {
      if (typeof window !== 'undefined' && window.LTI_QC && typeof window.LTI_QC.runQC === 'function') {
        qc = window.LTI_QC.runQC({ sub, docText: docText || draft, evidence: opts.evidence || [], models: opts.models || {} });
      } else if (typeof require !== 'undefined') {
        const LTI = require('./lti_qc.js');
        qc = LTI.runQC({ sub, docText: docText || draft, evidence: opts.evidence || [], models: opts.models || {} });
      }
    } catch (e) { qc = { error: String(e && e.message || e) }; }

    return {
      disputes,
      draft,
      focusList: Array.from(new Set(focusList)),
      tendencySummary: disputes.map(d => ({ focus: d.focus, tendency: d.tendency, tendencyLabel: d.tendencyLabel })),
      qc,
      tag: '【候选·待人工确认】'
    };
  }

  return {
    XIN_TENDENCY,
    matchCards,
    assessArgument,
    assessDispute,
    renderVerdictDraft,
    runTrialJudge
  };
});
