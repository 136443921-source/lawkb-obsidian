# -*- coding: utf-8 -*-
"""
月度回灌 · 运行态管理器 (intake_monthly_driver.py)
============================================================================
镜像 intake_daily_driver.DailyRun，把「月度回灌（M0 备份 / M1 扫描 / M2 追加 /
M3 日志 / FINAL 汇总）」接入同一套标准库：checkpoint 续跑 + 原子写 + 失败留痕。

与每日摄入的区别：
    - 状态文件独立：`03-连接/monthly_backfill_state.json`（空库 libs={}）
    - 无 IMA 摄入语义：不提供 ingest/on_fetch_fail；失败统一经 record_fail 留痕
    - M0 备份是安全铁律前置：记录备份路径于状态文件 `last_backup`，供 M2 异常秒级回滚

典型用法（写入月度回灌自动化 prompt 的「运行开头」）：
    import sys; sys.path.insert(0, "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/03-连接/scripts")
    from intake_monthly_driver import MonthlyRun
    run = MonthlyRun()                   # 自动 load + new_session + 打印续跑计划
    plan = run.plan                      # 仅剩未完成阶段；上轮中断自动跳过已完成
    for stage in plan:
        if stage == "M0_backup":   ... run.record_backup(path)  # 备份 self.md（六-B 前置）
        elif stage == "M1_scan":   ...  # 只读扫描 经验卡片/裁判规则 本月新增
        elif stage == "M2_append": ...  # 追加 self.md 经验索引区（仅追加，>400 行中止）
        elif stage == "M3_log":    ...  # 写 月度回灌日志.md
        elif stage == "FINAL":     ...  # 响应摘要
        run.stage_done(stage)           # 每阶段原子持久化断点
    run.finalize()                      # 标记 done + 原子写回

任一处异常：
    run.record_fail(stage, "异常摘要")   # 留痕 failed_stages
============================================================================
"""
import os, sys, re, datetime
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from intake_runner import IntakeState, IntakeMachine, MONTHLY_CONFIG, MONTHLY_STAGES


class MonthlyRun:
    """月度回灌运行态封装（checkpoint 续跑 + 原子写 + 失败留痕 + 备份记录）。"""

    def __init__(self, state_path=None):
        self.config = MONTHLY_CONFIG
        self.state = IntakeState(state_path or MONTHLY_CONFIG.state_path, libs={}).load()
        self.resume = self.state.new_session()
        self.machine = IntakeMachine(self.state, MONTHLY_STAGES)
        self.plan = self.machine.resume_plan()
        if self.resume:
            print("[monthly] 检测到上轮中断(in_progress)，自动续跑；跳过已完阶段：%s"
                  % self.state.data["checkpoint"].get("done"))
        else:
            print("[monthly] 全新运行；计划阶段：%s" % self.plan)

    # ---- 阶段钩子 ----
    def stage_done(self, stage):
        self.machine.complete(stage)
        self.state.save()

    def finalize(self):
        self.state.finish_session()
        self.state.save()
        fails = self.state.data.get("failed_stages", [])
        print("[monthly] 本轮完成；done=%s；failed_stages=%d"
              % (self.state.data["checkpoint"].get("done"), len(fails)))
        return fails

    # ---- 失败留痕 ----
    def record_fail(self, stage, note):
        fails = self.state.data.setdefault("failed_stages", [])
        fails.append({"stage": stage, "note": note, "date": self.state.data.get("updated")})
        self.state.save()
        return fails

    # ---- 备份记录（M0 安全铁律前置，异常时秒级回滚依据）----
    def record_backup(self, backup_path):
        self.state.data["last_backup"] = {
            "path": backup_path, "date": self.state.data.get("updated"),
        }
        self.state.save()
        return backup_path


