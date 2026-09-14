#!/bin/bash
# CI 检测机制自检：用固定摘要覆盖 python3.10 / 1 error / 收集 0 条等假绿场景。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=ci_guards.sh
source "${SCRIPT_DIR}/ci_guards.sh"

FAIL_COUNT=0

assert_eq() {
  local name="$1"
  local expected="$2"
  local actual="$3"
  if [[ "$expected" != "$actual" ]]; then
    echo "FAIL ${name}: expected='${expected}' actual='${actual}'"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  else
    echo "PASS ${name}"
  fi
}

assert_rc() {
  local name="$1"
  local expected_rc="$2"
  shift 2
  set +e
  "$@" >/dev/null
  local actual_rc=$?
  set -e
  assert_eq "$name" "$expected_rc" "$actual_rc"
}

echo "============================================================"
echo "CI guards self-test"
echo "============================================================"

assert_rc "supported python 3.11" 0 is_supported_python_version "3.11"
assert_rc "reject python 3.10 version" 1 is_supported_python_version "3.10"
assert_rc "forbid /usr/bin/python3.10" 0 is_forbidden_python_bin "/usr/bin/python3.10"
assert_rc "allow python3.11 bin" 1 is_forbidden_python_bin "/opt/hostedtoolcache/Python/3.11.10/x64/bin/python3"

parse_pytest_summary_line "======================== 26 warnings, 1 error in 51.72s ========================"
assert_eq "singular error count" "1" "$PYTEST_ERRORS"
assert_eq "singular error has no passed" "0" "$PYTEST_PASSED"

parse_pytest_summary_line "====== 1 failed, 109 passed, 3 skipped, 580 warnings, 3 errors in 48.02s ======="
assert_eq "failed count" "1" "$PYTEST_FAILED"
assert_eq "passed count" "109" "$PYTEST_PASSED"
assert_eq "skipped count" "3" "$PYTEST_SKIPPED"
assert_eq "plural errors count" "3" "$PYTEST_ERRORS"

parse_pytest_summary_line "==== 93 failed, 3607 passed, 16 skipped, 248 warnings in 299.94s (0:04:59) ====="
assert_eq "large failed count" "93" "$PYTEST_FAILED"
assert_eq "large passed count" "3607" "$PYTEST_PASSED"
assert_eq "no error token means 0" "0" "$PYTEST_ERRORS"

TMP_LOG="$(mktemp)"
trap 'rm -f "$TMP_LOG"' EXIT

cat >"$TMP_LOG" <<'EOF'
============================= test session starts ==============================
collected 0 items

======================== 26 warnings, 1 error in 51.72s ========================
EOF
parse_pytest_log "$TMP_LOG"
assert_eq "zero collected from log" "0" "$PYTEST_COLLECTED"
assert_eq "hidden 1 error from log" "1" "$PYTEST_ERRORS"
assert_rc "reject empty collection" 1 assert_pytest_session_healthy 1 "$PYTEST_COLLECTED" "$PYTEST_NOT_SUCCESS"

cat >"$TMP_LOG" <<'EOF'
============================= test session starts ==============================
collected 3716 items
==== 93 failed, 3607 passed, 16 skipped in 299.94s =====
EOF
parse_pytest_log "$TMP_LOG"
assert_eq "collected from log" "3716" "$PYTEST_COLLECTED"
assert_rc "reject pytest non-zero rc" 1 assert_pytest_session_healthy 1 "$PYTEST_COLLECTED" "$PYTEST_NOT_SUCCESS"

cat >"$TMP_LOG" <<'EOF'
============================= test session starts ==============================
collected 109 items
====== 109 passed, 3 skipped in 48.02s =======
EOF
parse_pytest_log "$TMP_LOG"
assert_rc "accept green session" 0 assert_pytest_session_healthy 0 "$PYTEST_COLLECTED" "$PYTEST_NOT_SUCCESS"

if [[ "$FAIL_COUNT" -ne 0 ]]; then
  echo "❌ CI 检测机制自检失败: ${FAIL_COUNT} 项"
  exit 1
fi

echo "✅ CI 检测机制自检通过"
exit 0
