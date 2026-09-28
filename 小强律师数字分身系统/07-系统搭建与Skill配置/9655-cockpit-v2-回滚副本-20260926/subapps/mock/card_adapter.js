/*
 * card_adapter.js — 卡源适配器（主控卡库 schema → 法官矩阵 JUDGE_CARDS schema）
 * ---------------------------------------------------------------------------
 * 背景（主控-法官关系收口·Gap C）：
 *   主控「知识飞轮卡库检索」产出的审判要件卡/案由路由卡（LawKB 裁判规则库 .md）
 *   其 frontmatter schema 为：
 *     rule_id / title / type / card_type / geo_scope / review_step
 *     elements: [{id,name,desc}]
 *     ruling: {support, reject}
 *     burden_of_proof / negative_note / request_base:[法条]
 *   而 judge_mind.js v2 消费的 JUDGE_CARDS 是扁平化后的：
 *     {id, name, domain, favor, support, points, pitfall, law}
 *   两套 schema 不一致，导致「整链吃卡闭环」未真正闭环——法官绕开主控自建 215 张卡。
 *
 * 本适配器把主控卡库的「正向裁判规则 + 常见误区」基准卡，映射为法官矩阵可消费的
 * 扁平结构，使主控检索到的卡能直接并入 JUDGE_CARDS，由 judge_mind.js v2 的
 * matchCards / _cardAdj 进行矩阵校准。
 *
 * 设计原则：
 *   ① 幂等：输入已是扁平 JUDGE_CARDS 形态（含 support 且无 ruling/elements）则原样返回，
 *      避免重复适配导致的字段丢失。
 *   ② 忠实：support←ruling.support（正向规则）、points←elements（要件要点）、
 *      pitfall←negative_note + ruling.reject（翻车点/驳回情形）、law←request_base。
 *   ③ favor 统一置「中立」：与 judge_mind v2 设计一致（195 张导入卡 favor 全为中立，
 *      方向判定不靠 favor，而靠 support/pitfall 校准）。
 *
 * 纯函数 UMD：Node(require) 与 浏览器(window.CARD_ADAPTER) 双形态可用，
 * 以便被 test_card_adapter.js 客观断言、被中台 HTML 直接消费。
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.CARD_ADAPTER = factory();
})(typeof self !== 'undefined' ? self : this, function () {

  /**
   * 由 raw 卡推导 domain（案由域桶）。
   * 优先取 type 首段（如 "执行程序·审判要件卡" → "执行程序"），
   * 否则取 card_type 首段，再否则 "通用"。
   */
  function _extractDomain(raw) {
    const src = raw.type || raw.card_type || '';
    const seg = String(src).split('·')[0].trim();
    return seg || '通用';
  }

  /**
   * 单卡适配（幂等）。
   * @param {object} raw 主控卡库原始卡（含 ruling/elements 嵌套）或已扁平 JUDGE_CARDS
   * @returns {object|null} JUDGE_CARDS 兼容对象；无效输入返回 null
   */
  function adaptOne(raw) {
    if (!raw || typeof raw !== 'object') return null;

    // —— 幂等守卫：已是扁平 JUDGE_CARDS 形态（有 support，且无主控嵌套结构）——
    const alreadyFlat = raw.support !== undefined &&
      (raw.points !== undefined || raw.pitfall !== undefined) &&
      !raw.ruling && !Array.isArray(raw.elements);
    if (alreadyFlat) return raw;

    const id = raw.rule_id || raw.id || '';
    if (!id) return null; // 无 rule_id 视为无效卡，交由批量层过滤
    const name = raw.title || raw.name || '';

    // ruling 可能是字符串（异常）或对象
    const ruling = raw.ruling || {};
    const rulingObj = (typeof ruling === 'string') ? { support: ruling } : ruling;
    const support = rulingObj.support || '';
    const reject = rulingObj.reject || '';

    // elements → points（"name：desc" 句池，与 support 在 judge_mind._prep 中拼接）
    const elements = Array.isArray(raw.elements) ? raw.elements : [];
    const points = elements.map(e => {
      if (typeof e === 'string') return e;
      if (e && typeof e === 'object') {
        return (e.name || '') + (e.desc ? ('：' + e.desc) : '');
      }
      return '';
    }).filter(Boolean).join('。');

    // pitfall ← 翻车点(negative_note) + 驳回情形(ruling.reject)
    const pitfall = [raw.negative_note, reject].filter(Boolean).join('；');

    // law ← request_base（法条列表，保留可追溯；judge_mind._lawHit 仅匹配"第X条"格式）
    const law = Array.isArray(raw.request_base)
      ? raw.request_base.join('、')
      : (raw.law || '');

    return {
      id,
      name,
      domain: _extractDomain(raw),
      favor: '中立',
      support: support || '',
      points: points || '',
      pitfall: pitfall || '',
      law: law || ''
    };
  }

  /**
   * 批量适配。
   * @param {array} rawCards 主控卡库原始卡数组
   * @returns {array} JUDGE_CARDS 兼容数组（自动过滤无效项）
   */
  function adaptCaseRouteCards(rawCards) {
    if (!Array.isArray(rawCards)) return [];
    return rawCards.map(adaptOne).filter(Boolean);
  }

  return { adaptOne, adaptCaseRouteCards, _extractDomain };
});
