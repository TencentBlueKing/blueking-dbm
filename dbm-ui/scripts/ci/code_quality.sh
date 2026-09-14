#!/bin/bash
# 执行单元测试，并检测收集结果，避免 0 用例 / 1 error 假绿。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=ci_guards.sh
source "${SCRIPT_DIR}/ci_guards.sh"

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"
assert_ci_python_bin "$(command -v python)" "单测 Python"

PYTEST_VER="$(python -c 'import pytest; print(pytest.__version__)')"
if [[ ! "$PYTEST_VER" =~ ^6\.2\. ]]; then
  echo "❌ pytest 版本异常: ${PYTEST_VER}（期望 6.2.x）。请勿在 prepare_services 中安装未钉版本的 pytest"
  exit 1
fi
echo "✅ pytest 版本: ${PYTEST_VER}"

DBM_DIR="./dbm-ui"
cd "$DBM_DIR"

PYTEST_LOG="pytest-output.log"
rm -f "$PYTEST_LOG" pytest-junit.xml pytest-cov.xml

set +e
pytest --cov \
  --cov-report=term \
  --cov-report=xml:pytest-cov.xml \
  --junitxml=pytest-junit.xml 2>&1 | tee "$PYTEST_LOG"
PYTEST_RC=${PIPESTATUS[0]}
set -e

parse_pytest_log "$PYTEST_LOG"

echo "${PYTEST_SUMMARY:-<missing pytest summary>}"
echo "测试时长: 见 pytest summary"
echo "单元测试覆盖率: ${PYTEST_COVERAGE:-N/A}"
echo "收集用例数: ${PYTEST_COLLECTED}"
echo "统计用例数: ${PYTEST_COUNT}"
echo "成功数: ${PYTEST_PASSED}"
echo "失败数: ${PYTEST_FAILED}"
echo "异常数: ${PYTEST_ERRORS}"
echo "跳过数: ${PYTEST_SKIPPED}"
echo "未通过数: ${PYTEST_NOT_SUCCESS}"
echo "pytest 退出码: ${PYTEST_RC}"

if ! assert_pytest_session_healthy "$PYTEST_RC" "$PYTEST_COLLECTED" "$PYTEST_NOT_SUCCESS"; then
  echo "❌ 单元测试未通过，完整日志见 ${PYTEST_LOG}"
  exit 1
fi

if [[ ! -f pytest-junit.xml ]]; then
  echo "❌ 未生成 pytest-junit.xml，CI 无法收集单测报告"
  exit 1
fi

exit 0
