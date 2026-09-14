#!/bin/bash
# CI 检测机制：Python 解释器约束 + pytest 结果解析
# 可被其它脚本 source，也可由 test_ci_guards.sh 做自检。

EXPECTED_PYTHON_MAJOR_MINOR="${EXPECTED_PYTHON_MAJOR_MINOR:-3.11}"
PINNED_VIRTUALENV_VERSION="${PINNED_VIRTUALENV_VERSION:-20.36.1}"

python_major_minor() {
  local py_bin="${1:-python3}"
  "$py_bin" -c 'import sys; print("%d.%d" % (sys.version_info.major, sys.version_info.minor))'
}

is_supported_python_version() {
  local ver="$1"
  [[ "$ver" == "$EXPECTED_PYTHON_MAJOR_MINOR" ]]
}

is_forbidden_python_bin() {
  local bin="$1"
  [[ "$bin" == *python3.10* ]]
}

assert_ci_python_bin() {
  local py_bin="$1"
  local context="${2:-python}"

  if [[ -z "$py_bin" ]]; then
    echo "❌ ${context}: 未找到 Python 解释器"
    return 1
  fi
  if [[ ! -x "$py_bin" ]]; then
    echo "❌ ${context}: 解释器不可执行: ${py_bin}"
    return 1
  fi
  if is_forbidden_python_bin "$py_bin"; then
    echo "❌ ${context}: 项目已升级到 Python ${EXPECTED_PYTHON_MAJOR_MINOR}，禁止使用 python3.10: ${py_bin}"
    return 1
  fi

  local ver
  ver="$(python_major_minor "$py_bin")"
  if ! is_supported_python_version "$ver"; then
    echo "❌ ${context}: Python 版本必须是 ${EXPECTED_PYTHON_MAJOR_MINOR}.x，实际为 ${ver} (${py_bin})"
    return 1
  fi

  echo "✅ ${context}: ${py_bin} (${ver})"
  return 0
}

extract_pytest_count() {
  local line="$1"
  local pattern="$2"
  if [[ "$line" =~ $pattern ]]; then
    echo "${BASH_REMATCH[1]}"
  else
    echo 0
  fi
}

parse_pytest_summary_line() {
  local line="$1"
  PYTEST_FAILED="$(extract_pytest_count "$line" '([0-9]+)[[:space:]]+failed')"
  PYTEST_PASSED="$(extract_pytest_count "$line" '([0-9]+)[[:space:]]+passed')"
  PYTEST_SKIPPED="$(extract_pytest_count "$line" '([0-9]+)[[:space:]]+skipped')"
  PYTEST_ERRORS="$(extract_pytest_count "$line" '([0-9]+)[[:space:]]+errors?')"
}

parse_pytest_collected() {
  local log_file="$1"
  local collected_line
  collected_line="$(grep -Eo 'collected [0-9]+ items?' "$log_file" 2>/dev/null | head -n 1 || true)"
  if [[ "$collected_line" =~ collected[[:space:]]+([0-9]+) ]]; then
    echo "${BASH_REMATCH[1]}"
  else
    echo 0
  fi
}

parse_pytest_log() {
  local log_file="$1"
  PYTEST_SUMMARY=""
  PYTEST_FAILED=0
  PYTEST_PASSED=0
  PYTEST_SKIPPED=0
  PYTEST_ERRORS=0
  PYTEST_COLLECTED=0
  PYTEST_COVERAGE=""

  if [[ ! -f "$log_file" ]]; then
    echo "❌ pytest 日志不存在: ${log_file}"
    return 1
  fi

  PYTEST_COLLECTED="$(parse_pytest_collected "$log_file")"
  PYTEST_SUMMARY="$(grep -E '=+ .*(failed|passed|skipped|error|warnings).* in [0-9.]+s' "$log_file" | tail -n 1 || true)"
  if [[ -n "$PYTEST_SUMMARY" ]]; then
    parse_pytest_summary_line "$PYTEST_SUMMARY"
  fi
  PYTEST_COVERAGE="$(grep -E '^TOTAL ' "$log_file" | tail -n 1 | sed -n 's/.*[[:space:]]\([0-9]*%\)$/\1/p' || true)"
  PYTEST_COUNT=$((PYTEST_PASSED + PYTEST_FAILED + PYTEST_SKIPPED + PYTEST_ERRORS))
  PYTEST_NOT_SUCCESS=$((PYTEST_FAILED + PYTEST_ERRORS))
}

assert_pytest_session_healthy() {
  local pytest_rc="$1"
  local collected="$2"
  local not_success="$3"

  if [[ "$pytest_rc" -ne 0 ]]; then
    echo "❌ pytest 退出码为 ${pytest_rc}，禁止将失败会话标记为通过"
    return 1
  fi
  if [[ "$collected" -le 0 ]]; then
    echo "❌ 未能收集到任何单元测试（collected=${collected}），禁止假绿"
    return 1
  fi
  if [[ "$not_success" -ne 0 ]]; then
    echo "❌ 单元测试未全部通过：失败+异常=${not_success}"
    return 1
  fi
  echo "✅ pytest 会话检测通过：collected=${collected}"
  return 0
}
