/* ============================================================
   9655 单机驾驶舱 · 子屏共享渲染器
   按 #viewer 的 data-cno 取 scorecard_data.json 真实切片渲染。
   六维字段: fresh/coverage/health/output/compliance/automation
   ============================================================ */
(function () {
  "use strict";
  var DIM_LABELS = {
    fresh: "数据新鲜度", coverage: "覆盖完备度", health: "运行健康度",
    output: "产出有效性", compliance: "安全合规度", automation: "自动化程度"
  };
  var DIM_COLORS = {
    fresh: "#5b9bff", coverage: "#2dd4bf", health: "#a78bfa",
    output: "#34d399", compliance: "#ef5350", automation: "#f59e0b"
  };

  function gradeOf(v) {
    if (v >= 90) return { t: "A 优秀", c: "#34d399" };
    if (v >= 75) return { t: "B 良好", c: "#2dd4bf" };
    if (v >= 60) return { t: "C 合格", c: "#5b9bff" };
    if (v >= 45) return { t: "D 待改进", c: "#f59e0b" };
    return { t: "E 高危", c: "#ef5350" };
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>]/g, function (m) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;" }[m];
    });
  }

  function render(el, s, data) {
    var score = (typeof s.score === "number") ? s.score : null;
    var g = score != null ? gradeOf(score) : { t: "—", c: "#8b97ad" };
    var accent = g.c;

    var html = "";

    // 评分卡
    html += '<section class="sc-card">';
    html += '<div class="ttl">本屏健康评分</div>';
    html += '<div class="sc-score-row">';
    html += '<div class="sc-ring" style="--p:' + (score != null ? score : 0) + ';--accent:' + accent + '">';
    html += '<div class="num"><b>' + (score != null ? score.toFixed(1) : "—") + '</b><span>/100</span></div></div>';
    html += '<div class="sc-meta">';
    html += '<span class="sc-grade" style="background:' + g.c + '22;color:' + g.c + ';border:1px solid ' + g.c + '55">' + esc(g.t) + '</span>';
    html += '<div class="sub">全局六维总评 <b>' + esc(data.total) + '（' + esc(data.grade) + '）</b></div>';
    html += '<div class="sub">数据更新于 <b>' + esc(s.updated || data.generated_at) + '</b></div>';
    html += '</div></div></section>';

    // 六维条
    html += '<section class="sc-card"><div class="ttl">六维明细</div><div class="dims">';
    var six = s.six || {};
    Object.keys(DIM_LABELS).forEach(function (k) {
      var v = (typeof six[k] === "number") ? six[k] : 0;
      var col = DIM_COLORS[k] || "#94a3b8";
      html += '<div class="dim"><span class="lab">' + esc(DIM_LABELS[k]) + '</span>';
      html += '<span class="track"><span class="bar" style="width:' + v + '%;background:' + col + '"></span></span>';
      html += '<span class="val">' + v.toFixed(0) + '</span></div>';
    });
    html += '</div></section>';

    // KPI
    var kpis = s.kpis || [];
    if (kpis.length) {
      html += '<section class="sc-card"><div class="ttl">关键指标（实扫）</div><table class="kpis">';
      kpis.forEach(function (r) {
        html += '<tr><td>' + esc(r[0]) + '</td><td>' + esc(r[1]) + '</td></tr>';
      });
      html += '</table></section>';
    }

    // 缺口清单（实扫，G2/G3/G4 真探产物；文档过度宣称者如实标"部分/缺失"）
    var gaps = s.gaps || [];
    if (gaps.length) {
      html += '<section class="sc-card"><div class="ttl">缺口清单（实扫）</div><table class="kpis">';
      gaps.forEach(function (g) {
        html += '<tr><td>' + esc(g.id + " " + g.name) + '</td><td>' + esc(g.status) + '</td></tr>';
      });
      html += '</table></section>';
    }

    // 状态旗
    var flag = s.flag;
    var risk = s.risk || "";
    if (flag) {
      html += '<div class="banner warn"><span class="ic">⚠️</span><span>' + esc(risk || "存在待关注项，请核查") + '</span></div>';
    } else {
      html += '<div class="banner ok"><span class="ic">✅</span><span>' + esc(risk || "状态正常，无高危告警") + '</span></div>';
    }

    el.innerHTML = html;
  }

  function boot() {
    var el = document.getElementById("viewer");
    if (!el) return;
    var cno = el.dataset.cno;
    fetch("/scorecard_data.json", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var s = (data.screens || []).find(function (x) { return x.cno === cno; });
        if (!s) {
          el.innerHTML = '<div class="empty">未找到屏 ' + esc(cno) + ' 的监控数据（请先运行 scan_9655.py 实扫）。</div>';
          return;
        }
        document.getElementById("scCno").textContent = s.cno;
        document.getElementById("scName").textContent = s.name;
        document.title = "9655 · " + s.name;
        render(el, s, data);
      })
      .catch(function (e) {
        el.innerHTML = '<div class="empty">数据加载失败：' + esc(e.message) + '<br/>请确认驾驶舱服务运行中（http://127.0.0.1:9655/）。</div>';
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
