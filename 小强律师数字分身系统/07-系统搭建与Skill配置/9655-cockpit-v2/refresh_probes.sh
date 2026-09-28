#!/usr/bin/env bash
# =============================================================================
# refresh_probes.sh — 统一刷新 9655 驾驶舱缺口探针 JSON（治「调度真空」根因）
# -----------------------------------------------------------------------------
# 单开 launchd（com.xiaoqiang.lawtwin-probes.plist，每日 07:15）周期跑本脚本，
# 串起 8 个 9655 根探针 + S1 四屏 live json + pillars 聚合，保证驾驶舱观测数据
# 持续新鲜（不再停更于某次批量重建的指纹）。
#
# 设计要点（守六-B / S1 范式）：
#   - 各探针独立运行、独立 JSON，单条失败不中断整链（|| true）
#   - 只读探针、零虚构；输出全部落到既有 9655 根目录 JSON（与 pillars_probe 同读位）
#   - 日志追加到 .probe_refresh.log，可审计
# =============================================================================
set -u
PY="/Users/chenyouqiang/.workbuddy/binaries/python/versions/3.13.12/bin/python3"
SK="/Users/chenyouqiang/lawtwin-open/skills"
COCK="/Users/chenyouqiang/Documents/LawKB/小强律师数字分身系统/07-系统搭建与Skill配置/9655-cockpit-v2"
LOG="$COCK/.probe_refresh.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] refresh_probes start" >> "$LOG"

# ---- 8 个 9655 根探针 JSON（运维可审计 / 防幻觉 / 可诊断 维度数据源）----
"$PY" "$SK/O1-audit-probe/lawtwin_audit_probe.py"        --out "$COCK/o1_health.json"   --quiet >> "$LOG" 2>&1 || true
"$PY" "$SK/O2-deploy-record/deploy_record_fill.py"      --json "$COCK/o2_g6.json"      --quiet >> "$LOG" 2>&1 || true
"$PY" "$SK/O3-maturity-track/lawtwin_maturity.py"        --json "$COCK/o3_maturity.json" --quiet >> "$LOG" 2>&1 || true
"$PY" "$SK/H2-statute-verify/h2_probe.py"                --out "$COCK/h2_verify.json"   --quiet >> "$LOG" 2>&1 || true
"$PY" "$SK/H4-hallucination-dash/hallucination_dash.py"  --out "$COCK/c8_metrics.json"   --quiet >> "$LOG" 2>&1 || true
"$PY" "$SK/D2-egress-audit/d2_probe.py"                  --out "$COCK/d2_egress.json"   --quiet >> "$LOG" 2>&1 || true
"$PY" "$SK/S2-redline-prehook/s2_probe.py"               --out "$COCK/s2_redline.json"  --quiet >> "$LOG" 2>&1 || true
"$PY" "$SK/S3-score-integrity/score_integrity_check.py" --out "$COCK/s3_integrity.json" --quiet >> "$LOG" 2>&1 || true

# ---- S1 四屏实时重接 live json（可诊断·可定责 维度数据源）----
"$PY" "$SK/S1-subapp-reconnect/probe_flywheel.py" --quiet >> "$LOG" 2>&1 || true
"$PY" "$SK/S1-subapp-reconnect/probe_clm.py"      --quiet >> "$LOG" 2>&1 || true
"$PY" "$SK/S1-subapp-reconnect/probe_xiaode.py"   --quiet >> "$LOG" 2>&1 || true
"$PY" "$SK/S1-subapp-reconnect/probe_lti.py"      --quiet >> "$LOG" 2>&1 || true

# ---- 聚合四支柱+四配套质量框架 → pillars.json ----
"$PY" "$COCK/pillars_probe.py" >> "$LOG" 2>&1 || true

echo "[$(date '+%Y-%m-%d %H:%M:%S')] refresh_probes done" >> "$LOG"
