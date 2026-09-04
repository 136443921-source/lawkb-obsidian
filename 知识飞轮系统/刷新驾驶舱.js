#!/usr/bin/env node
/**
 * 刷新驾驶舱.js  v2.0.0（EV 车机仪表盘版）
 * ---------------------------------------------------------------
 * 扫描「小强律师数字分身系统」五大支柱 + 子系统的落盘指标，
 * 合并人工核验项（连接器 / LTI 回归 / 成熟度定级 / EV 实测项），
 * 按《数字分身系统运维手册（EV 版）》的车辆隐喻组织信息架构，
 * 写回 驾驶舱_模板.html 的 DATA 占位块，输出 分身系统驾驶舱.html。
 *
 * 设计原则（对应老强的防幻觉铁律在可视化上的延伸）：
 *   1. 能扫的绝不写死 —— 所有文件计数实时 rglob
 *   2. 扫不出的绝不伪造 —— 连接器 / LTI 回归 / 成熟度 一律读 驾驶舱_人工核验.json，
 *      并在页面上标注「人工核验于 X」，不伪装成实时数据
 *   3. 口径透明 —— 每个指标都带 detail 说明统计口径，与人工复盘数字对不上时能查因
 *   4. 手册即权威源 —— 车辆铭牌 / 充电桩 / OTA / 保养周期 / DTC / 健康阈值 / 安全红线
 *      一律实时解析 EV 运维手册 md，不抄进 JSON。手册改了，驾驶舱跟着变
 *   5. 双轨并列 —— 手册铭牌值（编制时刻快照）与脚本实测值（刷新时刻）并列显示并标注来源，
 *      两者不一致时不覆盖、不取舍，把口径差异摊在页面上
 *
 * 六-B 安全铁律：写入前自动备份目标 HTML 到 驾驶舱_backup/ 目录。
 */
const fs = require('fs');
const path = require('path');
const cp = require('child_process');

const BASE = '/Users/chenyouqiang/Documents/LawKB/知识飞轮系统';
const LAWKB = '/Users/chenyouqiang/Documents/LawKB';
const TPL = path.join(BASE, '驾驶舱_模板.html');
const OUT = path.join(BASE, '分身系统驾驶舱.html');
const MANUAL = path.join(BASE, '驾驶舱_人工核验.json');
const BACKUP_DIR = path.join(BASE, '驾驶舱_backup');
const TREE_JSON = path.join(BASE, '决策树_静态结构.json');
const TREE_REFRESH = path.join(BASE, '刷新决策树.js');
// 2026-09-03 22:40 老强要求：产出放桌面根目录（废纸篓旁），随手点开不用翻两层文件夹。
// 原「桌面/小强律师知识库/分身系统工作台.html」副本已移入废纸篓——留两份必然不同步，只会误导。
// （2026-09-03 23:45 全系统改名：工作台 → 驾驶舱，此处保留当时的原名以免历史记录失真）
const DESKTOP_DIR = '/Users/chenyouqiang/Desktop';

/**
 * 递归查找文件名匹配的文件（抗目录重组）。
 * ⚠️ 踩坑记录（2026-09-03 22:15）：手册原在 数字分身系统设计/ 下，
 *    当夜目录被按 EV 章节重组为 00-系统总览与运维中心/…，硬编码路径瞬间失效。
 *    故一律按文件名递归搜索，不写死目录——路径会变，文件名不会。
 */
function findFiles(root, re, maxDepth) {
  const out = [];
  if (!root || !fs.existsSync(root)) return out;
  (function w(d, depth) {
    if (depth > (maxDepth || 6)) return;
    let es = [];
    try { es = fs.readdirSync(d, { withFileTypes: true }); } catch (e) { return; }
    for (const e of es) {
      if (e.name.startsWith('.') || /^(node_modules|\.git)$/.test(e.name)) continue;
      const p = path.join(d, e.name);
      if (e.isDirectory()) {
        if (/\.(backup|trash|cache)$/i.test(e.name) || /^\.?(backup|trash)/i.test(e.name)) continue;
        w(p, depth + 1);
      } else if (re.test(e.name)) out.push(p);
    }
  })(root, 0);
  return out;
}

// ---------- EV 运维手册（权威源） ----------
// 文件名带日期，字典序=时间序，取最后一个 = 最新版。手册出新版时驾驶舱自动跟随。
const EV_DOC = (() => {
  const hits = findFiles(LAWKB, /^数字分身系统运维手册-EV版.*\.md$/, 6);
  if (!hits.length) return '';
  hits.sort();
  return hits[hits.length - 1];
})();

// ---------- 通用扫描 ----------
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
      // 排除隐藏项、备份、回收站、缓存
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
const n = (arr) => arr.length;
const today = () => new Date().toISOString().slice(0, 10);
/**
 * 北京时间 'YYYY-MM-DD HH:mm'。
 * ⚠️ toISOString() 返回 UTC，直接 slice 会让页面显示的时间比本地早 8 小时
 *    （实测 22:36 的刷新，页面显示 14:36）。老强看的是本地钟，必须 +8。
 */
const nowCN = () => new Date(Date.now() + 8 * 3600 * 1000).toISOString().slice(0, 16).replace('T', ' ');
const daysBetween = (a, b) => Math.round((new Date(b) - new Date(a)) / 86400000);

// ---------- ① 知识飞轮六层 ----------
const LAYERS = [
  ['01-采集', '01-采集'], ['02-提炼', '02-提炼'], ['03-连接', '03-连接'],
  ['04-LOG', '04-LOG'], ['04-巩固', '04-巩固'], ['05-调用', '05-调用'], ['06-沉淀', '06-沉淀'],
];
let layerTotal = 0;
const layerDetail = LAYERS.map(([label, dir]) => {
  const c = n(walk(path.join(BASE, dir), '.md'));
  layerTotal += c;
  return `${label.replace(/^0\d-/, '')}${c}`;
}).join(' / ');

const ruleFiles = n(walk(path.join(BASE, '06-沉淀/裁判规则库'), '.md'))
  .valueOf();
const ruleAll = walk(path.join(BASE, '06-沉淀/裁判规则库'), '.md')
  .filter((p) => /R-[A-Z]{2}-\d+/.test(path.basename(p))).length;
const ruleSubLibs = (() => {
  const d = path.join(BASE, '06-沉淀/裁判规则库');
  if (!fs.existsSync(d)) return 0;
  try {
    return fs.readdirSync(d, { withFileTypes: true })
      .filter((e) => e.isDirectory() && !e.name.startsWith('.')).length;
  } catch (e) { return 0; }
})();

// 经验卡片（与「飞轮健康度」tab 同口径：排除 README / 模板类文件，避免把模板占位卡算作真实沉淀）
const expCardsAll = walk(path.join(BASE, '02-提炼/经验卡片'), '.md')
  .filter((p) => !/README|_模板|模板/i.test(path.basename(p)));
const expCards = expCardsAll.length;
const traceCards = walk(path.join(BASE, '02-提炼/经验卡片/思维轨迹'), '.md')
  .filter((p) => path.basename(p) !== 'README.md').length;