# ============================================================================
# 3) BackfillScanner —— 月度回灌「只读扫描 + 过滤」单一真源（v2.2 新增）
# ----------------------------------------------------------------------------
# 设计目标（来自 2026-10-29 事故复盘 · 月度回灌漏扫 裁判规则库）：
#   ① 目录防护：遍历前 test -d + 可读性校验；os.walk 返回 0 文件时**强制 ls 复核**，
#      若 ls 发现 .md 而 walk 为 0 → 视为遍历/沙箱失败，raise GuardError（上层告警中止）。
#      （根治「find 返回 0 即误判为空」的否定型结论铁律违反）
#   ② 过滤口径：未索引 + (created 或 updated) 在窗口内，**非纯 created 月份**；
#      批戳防护：updated 戳频率 ≥5 且 ≥ 月首 → 视为 relink/治理批戳，改用 created 判定。
#   ③ 分类：R-* / 含 rule_id / card_type 含「裁判规则」→ 裁判规则-；否则 经验卡片-。
#   ④ LTI 沉淀入口校验（仅 经验卡片 类，best-effort，不阻断主流程）。
# ============================================================================
_FLYWHEEL_ROOT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
_LTI_REF = "/Users/chenyouqiang/.workbuddy/skills/LTI文本监控器/references"
_Pollution_THRESHOLD = 5  # updated 同戳出现次数阈值

DEFAULT_SCAN_DIRS = [
    os.path.join(_FLYWHEEL_ROOT, "02-提炼/经验卡片"),
    os.path.join(_FLYWHEEL_ROOT, "06-沉淀/裁判规则库"),
    os.path.join(_FLYWHEEL_ROOT, "06-沉淀/通用裁判规则库"),
]


class GuardError(Exception):
    """目录防护失败：疑似遍历/沙箱拒绝，需上层告警并中止该阶段。"""


def _parse_frontmatter(path):
    try:
        t = open(path, encoding='utf-8').read()
    except Exception:
        return None
    m = re.match(r'^---\s*\n(.*?)\n---', t, re.S)
    if not m:
        return None
    fm = m.group(1)
    d = {}
    for k in ('created', 'updated', 'date', 'created_month', 'title', 'summary',
              'rule_id', 'type', 'card_type', 'aliases'):
        mm = re.search(r'^%s:\s*(.+)$' % re.escape(k), fm, re.M)
        if mm:
            d[k] = mm.group(1).strip()
    return d, t


def _date(s):
    if not s:
        return None
    m = re.match(r'(\d{4}-\d{2}-\d{2})', s)
    return datetime.date.fromisoformat(m.group(1)) if m else None


# 目录治理/导航元文件关键词：这些不是「经验卡片/裁判规则卡」资产，不进索引区
_META_KEYWORDS = ('索引', '快照', '治理', '体系规范', '卡型定义', '编号治理',
                  '执行记录', '全量物理', 'README')


def _is_meta(filename):
    base = os.path.splitext(os.path.basename(filename))[0]
    if base.startswith('_'):
        return True
    return any(k in base for k in _META_KEYWORDS)


