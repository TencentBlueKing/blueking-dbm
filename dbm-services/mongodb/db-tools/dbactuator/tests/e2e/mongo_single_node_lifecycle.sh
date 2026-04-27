#!/usr/bin/env bash
set -euo pipefail

# E2E lifecycle test:
# 1) mongod_install
# 2) init_replicaset
# 3) add_user
# 4) mongo_restart(auth=true)
# 5) mongo_deinstall
#
# Options:
#   --keep-instance    Keep instance after step 4 (skip step 5 deinstall)
#   --deinstall-only   Skip steps 1-4 and run only step 5 deinstall

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root (sudo)." >&2
  exit 1
fi

PORT="${TEST_PORT:-28017}"
# /data2 defaults are only for local/CI test environments.
# Production deployments should use their actual mount points (commonly /data1 or /data).
DATA_DIR="${TEST_DATA_DIR:-/data2}"
BACKUP_DIR="${TEST_BACKUP_DIR:-/data2}"
BIN_DIR="${TEST_BIN_DIR:-/data2}"
SET_ID="${TEST_SET_ID:-utRealSet}"
ADMIN_USER="${TEST_ADMIN_USER:-admin}"
ADMIN_PASS="${TEST_ADMIN_PASS:-test123456}"
PKG_NAME="${TEST_MONGO_PKG_NAME:-mongodb-linux-x86_64-rhel70-4.4.30.tar.gz}"
PKG_MD5="${TEST_MONGO_PKG_MD5:-0856af7ed34231d4b533581c11d9ebe6}"
DB_VERSION="${TEST_MONGO_DB_VERSION:-4.4.30}"
OS_INIT_USER="${TEST_OS_INIT_USER:-mysql}"
OS_INIT_GROUP="${TEST_OS_INIT_GROUP:-mysql}"
OS_INIT_PASSWORD="${TEST_OS_INIT_PASSWORD:-test123456}"

ACTUATOR_BIN="${ACTUATOR_BIN:-${BIN_DIR}/mongo-dbactuator}"
WORK_DIR="${TEST_WORK_DIR:-/tmp/mongo-e2e-${PORT}}"
LOG_SNAPSHOT_DIR="${WORK_DIR}/logs"
KEEP_INSTANCE="${KEEP_INSTANCE:-0}"
DEINSTALL_ONLY="${DEINSTALL_ONLY:-0}"

for arg in "$@"; do
  case "${arg}" in
    --keep-instance)
      KEEP_INSTANCE=1
      shift
      ;;
    --deinstall-only)
      DEINSTALL_ONLY=1
      shift
      ;;
    *)
      echo "ERROR: unknown argument: ${arg}" >&2
      exit 1
      ;;
  esac
done

if [[ "${KEEP_INSTANCE}" == "1" && "${DEINSTALL_ONLY}" == "1" ]]; then
  echo "ERROR: --keep-instance and --deinstall-only are mutually exclusive" >&2
  exit 1
fi

mkdir -p "${WORK_DIR}" "${LOG_SNAPSHOT_DIR}" "${BIN_DIR}"

on_fail() {
  local exit_code="$?"
  echo "E2E failed, collecting logs..." >&2
  cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
  netstat -ntpl 2>/dev/null | rg "${PORT}" || true
  echo "Logs saved under: ${LOG_SNAPSHOT_DIR}" >&2
  exit "${exit_code}"
}
trap on_fail ERR

echo "==> Building actuator"
go build -o mongo-dbactuator .
cp -f mongo-dbactuator "${ACTUATOR_BIN}"
chmod +x "${ACTUATOR_BIN}"

echo "==> Preparing payloads"
cat > "${WORK_DIR}/mongod_install.json" <<EOF
{
  "mediapkg": {
    "pkg": "${PKG_NAME}",
    "pkg_md5": "${PKG_MD5}"
  },
  "ip": "127.0.0.1",
  "port": ${PORT},
  "dbVersion": "${DB_VERSION}",
  "instanceType": "mongod",
  "setId": "${SET_ID}",
  "keyFile": "ut-real-key-file",
  "auth": false,
  "clusterRole": "",
  "dbConfig": {
    "slowOpThresholdMs": 200,
    "cacheSizeGB": 1,
    "oplogSizeMB": 500,
    "destination": "file"
  }
}
EOF

cat > "${WORK_DIR}/os_mongo_init.json" <<EOF
{
  "user": "${OS_INIT_USER}",
  "password": "${OS_INIT_PASSWORD}"
}
EOF

cat > "${WORK_DIR}/init_replicaset.json" <<EOF
{
  "ip": "127.0.0.1",
  "port": ${PORT},
  "setId": "${SET_ID}",
  "configSvr": false,
  "ips": ["127.0.0.1:${PORT}"],
  "priority": {"127.0.0.1:${PORT}": 1},
  "hidden": {"127.0.0.1:${PORT}": false}
}
EOF

cat > "${WORK_DIR}/add_user.json" <<EOF
{
  "ip": "127.0.0.1",
  "port": ${PORT},
  "instanceType": "mongod",
  "username": "${ADMIN_USER}",
  "password": "${ADMIN_PASS}",
  "adminUsername": "",
  "adminPassword": "",
  "authDb": "admin",
  "dbsPrivileges": [
    {
      "db": "admin",
      "privileges": ["root"]
    }
  ]
}
EOF

