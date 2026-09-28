#!/bin/bash
# start_lti_gate.command — Finder 双击即跑的包装器
# 仅负责定位同目录的 start_lti_gate.sh 并转交执行，逻辑单一真源在 .sh
DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$DIR/start_lti_gate.sh"