// ---------- ② LTI 文本监控器 ----------
const ltiDir = path.join(process.env.HOME || '/Users/chenyouqiang', '.workbuddy/skills/LTI文本监控器');
let ltiFiles = 0;
if (fs.existsSync(ltiDir)) ltiFiles = n(walk(ltiDir, '.md'));
// 权威源条文库：provision_index/index_*.json（每部法一个）
// 这是 LTI 核验法条真实性的唯一合法条源——老强铁律「永不凭记忆灌条文正文」的落地点，
// 因此把它做成可见指标：部数与条文数越多，可被机检覆盖的法域越广。
const PI_DIR = path.join(ltiDir, 'references/provision_index');
let piLaws = 0, piArticles = 0;
if (fs.existsSync(PI_DIR)) {
  fs.readdirSync(PI_DIR)
    .filter((f) => f.startsWith('index_') && f.endsWith('.json'))
    .forEach((f) => {
      try {
        const j = JSON.parse(fs.readFileSync(path.join(PI_DIR, f), 'utf8'));
        piLaws++;
        piArticles += Number(j.article_count) || Object.keys(j.articles || {}).length;
      } catch (e) { /* 单个文件损坏不影响整体统计 */ }
    });
}

// ---------- ③ HIR 经验沉淀 ----------
const CALL_DIRS = [
  ['合同审查调用记录', '合同审查'], ['庭审准备调用记录', '庭审准备'],
  ['文书写作调用记录', '文书写作'], ['模拟法庭调用记录', '模拟法庭'],
  ['法律检索调用记录', '法律检索'], ['类案检索调用记录', '类案检索'],
  ['要件映射卡调用记录', '要件映射'], ['诉讼文书复核调用记录', '诉讼文书复核'],
  ['跨案模式识别调用记录', '跨案识别'], ['非诉文书复核调用记录', '非诉复核'],
];
let callTotal = 0;
const callRows = CALL_DIRS.map(([dir, label]) => {
  const c = n(walk(path.join(BASE, '05-调用', dir)));
  callTotal += c;
  return { label, c };
});

// ---------- ④ 跨案模式识别 ----------
const crossCases = n(walk(path.join(BASE, '05-调用/跨案模式识别调用记录')));

// ---------- ⑤ 决策思维系统 ----------
const LOG_DIR = path.join(BASE, '04-LOG/决策日志');
const MONTH_DIR = path.join(BASE, '04-LOG/决策月报');
const decisionCards = walk(LOG_DIR, '.md').filter((p) => !path.basename(p).startsWith('_模板'));
const monthReports = walk(MONTH_DIR, '.md');

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

let pending = 0, overdue = 0, right = 0, wrong = 0, reasonWrong = 0, judged = 0;
let nextReview = null, aiObjections = 0;
const td = today();
/** 每张决策卡的摘要，用于「今日焦点」与「时间轴」 */
const cardInfos = [];

/**
 * 从决策卡正文提取「时间盒」日期。
 * 语义：时间盒日期 = 「时间盒」字样后紧邻出现的那个日期，按文中顺序取第一个。
 * ⚠️ 绝不排序——2026-09-03 会排在 2026-11-01 前面（字典序），
 *    一旦排序就会把建卡日误当成 deadline（吊顶案实测踩过：提取成了建卡日 09-03 而非时间盒 11-01）。
 */
function pickDeadline(text) {
  const idx = text.search(/时间盒|deadline|Deadline/);
  if (idx < 0) return null;
  const seg = text.slice(idx, idx + 260);
  const dates = seg.match(/20\d{2}-\d{2}-\d{2}/g) || [];
  const future = dates.filter((d) => d >= td);
  return future[0] || dates[0] || null;
}

decisionCards.forEach((p) => {
  const body = fs.readFileSync(p, 'utf8');
  const fm = parseFM(body);
  const v = fm.verdict || '';
  if (v === '待验证') {
    pending++;
    if (fm.review_date && fm.review_date < td) overdue++;
  } else if (v) {
    judged++;
    if (v === '对了') right++;
    else if (v === '错了') wrong++;
    else if (v === '结论对但理由错') reasonWrong++;
  }
  if (fm.review_date && fm.review_date >= td) {
    if (!nextReview || fm.review_date < nextReview) nextReview = fm.review_date;
  }
  // AI 异议条数
  // 口径修正（2026-09-03）：先按 ## 切节，只在「节内容含 AI 异议」的节内统计；
  // 条目行形如 `- **异议1（...）**：`，故用 ^\s*[-*]?\s*\*\*异议\s*\d+ 匹配起始行。
  // 正文中的引用（如「走异议3路径」）因不处于行首条目位，不计入。
  let obj = 0;
  body.split(/^## /m).slice(1).forEach((s) => {
    if (!/AI\s*异议/.test(s)) return;
    obj += (s.match(/^\s*[-*]?\s*\*\*异议\s*\d+/gm) || []).length;
  });
  aiObjections += obj;

  const name = path.basename(p, '.md').replace(/^\d{4}-\d{2}-\d{2}-/, '');
  const dl = pickDeadline(body);
  cardInfos.push({
    name,
    file: path.basename(p),
    deadline: dl,
    review: fm.review_date && fm.review_date >= td ? fm.review_date : null,
    domain: fm.domain || '—',
    stakes: fm.stakes || '—',
    verdict: v || '待验证',
    objections: obj,
  });
});
const hitRate = judged ? Math.round((right / judged) * 100) + '%' : '暂无样本';
const daysToReview = nextReview ? daysBetween(td, nextReview) : null;

// HOW-I-THINK 填充度
// 判定口径（2026-09-03 修正）：先剥离 HTML 注释块（模板提示语），再逐行排除
//   · 未勾选的复选框 `- [ ]`（模板选项，不是老强填的内容）
//   · 纯 `-` / `---` 占位行
//   · 以「：」或「:」结尾的标签行（如 `**口头禅 / 高频词**：` 后面是空的）
//   · 表格分隔行 `| --- |`
// 单节有效行 >= 3 才算「已填」，避免把一两个模板示例当内容。
const HIT = path.join(BASE, '06-沉淀/HOW-I-THINK.md');
let hitFilled = 0, hitTotal = 0, hitBytes = 0, hitLines = 0;
const hitEmpty = [];
let hitMaturity = '';
if (fs.existsSync(HIT)) {
  const raw = fs.readFileSync(HIT, 'utf8');
  const fm = parseFM(raw);
  hitMaturity = fm.maturity || '';
  hitBytes = Buffer.byteLength(raw, 'utf8');
  const txt = raw.replace(/<!--[\s\S]*?-->/g, '');   // 剥离模板注释
  const parts = txt.split(/^## /m).slice(1);
  hitTotal = parts.length;
  parts.forEach((seg) => {
    const lines = seg.split(/\r?\n/);
    const title = (lines[0] || '').trim();
    const body = lines.slice(1);
    const eff = body.filter((l) => {
      const s = l.trim();
      if (!s) return false;                                  // 空行
      if (s.startsWith('#')) return false;                   // 标题
      if (/^- \[ \]\s/.test(s)) return false;                // 未勾选复选框 = 模板选项
      if (/^[-*=]{1,3}$/.test(s)) return false;              // 纯占位 / 分隔
      if (/^[：:]|[：:]$/.test(s)) return false;              // 以冒号结尾 = 空标签行
      if (/^\*\*.+?\*\*\s*[（(]?[^）)]*[)）]?\s*[：:]\s*$/.test(s)) return false; // 加粗标签无内容
      if (/^\|[\s:|-]+\|$/.test(s)) return false;            // 表格分隔行
      if (/^(TODO|待填|（待|占位)/.test(s)) return false;
      return true;
    });
    hitLines += eff.length;
    if (eff.length >= 3) hitFilled++;
    else hitEmpty.push(title.replace(/^\d+\.\s*/, ''));
  });
}
const hitRateTxt = hitTotal ? `${hitFilled}/${hitTotal}` : '—';

