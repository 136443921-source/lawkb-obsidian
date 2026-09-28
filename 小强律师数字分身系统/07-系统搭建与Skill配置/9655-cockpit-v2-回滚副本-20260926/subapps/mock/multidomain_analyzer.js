/* ============================================================================
 * multidomain_analyzer.js — 路B 重 agent：多域竞合深度研判（纯离线·候选·R2）
 * ----------------------------------------------------------------------------
 * 定位：Path B 文书/主持智能体的"争点研判内核"。给定一段争议描述（或争议焦点），
 *      ① 识别涉及的**法律域**（合同效力 / 违约 / 相对性 / 承揽 / 建工 / 侵权 / 证据程序）；
 *      ② 判定各域之间的**竞合关系**（责任竞合 / 先决吸收 / 牵连 / 独立 / 排斥）；
 *      ③ 产出**结构化深度研判**（候选主路径 + 替代路径 + 须先决事项 + 候选建议）。
 *
 * 设计铁律（继承 R2 红线）：
 *   1. 只给候选：所有结论带【候选·待人工确认】，严禁 verdict / win_prob。
 *   2. 离线可用：纯 JS 不联网；域→法条映射取自引擎 ELEMENT_MODELS 口径。
 *   3. 教义化：竞合关系依据通说与民法典明文（如第186条责任竞合），不凭记忆编造。
 *   4. 只读：不写回 LawKB / statute_cache。
 *
 * 双形态：Node(module.exports) + 浏览器(window.MDA)。
 * ========================================================================== */

