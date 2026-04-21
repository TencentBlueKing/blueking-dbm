#!/usr/bin/env bash
set -euo pipefail

# Smoke test for clean_residual_exporter_exec.py:
# 1) Create a temporary exporter directory under external_plugins
# 2) Run cleaner script
# 3) Assert exporter directory is removed

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PY_SCRIPT="${ROOT_DIR}/backend/flow/engine/bamboo/scene/common/clean_residual_exporter_exec.py"

if [[ ! -f "${PY_SCRIPT}" ]]; then
  echo "ERROR: script not found: ${PY_SCRIPT}" >&2
  exit 1
fi

PYBIN=""
if command -v python3 >/dev/null 2>&1; then
  PYBIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYBIN="python"
else
  echo "ERROR: python3/python not found" >&2
  exit 1
fi

TMP_BASE="$(mktemp -d)"
trap 'rm -rf "${TMP_BASE}"' EXIT

EXPORTER_DIR="${TMP_BASE}/external_plugins/sub_001_service_001/dbm_test_exporter"
PARENT_DIR="$(dirname "${EXPORTER_DIR}")"
mkdir -p "${EXPORTER_DIR}"

echo "[before] exporter dir exists: ${EXPORTER_DIR}"
ls -ld "${EXPORTER_DIR}"

"${PYBIN}" "${PY_SCRIPT}" \
  --base-dir "${TMP_BASE}" \
  --exporters "dbm_test_exporter" \
  --dry-run false \
  --enable-legacy-clean false \
  --enable-reload false

if [[ -d "${EXPORTER_DIR}" ]]; then
  echo "FAIL: exporter dir still exists: ${EXPORTER_DIR}" >&2
  exit 1
fi

if [[ -d "${PARENT_DIR}" ]]; then
  echo "FAIL: empty parent dir still exists: ${PARENT_DIR}" >&2
  exit 1
fi

echo "PASS: exporter dir removed successfully"
echo "PASS: empty parent dir removed successfully"