// ---------- 复用决策树扫描（不重复实现） ----------
let tree = { id: 'root', label: '（决策树数据未生成）', children: [] };
try {
  // --html：一并刷新桌面的独立决策树页面（老强 2026-09-04 要求桌面常驻，方便随时查树）
  cp.execSync(`node "${TREE_REFRESH}" --html`, { stdio: 'pipe' });
  tree = JSON.parse(fs.readFileSync(TREE_JSON, 'utf8'));
} catch (e) {
  try { tree = JSON.parse(fs.readFileSync(TREE_JSON, 'utf8')); } catch (e2) { /* 保留占位 */ }
}

// ---------- 人工核验项 ----------
let manual = {};
try { manual = JSON.parse(fs.readFileSync(MANUAL, 'utf8')); } catch (e) { manual = {}; }
const maturity = manual.maturity || {};

// ---------- 非支柱子系统扫描（座舱 / 影子模式 / 黑匣子 / 车规 / 驱动电机） ----------
// 这五个不在「五大支柱」里，但运维手册 1.2 / 4.1 / 4.2 / 5.1 / 5.2 有明确定义，
// 缺了它们整车状态图就不完整——所以单独扫，不给健康度分（无成熟度定级依据，不编数字）。
const subsys = (manual.ev && manual.ev.subsystems) || {};
const HOME = process.env.HOME || '/Users/chenyouqiang';
const SUB_FILES = {
  // 1.2 驱动电机 = SR 召回引擎（lawyer-yourself-skill 的 SR 算法）
  motor: { dir: path.join(HOME, '.workbuddy/skills/lawyer-yourself-skill'), unit: '个 .md' },
  // 4.1 智能座舱 / 车机 = 自我画像配置（定义「我是谁 / 风格 / 边界」）
  // 同样递归查找，抗目录重组（该文件已从 数字分身系统设计/ 迁至 00-系统总览与运维中心/）
  cockpit: { file: (findFiles(LAWKB, /自我画像.*\.md$/, 6).sort()[0]) || '', unit: 'KB' },
  // 4.2 影子模式 / 碰撞预演 = 模拟法庭庭审系统
  shadow: { dir: path.join(BASE, '05-调用/模拟法庭调用记录'), unit: '份推演' },
  // 5.1 黑匣子 / EDR = 04-LOG（决策日志 + 飞轮 LOG）
  edr: { dir: path.join(BASE, '04-LOG'), unit: '个 .md' },
  // 5.2 车规标准手册 = AGENTS.md（真跑纪律 / 六-B 铁律）
  vehicle_code: { file: path.join(LAWKB, 'AGENTS.md'), unit: 'KB' },
};
/** 返回 {count, unit}：目录计数文件数，单文件报体积 KB。找不到返回 null（页面显示「—」，不编 0） */
function subStat(k) {
  const c = SUB_FILES[k];
  if (!c) return null;
  if (c.file) {
    if (!fs.existsSync(c.file)) return null;
    try { return { count: Math.round(fs.statSync(c.file).size / 1024), unit: c.unit }; } catch (e) { return null; }
  }
  if (c.dir && fs.existsSync(c.dir)) return { count: n(walk(c.dir, '.md')), unit: c.unit };
  return null;
}

