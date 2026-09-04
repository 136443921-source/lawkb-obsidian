#!/usr/bin/env node
/**
 * mindmap_source.js  —— 思维导图数据源（共享模块）
 *
 * 同时被两个脚本引用，保证「分身系统驾驶舱」与「决策思维树」两处的思维导图数据完全一致：
 *   - 刷新驾驶舱.js　（注入驾驶舱 DATA.mindmap）
 *   - 刷新决策树.js　（注入决策思维树页面 __MINDMAP_DATA__）
 *
 * 不再在两边各写一份解析逻辑，避免漂移。
 *
 * 设计要点（对应老强的防幻觉铁律）：
 *   1. 决策链＝真·决策过程，解析决策卡 10 分区，还原「当时怎么想的」
 *   2. 沉淀图谱＝经验卡知识结构的诚实呈现；经验卡没有推理链，页面必须标注「此乃结论非决策」
 *   3. 经验卡 source_rule 是嵌套 YAML 列表，扁平 parseFM 取不到，改对整段 frontmatter 跑正则
 */
const fs = require('fs');
const path = require('path');

/** 递归收集文件，排除隐藏目录 / 备份目录 / 回收站（口径：只数"活"资产） */
function walk(dir, ext) {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  const stack = [dir];
  while (stack.length) {
    const d = stack.pop();
    let ents = [];
    try { ents = fs.readdirSync(d, { withFileTypes: true }); } catch (e) { continue; }
    for (const e of ents) {
      if (e.name.startsWith('.')) continue;
      if (/^(backup|\.backup|trash|\.trash|cache|\.cache|node_modules)/i.test(e.name)) continue;
      if (/\.bak/i.test(e.name)) continue;
      const p = path.join(d, e.name);
      if (e.isDirectory()) stack.push(p);
      else if (!ext || p.toLowerCase().endsWith(ext)) out.push(p);
    }
  }
  return out;
}

/** 解析 frontmatter（只取 key: value 平面字段；嵌套 list 不取，规则号单独正则抽取） */
function parseFM(text) {
  const m = /^---\r?\n([\s\S]*?)\r?\n---/.exec(text);
  const fm = {};
  if (!m) return fm;
  m[1].split(/\r?\n/).forEach((line) => {
    const i = line.indexOf(':');
    if (i > 0) fm[line.slice(0, i).trim()] = line.slice(i + 1).trim();
  });
  return fm;
}

/** 按 ## 切分区 */
function mdSections(text) {
  const out = {};
  text.split(/^## /m).slice(1).forEach((seg) => {
    const nl = seg.indexOf('\n');
    const title = (nl < 0 ? seg : seg.slice(0, nl)).trim();
    out[title] = nl < 0 ? '' : seg.slice(nl + 1);
  });
  return out;
}

/** 解析 markdown 表格 → 行对象数组（key = 表头文字）；无表头时用 _c0/_c1… */
function mdTable(text) {
  const rows = [];
  let header = null;
  (text || '').split(/\r?\n/).forEach((raw) => {
    const line = raw.trim();
    if (!line.startsWith('|')) { header = null; return; }
    const cells = line.split('|').slice(1, -1).map((c) => c.trim());
    if (!cells.length) return;
    if (/^[-: ]+$/.test(cells.join(''))) return;      // 分隔行 | --- |
    if (!header) { header = cells; return; }          // 首行即表头
    const o = {};
    header.forEach((h, i) => { o[h] = cells[i] || ''; });
    cells.forEach((c, i) => { o['_c' + i] = c; });
    rows.push(o);
  });
  return rows;
}

/** 去掉 markdown 强调标记，只留纯文本 */
const stripMd = (s) => String(s || '')
  .replace(/\*\*(.+?)\*\*/g, '$1')
  .replace(/`(.+?)`/g, '$1')
  .replace(/\[\[(.+?)\]\]/g, '$1')
  .replace(/\[(.+?)\]\(.*?\)/g, '$1')
  .trim();

/** 剥离 AI 阅读说明等 HTML 注释与引用符 */
const cleanMd = (s) => String(s || '')
  .replace(/<!--[\s\S]*?-->/g, '')
  .replace(/^\s*>\s?/gm, '')
  .trim();

/**
 * 构建思维导图数据。
 * @param {string} BASE 知识飞轮系统根目录
 * @returns {{chains:object[], graph:object[], graphStat:object}}
 */
