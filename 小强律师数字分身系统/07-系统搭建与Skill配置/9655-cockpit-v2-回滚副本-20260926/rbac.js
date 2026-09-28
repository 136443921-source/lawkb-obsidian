/* =============================================================
 * 9655 驾驶舱 — RBAC + SSO 骨架配置（9360 标准 1:1 复原 · 全屏统一版）
 * -------------------------------------------------------------
 * 这是「对标 Harvey Command Center」权限层的静态可部署骨架。
 *
 * ⚠️ 安全边界（务必阅读）：
 *   当前为纯前端静态部署（app.workbuddy.link 无后端）。因此
 *   1) secret 仅是占位符，真实系统必须由【后端/IdP】签发令牌，
 *      前端绝不可持有签名密钥；
 *   2) 本文件的 roles/sites/users 仅作演示与架构说明；
 *      生产环境的「用户→角色」映射应落在服务端鉴权服务中。
 *
 * 🔧 生产升级路径（4 步即可从骨架变真 SSO）：
 *   A. 用 Authing / Keycloak / WorkBuddy SSO 等 IdP 做登录；
 *   B. 把 verifyToken() 换成对 IdP 下发的 OIDC id_token 的
 *      标准验签（aud/iss/exp + 公钥验签）；
 *   C. 把本文件的 users/roles 映射迁移到 IdP 的 Group/Role；
 *   D. 子驾驶舱（cheji/feilun/...）各自消费 ?token= 做二次校验，
 *      实现真正的端到端 SSO（不仅是导航可见性门禁）。
 * ============================================================= */
