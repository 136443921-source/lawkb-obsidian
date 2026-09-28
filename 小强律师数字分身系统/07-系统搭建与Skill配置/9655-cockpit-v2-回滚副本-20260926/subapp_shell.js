/* ============================================================
   9655 单机驾驶舱 · 子屏 9360 风格渲染器
   按 body[data-cno] 取 scorecard_data.json 真实切片，渲染 9360 风格仪表盘。
   数据字段（零虚构）：score / six(六维) / kpis / gaps / flag / risk / panels(扩展)
   配色与组件对齐 9360 子屏模板（见 subapp_shell.css）。
   ============================================================ */
(function () {
  "use strict";

  var DIM_LABELS = {
    fresh: "数据新鲜度", coverage: "覆盖完备度", health: "运行健康度",
    output: "产出有效性", compliance: "安全合规度", automation: "自动化程度"
  };
  var DIM_COLORS = {
    fresh: "#378ADD", coverage: "#1D9E75", health: "#7F77DD",
    output: "#34d399", compliance: "#E24B4A", automation: "#EF9F27"
  };

  function gradeOf(v) {
    if (v >= 90) return { t: "A 优秀", c: "#34d399" };
    if (v >= 75) return { t: "B 良好", c: "#1D9E75" };
    if (v >= 60) return { t: "C 合格", c: "#378ADD" };
    if (v >= 45) return { t: "D 待改进", c: "#EF9F27" };
    return { t: "E 高危", c: "#E24B4A" };
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>]/g, function (m) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[m];
    });
  }

  // 按值/状态文字判定 KPI / 模块配色
  function statusClass(text) {
    var t = String(text || "");
    if (t.indexOf("✅") >= 0 || t.indexOf("已加密") >= 0 || t.indexOf("就绪") >= 0 || t.indexOf("运行中") >= 0) return "ok";
    if (t.indexOf("⚠️") >= 0 || t.indexOf("缺失") >= 0 || t.indexOf("待") >= 0 || t.indexOf("不可达") >= 0) return "d";
    if (t.indexOf("🔄") >= 0) return "silent";
    return "";
  }
  function modClassByStatus(st) {
    return ({ active: "s-active", alert: "s-alert", warn: "s-warn", silent: "s-silent" })[st] || "s-silent";
  }
  function gapClass(text) {
    var t = String(text || "");
    if (t.indexOf("已消除") >= 0) return "ok";
    if (t.indexOf("部分") >= 0 || t.indexOf("⚠️") >= 0) return "part";
    return "todo";
  }

  function renderHeader(el, s, data) {
    var intro = document.body.dataset.intro || (s.risk || "");
    var weight = (typeof s.weight === "number") ? Math.round(s.weight * 100) : 0;
    var g = (typeof s.score === "number") ? gradeOf(s.score) : { t: "—", c: "#8b97ad" };
    var html = '<header><div><h1><span class="nm">' + esc(s.name) + '</span>' +
      '<span class="cno">' + esc(s.cno) + '</span></h1>' +
      '<div class="sub">' + esc(intro) + '</div></div>' +
      '<div class="meta">数据更新：<b>' + esc(s.updated || data.generated_at) + '</b><br/>' +
      '本屏权重：<b>' + weight + '%</b><br/>' +
      '全局总评：<b>' + esc(data.total) + '（' + esc(data.grade) + '）</b></div></header>';
    return html;
  }

  function renderScoreRow(s) {
    var score = (typeof s.score === "number") ? s.score : null;
    var g = score != null ? gradeOf(score) : { t: "—", c: "#8b97ad" };
    var circ = 2 * Math.PI * 46;
    var off = score != null ? circ * (1 - score / 100) : circ;
    var ring = '<div class="ring"><svg width="104" height="104" viewBox="0 0 104 104">' +
      '<circle cx="52" cy="52" r="46" fill="none" stroke="#1d212a" stroke-width="11"/>' +
      '<circle cx="52" cy="52" r="46" fill="none" stroke="' + g.c + '" stroke-width="11" stroke-linecap="round" ' +
      'stroke-dasharray="' + circ.toFixed(1) + '" stroke-dashoffset="' + off.toFixed(1) + '"/></svg>' +
      '<div class="ctr"><b>' + (score != null ? score.toFixed(0) : "—") + '</b><span>/100</span></div></div>';
    var bars, cap = "";
    if (Array.isArray(s.sixDims) && s.sixDims.length) {
      // D7/D8 自定义六维标签（真实口径）
      var PALETTE = ["#378ADD", "#1D9E75", "#7F77DD", "#34d399", "#E24B4A", "#EF9F27", "#22d3ee", "#a78bfa"];
      bars = s.sixDims.map(function (d, i) {
        var v = (typeof d[1] === "number") ? d[1] : 0;
        var col = PALETTE[i % PALETTE.length];
        return '<div class="sixRow"><span class="lab">' + esc(d[0]) + '</span>' +
          '<span class="sixTrack"><i style="width:' + v + '%;background:' + col + '"></i></span>' +
          '<span class="val">' + v.toFixed(0) + '</span></div>';
      }).join("");
      cap = '<div class="sixCap">版本/迭代 = 真实实扫值；其余四维 = SKILL.md 静态估算（无运行时埋点，不冒充遥测）</div>';
    } else {
      var six = s.six || {};
      bars = Object.keys(DIM_LABELS).map(function (k) {
        var v = (typeof six[k] === "number") ? six[k] : 0;
        var col = DIM_COLORS[k] || "#94a3b8";
        return '<div class="sixRow"><span class="lab">' + esc(DIM_LABELS[k]) + '</span>' +
          '<span class="sixTrack"><i style="width:' + v + '%;background:' + col + '"></i></span>' +
          '<span class="val">' + v.toFixed(0) + '</span></div>';
      }).join("");
    }
    return '<div class="scoreRow">' + ring +
      '<div class="scoreMeta"><span class="gradePill" style="border-color:' + g.c + ';background:' + g.c + '22;color:' + g.c + '">' + esc(g.t) + '</span>' +
      '<div class="ttl" style="margin-top:12px">六维明细（实源派生）</div>' + bars + cap + '</div></div>';
  }

  function renderKpis(title, kpis) {
    if (!kpis || !kpis.length) return "";
    var cards = kpis.map(function (r) {
      var cls = statusClass(r[1]);
      return '<div class="k ' + cls + '"><div class="lab">' + esc(r[0]) + '</div>' +
        '<div class="val">' + esc(r[1]) + '</div></div>';
    }).join("");
    return '<h2>' + esc(title) + ' <em>实扫</em></h2><div class="kpi">' + cards + '</div>';
  }

  function renderModules(title, mods) {
    if (!mods || !mods.length) return "";
    var cards = mods.map(function (m, i) {
      var cls = modClassByStatus(m.status);
      var stats = (m.stats || []).map(function (st) {
        return '<div class="ms"><div class="v">' + esc(st[1]) + '</div><div class="l">' + esc(st[0]) + '</div></div>';
      }).join("");
      var bar = (typeof m.pct === "number")
        ? '<div class="mod-bar"><i style="width:' + m.pct + '%"></i></div>' : '';
      var tag = m.tag ? '<span class="mod-tag">' + esc(m.tag) + '</span>' : '';
      var foot = m.foot ? '<div class="mod-foot">' + esc(m.foot) + '</div>' : '';
      return '<div class="mod ' + cls + '"><div class="mod-head"><span class="mod-no">' + (i + 1) + '</span>' +
        '<span class="mod-name">' + esc(m.name) + '</span><span class="mod-dot"></span>' + tag + '</div>' +
        '<div class="mod-duty">' + esc(m.detail || "") + '</div>' +
        (stats ? '<div class="mod-stats">' + stats + '</div>' : '') + bar + foot + '</div>';
    }).join("");
    return '<h2>' + esc(title) + ' <em>状态模块</em></h2><div class="modgrid">' + cards + '</div>';
  }

  function renderPanel(p) {
    if (p.kind === "kpis") return renderKpis(p.title, p.rows);
    if (p.kind === "modules") return renderModules(p.title, p.mods);
    return "";
  }

  function renderGaps(gaps) {
    if (!gaps || !gaps.length) return "";
    var rows = gaps.map(function (g) {
      var cls = gapClass(g.status);
      return '<tr><td>' + esc(g.id + " " + g.name) + '</td>' +
        '<td class="st ' + cls + '">' + esc(g.status) + '</td></tr>';
    }).join("");
    return '<h2>缺口清单 <em>实扫</em></h2><table class="defects"><thead><tr><th>缺口</th><th>状态</th></tr></thead><tbody>' +
      rows + '</tbody></table>';
  }

  function renderBanner(s) {
    var flag = s.flag, risk = s.risk || "";
    if (flag) {
      return '<div class="banner alert"><span class="ic">⚠️</span><span>' +
        esc(risk || "存在待关注项，请核查") + '</span></div>';
    }
    return '<div class="banner ok"><span class="ic">✅</span><span>' +
      esc(risk || "状态正常，无高危告警") + '</span></div>';
  }

  function render(el, s, data) {
    var html = renderHeader(el, s, data);
    html += '<div id="dash">';
    html += renderScoreRow(s);
    // 核心指标（实扫 kpis）
    html += renderKpis("核心指标", s.kpis);
    // 扩展面板（版本锁项 / 缺口项 / 门禁 / 磁盘 / 卡库 / 部署记录 等真实数据）
    (s.panels || []).forEach(function (p) { html += renderPanel(p); });
    // 缺口表（D2 等有实扫缺口清单）
    html += renderGaps(s.gaps);
    // 风险旗
    html += renderBanner(s);
    html += '</div>';
    html += '<div class="foot">9655 单机驾驶舱 · ' + esc(s.cno) + ' ' + esc(s.name) +
      ' ｜ 数据由 scan_9655.py 实扫真源生成，非凭记忆填写 ｜ 数据源：单机密文版部署目录 + LTI 门禁 + LawKB 实扫</div>';
    el.innerHTML = html;
  }

  function boot() {
    var el = document.getElementById("app");
    if (!el) return;
    var cno = document.body.dataset.cno;
    fetch("/scorecard_data.json", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var s = (data.screens || []).find(function (x) { return x.cno === cno; });
        if (!s) {
          el.innerHTML = '<div class="empty">未找到屏 ' + esc(cno) + ' 的监控数据（请先运行 scan_9655.py 实扫）。</div>';
          return;
        }
        document.title = "9655 · " + s.name;
        render(el, s, data);
      })
      .catch(function (e) {
        el.innerHTML = '<div class="empty">数据加载失败：' + esc(e.message) +
          '<br/>请确认驾驶舱服务运行中（http://127.0.0.1:9655/）。</div>';
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