class BackfillScanner:
    """月度回灌只读扫描器：目录防护 + 批戳过滤 + 分类 + LTI 校验。"""

    def __init__(self, scan_dirs=None, flywheel_root=_FLYWHEEL_ROOT):
        self.scan_dirs = scan_dirs or DEFAULT_SCAN_DIRS
        self.root = flywheel_root
        self.pollution = set()

    # ---- ① 目录防护：test -d + 可读性；walk 返回 0 时 ls 复核 ----
    def safe_walk(self, d):
        if not os.path.isdir(d):
            raise GuardError("目录不存在: %s" % d)
        files = []
        for dp, _, fns in os.walk(d):
            for fn in fns:
                if fn.endswith('.md') and fn not in ('_template.md', 'README.md'):
                    files.append(os.path.join(dp, fn))
        if len(files) == 0:
            # 二次源复核：用 ls 确认「真空」还是「遍历失败」
            try:
                ls_out = os.listdir(d)
            except Exception as e:
                raise GuardError("目录无法列举(权限/沙箱?) %s: %s" % (d, e))
            md_in_ls = [x for x in ls_out if x.endswith('.md')]
            if md_in_ls:
                raise GuardError("walk 返回0但ls发现%d个.md(疑似遍历失败): %s"
                                 % (len(md_in_ls), d))
            # 确为空目录（正常），返回空列表
        return files

    # ---- ② 批戳检测：updated 戳频率≥阈值 且 ≥ 月首 → 视为 relink/治理批戳 ----
    def detect_pollution(self, meta):
        cnt = Counter(u for _, _, u in meta if u)
        self.pollution = {u for u, n in cnt.items()
                         if n >= _Pollution_THRESHOLD
                         and _date(u) and _date(u) >= self.month_start}

    # ---- ③ 分类：规则卡 / 经验卡 ----
    def classify(self, path, fm):
        base = os.path.basename(path)
        is_rule = (base.startswith('R-') or 'rule_id' in fm
                   or ('裁判规则' in (fm.get('type', '') + fm.get('card_type', ''))))
        return '裁判规则' if is_rule else '经验卡片'

    # ---- 主扫描：返回候选 + 统计 ----
    def collect(self, month_start, already_paths, skip_lti=False):
        self.month_start = _date(month_start) or datetime.date.fromisoformat(month_start)
        all_files = []
        dir_report = {}
        for d in self.scan_dirs:
            fs = self.safe_walk(d)          # 任一目录 GuardError → 上层感知并中止
            dir_report[os.path.relpath(d, self.root)] = len(fs)
            all_files.extend(fs)

        parsed, meta = [], []
        for p in all_files:
            r = _parse_frontmatter(p)
            if not r:
                continue
            fm, txt = r
            meta.append((p, fm.get('created', ''), fm.get('updated', '')))
            parsed.append((p, fm, txt))
        self.detect_pollution(meta)

        candidates = []
        excluded = {'historical': 0, 'dup': 0}
        for p, fm, txt in parsed:
            c = _date(fm.get('created'))
            u = _date(fm.get('updated'))
            if fm.get('updated', '') in self.pollution:
                dec = c                                   # 批戳 → 退回 created
            else:
                cand_dates = [x for x in (c, u) if x]
                dec = max(cand_dates) if cand_dates else None
            if dec is None or dec < self.month_start:
                excluded['historical'] += 1
                continue
            rel = os.path.relpath(p, self.root)
            if rel in already_paths:
                excluded['dup'] += 1
                continue
            prefix = self.classify(p, fm)
            if _is_meta(os.path.basename(p)):
                excluded.setdefault('meta', 0)
                excluded['meta'] += 1
                continue
            title = fm.get('title')
            if not title:
                hm = re.search(r'^#\s+(.+)$', txt, re.M)
                title = hm.group(1).strip() if hm else os.path.splitext(os.path.basename(p))[0]
            summary = fm.get('summary')
            if not summary:
                body = txt.split('---', 2)[-1]
                for ln in body.split('\n'):
                    s = ln.strip()
                    if s and not s.startswith('#') and not s.startswith('>') \
                       and not s.startswith('|') and not s.startswith('-') \
                       and not s.startswith('```'):
                        summary = re.sub(r'[`*_#]', '', s).replace('\n', ' ').replace('|', '／')
                        summary = (summary[:80] + '…') if len(summary) > 80 else summary
                        break
                summary = summary or ''
            candidates.append({'rel': rel, 'prefix': prefix, 'title': title,
                               'summary': summary, 'path': p})

        # ④ LTI（仅 经验卡片 类，best-effort）
        final, lti_blocked = [], []
        if not skip_lti:
            for c in candidates:
                if c['prefix'] != '经验卡片':
                    final.append(c)
                    continue
                try:
                    sys.path.insert(0, _LTI_REF)
                    from main import wrap_output
                    wrap_output(open(c['path'], encoding='utf-8').read(),
                                ai_participation=['经验提炼与知识沉淀'])
                    final.append(c)
                except Exception as e:
                    lti_blocked.append({'rel': c['rel'],
                                        'err': type(e).__name__ + ':' + str(e)[:80]})
        else:
            final = candidates

        return {'candidates': final, 'lti_blocked': lti_blocked,
                'excluded': excluded, 'pollution': sorted(self.pollution),
                'dir_report': dir_report}


if __name__ == "__main__":
    # 直接运行：打印当前状态快照与续跑计划（不修改业务数据）
    r = MonthlyRun()
    print("state_path:", r.config.state_path)
    print("checkpoint:", r.state.data.get("checkpoint"))
    print("pending_stages:", r.plan)
    print("last_backup:", r.state.data.get("last_backup"))
    print("failed_stages:", r.state.data.get("failed_stages", []))