function buildMindmap(BASE) {
  const LOG_DIR = path.join(BASE, '04-LOG', '决策日志');
  const EXP_DIR = path.join(BASE, '02-提炼/经验卡片');

  // ---------- 决策链：解析决策卡 10 分区 ----------
  const decisionCards = walk(LOG_DIR, '.md').filter((p) => !path.basename(p).startsWith('_模板'));
  const chains = decisionCards.map((p) => {
    const body = fs.readFileSync(p, 'utf8');
    const fm = parseFM(body);
    const secs = mdSections(body);
    const pick = (key) => {
      const k = Object.keys(secs).find((t) => t.includes(key));
      return k ? secs[k] : '';
    };
    const options = mdTable(pick('①')).map((r) => {
      const verdictCell = stripMd(r['结论'] || r._c3 || '');
      return {
        label: stripMd(r['选项'] || r._c0 || ''),
        adopted: /✅|采用/.test(verdictCell),
        verdict: verdictCell,
      };
    }).filter((r) => r.label);
    const signals = cleanMd(pick('③')).split(/\r?\n/)
      .filter((l) => /^\s*[-*]\s*\[[ xX]\]/.test(l))
      .map((l) => {
        const t = l.replace(/^\s*[-*]\s*\[[ xX]\]\s*/, '');
        const m = /^\*\*(.+?)\*\*[：:]\s*([\s\S]*)$/.exec(t);
        const label = m ? stripMd(m[1]) : '';
        let type = '信号';
        if (/重估/.test(label)) type = '重估信号';
        else if (/转向/.test(label)) type = '转向信号';
        else if (/时间盒/.test(label)) type = '时间盒';
        return { type, label, text: stripMd(m ? m[2] : t) };
      });
    const firstLine = (s) => (cleanMd(s).split(/\r?\n/).find((l) => l.trim()) || '');
    return {
      id: path.basename(p, '.md'),
      name: path.basename(p, '.md').replace(/^\d{4}-\d{2}-\d{2}-/, ''),
      file: path.basename(p),
      date: fm.date || '', domain: fm.domain || '—', stakes: fm.stakes || '—',
      reversible: fm.reversible || '—',
      review: fm.review_date || '', verdict: fm.verdict || '待验证',
      conclusion: firstLine(pick('一句话结论')),
      options,
      reject: cleanMd(pick('②')),
      signals,
      assumption: cleanMd(pick('最关键的假设')),
      framework: cleanMd(pick('我调用了什么框架或经验')),
      state: cleanMd(pick('我当时的状态')),
      open: cleanMd(pick('未闭合项')),
      reviewTxt: cleanMd(pick('复盘')),
      transferable: cleanMd(pick('可迁移的规律')),
    };
  });

  // ---------- 沉淀图谱：解析经验卡 frontmatter ----------
  const expFiles = walk(EXP_DIR, '.md').filter((p) => !/README|_模板|模板/i.test(path.basename(p)));
  const graph = expFiles.map((p) => {
    const raw = fs.readFileSync(p, 'utf8');
    const fm = parseFM(raw);
    // source_rule 是嵌套 YAML 列表（"- - - R-PI-140|R-PI-140"），扁平 parseFM 取不到值。
    // 改为对整段 frontmatter 原始文本做正则抽取，鲁棒且不依赖缩进层级。
    const fmBlock = (() => { const m = /^---\r?\n([\s\S]*?)\r?\n---/.exec(raw); return m ? m[1] : ''; })();
    const rel = path.relative(EXP_DIR, p);
    const domain = rel.includes(path.sep) ? rel.split(path.sep)[0] : '未分类';
    const rules = [...new Set(String(fmBlock).match(/R-[A-Z]{2}-\d+/g) || [])];
    return {
      name: path.basename(p, '.md'),
      file: path.basename(p),
      domain,
      case_type: fm.case_type || fm.案由 || '',
      focus: fm.争议焦点 || '',
      relation: fm.法律关系 || '',
      evidence: fm.证据 || '',
      rules,
      trigger: fm.trigger || '',
      do: fm.do || '',
      dont: fm.dont || '',
      result: fm.result || '',
    };
  });

  const ruleHot = {};
  graph.forEach((g) => g.rules.forEach((r) => { ruleHot[r] = (ruleHot[r] || 0) + 1; }));
  const topRules = Object.entries(ruleHot).sort((a, b) => b[1] - a[1]).slice(0, 8)
    .map(([r, c]) => ({ rule: r, count: c }));
  const graphStat = {
    cards: graph.length,
    domains: [...new Set(graph.map((g) => g.domain))].sort(),
    ruleLinks: graph.reduce((s, g) => s + g.rules.length, 0),
    uniqueRules: Object.keys(ruleHot).length,
    topRules,
  };

  return { chains, graph, graphStat };
}

module.exports = { buildMindmap, walk, parseFM, mdSections, mdTable, stripMd, cleanMd };
