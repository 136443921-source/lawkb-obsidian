/* =============================================================
 * 小强总驾驶舱统一工作台 — SSO 门禁逻辑（前端骨架）
 * -------------------------------------------------------------
 * 流程：
 *   1. 启动即读 URL ?token= 或 localStorage 会话；
 *   2. verifyToken() 校验签名 + 有效期；
 *   3. 通过 → 按角色过滤驾驶舱标签并渲染；
 *   4. 失败 → 展示登录浮层（可贴令牌 / 演示角色快速登录）。
 *
 * verifyToken 用 Web Crypto HMAC-SHA256 做标准签名校验，
 * 与「生产替换为 OIDC id_token 验签」的接口形态一致（见 rbac.js）。
 * ============================================================= */
(function () {
  "use strict";
  const CFG = window.COCKPIT_CONFIG;
  const enc = new TextEncoder();
  /* 版本模式：统一为律师版（全屏显示，含律所业务屏 C4/C5/C6/C7，按角色授权） */
  window.APP_MODE = "lawyer";

  /* ---------- base64url 工具 ---------- */
  function b64urlEncode(str) {
    return btoa(unescape(encodeURIComponent(str)))
      .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }
  function b64urlDecode(str) {
    str = str.replace(/-/g, "+").replace(/_/g, "/");
    while (str.length % 4) str += "=";
    return decodeURIComponent(escape(atob(str)));
  }

  /* ---------- HMAC-SHA256（Web Crypto，异步） ---------- */
  async function hmac(message, key) {
    const cryptoKey = await crypto.subtle.importKey(
      "raw", enc.encode(key), { name: "HMAC", hash: "SHA-256" }, false,
      ["sign"]
    );
    const sig = await crypto.subtle.sign("HMAC", cryptoKey, enc.encode(message));
    return Array.from(new Uint8Array(sig))
      .map(b => b.toString(16).padStart(2, "0")).join("");
  }

  /* ---------- 签发令牌（演示用；生产由 IdP 完成） ----------
   * token = base64url(payload) + "." + hmac(payload, secret)
   * payload = { role, username, name, exp }
   */
  async function issueToken(role, username, name) {
    const payload = {
      role, username, name: name || username,
      exp: Math.floor(Date.now() / 1000) + CFG.tokenTtlSec
    };
    const p = b64urlEncode(JSON.stringify(payload));
    const sig = await hmac(p, CFG.secret);
    return p + "." + sig;
  }

  /* ---------- 校验令牌 ---------- */
  async function verifyToken(token) {
    if (!token || typeof token !== "string" || !token.includes(".")) return null;
    const [p, sig] = token.split(".");
    if (!p || !sig) return null;
    const expect = await hmac(p, CFG.secret);
    // 定长签名恒定时间比较
    if (sig.length !== expect.length) return null;
    let diff = 0;
    for (let i = 0; i < sig.length; i++) diff |= sig.charCodeAt(i) ^ expect.charCodeAt(i);
    if (diff !== 0) return null;
    let payload;
    try { payload = JSON.parse(b64urlDecode(p)); } catch (e) { return null; }
    if (!payload.role || !CFG.roles[payload.role]) return null;
    if (Math.floor(Date.now() / 1000) > payload.exp) return null; // 过期
    return payload;
  }

  /* ---------- DOM 引用 ---------- */
  const overlay = document.getElementById("loginOverlay");
  const appRoot = document.getElementById("appRoot");
  const tabsEl = document.getElementById("tabs");
  const frame = document.getElementById("frame");
  const homeView = document.getElementById("homeView");
  const wrap = document.querySelector(".framewrap");
  const curName = document.getElementById("curName");
  const curUrl = document.getElementById("curUrl");
  const openNew = document.getElementById("openNew");
  const roleBadge = document.getElementById("roleBadge");
  const userBadge = document.getElementById("userBadge");
  const logoutBtn = document.getElementById("logoutBtn");
  const tokenInput = document.getElementById("tokenInput");
  const tokenErr = document.getElementById("tokenErr");
  /* —— 演示席位工号+密码登录（2026-09-16）—— */
  const demoLoginForm = document.getElementById("demoLoginForm");
  const demoSeatTitle = document.getElementById("demoSeatTitle");
  const demoUser = document.getElementById("demoUser");
  const demoPass = document.getElementById("demoPass");
  const demoLoginBtn = document.getElementById("demoLoginBtn");
  const demoCancelBtn = document.getElementById("demoCancelBtn");
  const demoErr = document.getElementById("demoErr");
  let selectedSeatRole = null;
  let currentRole = null;

  /* ---------- 渲染应用（按角色过滤） ---------- */
  function enterApp(payload) {
    overlay.classList.add("hide");
    appRoot.classList.remove("hide");
    const role = CFG.roles[payload.role];
    roleBadge.textContent = role.label + (role.manage ? " · 管理员" : "");
    roleBadge.className = "badge role-" + payload.role;
    userBadge.textContent = payload.name || payload.username;
    logoutBtn.classList.remove("hide");

    currentRole = payload.role;
    renderTabs();
  }

  /* ---------- 按角色 + 版本模式构建标签 ---------- */
  function renderTabs() {
    if (!currentRole) return;
    const role = CFG.roles[currentRole];
    tabsEl.innerHTML = "";
    // 标签排序：本地视图（作战地图 HOME）置首 → 按 C1…C8 升序 → C0（监控位）压尾 → D 系列随后
    const cnoRank = (c) => {
      if (!c) return 98;
      if (String(c).toUpperCase() === "C0") return 99;
      const s = String(c);
      // D 系列（D1 积分监测 … D6 权限调用）置于 C 系列之后、C0 之前
      if (s[0] === "D" || s[0] === "d") { const dn = parseInt(s.slice(1), 10); return isNaN(dn) ? 97 : 50 + dn; }
      const n = parseInt(s.slice(1), 10);
      return isNaN(n) ? 98 : n;
    };
    const allowed = role.sites
      .map(k => ({ key: k, ...CFG.sites[k] }))
      .filter(Boolean)
      .sort((a, b) => (a.local ? -1 : 0) - (b.local ? -1 : 0) || cnoRank(a.cno) - cnoRank(b.cno));
    allowed.forEach((s, i) => {
      const dotClass = s.dot || "c";
      const div = document.createElement("div");
      div.className = "tab" + (i === 0 ? " on" : "");
      div.dataset.key = s.key;
      // 律所业务屏角标已移除
      const lawTag = '';
      div.innerHTML =
        '<span class="dot ' + dotClass + '"></span>' +
        (s.cno ? '<span class="cno">' + s.cno + '</span>' : '') +
        s.name + lawTag + '<span class="ext">↗</span>';
      tabsEl.appendChild(div);
    });
    if (allowed.length) load(allowed[0].key);
    // 暴露给版本切换按钮：重新渲染当前角色标签
    window.__rerenderTabs = renderTabs;
  }

  function load(key) {
    const s = CFG.sites[key];
    if (!s) return;
    // 作战地图本地视图（home）：显示地图容器，不加载外部 iframe
    if (key === "home" || s.local) {
      if (homeView) homeView.classList.remove("hide");
      if (wrap) wrap.classList.add("hide");
      curName.textContent = s.name || "八屏统一作战地图";
      curUrl.textContent = "本地视图 · 评分导航首页";
      openNew.removeAttribute("href");
      openNew.style.pointerEvents = "none";
      openNew.style.opacity = ".4";
      return;
    }
    // 完整 SSO 时此处可附加 ?token= 透传给子页做二次校验
    if (homeView) homeView.classList.add("hide");
    if (wrap) wrap.classList.remove("hide");
    // cache-busting：切屏强制拉最新，根治 http.server 强缓存旧 C4，refresh 后立即可见
    frame.src = s.url + (s.url.indexOf("?") >= 0 ? "&" : "?") + "nc=" + Date.now();
    curName.textContent = s.name;
    curUrl.textContent = s.url;
    openNew.href = s.url;
    openNew.style.pointerEvents = "";
    openNew.style.opacity = "";
  }

  // 供作战地图卡片「进入 ↗」调用：同步高亮标签并加载
  window.__cockpitLoad = function (k) {
    const t = tabsEl.querySelector('.tab[data-key="' + k + '"]');
    if (!t) return;
    tabsEl.querySelectorAll(".tab").forEach(x => x.classList.remove("on"));
    t.classList.add("on");
    load(k);
  };

  tabsEl.addEventListener("click", (e) => {
    const tab = e.target.closest(".tab");
    if (!tab) return;
    tabsEl.querySelectorAll(".tab").forEach(t => t.classList.remove("on"));
    tab.classList.add("on");
    load(tab.dataset.key);
  });

  /* ---------- 登录态建立 ---------- */
  async function establish(token, persist) {
    const payload = await verifyToken(token);
    if (!payload) {
      tokenErr.textContent = "令牌无效或已过期，请重新获取。";
      tokenErr.classList.remove("hide");
      return false;
    }
    if (persist !== false) {
      try { localStorage.setItem(CFG.sessionKey, token); } catch (e) {}
    }
    enterApp(payload);
    return true;
  }

  /* ---------- 登出 ---------- */
  logoutBtn.addEventListener("click", () => {
    try { localStorage.removeItem(CFG.sessionKey); } catch (e) {}
    location.reload();
  });

  /* ---------- 登录浮层事件 ---------- */
  document.getElementById("tokenLoginBtn").addEventListener("click", () => {
    tokenErr.classList.add("hide");
    const v = tokenInput.value.trim();
    if (!v) { tokenErr.textContent = "请粘贴访问令牌。"; tokenErr.classList.remove("hide"); return; }
    establish(v, true);
  });

  /* ---------- 演示席位：工号 + 密码登录（统一凭据） ----------
   * 流程：点席位卡 → 展开该席位的登录表单 → 校验工号/密码 → 按所选席位签发令牌进舱。
   * 校验规则（与 rbac.js 的 users 表对应）：
   *   1) 工号必须存在；
   *   2) 密码 SHA-256 必须与 pwdHash 一致；
   *   3) 四席位共用统一演示账号（LZ-001 / lz001@2026），选哪个席位即进哪个视图。
   */
  async function sha256Hex(text) {
    const buf = await crypto.subtle.digest("SHA-256", enc.encode(text));
    return Array.from(new Uint8Array(buf))
      .map(b => b.toString(16).padStart(2, "0")).join("");
  }

  function showDemoError(msg) {
    demoErr.textContent = msg;
    demoErr.classList.remove("hide");
  }

  function resetDemoForm() {
    selectedSeatRole = null;
    demoLoginForm.classList.add("hide");
    demoErr.classList.add("hide");
    demoUser.value = "";
    demoPass.value = "";
    document.querySelectorAll(".demoBtn").forEach(b => b.classList.remove("on"));
  }

  const SEAT_LABEL = { owner: "超级管理员", lawyer: "执业律师", paralegal: "律师助理", itops: "IT运维员" };

  document.querySelectorAll(".demoBtn").forEach(btn => {
    btn.addEventListener("click", () => {
      selectedSeatRole = btn.dataset.role;
      document.querySelectorAll(".demoBtn").forEach(b => b.classList.toggle("on", b === btn));
      demoSeatTitle.textContent = "「" + (SEAT_LABEL[selectedSeatRole] || selectedSeatRole) + "」席位登录（工号 + 密码）";
      demoErr.classList.add("hide");
      demoLoginForm.classList.remove("hide");
      demoUser.focus();
    });
  });

  async function demoLogin() {
    if (!selectedSeatRole) { showDemoError("请先选择演示席位。"); return; }
    demoErr.classList.add("hide");
    const u = demoUser.value.trim();
    const p = demoPass.value;
    if (!u || !p) { showDemoError("请输入工号与密码。"); return; }
    const rec = CFG.users[u];
    if (!rec) { showDemoError("工号不存在，请核对后重试。"); return; }
    // 统一演示凭据：不校验工号角色，按所选席位签发令牌（四席位共用 LZ-001 / lz001@2026）
    const h = await sha256Hex(p);
    if (h !== rec.pwdHash) { showDemoError("密码错误，请重试。"); return; }
    const token = await issueToken(selectedSeatRole, u, rec.name);
    resetDemoForm();
    establish(token, true);
  }

  demoLoginBtn.addEventListener("click", demoLogin);
  demoCancelBtn.addEventListener("click", resetDemoForm);
  [demoUser, demoPass].forEach(el => el.addEventListener("keydown", (e) => {
    if (e.key === "Enter") demoLogin();
  }));

  /* ---------- 启动引导 ---------- */
  async function bootstrap() {
    // 1) URL ?token=
    const params = new URLSearchParams(location.search);
    const urlToken = params.get("token");
    if (urlToken) {
      const ok = await establish(urlToken, true);
      if (ok) { history.replaceState({}, "", location.pathname); return; }
    }
    // 2) localStorage 会话
    let saved = null;
    try { saved = localStorage.getItem(CFG.sessionKey); } catch (e) {}
    if (saved) {
      const ok = await establish(saved, true);
      if (ok) return;
    }
    // 3) 否则展示登录浮层
    overlay.classList.remove("hide");
    appRoot.classList.add("hide");
  }

  bootstrap();
})();