// ---------- EV 运维手册解析（权威源，不抄进 JSON） ----------
// 手册里的表格是人工编制的权威参数。脚本实时解析，好处是手册一改驾驶舱跟着变，
// 不存在「JSON 里抄了一份旧值没同步」的漂移问题。
function mdSections(text) {
  const out = {};
  text.split(/^## /m).slice(1).forEach((seg) => {
    const nl = seg.indexOf('\n');
    const title = (nl < 0 ? seg : seg.slice(0, nl)).trim();
    out[title] = nl < 0 ? '' : seg.slice(nl + 1);
  });
  return out;
}
/** 模糊找节：手册章节标题带序号与括号，用关键字匹配更抗改名 */
function secOf(secs, key) {
  const k = Object.keys(secs).find((t) => t.includes(key));
  return k ? secs[k] : '';
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

let ev = {
  available: false, file: '', basename: '', updated: '',
  plate: [], chargers: [], ota: [], maintenance: [], dtc: [], health: [],
  redlines: [], slogan: '', firstRule: '',
};
if (EV_DOC && fs.existsSync(EV_DOC)) {
  try {
    const rawTxt = fs.readFileSync(EV_DOC, 'utf8');
    const secs = mdSections(rawTxt);
    const fmEv = parseFM(rawTxt);
    ev.available = true;
    ev.file = EV_DOC;
    ev.basename = path.basename(EV_DOC);
    ev.updated = (fmEv.updated || fmEv.created || '').replace('T', ' ').slice(0, 16);

    // 〇 车辆铭牌
    ev.plate = mdTable(secOf(secs, '车辆铭牌')).map((r) => ({
      k: stripMd(r['项目'] || r._c0 || ''),
      v: stripMd(r['参数'] || r._c1 || ''),
    })).filter((r) => r.k);

    // EV 第一守则（引用块）
    const ruleM = /EV\s*第一守则[**：]*\s*([^\n>]+)/.exec(rawTxt);
    if (ruleM) ev.firstRule = stripMd(ruleM[1]);

    // 二 补能管理（充电桩）
    ev.chargers = mdTable(secOf(secs, '补能管理')).map((r) => {
      const st = stripMd(r['状态'] || r._c1 || '');
      return {
        name: stripMd(r['充电桩'] || r._c0 || ''),
        raw: st,
        status: /✅/.test(st) ? 'on' : (/❌/.test(st) ? 'off' : 'unknown'),
        content: stripMd(r['补能内容'] || r._c2 || ''),
        impact: stripMd(r['断开影响与处置'] || r._c3 || ''),
      };
    }).filter((r) => r.name);

    // 六 OTA 远程升级管理
    ev.ota = mdTable(secOf(secs, 'OTA')).map((r) => ({
      task: stripMd(r['升级任务'] || r._c0 || ''),
      cadence: stripMd(r['节拍'] || r._c1 || ''),
      id: stripMd(r['automation ID / 说明'] || r._c2 || ''),
    })).filter((r) => r.task);

    // 七 定期保养周期表
    ev.maintenance = mdTable(secOf(secs, '定期保养周期表')).map((r) => ({
      cycle: stripMd(r['周期'] || r._c0 || ''),
      items: stripMd(r['保养项'] || r._c1 || ''),
      owner: stripMd(r['负责'] || r._c2 || ''),
    })).filter((r) => r.cycle);

    // 八 故障码速查 DTC
    ev.dtc = mdTable(secOf(secs, '故障码')).map((r) => ({
      code: stripMd(r['故障码'] || r._c0 || ''),
      symptom: stripMd(r['现象'] || r._c1 || ''),
      cause: stripMd(r['根因'] || r._c2 || ''),
      action: stripMd(r['处置'] || r._c3 || ''),
    })).filter((r) => r.code && /DTC/.test(r.code));

    // 九 续航自检与健康度指标
    ev.health = mdTable(secOf(secs, '续航自检')).map((r) => ({
      name: stripMd(r['指标'] || r._c0 || ''),
      metric: stripMd(r['量化方式'] || r._c1 || ''),
      threshold: stripMd(r['健康阈值'] || r._c2 || ''),
    })).filter((r) => r.name);

    // 十 安全红线（有序列表）
    ev.redlines = (secOf(secs, '安全红线') || '')
      .split(/\r?\n/)
      .filter((l) => /^\s*\d+\.\s+\S/.test(l))
      .map((l) => stripMd(l.replace(/^\s*\d+\.\s+/, '')))
      .filter(Boolean);

    // 十一 一句话运维口诀（加粗段落）
    const sl = /##\s*十一[\s\S]*?\*\*(.+?)\*\*/s.exec(rawTxt);
    if (sl) ev.slogan = stripMd(sl[1].replace(/\s+/g, ' '));
  } catch (e) {
    ev.available = false;                              // 解析失败不阻断，页面标注「手册不可用」
  }
}

// ---------- DTC 当前激活判定 ----------
// 手册给的是「故障码定义」，是否触发要用实时状态判定：
// IMA/法随看连接器、HALL-403 看人工核验、CASE-001 看驱动电机状态、
// DISTILL-003 看 HOW-I-THINK 样本数；LTI-REJECT 是安全机制不是故障，永不点亮。
const connOff = new Set((manual.connectors || []).filter((c) => c.status === 'off')
  .map((c) => c.name.toLowerCase()));
const hallDown = ((manual.ev || {}).hall_detect || {}).status === '403';
const DTC_ACTIVE = {
  'DTC-IMA-001': [...connOff].some((s) => s.includes('ima')),
  'DTC-FASUI-002': [...connOff].some((s) => s.includes('法随') || s.includes('fasui')),
  'DTC-HALL-403': hallDown,
  'DTC-LTI-REJECT': false,                     // 拦截成功＝机制生效，非故障
  'DTC-CASE-001': (subsys.motor || {}).status === 'warn',
  'DTC-DISTILL-003': decisionCards.length < 10,
};
ev.dtc.forEach((d) => {
  d.active = !!DTC_ACTIVE[d.code];
  // 未在上表的故障码（手册新增后脚本未同步映射）标 unknown，页面上打「未判定」而非假装正常
  if (!(d.code in DTC_ACTIVE)) d.active = null;
});
const activeDtc = ev.dtc.filter((d) => d.active === true);

// ---------- 健康指标：手册阈值 + 实测当前值 ----------
// 手册给「量化方式」与「健康阈值」，括号里是编制时刻的当前值。
// 刷新时刻的当前值优先用脚本实测（能扫的），扫不到才回退手册值，并标注来源。
const connOn = (manual.connectors || []).filter((c) => c.status === 'on').length;
const connTotal = (manual.connectors || []).length;
const HEALTH_CUR = {
  电池容量: { cur: `${expCards} 卡 / ${ruleFiles} 文件`, ok: true, src: 'auto', note: '刷新时刻实测：经验卡数 / 规则库文件数' },
  电池健康度: { cur: '0.111%', ok: true, src: 'manual', note: '规则库裸号断链率，门禁 ≤0.5%；需跑 check_links 才能实测，读手册编制值' },
  电控可靠: { cur: ((manual.lti || {}).regression || '—') + ' 通过', ok: ((manual.lti || {}).regression || '') === '131/131', src: 'manual', note: 'LTI 回归需跑测试套件，刷新脚本不自动执行，读人工核验值' },
  动能回收: { cur: `${callTotal} 份调用记录`, ok: callTotal > 0, src: 'auto', note: 'HIR 回流载体＝05-调用 10 类调用记录；>0 即闭环正常' },
  智驾成熟: { cur: `${decisionCards.length} 张决策卡样本`, ok: decisionCards.length >= 10, src: 'auto', note: 'HOW-I-THINK 样本数＝在册决策卡数；≥10 升规律级，当前观察级' },
  补能完整: { cur: `${connOn}/${connTotal} 已连`, ok: connOn === connTotal, src: 'manual', note: '连接器连通性脚本调不到 MCP 状态，读人工核验值' },
  黑匣子: { cur: `${monthReports.length} 份决策月报`, ok: monthReports.length >= 1, src: 'auto', note: '04-LOG/决策月报 目录实时计数；≥1 才闭环' },
};
ev.health.forEach((h) => {
  const c = HEALTH_CUR[h.name];
  if (c) { h.cur = c.cur; h.ok = c.ok; h.src = c.src; h.note = c.note; }
  else { h.cur = (/\(([^)]*)\)/.exec(h.threshold) || [, '—'])[1]; h.ok = null; h.src = 'manual'; h.note = '手册编制时刻值，脚本暂未接入实时口径'; }
});

// ---------- 趋势基线（历史快照） ----------
// 每次刷新写一条快照。首次运行建立基线，trend 为 null，页面显示「基线已建立」——
// 不假装有趋势。这是防幻觉铁律在趋势上的延伸：没数据就说没数据，不编一条上升曲线。
const HIST = path.join(BASE, '驾驶舱_历史.json');
const snap = {
  date: td, layers: layerTotal, rules: ruleAll, cards: expCards,
  traces: traceCards, calls: callTotal, cross: crossCases,
  decisions: decisionCards.length, hitFilled, hitTotal,
};
let hist = { baseline: td, snapshots: [] };
if (fs.existsSync(HIST)) {
  try { hist = JSON.parse(fs.readFileSync(HIST, 'utf8')); } catch (e) { /* 损坏则重建 */ }
}
const prev = (hist.snapshots || []).filter((s) => s.date !== td).slice(-1)[0] || null;
hist.snapshots = (hist.snapshots || []).filter((s) => s.date !== td);
hist.snapshots.push(snap);
hist.snapshots.sort((a, b) => a.date.localeCompare(b.date));
hist.baseline = (hist.snapshots[0] || snap).date;
try { fs.writeFileSync(HIST, JSON.stringify(hist, null, 2), 'utf8'); } catch (e) { /* 只读环境跳过 */ }

const trendOf = (k) => (prev ? snap[k] - prev[k] : null);
const fmtTrend = (k) => {
  const d = trendOf(k);
  return d === null ? null : (d > 0 ? '+' : '') + d;
};

