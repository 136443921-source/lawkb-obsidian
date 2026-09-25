/* ============================================================
   9655 子屏评分对齐器（方案B：保留9360外观，只对齐分数）
   - 对标准分数容器的子屏（ev/xiaode/contract-lifecycle）原地改写
     分数数字 + 圆环/仪表盘上色，不改任何 9360 结构与内容。
   - 其余异构子屏降级为右上角「实扫实时评分」浮卡（与首页 C0 同源）。
   - 数据唯一真源：/scorecard_data.json（scan_9655.py 实扫生成）。
   - D7/D8（agenthub/workflowhub）已用 subapp_shell.js 实时渲染，不注入本脚本。
   - D3（cloud）为外部链接，无本地文件，不注入。
   ============================================================ */
(function () {
  "use strict";

  var CNO = document.body && document.body.getAttribute("data-cno");
  if (!CNO) return;

  // 原地改写配置（仅限标准分数 DOM 的子屏）
  var INPLACE = {
    "C1": { num: "#ov",    ring: "#ring", r: 42 }, // ev 车机驾驶舱
    "C5": { num: "#scoreN", ring: "#arc",  r: 60 }, // xiaode 合规中台
    "C7": { num: "#scoreN", ring: "#arc",  r: 60 }  // contract-lifecycle 合同中台
  };

  function gradeOf(v) {
    if (v >= 90) return { t: "A 优秀", c: "#34d399" };
    if (v >= 75) return { t: "B 良好", c: "#1D9E75" };
    if (v >= 60) return { t: "C 合格", c: "#378ADD" };
    if (v >= 45) return { t: "D 待改进", c: "#EF9F27" };
    return { t: "E 高危", c: "#E24B4A" };
  }
  function fmt(v) { return (Math.round(v * 10) / 10).toString(); }

  // ---- 角标（兜底）样式 + 节点 ----
  function ensureStyle() {
    if (document.getElementById("lsb-style")) return;
    var st = document.createElement("style");
    st.id = "lsb-style";
    st.textContent =
      "#liveScoreBadge{position:fixed;top:14px;right:14px;z-index:99999;display:flex;" +
      "align-items:center;gap:9px;padding:8px 13px;border-radius:11px;" +
      "background:rgba(18,22,31,.93);border:1px solid rgba(255,255,255,.14);" +
      "box-shadow:0 8px 24px rgba(0,0,0,.5);backdrop-filter:blur(7px);" +
      "font:600 13px/1.15 -apple-system,system-ui,'PingFang SC',sans-serif;color:#e6edf6;" +
      "user-select:none;pointer-events:none}" +
      "#liveScoreBadge .lsb-dot{width:9px;height:9px;border-radius:50%;box-shadow:0 0 9px currentColor}" +
      "#liveScoreBadge .lsb-t{opacity:.72;font-weight:500;letter-spacing:.3px}" +
      "#liveScoreBadge .lsb-s{font-size:21px;font-weight:800;line-height:1}" +
      "#liveScoreBadge .lsb-g{opacity:.85;font-size:12px}";
    document.head.appendChild(st);
  }
  function badge(score, g) {
    ensureStyle();
    var box = document.getElementById("liveScoreBadge");
    if (!box) {
      box = document.createElement("div");
      box.id = "liveScoreBadge";
      document.body.appendChild(box);
    }
    box.innerHTML =
      '<span class="lsb-dot" style="color:' + (g ? g.c : "#8b97ad") + '"></span>' +
      '<span class="lsb-t">实扫实时评分</span>' +
      '<b class="lsb-s" style="color:' + (g ? g.c : "#e6edf6") + '">' + fmt(score) + '</b>' +
      '<span class="lsb-g">' + (g ? g.t : "") + '</span>';
  }

  function applyInPlace(cfg, sc, g) {
    var numEl = document.querySelector(cfg.num);
    if (!numEl) return false; // 关键数字节点缺失 → 降级角标
    numEl.textContent = fmt(sc);
    if (numEl.style) numEl.style.color = g.c;
    var ringEl = document.querySelector(cfg.ring);
    if (ringEl) {
      var circ = 2 * Math.PI * cfg.r;
      ringEl.setAttribute("stroke", g.c);
      ringEl.setAttribute("stroke-dasharray", circ.toFixed(2));
      ringEl.setAttribute("stroke-dashoffset", (circ * (1 - sc / 100)).toFixed(2));
    }
    var glow = document.querySelector(cfg.ring + "glow");
    if (glow) glow.setAttribute("stroke", g.c);
    return true;
  }

  function run() {
    fetch("/scorecard_data.json", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var s = (data.screens || []).find(function (x) { return x.cno === CNO; });
        if (!s || typeof s.score !== "number") { badge(null, null); return; }
        var sc = s.score, g = gradeOf(sc), cfg = INPLACE[CNO];
        if (cfg) {
          // 原地改写；若成功则不再显示角标
          // 轻量重断言：防止个别子屏自身定时器把数字刷回静态值
          function assert() { applyInPlace(cfg, sc, g); }
          if (assert()) {
            setInterval(assert, 1500);
            return;
          }
          // 失败则落到角标
        }
        badge(sc, g);
      })
      .catch(function () { /* 网络/数据异常：保持 9360 原貌，不强行覆盖 */ });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
})();
