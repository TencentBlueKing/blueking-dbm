#!/bin/bash
# ============================================================
# DBM 项目 CI 检查主脚本
# 功能：执行项目的完整性检查、安装和质量控制
# ============================================================
set -euo pipefail

# 获取当前脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "当前脚本目录: $SCRIPT_DIR"
echo "============================================================"

run_step() {
  local name="$1"
  local script="$2"
  echo "${name}"
  if ! "${script}"; then
    echo "❌ ${name} 失败，终止 CI"
    exit 1
  fi
}

run_step "[0/4] CI 检测机制自检..." "${SCRIPT_DIR}/test_ci_guards.sh"
run_step "[1/4] 准备服务环境..." "${SCRIPT_DIR}/prepare_services.sh"
run_step "[2/4] 安装项目依赖并进行迁移文件检查..." "${SCRIPT_DIR}/install.sh"
run_step "[3/4] 执行代码质量检查..." "${SCRIPT_DIR}/code_quality.sh"

echo "============================================================"
echo "🎉 所有 CI 检查通过！"
exit 0
