#!/usr/bin/env node
/**
 * 刷新决策思维层总览树
 *
 * 作用：扫描 04-LOG/决策日志/ 下所有决策卡，重建「二、已在册决策卡」分支，
 *       注入决策树_模板.html 后输出单文件 决策树总览.html（并同步桌面副本）。
 *
 * 用法：
 *   /Users/chenyouqiang/.workbuddy/binaries/node/versions/22.12.0/bin/node \
 *     "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/刷新决策树.js"
 *
 * 设计要点：
 *   - 方法论分支（思维层/人格层/知识层/运转节奏）来自 决策树_静态结构.json，手工维护，很少变
 *   - 卡片分支完全由脚本重建，改完卡片跑一次即可，不需要手改 HTML
 *   - 输出仍是单文件 HTML（数据与样式全内联），双击即开，不受 file:// 的 CORS 限制
 */

const fs = require('fs');
const path = require('path');
// 思维导图数据源（与「分身系统驾驶舱」共用同一模块，保证两处口径一致）
const { buildMindmap } = require('./mindmap_source');

const BASE = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统';
const LOG_DIR = path.join(BASE, '04-LOG', '决策日志');
const TPL = path.join(BASE, '决策树_模板.html');
const STATIC = path.join(BASE, '决策树_静态结构.json');
// 文件名刻意用「决策树总览」——Spotlight 搜这四个字可精确命中，
// 不会被同名的「决策思维层」文件夹、决策卡 md 正文里的「决策思维层」字样抢走首位。
//
// 【2026-09-03 变更】默认不再产出独立 HTML：决策树已完整整合进
// 「分身系统驾驶舱」的「🌳 决策思维层总览树」tab，留两个入口只会互相混淆
// （老强实测：点开桌面旧文件，以为新页面没换）。
// 需要单独出页面时显式加 --html 参数即可，能力保留、默认不产生冗余文件。
const OUT = path.join(BASE, '决策树总览.html');
// 桌面对外副本放根目录，命名用「决策思维树」——老强嘴上就叫这个名，Spotlight 也更好命中。
// 2026-09-04：从 小强律师知识库/决策思维层/ 迁到桌面根目录，与驾驶舱并排，随手点开。
const DESKTOP = '/Users/chenyouqiang/Desktop/决策思维树.html';
const WANT_HTML = process.argv.includes('--html');

const C = {
  gold: '#e0a458', purple: '#a78bfa', blue: '#60a5fa', teal: '#2dd4bf',
  green: '#4ade80', orange: '#fb923c', red: '#f87171', pink: '#f472b6', gray: '#6b7484'
};

const VERDICT_META = {
  '待验证':      { icon: '🔵', c: C.blue,   tag: '待验证' },
  '对了':        { icon: '✅', c: C.green,  tag: '对了' },
  '错了':        { icon: '❌', c: C.red,    tag: '错了' },
  '结论对但理由错': { icon: '⚠️', c: C.red,  tag: '结论对但理由错' }
};

const esc = s => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const md = s => esc(s)
  .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
  .replace(/`(.+?)`/g, '<code>$1</code>')
  .replace(/\n/g, '<br>');
const clip = (s, n = 1100) => {
  const t = String(s || '').trim();
  return t.length > n ? t.slice(0, n) + '…' : t;
};
/** 节点标签用：剥掉 markdown 记号，避免 ** 和 ` 直接显示出来 */
const plain = s => esc(s).replace(/\*\*(.+?)\*\*/g, '$1').replace(/`(.+?)`/g, '$1');
const today = () => new Date().toISOString().slice(0, 10);

/** 解析 frontmatter（只取 key: value 与 tags 列表，够用即可） */
function parseFM(text) {
  const m = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  const fm = {};
  if (!m) return { fm, body: text };
  let key = null;
  for (const raw of m[1].split(/\r?\n/)) {
    const kv = raw.match(/^([A-Za-z_][\w-]*)\s*:\s*(.*)$/);
    if (kv) { key = kv[1]; fm[key] = kv[2].trim(); }
    else if (key === 'tags' && /^\s*-\s+/.test(raw)) {
      fm.tags = fm.tags || []; fm.tags.push(raw.replace(/^\s*-\s+/, '').trim());
    }
  }
  return { fm, body: text.slice(m[0].length) };
}

