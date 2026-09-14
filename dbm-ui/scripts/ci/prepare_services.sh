#!/bin/bash
# 准备 CI Python 虚拟环境，并校验解释器版本（必须是 3.11.x）。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=ci_guards.sh
source "${SCRIPT_DIR}/ci_guards.sh"

PYTHON_BIN="$(command -v python3 || true)"
assert_ci_python_bin "$PYTHON_BIN" "系统 Python"

if [ "${CREATE_PYTHON_VENV:-}" ]; then
  VENV_DIR="${VENV_DIR:-/tmp/ci_py_venv}"
  python3 -m pip install --disable-pip-version-check "virtualenv==${PINNED_VIRTUALENV_VERSION}"
  echo "使用 ${PYTHON_BIN} 创建虚拟环境: ${VENV_DIR}"
  python3 -m virtualenv --clear -p "$PYTHON_BIN" "$VENV_DIR"
  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
  assert_ci_python_bin "$(command -v python)" "虚拟环境 Python"
fi

python -m pip install --upgrade pip
python -V
pip list