window.COCKPIT_CONFIG = {
  /* 静态占位密钥 —— 仅用于本地骨架演示，生产环境由后端签发，前端不持有 */
  secret: "CHANGE_ME_SERVER_SIDE_SECRET",

  /* localStorage 会话键名 */
  sessionKey: "cockpit_ssosession_v1",

  /* 令牌有效期（秒） */
  tokenTtlSec: 60 * 60 * 8,

  /* —— 角色定义（席位权限模型）——
   * sites: 该角色可见的驾驶舱 key 列表（见下方 sites 注册表）
   * manage: 是否拥有用户/权限管理入口（仅 owner）
   */
  /* ⭐ 分屏编号秩序（2026-09-18 修正·C0–C8/D1–D6 严格按 9360 真源；D7/D8 为数字分身系统新增中台·Harvey 对标）：
   *    C0 为作战地图(本地视图·导航中枢，不占业务编号)，C1–C8 为九屏业务主体，
   *    D1–D6 为 9360 真源分屏中台，D7 智能体中台 / D8 工作流中台为本次批准新增（对标 Harvey Command Center）。
   *    C1 车机 / C2 决策树 / C3 飞轮 / C4 案件 / C5 小德合规 /
   *    C6 模拟法庭 / C7 合同 / C8 幻觉监控 / D1 积分 / D2 冲突 /
   *    D3 云 / D4 心智 / D5 权限管理 / D6 权限调用 / D7 智能体中台 / D8 工作流中台 / D9 共享中枢中台。
   *    C4/C5/C6/C7 为律所业务屏，sites 中标记 lawFirm:true；统一全屏显示（按角色授权）。 */
  roles: {
    owner: {
      label: "超级管理员",
      desc: "全部驾驶舱 + 用户与权限管理",
      sites: ["home", "ev", "decision", "flywheel", "clm", "xiaode", "mock", "contractlifecycle", "lti", "governance", "credits", "conflict", "cloud", "mindmodel", "permcenter", "d6permcenter", "agenthub", "workflowhub", "sharedhub"],
      manage: true
    },
    lawyer: {
      label: "标准用户",
      desc: "C1–C8 监控屏 + D1–D6 中台（含律所业务屏，按角色授权）",
      sites: ["ev", "decision", "flywheel", "clm", "xiaode", "mock", "contractlifecycle", "lti", "governance", "credits", "conflict", "cloud", "mindmodel", "agenthub", "workflowhub", "sharedhub"],
      manage: false
    },
    paralegal: {
      label: "只读访客",
      desc: "知识体 / 存储备份 / 门禁监控（只读协作）",
      sites: ["flywheel", "credits", "contractlifecycle", "clm", "xiaode", "lti"],
      manage: false
    },
    itops: {
      label: "IT 运维员",
      desc: "权限管理（账号 / 角色 / 权限）+ 智能体/工作流中台治理",
      sites: ["permcenter", "d6permcenter", "governance", "agenthub", "workflowhub", "sharedhub"],
      manage: true
    }
  },

  /* —— 站点注册表（与 roles.*.sites 的 key 对应）——
   * 每个驾驶舱是一个独立 sandbox 子页；门禁控制其「是否出现在导航」。
   * 注：子页自身访问仍由其部署域控制；完整 SSO 需各子页消费 ?token=。
   */
  sites: {
    home: {
      name: "九屏维度",
      cno: "C0",
      url: "",            /* 本地视图，由 auth.js 切回作战地图容器，不加载外部 iframe */
      dot: "m",
      local: true
    },
    contractlifecycle: {
      name: "合同管理中台",
      cno: "C7",
      url: "./subapps/contract-lifecycle/index.html",
      dot: "g",
      lawFirm: true
    },
    mock: {
      name: "模拟庭审中台",
      cno: "C6",
      url: "./subapps/mock/index.html",
      dot: "c",
      lawFirm: true
    },
    ev: {
      name: "车机驾驶舱",
      cno: "C1",
      url: "./subapps/ev/index.html",
      dot: "a"
    },
    flywheel: {
      name: "知识飞轮舱",
      cno: "C3",
      url: "./subapps/flywheel/index.html",
      dot: "b"
    },
    decision: {
      name: "决策思维舱",
      cno: "C2",
      url: "./subapps/decision/index.html",
      dot: "d"
    },
    credits: {
      name: "积分监测中台",
      cno: "D1",
      url: "./subapps/credits/index.html",
      dot: "e"
    },
    conflict: {
      name: "知识冲突中台",
      cno: "D2",
      url: "./subapps/conflict-arbitration/index.html",
      dot: "conf"
    },
    clm: {
      name: "案件管理中台",
      cno: "C4",
      url: "./subapps/clm/index.html",
      dot: "f",
      lawFirm: true
    },
    lti: {
      name: "AI 幻觉监控舱",
      cno: "C8",
      url: "./subapps/lti/index.html",
      dot: "h"
    },
    xiaode: {
      name: "合规管理中台",
      cno: "C5",
      url: "./subapps/xiaode/index.html",
      dot: "k",
      lawFirm: true
    },
    cloud: {
      name: "云服务中台",
      cno: "D3",
      url: "https://xiaoqiang-cloud-service.app.workbuddy.host/",
      dot: "i"
    },
    mindmodel: {
      name: "心智模型中台",
      cno: "D4",
      url: "./subapps/mind-models/index.html",
      dot: "mm"
    },
    permcenter: {
      name: "权限管理中心",
      cno: "D5",
      url: "./subapps/permcenter/index.html",
      dot: "pc"
    },
    d6permcenter: {
      name: "权限调用中台",
      cno: "D6",
      url: "./subapps/d6permcenter/index.html",
      dot: "d6"
    },
    agenthub: {
      name: "智能体中台",
      cno: "D7",
      url: "./subapps/agenthub/index.html",
      dot: "ag"
    },
    workflowhub: {
      name: "工作流中台",
      cno: "D8",
      url: "./subapps/workflowhub/index.html",
      dot: "wf"
    },
    sharedhub: {
      name: "共享中枢中台",
      cno: "D9",
      url: "./subapps/sharedhub/index.html",
      dot: "sh"
    },
    governance: {
      name: "OPC治理中台",
      cno: "C9",
      url: "./subapps/governance/index.html",
      dot: "n"
    }
  },

  /* —— 席位账号目录（2026-09-16 老强指令：演示席位须工号+密码登录）——
   * key = 工号（登录用户名）；pwdHash = 密码的 SHA-256 十六进制（前端不存明文）。
   * 演示席位对应关系：超级管理员→owner / 执业律师→lawyer / 律师助理→paralegal / IT运维员→itops。
   * 换密码方法：node -e 'console.log(require("crypto").createHash("sha256").update("新密码").digest("hex"))'
   * 然后替换对应 pwdHash 即可。
   * ⚠️ 此为本地静态演示门禁（仅防误入、不做真实鉴权）；生产环境仍须迁移至服务端/IdP。
   */
  users: {
    /* —— 统一演示账号：四席位共用主任凭据（工号 LZ-001 / 密码 lz001@2026）——
     * 选哪个席位即进哪个视图，auth.js 按 selectedSeatRole 签发令牌，不校验工号角色。
     * 改密码只需替换下方 pwdHash（lz001@2026 的 SHA-256）。 */
    "LZ-001": { name: "LZ-001 · 陈友强", pwdHash: "b172e7262f1cf4c1e0c738866e1e6e140c2a69418a2b06d7a4ff5d8ab00f3d73" }
  }
};