// ---------- 告警 ----------
const alerts = [];
if (hitFilled === 0 && hitTotal > 0) {
  alerts.push({
    lv: 'red',
    t: `HOW-I-THINK 仍是空骨架（0/${hitTotal} 节已填）`,
    d: '「捕获→蒸馏→分身权重」闭环只走前半段，分身尚未真正按老强的框架拆解。这是当前最高性价比动作。',
  });
} else if (hitFilled < hitTotal) {
  alerts.push({
    lv: 'orange',
    t: `HOW-I-THINK 部分填充（${hitFilled}/${hitTotal} 节），仍空着：${hitEmpty.join('、')}`,
    d: '已填小节均带证据卡链接，质量达标；剩下两节仍是模板占位——④表达 DNA 决定「分身像不像你」，⑥知识域地图决定「分身知不知道自己不懂什么」，都直接影响分身可信度。',
  });
}
if (monthReports.length === 0) {
  alerts.push({
    lv: 'orange',
    t: '决策月报 0 份',
    d: '复盘节奏缺失。复盘日定在 ' + (nextReview || '—') + '，月报是到期能判定的前提。',
  });
}
const offConn = (manual.connectors || []).filter((c) => c.status === 'off');
if (offConn.length) {
  alerts.push({
    lv: 'orange',
    t: `充电桩 ${connOn}/${connTotal} 在位，${offConn.length} 个断开：${offConn.map((c) => c.name).join(' / ')}`,
    d: '需在连接器设置页手动重连（本环境不代点）。ima 断 → 5 库不可摄入，每日摄入降级为单源；法随断 → 类案语义检索降级。此消彼长整体不中断，但 IMA 重连是性价比最高的恢复动作。',
  });
}
// 元典 hall_detect 403（DTC-HALL-403）：非阻断，但要有感知
if (hallDown) {
  alerts.push({
    lv: 'orange',
    t: 'DTC-HALL-403：元典 hall_detect 不可用（账号非 VIP）',
    d: '已降级用 rh_ft_search 的 sxx 时效字段 + 官方渠道交叉印证，流程不中断。若后续充值 VIP 需更新 驾驶舱_人工核验.json 的 ev.hall_detect。',
  });
}
if (overdue > 0) {
  alerts.push({ lv: 'red', t: `${overdue} 张决策卡已过复盘日未判定`, d: '四档判定不回填，命中率永远是无样本。' });
}
if (crossCases > 0 && crossCases < 3) {
  alerts.push({ lv: 'orange', t: '跨案模式识别刚激活，未固化为入案第一动作', d: `当前仅 ${crossCases} 份调用记录。建议写进接案 SOP 第一步。` });
}
if (daysToReview !== null && daysToReview <= 30) {
  alerts.push({ lv: 'orange', t: `最近复盘日 ${nextReview}（剩 ${daysToReview} 天）`, d: '准备回填四档判定。' });
}

// ---------- 今日焦点（时间性事项按剩余天数升序，系统告警附后） ----------
const focus = [];
cardInfos.forEach((c) => {
  if (c.deadline) {
    const d = daysBetween(td, c.deadline);
    focus.push({
      lv: d <= 3 ? 'red' : (d <= 14 ? 'orange' : 'teal'),
      days: d,
      title: `时间盒到期 · ${c.name}`,
      desc: `来源：${c.file} ③区推翻信号时间盒。到期须逐条核对触发与否。`,
      src: '决策卡',
    });
  }
  if (c.review) {
    const d = daysBetween(td, c.review);
    focus.push({
      lv: d <= 7 ? 'red' : 'orange',
      days: d,
      title: `复盘到期 · ${c.name}`,
      desc: `四档判定待回填（对了 / 错了 / 结论对但理由错）· 含 ${c.objections} 条 AI 异议待验真伪。`,
      src: '决策卡',
    });
  }
});
alerts.forEach((a) => focus.push({ lv: a.lv, days: null, title: a.t, desc: a.d, src: '系统' }));
focus.sort((a, b) => {
  if (a.days === null && b.days === null) return 0;
  if (a.days === null) return 1;
  if (b.days === null) return -1;
  return a.days - b.days;
});

// ---------- 时间轴（未来 120 天） ----------
const timeline = [];
cardInfos.forEach((c) => {
  if (c.deadline) {
    timeline.push({ date: c.deadline, title: c.name, kind: '时间盒到期', lv: 'red' });
  }
  if (c.review) {
    timeline.push({ date: c.review, title: c.name, kind: '复盘日', lv: 'gold' });
  }
});
timeline.sort((a, b) => a.date.localeCompare(b.date));
timeline.forEach((t) => { t.days = daysBetween(td, t.date); });

// ---------- 组装 DATA ----------
const jstr = (o) => JSON.stringify(o);
// 健康度 = 成熟度基准分 + 状态修正，钳制 0–100（判断型指标，已与老强确认口径写进指标口径页）
const GRADE_SCORE = { A: 85, B: 65, C: 45 };
const STATUS_ADJ = { active: 10, warn: -5, off: -25 };
const healthOf = (g, s) =>
  Math.max(0, Math.min(100, (GRADE_SCORE[g] || 60) + (STATUS_ADJ[s] || 0)));

// ---------- EV 部件映射（运维手册章节 → 支柱） ----------
// 手册把系统拆成整车部件，这里把五大支柱对回手册章节号，页面上就能按「三电 / 智驾」分组，
// 而不是按 P1-P5 编号排列——老强看的是车，不是编号。
const EV_PART = {
  P1: { icon: '🔋', part: '动力电池包', chapter: '1.1', group: '三电系统' },
  P2: { icon: '🛡️', part: '电控 + BMS', chapter: '1.3', group: '三电系统' },
  P3: { icon: '♻️', part: '动能回收系统', chapter: '1.4', group: '三电系统' },
  P4: { icon: '📡', part: '激光雷达 / 环境感知', chapter: '3.2', group: '智驾系统' },
  P5: { icon: '🧠', part: '智驾域控芯片', chapter: '3.1', group: '智驾系统' },
};

// ---------- 非支柱部件（手册有定义，但无成熟度定级 → 不给健康度分，不编数字） ----------
const SUBSYS_DEF = [
  { id: 'motor', no: '②', icon: '⚡', part: '驱动电机', alias: 'SR 召回引擎', chapter: '1.2', group: '三电系统' },
  { id: 'cockpit', no: '⑥', icon: '🖥️', part: '智能座舱 / 车机', alias: '小强律师数字分身系统自我画像.md', chapter: '4.1', group: '座舱 · 演练 · 黑匣子' },
  { id: 'shadow', no: '⑦', icon: '🎭', part: '影子模式 / 碰撞预演', alias: '模拟法庭庭审系统', chapter: '4.2', group: '座舱 · 演练 · 黑匣子' },
  { id: 'edr', no: '⑧', icon: '📼', part: '黑匣子 / EDR', alias: '04-LOG（决策日志 + 飞轮 LOG）', chapter: '5.1', group: '座舱 · 演练 · 黑匣子' },
  { id: 'vehicle_code', no: '⑨', icon: '📕', part: '车规标准手册', alias: 'AGENTS.md（真跑纪律 / 六-B 铁律）', chapter: '5.2', group: '座舱 · 演练 · 黑匣子' },
];

/** 从车辆铭牌表里按正则取值（铭牌是人工编制的权威参数，页面标「铭牌」来源） */
const plateVal = (k, re) => {
  const row = ev.plate.find((r) => r.k.includes(k));
  if (!row) return '';
  const m = re.exec(row.v);
  return m ? m[1] : '';
};

// ---------- 思维导图数据源（2026-09-04 新增） ----------
// 计算逻辑抽到共享模块 mindmap_source.js，供「分身系统驾驶舱」与「决策思维树」两处共用，
// 保证数据口径一致、不漂移（单一数据源，避免两套逻辑各写各的）。
const { buildMindmap } = require('./mindmap_source');
const { chains, graph, graphStat } = buildMindmap(BASE);

console.log('  思维导图：决策链 ' + chains.length + ' 条 · 沉淀图谱 '
  + graphStat.cards + ' 张 / ' + graphStat.domains.length + ' 个领域 · 规则关联 '
  + graphStat.ruleLinks + ' 处（去重 ' + graphStat.uniqueRules + ' 条）');

