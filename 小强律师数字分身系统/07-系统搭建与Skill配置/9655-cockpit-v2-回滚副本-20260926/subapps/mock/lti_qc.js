/* ============================================================================
 * lti_qc.js — LTI 五维 QC 前端校验器（R / L / C / T / P）
 * ----------------------------------------------------------------------------
 * 定位：在「模拟法官」交付候选稿前，对生成的要件涵摄结果（sub）与可选文书
 *      （docText）做五维质量门禁校验，输出 REJECT 计数；REJECT=0 才准交付
 *      （遵循老强「LTI 五维 QC(R/L/C/T/P)·REJECT=0 才准交付」铁律）。
 *
 * 五维：
 *   R 法条真实性  — 引用法条存在 × 可溯源北大法宝 × 无待回源标记
 *   L 法理逻辑    — 结论类型与要件状态自洽 × §F 数额门控被尊重 × 心证倾向不矛盾
 *   C 一致性      — C301 金额（585条30%参考·候选标注）/ C302 名称占位 / C304 案号
 *   T 溯源        — 建议证据可溯源 × 文书引用证据编号须落在卷宗登记 × 人工在环标记
 *   P 程序        — R2 红线（无 verdict/win_prob）× 禁绝对词 × 举证程序完备
 *
 * 双形态：Node(module.exports) + 浏览器(window.LTI_QC)。纯函数，零 DOM 依赖。
 * 铁律：本模块不硬编码任何法条正文；只基于传入的 sub / docText / 卷宗登记 校验。
 * ========================================================================== */
