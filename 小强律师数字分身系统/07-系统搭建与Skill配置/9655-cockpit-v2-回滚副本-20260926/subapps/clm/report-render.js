/* =============================================================
 * report-render.js · 当事人可视化报告（Harvey Command Center 风格）
 * 六段式：①执行摘要 ②案件里程碑时间线 ③当前阶段进度 ④本期关键进展
 *          ⑤下一步动作 ⑥费用与期限 + 风险提示(脱敏)
 * 对当事人友好版：展示阶段/时间线/下一步/下次开庭/费用进度，
 *   隐藏内部策略(stance)、风险敞口(risks 内部版)、智能体挂载(meta/agents)。
 * 案号、委托人姓名脱敏。单一模板源，供 #viewClient 与 report.html 复用。
 * ============================================================= */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function redactCaseNo(no) {
    if (!no) return "（案号已脱敏）";
    var m = String(no).match(/^(.*?民[初终])\d+/);
    return m ? m[1] + "****号" : "（案号已脱敏）";
  }

  // 内部字眼过滤：含这些词的文本/事件不向当事人展示
  var INTERNAL_HINT = ["老强拍板", "红蓝", "程序战", "版本混乱", "自认", "冒名", "驳回起诉", "平行备位", "门禁", "LTI"];
  // 同时兼容「字符串(如 nextActions)」与「对象(如 timeline 事件)」两种入参
  function safeText(t) {
    if (t == null) return "";
    if (typeof t === "string") return t;
    // timeline 事件对象：拼接所有可展示文本字段
    return [t.event, t.note, t.title, t.name, t.desc, t.detail, t.summary]
      .filter(function (x) { return x; }).join(" ");
  }
  function isClientSafe(t) {
    var s = safeText(t);
    if (!s) return true; // 空内容不视为泄漏，可展示
    for (var i = 0; i < INTERNAL_HINT.length; i++) {
      if (s.indexOf(INTERNAL_HINT[i]) >= 0) return false;
    }
    return true;
  }

  var STYLE = [
    ".creport{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;color:#e9ecf1;max-width:920px;margin:0 auto;padding:8px 4px}",
    ".creport .cr-head{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;flex-wrap:wrap;padding:18px 20px;background:linear-gradient(135deg,rgba(55,138,221,.16),rgba(29,158,117,.10));border:1px solid rgba(55,138,221,.35);border-radius:16px;margin-bottom:16px}",
    ".creport .cr-title{font-size:19px;font-weight:700;letter-spacing:.4px;line-height:1.4}",
    ".creport .cr-sub{font-size:12.5px;color:#9aa3b2;margin-top:6px}",
    ".creport .cr-badge{display:inline-block;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600;background:rgba(29,158,117,.16);color:#5DCAA5;border:1px solid rgba(29,158,117,.4);white-space:nowrap}",
    ".creport .cr-sec{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.09);border-radius:14px;padding:16px 18px;margin-bottom:14px}",
    ".creport .cr-h{font-size:14px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:8px;color:#fff}",
    ".creport .cr-h::before{content:'';width:4px;height:15px;background:#378ADD;border-radius:2px}",
    ".creport .cr-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}",
    ".creport .cr-kpi{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.10);border-radius:10px;padding:11px 13px}",
    ".creport .cr-kpi .n{font-size:16px;font-weight:700;color:#9CC7F0}",
    ".creport .cr-kpi .l{font-size:11.5px;color:#9aa3b2;margin-top:2px}",
    ".creport .cr-tl{position:relative;padding-left:22px}",
    ".creport .cr-tl::before{content:'';position:absolute;left:6px;top:4px;bottom:4px;width:2px;background:rgba(255,255,255,.12)}",
    ".creport .cr-ev{position:relative;padding:7px 0 7px 4px}",
    ".creport .cr-ev::before{content:'';position:absolute;left:-19px;top:11px;width:10px;height:10px;border-radius:50%;background:#378ADD;border:2px solid #0b0d12}",
    ".creport .cr-ev .d{font-size:12px;color:#9CC7F0;font-weight:600}",
    ".creport .cr-ev .e{font-size:13px;color:#d6dbe4;margin-top:1px;line-height:1.5}",
    ".creport .cr-step{display:flex;gap:4px;margin:6px 0 4px}",
    ".creport .cr-st{flex:1;text-align:center;font-size:11px;padding:7px 2px;border-radius:7px;background:rgba(255,255,255,.04);color:#9aa3b2;border:1px solid transparent;line-height:1.3}",
    ".creport .cr-st.done{background:rgba(29,158,117,.13);color:#5DCAA5}",
    ".creport .cr-st.cur{background:rgba(55,138,221,.22);color:#B5D4F4;border-color:rgba(55,138,221,.55);font-weight:700}",
    ".creport .cr-bar{height:9px;border-radius:5px;background:rgba(255,255,255,.08);overflow:hidden;margin:10px 0 4px}",
    ".creport .cr-fill{height:100%;background:linear-gradient(90deg,#378ADD,#1D9E75);border-radius:5px}",
    ".creport .cr-barlbl{font-size:11.5px;color:#9aa3b2;display:flex;justify-content:space-between}",
    ".creport ul.cr-list{list-style:none;margin:0;padding:0}",
    ".creport ul.cr-list li{font-size:13px;color:#d6dbe4;padding:5px 0 5px 22px;position:relative;line-height:1.55;border-bottom:1px solid rgba(255,255,255,.05)}",
    ".creport ul.cr-list li:last-child{border-bottom:none}",
    ".creport ul.cr-list li.ok::before{content:'✓';position:absolute;left:2px;top:5px;color:#5DCAA5;font-weight:700}",
    ".creport ul.cr-list li.act::before{content:'➤';position:absolute;left:2px;top:5px;color:#9CC7F0;font-weight:700}",
    ".creport .cr-dl{font-size:13px}",
    ".creport .cr-dl-row{display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.06)}",
    ".creport .cr-dl-row:last-child{border-bottom:none}",
    ".creport .cr-dl-date{color:#FAC775;font-weight:600;white-space:nowrap;font-size:12.5px}",
    ".creport .cr-dl-name{color:#d6dbe4}",
    ".creport .cr-note{font-size:12px;color:#9aa3b2;background:rgba(239,159,39,.08);border:1px solid rgba(239,159,39,.25);border-radius:10px;padding:11px 13px;line-height:1.6}",
    ".creport .cr-foot{font-size:11px;color:#7c8696;text-align:center;padding:12px 0 4px}",
    ".creport .cr-empty{color:#9aa3b2;font-size:13px;padding:6px 0}"
  ].join("");

  function ensureStyle() {
    if (window.__creportStyleInjected) return;
    var st = document.createElement("style");
    st.id = "creport-style";
    st.textContent = STYLE;
    document.head.appendChild(st);
    window.__creportStyleInjected = true;
  }

  function fmtDate(d) {
    if (!d) return "—";
    return String(d);
  }

  function renderClientReport(c, ctx) {
    ctx = ctx || {};
    var stageNames = ctx.stageNames || ["①接案建档", "②检索研究", "③文书起草", "④庭审查庭", "⑤客户协作", "⑥程序执行", "⑦风控归档"];
    ensureStyle();
    if (!c) return '<div class="creport"><div class="cr-empty">未找到该案件数据。</div></div>';
    var st = c.stage || {};
    var cur = (typeof st.current === "number") ? st.current : 1;
    var pct = Math.round((cur - 1) / (stageNames.length - 1) * 100);
    var pub = c.publicView || {};

    /* ① 执行摘要 */
    var summary = isClientSafe(pub.stageText)
      ? (pub.stageText || (st.name ? ("当前处于「" + st.name + "」阶段") : "案件办理中"))
      : "案件正在按既定方案有序推进，重大进展将及时同步。";
    var roleTxt = [c.partyRole, c.counselRole].filter(Boolean).join(" · ");
    var head =
      '<div class="cr-head">' +
        '<div>' +
          '<div class="cr-title">' + esc(redactCaseNo(c.caseNo)) + '</div>' +
          '<div class="cr-sub">' + esc(c.court || "") + (c.judge ? " · " + esc(c.judge) : "") + '</div>' +
          '<div class="cr-sub" style="margin-top:4px">我方地位：' + esc(roleTxt || "—") + ' ｜ 案由：' + esc(c.domain || "—") + ' ｜ 程序：' + esc(c.procedure || "—") + '</div>' +
        '</div>' +
        '<span class="cr-badge">' + esc(c.status || "办理中") + '</span>' +
      '</div>';

    var sec1 =
      '<div class="cr-sec"><div class="cr-h">① 执行摘要</div>' +
        '<div class="cr-kpis">' +
          '<div class="cr-kpi"><div class="n">' + esc(st.name || "—") + '</div><div class="l">当前阶段</div></div>' +
          '<div class="cr-kpi"><div class="n">' + esc(c.procedure || "—") + '</div><div class="l">审理程序</div></div>' +
          '<div class="cr-kpi"><div class="n">' + esc(roleTxt || "—") + '</div><div class="l">我方地位</div></div>' +
          '<div class="cr-kpi"><div class="n">' + esc(c.updatedAt || "—") + '</div><div class="l">最近更新</div></div>' +
        '</div>' +
        '<div style="margin-top:12px;font-size:13.5px;color:#d6dbe4;line-height:1.7">' + esc(summary) + '</div>' +
      '</div>';

    /* ② 案件里程碑时间线（过滤含内部策略/风险字眼的时间线事件，避免向当事人泄漏） */
    var tl = (c.timeline || []).filter(isClientSafe).slice().sort(function (a, b) { return String(a.date) < String(b.date) ? -1 : 1; });
    var tlHtml = tl.length
      ? tl.map(function (t) {
          return '<div class="cr-ev"><div class="d">' + esc(t.date || "—") + '</div><div class="e">' + esc(t.event || "") + '</div></div>';
        }).join("")
      : '<div class="cr-empty">暂无里程碑记录。</div>';
    var sec2 =
      '<div class="cr-sec"><div class="cr-h">② 案件里程碑时间线</div><div class="cr-tl">' + tlHtml + '</div></div>';

    /* ③ 当前阶段进度 */
    var steps = stageNames.map(function (nm, idx) {
      var n = idx + 1;
      var cls = n < cur ? "done" : (n === cur ? "cur" : "");
      return '<div class="cr-st ' + cls + '">' + esc(nm) + '</div>';
    }).join("");
    var sec3 =
      '<div class="cr-sec"><div class="cr-h">③ 当前阶段进度</div>' +
        '<div class="cr-step">' + steps + '</div>' +
        '<div class="cr-bar"><div class="cr-fill" style="width:' + pct + '%"></div></div>' +
        '<div class="cr-barlbl"><span>立案</span><span>整体进度 ' + pct + '%</span><span>结案</span></div>' +
        (st.note ? '<div style="margin-top:8px;font-size:12px;color:#9aa3b2;line-height:1.6">📌 ' + esc(st.note) + '</div>' : '') +
      '</div>';

    /* ④ 本期关键进展 */
    var done = (pub.done || []).filter(isClientSafe);
    var progHtml = done.length
      ? '<ul class="cr-list">' + done.map(function (x) { return '<li class="ok">' + esc(x) + '</li>'; }).join("") + '</ul>'
      : (tl.length
          ? '<ul class="cr-list">' + tl.slice(-4).map(function (t) { return '<li class="ok">' + esc(t.date + ' · ' + t.event) + '</li>'; }).join("") + '</ul>'
          : '<div class="cr-empty">暂无进展记录。</div>');
    var sec4 =
      '<div class="cr-sec"><div class="cr-h">④ 本期关键进展</div>' + progHtml + '</div>';

    /* ⑤ 下一步动作（合并 pub.next / nextActions / clientTodo，逐条过滤内部字眼） */
    var nextList = [];
    if (pub.next && isClientSafe(pub.next)) nextList.push(pub.next);
    (c.nextActions || []).filter(isClientSafe).slice(0, 3).forEach(function (x) { if (nextList.indexOf(x) < 0) nextList.push(x); });
    (pub.clientTodo || []).filter(isClientSafe).forEach(function (x) { if (nextList.indexOf(x) < 0) nextList.push(x); });
    var nextHtml = nextList.length
      ? '<ul class="cr-list">' + nextList.map(function (x) { return '<li class="act">' + esc(x) + '</li>'; }).join("") + '</ul>'
      : '<div class="cr-empty">暂未排定下一步。</div>';
    var sec5 =
      '<div class="cr-sec"><div class="cr-h">⑤ 下一步动作</div>' + nextHtml + '</div>';

    /* ⑥ 费用与期限 + 风险提示(脱敏) */
    var dls = (c.deadlines || []).filter(function (d) { return d && d.due && d.state !== "done"; });
    dls.sort(function (a, b) { return String(a.due) < String(b.due) ? -1 : 1; });
    var dlHtml = dls.length
      ? dls.slice(0, 5).map(function (d) {
          return '<div class="cr-dl-row"><span class="cr-dl-date">' + esc(d.due) + '</span><span class="cr-dl-name">' + esc(d.name || "") + '</span></div>';
        }).join("")
      : '<div class="cr-empty">近期暂无明确期限节点。</div>';
    var feeTxt = (c.meta && c.meta.fee) ? esc(c.meta.fee) : "（具体费用以《委托代理协议》约定为准）";
    var riskNote = "🔒 本案正按既定方案有序推进，重大进展将及时同步。如对办理进展有疑问，可随时联系经办律师。案件信息已脱敏处理，仅向本案当事人开放。";
    var sec6 =
      '<div class="cr-sec"><div class="cr-h">⑥ 费用与期限 · 风险提示（脱敏）</div>' +
        '<div class="cr-dl" style="margin-bottom:12px">' + dlHtml + '</div>' +
        '<div style="font-size:12.5px;color:#9aa3b2;margin-bottom:10px">💰 费用说明：' + feeTxt + '</div>' +
        '<div class="cr-note">' + esc(riskNote) + '</div>' +
      '</div>';

    var foot = '<div class="cr-foot">🔒 只读脱敏视图 · 数据更新 ' + esc(c.updatedAt || "—") + ' · 小强律师数字分身系统</div>';

    var html = '<div class="creport">' + head + sec1 + sec2 + sec3 + sec4 + sec5 + sec6 + foot + '</div>';
    /* 委托人姓名脱敏：将本案委托人姓名统一替换为「您方」，避免链接外传时暴露当事人身份 */
    (c.client || []).filter(Boolean).forEach(function (nm) {
      html = html.split(nm).join("您方");
    });
    return html;
  }

  window.renderClientReport = renderClientReport;

  // 暴露内联样式，供「导出单文件 HTML」复用
  window.CREPORT_STYLE = STYLE;

  // 生成完全自包含的独立 HTML 文档（内联全部样式 + 该案件渲染结果，无任何外部依赖）。
  // 下载后可用任意浏览器离线打开，亦可直接作为文件通过微信/邮件发送给当事人，彻底不依赖服务器与网络。
  window.buildStandaloneReport = function (c, ctx) {
    var inner = renderClientReport(c, ctx);
    return '<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
      + '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
      + '<title>' + esc(redactCaseNo(c.caseNo)) + ' · 案件可视化报告</title>\n'
      + '<style>\n'
      + 'body{margin:0;background:#0b0d12;padding:18px 12px;font-family:-apple-system,\'PingFang SC\',\'Microsoft YaHei\',sans-serif}\n'
      + STYLE + '\n'
      + '</style>\n</head>\n<body>\n' + inner + '\n</body>\n</html>';
  };
})();