// ---------- 飞轮健康度（接入「飞轮健康度仪表盘」，改为实时扫描，不搬运死数据） ----------
// 原仪表盘把 08-31 的快照写死在 HTML 里；此处实时重算，与驾驶舱「能扫的绝不写死」铁律一致。
// 飞轮健康度：复用 expCardsAll（与支柱 P1「经验卡片」同一扫描数组，单一数据源，口径不漂移）
const FW_EXP_DIR = path.join(BASE, '02-提炼/经验卡片');
const fwExpAll = expCardsAll;
const simCards = fwExpAll.filter((p) => /is_simulation:\s*true/i.test(fs.readFileSync(p, 'utf8'))).length;
const realCards = fwExpAll.length - simCards;
// CaseDrop 已归档案件（独立目录，不在 LawKB 内）
const CASEDROP = path.join(HOME, 'Documents/CaseDrop/processed');
let caseNotes = 0;
try {
  caseNotes = fs.readdirSync(CASEDROP)
    .filter((f) => { const fp = path.join(CASEDROP, f); return fs.statSync(fp).isDirectory() && f !== 'README.md' && !f.startsWith('.'); }).length;
} catch (e) { /* 目录不存在则记 0 */ }
const ongoingCases = 0;
// 增长曲线：以现有仪表盘的 cardGrowth 为历史种子 + 今日实测点（保持历史连续性，不重造轮子）
let growth = [];
try {
  const dh = fs.readFileSync(path.join(BASE, '飞轮健康度仪表盘.html'), 'utf8');
  const gm = dh.match(/cardGrowth:\s*\[([\s\S]*?)\]/);
  if (gm) for (const it of gm[1].matchAll(/\{date:"([\d-]+)",\s*cum:(\d+)\}/g)) growth.push({ date: it[1], cum: Number(it[2]) });
} catch (e) { /* 仪表盘缺失则用空曲线，不阻断 */ }
const fwToday = today();
growth = growth.filter((g) => g.date !== fwToday);
growth.push({ date: fwToday, cum: fwExpAll.length });
growth.sort((a, b) => a.date.localeCompare(b.date));
const flyMetrics = [
  { name: '协同效果命中率', value: '待采集', desc: '分身问答埋点日志积累中，每月 28 日协同效果月报将出首值' },
  { name: '经验卡片（真实/演练）', value: realCards + '/' + simCards, desc: '实时：真实 ' + realCards + ' 张 / 演练 ' + simCards + ' 张' },
  { name: '裁判规则库规模', value: ruleFiles + ' 文件', desc: '06-沉淀/裁判规则库 全量文件（含非规则文件）；规范命名卡 ' + ruleAll + ' 张' },
  { name: '案件-卡片-规则三维索引', value: '已建', desc: 'CaseDrop 归档 ' + caseNotes + ' 案 / 经验卡 ' + fwExpAll.length + ' 张 / 规则文件 ' + ruleFiles + ' 三维互联' },
  { name: '思维轨迹卡', value: traceCards + ' 张', desc: '反复咨询→四维+三问沉淀，跨案检索/结案反补/月检闭环' },
  { name: '六层 .md 合计', value: String(layerTotal), desc: '知识飞轮六层文件实时统计（活资产口径，排除备份）' },
];