(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window !== 'undefined') window.LTI_QC = api;
})(typeof self !== 'undefined' ? self : this, function () {

  // —— 金额预估纯函数（供 amCalc 复用，便于单测）——
  // 民法典第585条：违约金一般以超损失 30% 为酌减参考（候选）。
  function computeAmountEstimate(liquid, loss, paid) {
    const cap = loss * 1.3;
    const hasBoth = liquid > 0 && loss > 0;
    const overCap = hasBoth && liquid > cap;
    const due = Math.max(loss - paid, 0);
    return {
      cap: cap,
      capRounded: Math.round(cap),
      overCap: overCap,
      hasBoth: hasBoth,
      due: due,
      hasLoss: loss > 0,
      hasLiquid: liquid > 0
    };
  }

  // —— 证据编号引用解析（纯函数，可单测）——
  // 从文本抽取「证N」编号，去重保序。
  function parseEvidenceRefs(text) {
    if (!text) return [];
    const re = /证\s*(\d+)/g;
    const out = [], seen = {};
    let m;
    while ((m = re.exec(text)) !== null) {
      const id = '证' + m[1];
      if (!seen[id]) { seen[id] = true; out.push(id); }
    }
    return out;
  }

  // —— 案号格式校验（2026黔0330民初6658号 形态）——
  function validateCaseNo(caseNo) {
    if (!caseNo || !caseNo.trim()) return { ok: false, reason: '未填写案号' };
    const re = /^\d{4}.*?[民刑行]初\d+号$/;
    if (!re.test(caseNo.trim())) return { ok: false, reason: '案号格式异常（应为形如「2026黔0330民初6658号」）' };
    return { ok: true, reason: '' };
  }

  // —— 五维校验主入口 ——
  // opts: { sub, docText, caseNo, evidence:[{id,name,source,...}], models:{} }
  //   sub: buildSubsumption 的返回（含 statuteKey/law/article/title/pkulawUrl/rows/
  //        conclusionType/chain/xinZheng/amountGate/tag）
  //   docText: 可选，用户粘贴的「文书草稿」纯文本（用于 C/P 维度深校）
  //   evidence: 卷宗证据登记 [{id:'证1',name,source:'卷二P45',...}]
  function runQC(opts) {
    opts = opts || {};
    const sub = opts.sub || null;
    const doc = (opts.docText || '').toString();
    const caseNo = (opts.caseNo || '').toString().trim();
    const evidence = Array.isArray(opts.evidence) ? opts.evidence : [];
    const models = opts.models || (typeof window !== 'undefined' && window.SUBSUMPTION ? window.SUBSUMPTION.ELEMENT_MODELS : null) || {};

    const checks = []; // {dim,id,label,severity,status,detail}
    function add(dim, id, label, severity, status, detail) {
      checks.push({ dim, id, label, severity, status: status || 'pass', detail: detail || '' });
    }

    const chainText = sub && sub.chain ? sub.chain.join('\n') : '';
    const fullText = chainText + '\n' + doc;
    const hasDoc = doc.trim().length > 0;

    /* ===================== R 法条真实性 ===================== */
    if (!sub) {
      add('R', 'R0', '已运行要件涵摄（存在 sub 结果）', 'reject', 'fail', '未找到要件涵摄结果，无法校验。请先生成推理链。');
    } else {
      // R1 引用法条存在于要件模型库
      const inModel = !!models[sub.statuteKey];
      add('R', 'R1', '引用法条存在于要件模型库（' + (sub.law || '') + (sub.article || '') + '）',
        'reject', inModel ? 'pass' : 'fail', inModel ? '命中本地权威要件模型。' : 'statuteKey「' + sub.statuteKey + '」不在模型库，法条真实性无法核验。');

      // R2 可溯源北大法宝（pkulawUrl）
      const hasUrl = !!(sub.pkulawUrl && sub.pkulawUrl.indexOf('pkulaw') >= 0);
      add('R', 'R2', '引用法条带北大法宝溯源链接', 'reject', hasUrl ? 'pass' : 'fail',
        hasUrl ? 'pkulawUrl 存在，可一键溯源核验。' : '缺少 pkulawUrl，无法溯源北大法宝权威文本。');

      // R3 无待回源标记
      const pendingMark = /statute_text_pending|待回源核填|权威源回填|pending/i.test(fullText);
      add('R', 'R3', '无「待回源核填 / statute_text_pending」风险标记', 'reject', pendingMark ? 'fail' : 'pass',
        pendingMark ? '文本含待回源标记，条文真实性未坐实，禁止交付。' : '未发现待回源标记。');

      // R4 结论未引用不存在的法条（链中若出现「第XXX条」需能对应；此处仅校验无空引用）
      const emptyRef = /《[^》]*》\s*第\s*条\s*（\s*）/.test(fullText) || /法条[:：]\s*$/m.test(fullText);
      add('R', 'R4', '无空法条引用占位', 'warn', emptyRef ? 'fail' : 'pass',
        emptyRef ? '存在空法条引用占位，须补全条号。' : '未见空法条引用占位。');
    }

    /* ===================== L 法理逻辑 ===================== */
    if (!sub) {
      add('L', 'L0', '存在 sub 结果', 'reject', 'fail', '无 sub，无法校验逻辑。');
    } else {
      // L1 结论类型与要件状态自洽
      const req = sub.rows.filter(r => !r.optional);
      const hasNot = req.some(r => r.status === '不满足');
      const hasDoubt = req.some(r => r.status === '存疑' || r.status === '未认定');
      let expected;
      if (hasNot) expected = 'effect-not-established';
      else if (hasDoubt) expected = 'pending-burden';
      else expected = 'effect-established';
      const logicOk = expected === sub.conclusionType;
      add('L', 'L1', '结论类型与要件状态自洽（' + sub.conclusionType + ' / 应得 ' + expected + '）',
        'reject', logicOk ? 'pass' : 'fail',
        logicOk ? '要件状态与结论类型一致。' : '结论类型与要件状态矛盾，逻辑断裂。');

      // L2 §F 数额门控被尊重（门控未解锁不得出现确定数额结论）
      const gate = sub.amountGate;
      const docAssertsAmount = /应付\s*¥|违约金为\s*¥|赔偿\s*¥\s*\d|数额为\s*¥|判赔\s*¥/i.test(doc);
      if (gate && !gate.enabled && docAssertsAmount) {
        add('L', 'L2', '§F 门控未解锁时不输出确定数额结论', 'reject', 'fail',
          '责任基础未确立（门控锁定），文书却出现确定数额主张，违反「违约责任成立才进数额」。');
      } else {
        add('L', 'L2', '§F 数额门控与文书数额断言一致', 'pass', 'pass',
          gate && gate.enabled ? '门控已解锁，可进数额。' : '无数额断言或门控未涉及数额，合规。');
      }

      // L3 心证倾向与结论类型不矛盾
      const lean = sub.xinZheng && sub.xinZheng.lean ? sub.xinZheng.lean.type : '';
      const leanMap = { 'effect-established': '成立倾向', 'effect-not-established': '不成立倾向', 'pending-burden': '真伪不明·待举证' };
      const leanOk = !lean || leanMap[sub.conclusionType] === lean;
      add('L', 'L3', '心证倾向与结论类型一致（' + lean + '）', 'reject', leanOk ? 'pass' : 'fail',
        leanOk ? '心证段与结论类型自洽。' : '心证倾向「' + lean + '」与结论类型矛盾。');

      // L4 缺口建议证据完备
      const gapsNoEv = (sub.gaps || []).filter(g => g.status === '不满足' && (!g.suggestedEvidence || !g.suggestedEvidence.length));
      add('L', 'L4', '「不满足」缺口均给出建议证据类型', 'warn', gapsNoEv.length ? 'fail' : 'pass',
        gapsNoEv.length ? gapsNoEv.length + ' 处缺口缺建议证据。' : '缺口证据建议完备。');
    }

    /* ===================== C 一致性 ===================== */
    // C301 金额：文书出现金额时须引用 585条30% 参考 或 带候选标注
    const docHasAmount = /¥\s*\d|万元|元（|元\)|\d+\s*元/.test(doc);
    if (docHasAmount) {
      const ok = /第\s*585\s*条|30%|候选|待人工确认/.test(doc);
      const gate = sub && sub.amountGate;
      if (gate && !gate.enabled) {
        add('C', 'C301', '金额断言不早于责任成立（§F 门控）', 'reject', 'fail', '文书已出现金额，但责任基础未确立，违反门控。');
      } else if (!ok) {
        add('C', 'C301', '金额断言须引用第585条30%参考或标注候选', 'warn', 'fail', '文书含金额但未见「第585条/30%/候选」标注，易致数额失焦。');
      } else {
        add('C', 'C301', '金额断言已附 585条30% 参考或候选标注', 'pass', 'pass', '金额表述合规。');
      }
    } else {
      add('C', 'C301', '文书金额表述合规（无金额 或 已附参考）', 'pass', 'pass', '未检测到需特别核验的金额断言。');
    }

    // C302 名称占位符
    const placeholder = /XXX|XX公司|某先生|某女士|［请填|请填写|某某（|某某\(/.test(doc);
    add('C', 'C302', '无名称占位符（XXX/某先生/某某）', 'warn', placeholder ? 'fail' : 'pass',
      placeholder ? '文书含占位符，交付前须替换为真实名称。' : '未见名称占位符。');

    // C304 案号：格式 + 一致性
    if (caseNo) {
      const v = validateCaseNo(caseNo);
      add('C', 'C304a', '案号格式合法（' + caseNo + '）', 'warn', v.ok ? 'pass' : 'fail', v.ok ? '案号格式合规。' : v.reason);
      // 文书内若提及案号须与登记一致
      const m = doc.match(/\d{4}.*?[民刑行]初\d+号/);
      if (m) {
        const docNo = m[0].replace(/[（）]/g, '');
        const regNo = caseNo.replace(/[（）]/g, '');
        const consistent = docNo.indexOf(regNo) >= 0 || regNo.indexOf(docNo) >= 0;
        add('C', 'C304b', '文书案号与登记案号一致', 'reject', consistent ? 'pass' : 'fail',
          consistent ? '案号一致。' : '文书案号「' + docNo + '」与登记「' + caseNo + '」不一致。');
      } else {
        add('C', 'C304b', '文书未提及案号（无需比对）', 'pass', 'pass', '');
      }
    } else {
      add('C', 'C304a', '案号已登记', 'warn', 'pass', '未登记案号，建议补全以便 C304 校验。');
    }

    /* ===================== T 溯源 ===================== */
    // T1 建议证据可溯源（缺口均有建议证据类型）
    if (sub) {
      const gapsNoEv2 = (sub.gaps || []).filter(g => !g.suggestedEvidence || !g.suggestedEvidence.length);
      add('T', 'T1', '证据缺口建议可追溯至证据类型', 'warn', gapsNoEv2.length ? 'fail' : 'pass',
        gapsNoEv2.length ? gapsNoEv2.length + ' 处缺口缺可溯源证据建议。' : '缺口均已给出证据类型建议。');
    }
    // T2 文书引用证据编号须落在卷宗登记
    const refs = parseEvidenceRefs(doc);
    if (refs.length) {
      const regIds = evidence.map(e => e.id);
      const missing = refs.filter(r => regIds.indexOf(r) < 0);
      add('T', 'T2', '文书证据编号均落在卷宗登记（' + refs.join('、') + '）', 'warn', missing.length ? 'fail' : 'pass',
        missing.length ? '编号 ' + missing.join('、') + ' 未在卷宗证据登记中找到。' : '所引证据编号均已登记。');
    } else {
      add('T', 'T2', '文书未引用证据编号（无需比对）', 'pass', 'pass', '');
    }
    // T3 人工在环标记（候选·待人工确认）存在
    const hasTag = (sub && sub.tag && sub.tag.indexOf('候选') >= 0) || /候选·待人工确认|待人工确认/.test(fullText);
    add('T', 'T3', '携带「候选·待人工确认」人工在环标记', 'reject', hasTag ? 'pass' : 'fail',
      hasTag ? '标记完整，交付前须人工确认。' : '缺少人工在环标记，禁止自动判定。');

    /* ===================== P 程序 ===================== */
    // P1 R2 红线：无 verdict / win_prob 语言
    const verdictWord = /必然胜诉|应当判决|本院直接认定|胜诉率|win_prob|确定性结论|必定支持/.test(fullText);
    add('P', 'P1', 'R2 红线：无 verdict / 胜诉率 / 必然判定 语言', 'reject', verdictWord ? 'fail' : 'pass',
      verdictWord ? '出现终局/胜率类表述，违反 R2 只给候选。' : '未见终局判定语言。');

    // P2 禁绝对词（在 xinZheng / chain 中）
    const absWord = /显然|当然|必定|无疑|毫无疑问/.test(chainText);
    add('P', 'P2', '心证/推理链禁用绝对词（显然/当然/必定）', 'reject', absWord ? 'fail' : 'pass',
      absWord ? '出现绝对词，心证表述不合规。' : '未见绝对词。');

    // P3 举证程序完备：有缺口则须有证据清单/举证期限
    if (sub && sub.gaps && sub.gaps.length) {
      const ok = /证据清单|举证期限|举证期限届满/.test(fullText);
      add('P', 'P3', '存在证据缺口时附举证程序提示', 'warn', ok ? 'pass' : 'fail',
        ok ? '已附证据清单/举证期限提示。' : '有证据缺口但未提示举证程序。');
    } else {
      add('P', 'P3', '举证程序提示（无缺口·免检）', 'pass', 'pass', '');
    }

    // P4 结论块均带候选标注
    if (sub && sub.chain) {
      const conclLines = sub.chain.filter(l => /【结论|【心证|【§F/.test(l));
      const missTag = conclLines.filter(l => l.indexOf('候选') < 0);
      add('P', 'P4', '结论/心证/§F 块均带候选标注', 'warn', missTag.length ? 'fail' : 'pass',
        missTag.length ? missTag.length + ' 个结论块缺候选标注。' : '结论块标注完整。');
    }

    // —— 汇总 ——
    const dims = {};
    ['R', 'L', 'C', 'T', 'P'].forEach(dim => {
      const items = checks.filter(c => c.dim === dim);
      const fail = items.filter(c => c.status === 'fail');
      const rejectCount = fail.filter(c => c.severity === 'reject').length;
      const warnCount = fail.filter(c => c.severity === 'warn').length;
      dims[dim] = { items, fail, pass: items.filter(c => c.status === 'pass').length, rejectCount, warnCount };
    });
    const reject = checks.filter(c => c.status === 'fail' && c.severity === 'reject').length;
    const warnCount = checks.filter(c => c.status === 'fail' && c.severity === 'warn').length;
    let grade;
    if (reject > 0) grade = { level: 'reject', text: '⛔ 须整改后交付（REJECT=' + reject + '）' };
    else if (warnCount > 0) grade = { level: 'warn', text: '⚠️ 可交付·建议复核（REJECT=0，WARN=' + warnCount + '）' };
    else grade = { level: 'pass', text: '✅ 可交付（REJECT=0，WARN=0）' };

    return { checks, dims, reject, warnCount, grade, report: buildReport(dims, reject, warnCount, grade) };
  }

  function buildReport(dims, reject, warnCount, grade) {
    const names = { R: 'R 法条真实性', L: 'L 法理逻辑', C: 'C 一致性', T: 'T 溯源', P: 'P 程序' };
    let h = '<div class="qc-grade ' + grade.level + '">' + grade.text + '</div>';
    ['R', 'L', 'C', 'T', 'P'].forEach(dim => {
      const d = dims[dim];
      const badge = d.rejectCount ? ('⛔' + d.rejectCount) : (d.warnCount ? ('⚠️' + d.warnCount) : '✅');
      h += '<div class="qc-dim"><div class="qch">' + names[dim] + ' <span class="qc-badge">' + badge + '</span></div>';
      d.items.forEach(it => {
        const ic = it.status === 'pass' ? '✅' : (it.severity === 'reject' ? '⛔' : '⚠️');
        h += '<div class="qc-item ' + it.status + '">' + ic + ' <b>' + it.id + '</b> ' + it.label +
          (it.detail ? ' <span class="qcd">— ' + it.detail + '</span>' : '') + '</div>';
      });
      h += '</div>';
    });
    return h;
  }

  return {
    runQC,
    computeAmountEstimate,
    parseEvidenceRefs,
    validateCaseNo,
    DIM_NAMES: { R: 'R 法条真实性', L: 'L 法理逻辑', C: 'C 一致性', T: 'T 溯源', P: 'P 程序' }
  };
});