/** 按 ## 切分区 */
function sections(body) {
  const out = {};
  const parts = body.split(/^##\s+/m).slice(1);
  for (const p of parts) {
    const nl = p.indexOf('\n');
    const title = (nl < 0 ? p : p.slice(0, nl)).trim().replace(/^#+\s*/, '');
    out[title] = nl < 0 ? '' : p.slice(nl + 1);
  }
  return out;
}

/**
 * 从 ③ 区提取时间盒日期。
 * 必须先剥掉 HTML 注释（备注里常有建卡日等非信号日期），
 * 且只在「- [ ] 信号行」里找——否则会把进展备注里的日期误当成 deadline。
 */
function pickDeadline(sec3) {
  if (!sec3) return '';
  const clean = sec3.replace(/<!--[\s\S]*?-->/g, '');
  const blocks = clean.split(/\r?\n(?=-\s*\[)/);
  const sigBlocks = blocks.filter(b => /^\s*-\s*\[[ xX]\]/.test(b));
  const src = sigBlocks.length ? sigBlocks.join('\n') : clean;
  const ds = [...src.matchAll(/(\d{4})-(\d{2})-(\d{2})/g)].map(m => m[0]);
  const t = today();
  return ds.filter(d => d >= t).sort()[0] || '';
}

/** 把一张决策卡 md 转成树节点 */
function cardNode(file, idx) {
  const full = path.join(LOG_DIR, file);
  const raw = fs.readFileSync(full, 'utf8');
  const { fm, body } = parseFM(raw);
  const sec = sections(body);

  const verdict = (fm.verdict || '待验证').trim();
  const vm = VERDICT_META[verdict] || VERDICT_META['待验证'];
  const review = (fm.review_date || '').trim();
  const deadline = pickDeadline(sec['③ 什么信号会让我推翻这个决定'] || sec['③ 什么信号会让我推翻'] || '');
  const overdue = verdict === '待验证' && review && review < today();

  // 标题：优先取 # 决策：后面的部分
  const h1 = (raw.match(/^#\s*决策[：:]\s*(.+)$/m) || [])[1];
  let label = (h1 || file.replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/\.md$/, '')).trim();
  if (overdue) label = '🚨 已逾期 · ' + label;
  else if (verdict === '结论对但理由错') label = '⚠️ ' + label;
  else label = vm.icon + ' ' + label;

  const meta = [];
  if (fm.date) meta.push('建卡：' + fm.date);
  if (fm.domain) meta.push('domain：' + fm.domain);
  if (fm.stakes) meta.push('stakes：' + fm.stakes);
  if (fm.reversible) meta.push('reversible：' + fm.reversible);
  if (review) meta.push('复盘日：' + review + (overdue ? '　⚠️ 已逾期' : ''));
  meta.push('判定：' + vm.tag);
  meta.push('文件：' + file);

  // 一句话结论
  const concl = (sec['一句话结论'] || '').replace(/<!--[\s\S]*?-->/g, '').trim();
  const kids = [];

  // ① 选项
  const s1 = sec['① 我考虑了哪几个选项'];
  if (s1) {
    const rows = [...s1.matchAll(/^\|\s*([A-D])[\.、]\s*(.+?)\s*\|/gm)];
    if (rows.length) {
      kids.push({
        id: `c${idx}_1`, label: `① 考虑的 ${rows.length} 个选项`, c: C.blue,
        desc: '（从卡片 ① 区自动提取）',
        children: rows.map((r, i) => {
          const line = s1.split(/\r?\n/).find(l => l.trim().startsWith('|') && l.includes(r[1] + '.') ) || '';
          const cells = line.split('|').map(s => s.trim()).filter(Boolean);
          const picked = /✅|采用/.test(cells[cells.length - 1] || '');
          return {
            id: `c${idx}_1_${i}`,
            label: (picked ? '✅ 采用 · ' : '未采 · ') + plain(r[2]),
            c: picked ? C.green : C.gray,
            desc: cells.length > 3 && cells[2] && cells[2] !== '见 ② 区'
              ? md(cells.slice(1, 3).join('｜'))
              : '（优劣判断见 ② 区）'
          };
        })
      });
    }
  }

  // ② 排除理由
  const s2 = sec['② 我为什么排除了其他的'];
  if (s2) {
    kids.push({
      id: `c${idx}_2`, label: '② 排除理由（全卡最值钱）', c: C.gold,
      desc: md(clip(s2.replace(/<!--[\s\S]*?-->/g, '').trim(), 1600))
    });
  }

  // ③ 推翻信号
  const s3 = sec['③ 什么信号会让我推翻这个决定'] || sec['③ 什么信号会让我推翻'];
  if (s3) {
    const sigs = [...s3.matchAll(/^-\s*\[.\]\s*(.+)$/gm)].map(m => m[1].trim());
    kids.push({
      id: `c${idx}_3`, label: `③ 推翻信号（${sigs.length} 条）`, c: C.orange,
      desc: sigs.length ? sigs.map(s => '• ' + md(clip(s, 400))).join('<br><br>')
        : md(clip(s3.replace(/<!--[\s\S]*?-->/g, '').trim(), 900))
    });
  }

  // ④ 假设
  const s4 = sec['最关键的假设'];
  if (s4) {
    kids.push({
      id: `c${idx}_4`, label: '④ 最关键的假设', c: C.purple,
      desc: md(clip(s4.replace(/<!--[\s\S]*?-->/g, '').trim(), 1200))
    });
  }

  // 🚨 AI 异议
  const sObj = Object.keys(sec).find(k => k.includes('AI 当面提出的异议'));
  if (sObj) {
    const so = sec[sObj];
    // 分隔符兼容全角冒号 / 半角冒号 / 间隔号 / 顿号 / 连字符，卡片里怎么写都能解析
    const SEP = /^###\s*(异议\s*\d+\s*[：:·、.\-]?\s*.+)$/gm;
    const items = [...so.matchAll(SEP)].map(m => m[1].trim());
    // split 已吃掉「异议」二字，故前缀设为可选
    const strip = t => t.replace(/^(异议)?\s*\d+\s*[：:·、.\-]?\s*/, '').trim();
    kids.push({
      id: `c${idx}_5`, label: `🚨 AI 异议（${items.length} 条，未获采纳）`, c: C.red,
      desc: items.length
        ? '建卡时 AI 当面提出、未被采纳的反对意见：<br><br>' +
          items.map((t, i) => `<b>${i + 1}. ${esc(strip(t))}</b>`).join('<br>') +
          '<br><br>（展开子节点看逐条内容；复盘时必须回答「哪几条成真了」）'
        : md(clip(so.replace(/<!--[\s\S]*?-->/g, '').trim(), 1200)),
      children: items.length ? (() => {
        const blocks = so.split(/^###\s*异议/gm).slice(1);
        return blocks.map((b, i) => {
          const nl = b.indexOf('\n');
          const t = strip(b.slice(0, nl));
          return { id: `c${idx}_5_${i}`, label: `异议 ${i + 1} · ${t}`, c: C.red,
                   desc: md(clip(b.slice(nl + 1).replace(/<!--[\s\S]*?-->/g, '').trim(), 1800)) };
        });
      })() : undefined
    });
  }

  // 复盘（仅当已回填时生成）
  const rv = sec['复盘（2026-12-02 回填，与吊顶案同日）'] || Object.keys(sec).find(k => k.startsWith('复盘'));
  if (rv) {
    const body2 = typeof rv === 'string' && sec[rv] !== undefined ? sec[rv] : '';
    const filled = body2 && !/^-?\s*$/m.test(body2.replace(/[-*]/g, '').trim());
    if (filled) {
      kids.push({
        id: `c${idx}_6`, label: '复盘（已回填）', c: vm.c,
        desc: md(clip(body2.replace(/<!--[\s\S]*?-->/g, '').trim(), 1500))
      });
    }
  }

  return {
    id: 'card_' + idx,
    label,
    c: overdue ? C.red : vm.c,
    bold: 1,
    verdict, review_date: review, deadline,
    desc: (concl ? md(concl) + '<br><br>' : '') +
      `<span style="color:var(--txt3);font-size:12px">本节点由脚本从卡片自动生成 · 源文件：<code>${esc(file)}</code></span>`,
    meta,
    children: kids.length ? kids : undefined
  };
}

// ---------- 主流程 ----------
function main() {
  // 模板只在 --html 时才需要；默认路径只更新静态结构，不依赖模板文件
  if (WANT_HTML && !fs.existsSync(TPL)) { console.error('❌ 缺少模板：' + TPL); process.exit(1); }
  if (!fs.existsSync(STATIC)) { console.error('❌ 缺少静态结构：' + STATIC); process.exit(1); }

  const tree = JSON.parse(fs.readFileSync(STATIC, 'utf8'));

  const files = fs.existsSync(LOG_DIR)
    ? fs.readdirSync(LOG_DIR).filter(f => f.endsWith('.md') && !f.startsWith('_模板')).sort()
    : [];

  const cards = files.map(cardNode);

  // 重建卡片分支
  const cb = tree.children.find(c => c.id === 'cards');
  if (!cb) { console.error('❌ 静态结构中找不到 id=cards 的分支'); process.exit(1); }
  cb.children = cards;
  cb.label = `二、已在册决策卡（${cards.length} 张）`;
  cb.desc = cards.length
    ? `共 ${cards.length} 张。<b>卡片分支由脚本自动生成</b>——改完卡片跑一次刷新脚本即可，不必手改 HTML。<br><br>` +
      `判定图例：🔵 待验证　✅ 对了　❌ 错了　⚠️ 结论对但理由错（最危险）　🚨 逾期未复盘`
    : '暂无决策卡。说出「我决定」「选 A 还是 B」即触发记卡流程。';

  // 同步运转节奏里的月报节点（保持信息一致）
  const rhythm = tree.children.find(c => c.id === 'rhythm');
  if (rhythm) {
    const r3 = rhythm.children.find(c => c.id === 'rh3');
    if (r3) r3.desc = r3.desc.replace(/输出至[\s\S]*?`$/,
      '输出至 <code>知识飞轮系统/04-LOG/决策月报/YYYY-MM_决策思维月报.md</code>');
  }

  // ★ 回写静态结构——这是「分身系统驾驶舱」决策树 tab 的唯一数据源。
  //   ⚠️ 2026-09-03 修复：此前本脚本对 STATIC 只读不写，合并结果只进了 HTML，
  //   导致驾驶舱拿到的树长期停留在 16:56 的旧快照——卡片的 deadline / verdict 全为空。
  fs.writeFileSync(STATIC, JSON.stringify(tree, null, 2));
  console.log('✅ 已更新静态结构：' + STATIC);

  const t = today();
  const judged = cards.filter(c => c.verdict !== '待验证');
  const overdue = cards.filter(c => c.verdict === '待验证' && c.review_date && c.review_date < t);
  console.log(`   卡片 ${cards.length} 张 · 节点 ${JSON.stringify(tree).match(/"id":/g).length} 个`
    + ` · 已判定 ${judged.length} / 待验证 ${cards.length - judged.length}`
    + (overdue.length ? `　🚨 逾期 ${overdue.length}` : ''));
  cards.forEach(c => {
    const vm = VERDICT_META[c.verdict] || VERDICT_META['待验证'];
    console.log(`   ${vm.icon} ${c.label.replace(/^[^\s]+\s/, '')}　复盘 ${c.review_date || '—'}${c.deadline ? '　⏱ ' + c.deadline : ''}`);
  });

  // 默认到此为止：不再产出独立的 决策树总览.html
  if (!WANT_HTML) return;

  // ---- 以下仅 --html 显式请求时执行（保留能力，需要独立页面时可一键恢复）----
  const tpl = fs.readFileSync(TPL, 'utf8');
  if (!tpl.includes('__TREE_DATA__')) { console.error('❌ 模板中未找到 __TREE_DATA__ 占位符'); process.exit(1); }
  // 思维导图：与驾驶舱共用 mindmap_source.js，单一数据源，两处一致
  const mindmap = buildMindmap(BASE);
  const out = tpl.replace('__TREE_DATA__', JSON.stringify(tree))
                 .replace('__MINDMAP_DATA__', JSON.stringify(mindmap));

  // 刷新页脚时间戳
  const stamp = '　|　数据刷新：' + today();
  const final = out.replace(/(<footer>[\s\S]*?)(　\||<\/footer>)/, `$1${stamp}$2`);

  fs.writeFileSync(OUT, final);
  console.log('✅ 已生成独立 HTML：' + OUT + `（${(Buffer.byteLength(final) / 1024).toFixed(1)} KB）`);
  console.log('✅ 思维导图：决策链 ' + mindmap.chains.length + ' 条 · 沉淀图谱 ' + mindmap.graphStat.cards + ' 张 / ' + mindmap.graphStat.domains.length + ' 个领域 · 规则关联 ' + mindmap.graphStat.ruleLinks + ' 处（去重 ' + mindmap.graphStat.uniqueRules + ' 条）');

  if (fs.existsSync(path.dirname(DESKTOP))) {
    fs.copyFileSync(OUT, DESKTOP);
    console.log('✅ 已同步桌面：' + DESKTOP);
  } else {
    console.log('⚠️  桌面目录不存在，跳过同步：' + DESKTOP);
  }
}

main();