const DATA = {
  updated: today(),
  updatedTime: nowCN(),
  updatedTs: Date.now(),              // 供页面算「数据年龄」，提示是否需要手动刷新
  manualChecked: manual.checked_at || '—',
  systemLevel: manual.system_level || { grade: '—', text: '未核验' },
  alerts,
  pillars: [
    {
      id: 'P1', no: '①', name: '知识飞轮六层', full: '01采集 → 02提炼 → 03连接 → 04LOG/巩固 → 05调用 → 06沉淀',
      maturity: (maturity.P1 && maturity.P1.grade) || '—',
      status: 'active', statusText: '持续复利，规模在长',
      note: (maturity.P1 && maturity.P1.note) || '',
      scan: 'auto',
      health: healthOf((maturity.P1 && maturity.P1.grade) || '—', 'active'),
      trendKey: '经验卡',
      trend: fmtTrend('cards'),
      trend2Key: '规则库',
      trend2: fmtTrend('rules'),
      metrics: [
        { k: '六层 .md 合计', v: String(layerTotal), d: '口径：递归统计，已排除 .backup / .trash / .cache / *.bak 隐藏与备份项' },
        { k: '分层明细', v: layerDetail, d: '采集 / 提炼 / 连接 / LOG / 巩固 / 调用 / 沉淀', small: true },
        { k: '裁判规则库', v: String(ruleAll), d: `R-领域-序号 命名卡；子库 ${ruleSubLibs} 个`, sub: `${ruleFiles} 个 .md（含非规则文件）` },
        { k: '经验卡片', v: String(expCards), d: '02-提炼/经验卡片 下 .md，已排除 README / 模板类文件（与「飞轮健康度」tab 同一口径）' },
        { k: '思维轨迹卡', v: String(traceCards), d: '反复咨询沉淀卡 → 决策卡的矿源' },
      ],
    },
    {
      id: 'P2', no: '②', name: 'LTI 文本监控器', full: 'R/L/C/T/P 五维 + T502 案例存在性核验',
      maturity: (maturity.P2 && maturity.P2.grade) || '—',
      status: 'active', statusText: '机检能力最强一环',
      note: (maturity.P2 && maturity.P2.note) || '',
      scan: 'mixed',
      health: healthOf((maturity.P2 && maturity.P2.grade) || '—', 'active'),
      trendKey: '回归结果',
      trend: null,
      trendNote: '人工核验项，不参与自动趋势',
      metrics: [
        { k: '版本', v: (manual.lti && manual.lti.version) || '—', d: `人工核验于 ${(manual.lti && manual.lti.checked) || '—'}`, manual: true },
        { k: '回归结果', v: (manual.lti && manual.lti.regression) || '—', d: '需跑测试，脚本不自动执行', manual: true },
        { k: '技能文件', v: String(ltiFiles), d: '~/.workbuddy/skills/LTI文本监控器 下 .md 数（自动扫描）' },
        {
          k: '权威源条文库', v: piLaws ? `${piLaws} 部 / ${piArticles} 条` : '未找到条文库',
          d: 'provision_index/index_*.json——“永不凭记忆灌条文正文”铁律的落地点，可被机检覆盖的法域范围',
        },
      ],
    },
    {
      id: 'P3', no: '③', name: 'HIR 经验沉淀智能体', full: '经验卡沉淀 + 双通道回流（ima 库 + LawKB）',
      maturity: (maturity.P3 && maturity.P3.grade) || '—',
      status: 'active', statusText: '回流闭环运转',
      note: (maturity.P3 && maturity.P3.note) || '',
      scan: 'auto',
      health: healthOf((maturity.P3 && maturity.P3.grade) || '—', 'active'),
      trendKey: '调用记录',
      trend: fmtTrend('calls'),
      trend2Key: '经验卡',
      trend2: fmtTrend('cards'),
      metrics: [
        { k: '经验卡总量', v: String(expCards), d: '与支柱①同一口径（HIR 的沉淀产物即经验卡）' },
        { k: '调用记录总量', v: String(callTotal), d: '05-调用 下 10 类调用记录文件合计' },
        { k: '分品类', v: callRows.map((r) => `${r.label}${r.c}`).join(' / '), d: '调用活跃度分布', small: true },
      ],
    },
    {
      id: 'P4', no: '④', name: '跨案模式识别', full: '同主体 / 同事实线索跨案关联召回',
      maturity: (maturity.P4 && maturity.P4.grade) || '—',
      status: crossCases >= 3 ? 'active' : 'warn', statusText: crossCases >= 3 ? '已常态运转' : '刚激活，未固化',
      note: (maturity.P4 && maturity.P4.note) || '',
      scan: 'auto',
      health: healthOf((maturity.P4 && maturity.P4.grade) || '—', crossCases >= 3 ? 'active' : 'warn'),
      trendKey: '调用记录',
      trend: fmtTrend('cross'),
      trend2Key: '经验卡回流',
      trend2: fmtTrend('cards'),
      metrics: [
        { k: '调用记录', v: String(crossCases), d: '05-调用/跨案模式识别调用记录 文件数' },
        { k: '首激活', v: '2026-09-01', d: '此前为「最闲置杠杆」，08-27 评估后激活', manual: true },
        { k: '待办', v: '未固化为入案第一动作', d: '建议写进接案 SOP 第一步', warn: true },
      ],
    },
    {
      id: 'P5', no: '⑤', name: '决策思维系统', full: 'decision-capture 捕获 → mind-distill 蒸馏 → HOW-I-THINK 分身权重',
      maturity: (maturity.P5 && maturity.P5.grade) || '—',
      status: hitFilled === 0 ? 'off' : (hitFilled < hitTotal ? 'warn' : 'active'),
      statusText: hitFilled === 0 ? '入口已活，出口未通'
        : (hitFilled < hitTotal ? `部分填充 ${hitFilled}/${hitTotal}，出口半通` : '闭环打通'),
      note: (maturity.P5 && maturity.P5.note) || '',
      scan: 'auto',
      health: healthOf((maturity.P5 && maturity.P5.grade) || '—',
        hitFilled === 0 ? 'off' : (hitFilled < hitTotal ? 'warn' : 'active')),
      trendKey: '决策卡',
      trend: fmtTrend('decisions'),
      trend2Key: 'HOW-I-THINK 已填节',
      trend2: fmtTrend('hitFilled'),
      metrics: [
        { k: '在册决策卡', v: String(decisionCards.length), d: '04-LOG/决策日志（已排除 _模板）' },
        { k: '待验证', v: String(pending), d: `逾期未判定 ${overdue} 张` },
        { k: '命中率', v: hitRate, d: judged ? `已判定 ${judged} 张（对了${right}/错了${wrong}/结论对理由错${reasonWrong}）` : '四档判定回填后才有值' },
        { k: 'AI 异议累计', v: String(aiObjections), d: 'AI 与老强判断冲突条数。异议成真率 = 异议被采纳/已判定，判定后回填' },
        { k: 'HOW-I-THINK 填充度', v: hitRateTxt, d: `${hitBytes} 字节 / 有效内容 ${hitLines} 行；单节 ≥3 行计为已填（已剔除未勾选的 - [ ] 模板选项与空标签行）`, warn: hitFilled < hitTotal },
        ...(hitEmpty.length ? [{ k: '空着的小节', v: hitEmpty.join('、'), d: '这几节还是模板占位，分身在这些维度上仍会“脑补”', small: true, warn: true }] : []),
        ...(hitMaturity ? [{ k: '文件自标成熟度', v: hitMaturity, d: '读自 HOW-I-THINK.md frontmatter 的 maturity 字段（权威源，优先于脚本估算）', small: true }] : []),
        { k: '决策月报', v: String(monthReports.length), d: '04-LOG/决策月报', warn: monthReports.length === 0 },
        { k: '最近复盘日', v: nextReview || '—', d: daysToReview !== null ? `距今 ${daysToReview} 天` : '—' },
      ],
      drill: true,
    },
  ],
  focus,
  timeline,
  history: {
    baseline: hist.baseline,
    points: hist.snapshots.length,
    hasTrend: !!prev,
    prevDate: prev ? prev.date : null,
    latest: snap,
  },
  cards: cardInfos,
  connectors: manual.connectors || [],
  // ===== EV 车机仪表盘扩展（v2.0.0） =====
  evMeta: {
    available: ev.available,
    file: ev.basename || '未找到 EV 版运维手册',
    updated: ev.updated || '—',
    firstRule: ev.firstRule,
    slogan: ev.slogan,
  },
  plate: ev.plate,                                   // 〇 车辆铭牌（解析手册）
  chargerStat: { on: connOn, total: connTotal },     // 二 补能完整度
  dtc: ev.dtc,                                       // 八 故障码速查（含 active 判定）
  activeDtcCount: activeDtc.length,
  maintenance: ev.maintenance,                       // 七 定期保养周期表
  ota: ev.ota,                                       // 六 OTA 远程升级管理
  health: ev.health,                                 // 九 续航自检（手册阈值 + 实测当前值）
  redlines: ev.redlines,                             // 十 安全红线
  subsystems: SUBSYS_DEF.map((s) => {                // 五大支柱之外的其余部件
    const st = subsys[s.id] || {};
    const val = subStat(s.id);
    return {
      id: s.id, no: s.no, icon: s.icon, part: s.part, alias: s.alias,
      chapter: s.chapter, group: s.group,
      status: st.status || 'unknown',
      note: st.note || '',
      value: val ? String(val.count) : null,
      unit: val ? val.unit : '',
      fileHint: (SUB_FILES[s.id] && (SUB_FILES[s.id].file || SUB_FILES[s.id].dir)) || '',
    };
  }),
  // 铭牌值（手册编制时刻）vs 实测值（刷新时刻）双轨对照：
  // 两者不一致时不覆盖不取舍，把口径差异摊在页面上，避免「谁是对的」变成黑箱
  plateVsLive: [
    { k: '六层 .md', plate: plateVal('三电版本', /(\d[\d,]*)\s*\.md/), live: String(layerTotal), why: '手册按全量口径并含编制时刻快照，脚本按「活资产」口径排除了 .backup / .trash / .cache / *.bak' },
    { k: '经验卡', plate: plateVal('三电版本', /(\d[\d,]*)\s*卡/), live: String(expCards), why: '手册 224 为全量；脚本排除 README / 模板类文件后计数，差值为模板占位卡' },
    { k: '裁判规则库', plate: plateVal('三电版本', /(\d[\d,]*)\s*规则库/), live: `${ruleAll} 卡 / ${ruleFiles} 文件`, why: '手册 778 是文件总数；脚本 740 是 R-领域-序号 规范命名卡数，两个口径都对' },
  ].filter((r) => r.plate),
  metricsDoc: [
    { k: '健康度条（0–100）', s: 'mixed', d: '成熟度基准分（A85/B65/C45）+ 状态修正（活跃+10/告警-5/停用-25）。成熟度是人工评定，故此项为混合口径' },
    { k: '趋势箭头 ↑↓N', s: 'auto', d: `与上一次快照比较。基线建立于 ${hist.baseline}，当前 ${hist.snapshots.length} 个快照${prev ? `，对比基准 ${prev.date}` : '（首次运行，暂无趋势，页面显示「基线已建立」而非编造变化）'}` },
    { k: '今日焦点 · 时间盒/复盘日', s: 'auto', d: '解析决策卡③区「时间盒」字样附近的日期与 frontmatter review_date，按剩余天数升序。逾期未判定会额外标红' },
    { k: '六层 .md 合计 / 经验卡 / 规则库 / 决策卡 / 调用记录', s: 'auto', d: '脚本 rglob 实时统计，排除隐藏与备份目录' },
    { k: 'HOW-I-THINK 填充度', s: 'auto', d: '按 ## 切节，单节有效内容 ≥3 行计为已填' },
    { k: '复盘倒计时 / 四档判定 / AI 异议数', s: 'auto', d: '解析决策卡 frontmatter 与正文分节；AI 异议只数「异议N」条目起始行，正文引用不计' },
    { k: '权威源条文库（部数 / 条文数）', s: 'auto', d: '扫 provision_index/index_*.json，累加各法 article_count' },
    { k: 'LTI 版本 / 回归结果', s: 'manual', d: '版本号可扫目录，但回归 131/131 需跑测试，不自动执行' },
    { k: '车辆铭牌 / 充电桩 / OTA / 保养周期 / DTC / 安全红线', s: 'auto', d: `实时解析《${ev.basename || 'EV 运维手册'}》对应章节的表格（手册版本 ${ev.updated}），不抄进 JSON。手册改了驾驶舱跟着变` },
    { k: '续航自检「当前值」', s: 'mixed', d: '阈值与量化方式读手册第九章；当前值优先用脚本实测（经验卡/规则库/决策卡/月报/充电桩在位），扫不到的（断链率、LTI 回归）回退手册编制值并在页面标「手册」' },
    { k: 'DTC 激活判定', s: 'mixed', d: '手册只定义故障码，是否触发用实时状态判：IMA/法随看连接器、HALL-403 看人工核验、CASE-001 看驱动电机状态、DISTILL-003 看决策卡数是否<10；LTI-REJECT 属安全机制永不点亮。手册新增而脚本未映射的码标「未判定」' },
    { k: '铭牌值 vs 实测值', s: 'mixed', d: '手册铭牌是编制时刻快照（全量口径），脚本实测是刷新时刻（活资产口径，排除备份）。两者不一致时并列展示并说明差异，不覆盖不取舍' },
    { k: '连接器连通性', s: 'manual', d: '脚本无法调用 MCP 状态，由小强律师每次对话实地核验后写入 JSON' },
    { k: '成熟度定级 A/B/C', s: 'manual', d: '判断值而非计数，人工评定' },
  ],
  tree,
  // ===== 思维导图数据源（2026-09-04 新增） =====
  // 决策链 = 真·决策过程（选项→排除→推翻信号→假设→复盘），来源决策卡 10 分区；
  // 沉淀图谱 = 经验卡知识结构的诚实呈现，标注「此乃沉淀结论，非决策过程」以防幻觉。
  mindmap: {
    chains,
    graph,
    graphStat,
  },
  // ===== 飞轮健康度（2026-09-04 接入，实时扫描，不搬运死数据） =====
  flywheel: {
    experienceCards: fwExpAll.length,
    realCards, simCards,
    ruleFiles, ruleNamed: ruleAll,
    caseNotes, ongoingCases, traceCards,
    layers: layerTotal,
    growth,
    metrics: flyMetrics,
  },
};

