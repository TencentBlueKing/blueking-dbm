#!/usr/bin/env bash
set -euo pipefail

# E2E os_mongo_init test:
# - run os_mongo_init atom
# - verify lock file and required directories
# - verify kernel variables are applied during init and restored on exit

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root (sudo)." >&2
  exit 1
fi

RUN_ID="$(date +%s)"
INIT_USER="${TEST_OS_INIT_USER:-mongoosinit}"
INIT_GROUP="${TEST_OS_INIT_GROUP:-mongoosinit}"
INIT_PASSWORD="${TEST_OS_INIT_PASSWORD:-test123456}"
DATA_DIR="${TEST_DATA_DIR:-/tmp/mongo-os-init-data-${RUN_ID}}"
BACKUP_DIR="${TEST_BACKUP_DIR:-/tmp/mongo-os-init-backup-${RUN_ID}}"
BIN_DIR="${TEST_BIN_DIR:-/tmp}"
ACTUATOR_BIN="${ACTUATOR_BIN:-${BIN_DIR}/mongo-dbactuator}"
WORK_DIR="${TEST_WORK_DIR:-/tmp/mongo-os-init-e2e-${RUN_ID}}"

mkdir -p "${WORK_DIR}" "${BIN_DIR}"

old_swappiness="$(sysctl -n vm.swappiness)"
old_pid_max="$(sysctl -n kernel.pid_max)"

cleanup() {
  set +e
  sysctl -w "vm.swappiness=${old_swappiness}" >/dev/null 2>&1 || true
  sysctl -w "kernel.pid_max=${old_pid_max}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

ensure_user_group() {
  if ! getent group "${INIT_GROUP}" >/dev/null 2>&1; then
    groupadd "${INIT_GROUP}"
  fi
  if ! id "${INIT_USER}" >/dev/null 2>&1; then
    useradd -m -g "${INIT_GROUP}" "${INIT_USER}"
  fi
}

run_atom() {
  local payload_file="$1"
  "${ACTUATOR_BIN}" \
    --uid="e2e-os-init-${RUN_ID}" \
    --root_id="e2e-root-os-init-${RUN_ID}" \
    --node_id="e2e-node-os-init-${RUN_ID}" \
    --version_id="v1" \
    --atom-job-list="os_mongo_init" \
    --payload_file="${payload_file}" \
    --data_dir="${DATA_DIR}" \
    --backup_dir="${BACKUP_DIR}" \
    --bin_dir="${BIN_DIR}" \
    --user="${INIT_USER}" \
    --group="${INIT_GROUP}"
}

echo "==> Build actuator"
go build -o mongo-dbactuator .
cp -f mongo-dbactuator "${ACTUATOR_BIN}"
chmod +x "${ACTUATOR_BIN}"

ensure_user_group

echo "==> Prepare payload"
cat > "${WORK_DIR}/os_mongo_init.json" <<EOF
{
  "user": "${INIT_USER}",
  "password": "${INIT_PASSWORD}"
}
EOF

echo "==> Run os_mongo_init"
run_atom "${WORK_DIR}/os_mongo_init.json"

echo "==> Verify lock file"
[[ -f /tmp/mongoinstall.lock ]]

echo "==> Verify directories from env"
[[ -d "${DATA_DIR}" ]]
[[ -d "${BACKUP_DIR}" ]]
[[ -d "${BACKUP_DIR}/dbbak" ]]

echo "==> Verify kernel variables changed by init"
[[ "$(sysctl -n vm.swappiness)" == "0" ]]
[[ "$(sysctl -n kernel.pid_max)" == "200000" ]]

echo "E2E PASSED: os_mongo_init"
