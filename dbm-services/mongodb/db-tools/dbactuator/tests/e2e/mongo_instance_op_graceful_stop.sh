#!/usr/bin/env bash
set -euo pipefail

# E2E: validate mongodb_instance_op gracefulStop behavior on a 3-node replica set.
# 1) bootstrap RS by reusing mongo_three_node_replicaset_lifecycle.sh --keep-instance
# 2) stop current primary with gracefulStop=true, then start it back
# 3) stop current primary with gracefulStop=false, then start it back
# 4) deinstall all nodes

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root (sudo)." >&2
  exit 1
fi

# Keep defaults aligned with mongo_three_node_replicaset_lifecycle.sh.
DATA_DIR="${TEST_DATA_DIR:-/data2}"
BACKUP_DIR="${TEST_BACKUP_DIR:-/data2}"
BIN_DIR="${TEST_BIN_DIR:-/data2}"
DBA_USER="${TEST_DBA_USER:-xuser1}"
DBA_PASS="${TEST_DBA_PASS:-test123456}"
PORT1="${TEST_PORT1:-28017}"
PORT2="${TEST_PORT2:-28018}"
PORT3="${TEST_PORT3:-28019}"
NODE1_IP="${TEST_NODE1_IP:-127.0.0.2}"
NODE2_IP="${TEST_NODE2_IP:-127.0.0.3}"
NODE3_IP="${TEST_NODE3_IP:-127.0.0.4}"
PORTS=("${PORT1}" "${PORT2}" "${PORT3}")

ACTUATOR_BIN="${ACTUATOR_BIN:-${BIN_DIR}/mongo-dbactuator}"
WORK_DIR="${TEST_WORK_DIR:-/tmp/mongo-instance-op-graceful-e2e-${PORT1}}"
LOG_SNAPSHOT_DIR="${WORK_DIR}/logs"
mkdir -p "${WORK_DIR}" "${LOG_SNAPSHOT_DIR}" "${BIN_DIR}"

lifecycle_script="${ROOT_DIR}/tests/e2e/mongo_three_node_replicaset_lifecycle.sh"

run_three_node_lifecycle() {
  TEST_DATA_DIR="${DATA_DIR}" \
  TEST_BACKUP_DIR="${BACKUP_DIR}" \
  TEST_BIN_DIR="${BIN_DIR}" \
  TEST_DBA_USER="${DBA_USER}" \
  TEST_DBA_PASS="${DBA_PASS}" \
  TEST_PORT1="${PORT1}" \
  TEST_PORT2="${PORT2}" \
  TEST_PORT3="${PORT3}" \
  TEST_NODE1_IP="${NODE1_IP}" \
  TEST_NODE2_IP="${NODE2_IP}" \
  TEST_NODE3_IP="${NODE3_IP}" \
  "${lifecycle_script}" "$@"
}

on_fail() {
  local exit_code="$?"
  echo "E2E failed, trying to cleanup cluster..." >&2
  run_three_node_lifecycle --deinstall-only || true
  cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
  for p in "${PORTS[@]}"; do
    netstat -ntpl 2>/dev/null | rg "${p}" || true
  done
  echo "Logs saved under: ${LOG_SNAPSHOT_DIR}" >&2
  exit "${exit_code}"
}
trap on_fail ERR

mongo_shell_bin() {
  if [[ -x "${BIN_DIR}/mongodb/bin/mongo" ]]; then
    echo "${BIN_DIR}/mongodb/bin/mongo"
  else
    echo "${BIN_DIR}/mongodb/bin/mongosh"
  fi
}

run_atom() {
  local uid="$1"
  local atom="$2"
  local payload_file="$3"
  local node_id="$4"
  local run_as="${5:-}"
  echo "==> Running ${atom} (${uid}) on ${node_id}"
  if [[ -n "${run_as}" ]]; then
    sudo -u "${run_as}" "${ACTUATOR_BIN}" \
      --uid="${uid}" \
      --root_id="e2e-root-graceful-stop-${PORT1}" \
      --node_id="${node_id}" \
      --version_id="v1" \
      --atom-job-list="${atom}" \
      --payload_file="${payload_file}" \
      --data_dir="${DATA_DIR}" \
      --backup_dir="${BACKUP_DIR}" \
      --bin_dir="${BIN_DIR}"
  else
    "${ACTUATOR_BIN}" \
      --uid="${uid}" \
      --root_id="e2e-root-graceful-stop-${PORT1}" \
      --node_id="${node_id}" \
      --version_id="v1" \
      --atom-job-list="${atom}" \
      --payload_file="${payload_file}" \
      --data_dir="${DATA_DIR}" \
      --backup_dir="${BACKUP_DIR}" \
      --bin_dir="${BIN_DIR}"
  fi
}