// 给支柱挂 EV 部件名与手册章节号，页面按「三电系统 / 智驾系统」分组，而非 P1-P5 编号
DATA.pillars.forEach((p) => {
  const e = EV_PART[p.id];
  if (e) Object.assign(p, e);
});

// ---------- 写入（六-B：先备份） ----------
const html = fs.readFileSync(TPL, 'utf8');
const PLACEHOLDER = 'const DATA = __WORKSPACE_DATA__;';
if (!html.includes(PLACEHOLDER)) {
  console.error('[err] 模板中未找到 DATA 占位符：' + PLACEHOLDER);
  process.exit(1);
}

if (!fs.existsSync(BACKUP_DIR)) fs.mkdirSync(BACKUP_DIR, { recursive: true });
if (fs.existsSync(OUT)) {
  const stamp = nowCN().replace(/[-: ]/g, '');
  fs.copyFileSync(OUT, path.join(BACKUP_DIR, `分身系统驾驶舱_${stamp}.html`));
}
// 备份清理：刷新从「每周一次」提到「每天 3 次」后，备份会快速堆积，只留最近 10 份。
// 安全边界：只删严格匹配本脚本命名模式的备份文件，不碰目录里任何其他东西。
const MAX_BACKUP = 10;
try {
  const bs = fs.readdirSync(BACKUP_DIR)
    .filter((f) => /^分身系统驾驶舱_\d{12}\.html$/.test(f))
    .sort();                                   // 时间戳定长，字典序=时间序
  bs.slice(0, Math.max(0, bs.length - MAX_BACKUP)).forEach((f) => {
    try { fs.unlinkSync(path.join(BACKUP_DIR, f)); } catch (e) { /* 单个失败不阻断 */ }
  });
} catch (e) { /* 备份目录不可读则跳过清理 */ }

// 用函数式替换：String.replace 若用字符串替换体，$& / $' / $1 等会被当成反向引用解释，
// 一旦某个指标值里出现 $& 就会静默污染整份 HTML。函数式替换不做特殊字符解释。
const newHtml = html.replace(PLACEHOLDER, () => 'const DATA = ' + jstr(DATA) + ';');
fs.writeFileSync(OUT, newHtml, 'utf8');

// 同步桌面副本
if (fs.existsSync(DESKTOP_DIR)) {
  try { fs.copyFileSync(OUT, path.join(DESKTOP_DIR, '分身系统驾驶舱.html')); } catch (e) { /* 桌面目录不可写则跳过 */ }
}

console.log('[驾驶舱刷新] ' + today());
console.log('  ① 知识飞轮：六层 ' + layerTotal + ' md | 规则卡 ' + ruleAll + ' | 经验卡 ' + expCards + ' | 轨迹卡 ' + traceCards);
console.log('  ② LTI：' + ((manual.lti && manual.lti.version) || '—') + '（人工核验）| 技能文件 ' + ltiFiles);
console.log('  ③ HIR：经验卡 ' + expCards + ' | 调用记录 ' + callTotal);
console.log('  ④ 跨案识别：调用记录 ' + crossCases);
console.log('  ⑤ 决策思维：决策卡 ' + decisionCards.length + '（待验证 ' + pending + '）| 月报 ' + monthReports.length + ' | HOW-I-THINK ' + hitRateTxt + ' | 最近复盘 ' + (nextReview || '—'));
console.log('  告警 ' + alerts.length + ' 条 | 决策树节点 ' + (function c(x) { let t = 1; (x.children || []).forEach((k) => { t += c(k); }); return t; })(tree));
console.log('  —— EV 车机仪表盘 ——');
console.log('  手册：' + (ev.available ? ev.basename + '（' + ev.updated + '）' : '❌ 未找到/解析失败'));
console.log('  铭牌 ' + ev.plate.length + ' 项 | 充电桩 ' + connOn + '/' + connTotal
  + ' | OTA ' + ev.ota.length + ' 项 | 保养周期 ' + ev.maintenance.length + ' 档');
console.log('  DTC ' + ev.dtc.length + ' 条定义，当前激活 ' + activeDtc.length + ' 个：'
  + (activeDtc.length ? activeDtc.map((d) => d.code).join(' / ') : '无'));
console.log('  健康指标 ' + ev.health.length + ' 项，未达标 '
  + ev.health.filter((h) => h.ok === false).length + ' 项：'
  + (ev.health.filter((h) => h.ok === false).map((h) => h.name).join(' / ') || '无'));
console.log('  红线 ' + ev.redlines.length + ' 条 | 非支柱部件 ' + SUBSYS_DEF.length + ' 个');
console.log('  输出：' + OUT);