cat > "${WORK_DIR}/mongo_restart.json" <<EOF
{
  "ip": "127.0.0.1",
  "port": ${PORT},
  "instanceType": "mongod",
  "auth": true,
  "setId": "${SET_ID}",
  "adminUsername": "${ADMIN_USER}",
  "adminPassword": "${ADMIN_PASS}",
  "cacheSizeGB": 1
}
EOF

cat > "${WORK_DIR}/mongo_deinstall.json" <<EOF
{
  "ip": "127.0.0.1",
  "port": ${PORT},
  "setId": "${SET_ID}",
  "nodeInfo": ["127.0.0.1"],
  "instanceType": "mongod",
  "force": true,
  "renameDir": true
}
EOF

run_atom() {
  local uid="$1"
  local atom="$2"
  local payload_file="$3"
  echo "==> Running ${atom}"
  "${ACTUATOR_BIN}" \
    --uid="${uid}" \
    --root_id="e2e-root-${PORT}" \
    --node_id="e2e-node-${PORT}" \
    --version_id="v1" \
    --atom-job-list="${atom}" \
    --payload_file="${payload_file}" \
    --data_dir="${DATA_DIR}" \
    --backup_dir="${BACKUP_DIR}" \
    --bin_dir="${BIN_DIR}"
}

run_os_init() {
  echo "==> Running os_mongo_init"
  "${ACTUATOR_BIN}" \
    --uid="e2e-os-init-${PORT}" \
    --root_id="e2e-root-${PORT}" \
    --node_id="e2e-node-${PORT}" \
    --version_id="v1" \
    --atom-job-list="os_mongo_init" \
    --payload_file="${WORK_DIR}/os_mongo_init.json" \
    --data_dir="${DATA_DIR}" \
    --backup_dir="${BACKUP_DIR}" \
    --bin_dir="${BIN_DIR}" \
    --user="${OS_INIT_USER}" \
    --group="${OS_INIT_GROUP}"
}

assert_port_listening() {
  echo "==> Assert port ${PORT} is listening"
  netstat -ntpl 2>/dev/null | rg -q "${PORT}"
}

assert_port_stopped() {
  echo "==> Assert port ${PORT} is stopped"
  local attempt=0
  local max_attempts=30
  while [[ ${attempt} -lt ${max_attempts} ]]; do
    if ! netstat -ntpl 2>/dev/null | rg -q "${PORT}"; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 1
  done
  echo "ERROR: port ${PORT} is still listening after ${max_attempts}s" >&2
  netstat -ntpl 2>/dev/null | rg "${PORT}" || true
  exit 1
}

mongo_shell_bin() {
  if [[ -x "${BIN_DIR}/mongodb/bin/mongo" ]]; then
    echo "${BIN_DIR}/mongodb/bin/mongo"
  else
    echo "${BIN_DIR}/mongodb/bin/mongosh"
  fi
}

assert_primary_noauth() {
  echo "==> Assert rs primary (noauth)"
  [[ "$($(mongo_shell_bin) --host 127.0.0.1 --port "${PORT}" --quiet --eval "rs.isMaster().ismaster")" == "true" ]]
}

assert_primary_auth() {
  echo "==> Assert rs primary (auth)"
  [[ "$($(mongo_shell_bin) -u "${ADMIN_USER}" -p "${ADMIN_PASS}" --authenticationDatabase=admin --host 127.0.0.1 --port "${PORT}" --quiet --eval "rs.isMaster().ismaster")" == "true" ]]
}

if [[ "${DEINSTALL_ONLY}" == "1" ]]; then
  echo "==> Deinstall-only mode"
  run_atom "e2e-deinstall-${PORT}" "mongo_deinstall" "${WORK_DIR}/mongo_deinstall.json"
  assert_port_stopped
  cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
  echo "E2E PASSED (deinstall-only). Logs: ${LOG_SNAPSHOT_DIR}"
  exit 0
fi

run_os_init

run_atom "e2e-install-${PORT}" "mongod_install" "${WORK_DIR}/mongod_install.json"
assert_port_listening

run_atom "e2e-init-rs-${PORT}" "init_replicaset" "${WORK_DIR}/init_replicaset.json"
assert_primary_noauth

run_atom "e2e-add-user-${PORT}" "add_user" "${WORK_DIR}/add_user.json"

run_atom "e2e-restart-${PORT}" "mongo_restart" "${WORK_DIR}/mongo_restart.json"
assert_primary_auth

if [[ "${KEEP_INSTANCE}" == "1" ]]; then
  cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
  echo "E2E PASSED (keep instance mode). Deinstall skipped. Logs: ${LOG_SNAPSHOT_DIR}"
  exit 0
fi

run_atom "e2e-deinstall-${PORT}" "mongo_deinstall" "${WORK_DIR}/mongo_deinstall.json"
assert_port_stopped

cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
echo "E2E PASSED. Logs: ${LOG_SNAPSHOT_DIR}"