wait_rs_healthy_auth() {
  local attempt=0
  while [[ ${attempt} -lt 40 ]]; do
    local total healthy
    total="$($(mongo_shell_bin) -u "${DBA_USER}" -p "${DBA_PASS}" --authenticationDatabase=admin --host "${NODE1_IP}" --port "${PORT1}" --quiet --eval "rs.status().members.length" || true)"
    healthy="$($(mongo_shell_bin) -u "${DBA_USER}" -p "${DBA_PASS}" --authenticationDatabase=admin --host "${NODE1_IP}" --port "${PORT1}" --quiet --eval "rs.status().members.filter(function(m){return m.stateStr==='PRIMARY'||m.stateStr==='SECONDARY';}).length" || true)"
    if [[ "${total}" == "3" && "${healthy}" == "3" ]]; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 2
  done
  echo "ERROR: replica set not healthy(auth) within timeout" >&2
  exit 1
}

current_primary() {
  "$(mongo_shell_bin)" -u "${DBA_USER}" -p "${DBA_PASS}" \
    --authenticationDatabase=admin --host "${NODE1_IP}" --port "${PORT1}" \
    --quiet --eval "rs.isMaster().primary" | tr -d '[:space:]'
}

wait_port_stopped() {
  local port="$1"
  local attempt=0
  while [[ ${attempt} -lt 30 ]]; do
    if ! netstat -ntpl 2>/dev/null | rg -q ":${port}[[:space:]]"; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 1
  done
  echo "ERROR: port ${port} still listening after stop" >&2
  netstat -ntpl 2>/dev/null | rg ":${port}[[:space:]]" || true
  exit 1
}

wait_port_listen() {
  local port="$1"
  local attempt=0
  while [[ ${attempt} -lt 30 ]]; do
    if netstat -ntpl 2>/dev/null | rg -q ":${port}[[:space:]]"; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 1
  done
  echo "ERROR: port ${port} not listening after start" >&2
  exit 1
}

build_instance_stop_payload() {
  local ip="$1"
  local port="$2"
  local graceful="$3"
  local out="$4"
  cat > "${out}" <<EOF
{
  "ip": "${ip}",
  "port": ${port},
  "adminUsername": "${DBA_USER}",
  "adminPassword": "${DBA_PASS}",
  "op": "stop",
  "gracefulStop": ${graceful}
}
EOF
}

build_instance_start_payload() {
  local ip="$1"
  local port="$2"
  local out="$3"
  cat > "${out}" <<EOF
{
  "ip": "${ip}",
  "port": ${port},
  "adminUsername": "${DBA_USER}",
  "adminPassword": "${DBA_PASS}",
  "op": "start"
}
EOF
}

stop_and_start_primary() {
  local graceful="$1"
  local tag="$2"
  local primary host port payload_stop payload_start

  primary="$(current_primary)"
  if [[ -z "${primary}" || "${primary}" != *:* ]]; then
    echo "ERROR: failed to detect current primary, got '${primary}'" >&2
    exit 1
  fi
  host="${primary%:*}"
  port="${primary##*:}"
  payload_stop="${WORK_DIR}/instance_op_stop_${tag}_${port}.json"
  payload_start="${WORK_DIR}/instance_op_start_${tag}_${port}.json"

  echo "==> Testing gracefulStop=${graceful} on primary ${host}:${port}"
  build_instance_stop_payload "${host}" "${port}" "${graceful}" "${payload_stop}"
  run_atom "e2e-instance-op-stop-${tag}-${port}" "mongodb_instance_op" "${payload_stop}" "e2e-node-${port}" "mysql"
  wait_port_stopped "${port}"

  build_instance_start_payload "${host}" "${port}" "${payload_start}"
  run_atom "e2e-instance-op-start-${tag}-${port}" "mongodb_instance_op" "${payload_start}" "e2e-node-${port}" "mysql"
  wait_port_listen "${port}"
  wait_rs_healthy_auth
}

echo "==> Building actuator"
go build -o mongo-dbactuator .
cp -f mongo-dbactuator "${ACTUATOR_BIN}"
chmod +x "${ACTUATOR_BIN}"

echo "==> Bootstrapping 3-node replica set"
run_three_node_lifecycle --keep-instance
wait_rs_healthy_auth

stop_and_start_primary "true" "graceful"
stop_and_start_primary "false" "non_graceful"

echo "==> Cleanup cluster"
run_three_node_lifecycle --deinstall-only

cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
echo "E2E PASSED. Logs: ${LOG_SNAPSHOT_DIR}"