(function (root, factory) {
  const api = factory(typeof require !== 'undefined' ? require : null);
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined') window.MDA = api;
})(this, function (requireFn) {

  /* ----------------------------- 法律域分类法 -----------------------------
   * 每个域含：label 域标签 / keywords 触发关键词（命中即计分）/ statuteKeys 该域对应要件模型 key
   * 注意：statuteKeys 仅列 ELEMENT_MODELS 中真实存在的 key，保证「→要件涵摄」可落地。
   * ---------------------------------------------------------------------- */
  const DOMAIN_TAXONOMY = {
    contract_validity: {
      label: '合同效力',
      statuteKeys: ['civ_143', 'civ_153'],
      keywords: ['效力', '有效', '无效', '生效', '意思表示', '欺诈', '胁迫', '重大误解',
                 '冒名', '虚假', '撤销', '可撤销', '强制性规定', '公序良俗']
    },
    breach: {
      label: '违约责任',
      statuteKeys: ['civ_577'],
      keywords: ['违约', '不履行', '逾期', '迟延', '瑕疵履行', '拒绝履行', '违约金',
                 '赔偿损失', '继续履行', '补救措施', '交付']
    },
    relativity: {
      label: '合同相对性',
      statuteKeys: ['civ_465'],
      keywords: ['相对性', '第三人', '实际买受人', '突破相对性', '挂靠', '合同外', '非当事人']
    },
    undertaking: {
      label: '承揽关系',
      statuteKeys: ['civ_770', 'civ_787'],
      keywords: ['承揽', '定作', '加工', '完成工作', '交付成果', '任意解除', '报酬']
    },
    construction: {
      label: '建工合同',
      statuteKeys: ['civ_793'],
      keywords: ['建设工程', '施工', '资质', '招投标', '折价补偿', '验收合格', '发包', '承包']
    },
    tort: {
      label: '过错侵权',
      statuteKeys: ['civ_1165'],
      keywords: ['侵权', '过错', '损害', '人身', '医疗', '交通事故', '财产损害',
                 '精神损害', '加害', '赔偿权利人']
    },
    evidence_procedure: {
      label: '证据与程序',
      statuteKeys: ['ms2023_67', 'ms2023_68', 'ms2023_71', 'evid_53'],
      keywords: ['举证', '质证', '证据', '释明', '争议焦点', '举证期限', '真伪不明',
                 '高度盖然性', '自认', '焦点审理']
    }
  };

  /* ----------------------- 域间竞合关系矩阵（教义） -----------------------
   * 关系类型：
   *   concurrence 竞合   —— 同一事实满足多域要件，权利人择一主张（民法典第186条责任竞合等）
   *   prerequisite 先决  —— A 是 B 的前提，须先解决 A 再论 B（如效力先于违约）
   *   connected   牵连   —— 论证时一并考量，但非竞合非先决
   *   absorb      吸收   —— 特别法优先 / 一域吸收另一域（如建工吸收于承揽）
   *   independent 独立   —— 各论各的，互不干扰
   *   exclusive   排斥   —— 成立其一则排除另一（如侵权不采合同相对性）
   * basis：教义/法条依据（候选引用）。 */
  const RELATION_MATRIX = {
    'breach|tort': {
      type: 'concurrence',
      basis: '民法典第186条：因当事人一方的违约行为，损害对方人身、财产权益的，受损害方有权选择请求其承担违约责任或者侵权责任。',
      note: '责任竞合，受损害方应择一主张，避免双重获利；择一后不得再主张另一路径。'
    },
    'contract_validity|breach': {
      type: 'prerequisite',
      basis: '合同有效是违约责任的前提；无效合同不生违约，转为缔约过失或返还（民法典第157条）。',
      note: '须先审查合同效力，效力不成立则违约责任路径落空。'
    },
    'contract_validity|relativity': {
      type: 'connected',
      basis: '合同效力与相对性均围绕合同关系展开，效力影响相对性突破的正当性。',
      note: '论证相对性突破时，先确认合同效力状态。'
    },
    'relativity|breach': {
      type: 'connected',
      basis: '违约责任以相对性为基础，但可向实际买受人突破（如买卖挂靠）。',
      note: '向非署名当事人主张违约时，须论证相对性突破事由。'
    },
    'undertaking|construction': {
      type: 'absorb',
      basis: '民法典第808条：建设工程合同章没有规定的，适用承揽合同有关规定；建工为承揽特殊形态。',
      note: '建工优先适用建工专章，无规定时回承揽；定性时二选一为主。'
    },
    'breach|undertaking': {
      type: 'connected',
      basis: '承揽违约同样适用违约责任一般规定（民法典第577条）。',
      note: '承揽关系下的违约，一并考量承揽专属规则与违约一般规则。'
    },
    'tort|undertaking': {
      type: 'concurrence',
      basis: '承揽物致害可能同时构成违约（瑕疵担保）与侵权（缺陷致害），权利人择一。',
      note: '承揽成果致害时，注意违约与侵权竞合。'
    },
    'evidence_procedure|*': {
      type: 'independent',
      basis: '证据与程序规则为事实认定基础，贯穿各域，不与实体域竞合。',
      note: '证据程序域为各路径共同前置，单列考量。'
    },
    'relativity|tort': {
      type: 'exclusive',
      basis: '侵权责任不采合同相对性，向侵权人（无论是否合同当事人）主张。',
      note: '侵权路径下相对性抗辩通常不成立。'
    },
    'construction|contract_validity': {
      type: 'prerequisite',
      basis: '建工合同效力（资质/招投标合规）先于折价补偿等责任判断。',
      note: '先审查施工合同效力，再论折价补偿。'
    }
  };

  // 规范化一对域 key 为稳定查询串（无序）
  function pairKey(a, b) {
    return [a, b].sort().join('|');
  }

  // 规范化关系矩阵键（统一按字母序，避免 a|b 与 b|a 写法不一致导致漏配）
  const RELATION_LOOKUP = {};
  Object.keys(RELATION_MATRIX).forEach(k => {
    RELATION_LOOKUP[k.split('|').sort().join('|')] = RELATION_MATRIX[k];
  });

  function relationBetween(domA, domB) {
    if (domA === domB) return { type: 'self', basis: '', note: '同一域。' };
    const direct = RELATION_LOOKUP[pairKey(domA, domB)];
    if (direct) return direct;
    // 通配：任一方为 evidence_procedure 视为独立
    if (domA === 'evidence_procedure' || domB === 'evidence_procedure') {
      const w = RELATION_MATRIX['evidence_procedure|*'];
      return { type: w.type, basis: w.basis, note: w.note };
    }
    // 默认：无明确竞合 → 独立（不臆造关系）
    return { type: 'independent', basis: '', note: '两域无明文竞合关系，按各自要件独立审查。' };
  }

  const RELATION_LABEL = {
    concurrence: '责任竞合 · 择一主张',
    prerequisite: '先决关系 · 须先审查',
    connected: '牵连关系 · 一并考量',
    absorb: '吸收关系 · 特别法优先',
    independent: '相互独立 · 各论各的',
    exclusive: '相互排斥 · 成立其一排除另一',
    self: '同一域'
  };

  // 域优先级（同分时 deterministic 且教义上优先审查靠前域：先合同效力，后违约/侵权…）
  const DOMAIN_PRIORITY = [
    'contract_validity', 'breach', 'relativity', 'undertaking',
    'construction', 'tort', 'evidence_procedure'
  ];

  /* ----------------------------- 域识别打分 ----------------------------- */
  function detectDomains(text) {
    const t = (text || '').toLowerCase();
    const scored = [];
    Object.keys(DOMAIN_TAXONOMY).forEach(dom => {
      const tx = DOMAIN_TAXONOMY[dom];
      let hits = [], score = 0;
      tx.keywords.forEach(k => {
        // 中文关键词直接包含匹配；统计命中次数加权
        if (t.includes(k.toLowerCase())) { hits.push(k); score += 1; }
      });
      if (score > 0) {
        scored.push({
          domain: dom,
          label: tx.label,
          statuteKeys: tx.statuteKeys.slice(),
          score,
          prio: DOMAIN_PRIORITY.indexOf(dom),
          hits: Array.from(new Set(hits))
        });
      }
    });
    scored.sort((a, b) => b.score - a.score || a.prio - b.prio);
    return scored;
  }

  /* ------------------------- 多域竞合深度研判 ------------------------- */
  function analyzeConcurrence(text, opts) {
    opts = opts || {};
    const topN = opts.topN || 4;
    const domains = detectDomains(text);
    if (!domains.length) {
      return {
        input: text,
        domains: [],
        primary: null,
        relations: [],
        recommendation: '【候选·待人工确认】未识别到明确法律域，请补充争议事实（如"合同违约""侵权损害""合同效力"等关键词）后再研判。',
        tag: '【候选·待人工确认】'
      };
    }
    const top = domains.slice(0, topN);
    const primary = top[0];

    // 两两关系（在 top 内）
    const relations = [];
    for (let i = 0; i < top.length; i++) {
      for (let j = i + 1; j < top.length; j++) {
        const a = top[i], b = top[j];
        const rel = relationBetween(a.domain, b.domain);
        relations.push({
          a: a.label, b: b.label,
          aDomain: a.domain, bDomain: b.domain,
          type: rel.type,
          typeLabel: RELATION_LABEL[rel.type] || rel.type,
          basis: rel.basis,
          note: rel.note
        });
      }
    }

    // 关系聚合（生成候选建议）
    const concurrence = relations.filter(r => r.type === 'concurrence');
    const prerequisite = relations.filter(r => r.type === 'prerequisite');
    const absorb = relations.filter(r => r.type === 'absorb');
    const exclusive = relations.filter(r => r.type === 'exclusive');
    const connected = relations.filter(r => r.type === 'connected');

    const recParts = [];
    recParts.push(`依争议描述，识别到 ${domains.length} 个候选法律域，建议以【${primary.label}】为主路径（匹配度 ${primary.score}，关键词：${primary.hits.join('、')}），其要件涵摄见 ${primary.statuteKeys.join('、')} 等条。`);
    if (prerequisite.length) {
      recParts.push(`须先解决：${prerequisite.map(r => `【${r.a}】与【${r.b}】为先决关系（${r.note}）`).join('；')}。`);
    }
    if (concurrence.length) {
      recParts.push(`注意竞合：${concurrence.map(r => `【${r.a}】与【${r.b}】构成${r.typeLabel}（${r.basis}${r.note}）`).join('；')}。`);
    }
    if (absorb.length) {
      recParts.push(`吸收关系：${absorb.map(r => `【${r.a}】与【${r.b}】${r.note}`).join('；')}。`);
    }
    if (exclusive.length) {
      recParts.push(`排斥关系：${exclusive.map(r => `【${r.a}】与【${r.b}】${r.note}`).join('；')}。`);
    }
    if (connected.length) {
      recParts.push(`牵连考量：${connected.map(r => `【${r.a}】与【${r.b}】${r.note}`).join('；')}。`);
    }
    recParts.push('以上为机器候选研判，供律师人工确认争点范围与诉讼/抗辩路径，不构成任何确定性结论。');

    const recommendation = '【候选·待人工确认】' + recParts.join('');

    return {
      input: text,
      domains: domains.map(d => ({ domain: d.domain, label: d.label, score: d.score, hits: d.hits, statuteKeys: d.statuteKeys })),
      primary: { domain: primary.domain, label: primary.label, score: primary.score, statuteKeys: primary.statuteKeys, hits: primary.hits },
      relations,
      concurrenceCount: concurrence.length,
      prerequisiteCount: prerequisite.length,
      recommendation,
      tag: '【候选·待人工确认】'
    };
  }

  return {
    DOMAIN_TAXONOMY,
    RELATION_MATRIX,
    RELATION_LABEL,
    detectDomains,
    relationBetween,
    analyzeConcurrence
  };
});
