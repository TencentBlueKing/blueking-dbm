#!/usr/bin/env bash
set -euo pipefail

# E2E add_user idempotency test:
# A) first add_user succeeds
# B) repeated add_user with same password/roles succeeds
# C) repeated add_user with mismatched roles fails
#
# Options:
#   --keep-instance    Keep instance after scenario B/C (skip deinstall)
#   --deinstall-only   Skip setup scenarios and run only deinstall

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root (sudo)." >&2
  exit 1
fi

PORT="${TEST_PORT:-28017}"
SECONDARY_PORT="${TEST_SECONDARY_PORT:-28018}"
# /data2 defaults are only for local/CI test environments.
# Production deployments should use their actual mount points (commonly /data1 or /data).
DATA_DIR="${TEST_DATA_DIR:-/data2}"
BACKUP_DIR="${TEST_BACKUP_DIR:-/data2}"
BIN_DIR="${TEST_BIN_DIR:-/data2}"
SET_ID="${TEST_SET_ID:-utAddUserSet}"

ADMIN_USER="${TEST_ADMIN_USER:-admin}"
ADMIN_PASS="${TEST_ADMIN_PASS:-test123456}"

PKG_NAME="${TEST_MONGO_PKG_NAME:-mongodb-linux-x86_64-rhel70-4.4.30.tar.gz}"
PKG_MD5="${TEST_MONGO_PKG_MD5:-0856af7ed34231d4b533581c11d9ebe6}"
DB_VERSION="${TEST_MONGO_DB_VERSION:-4.4.30}"
OS_INIT_USER="${TEST_OS_INIT_USER:-mysql}"
OS_INIT_GROUP="${TEST_OS_INIT_GROUP:-mysql}"
OS_INIT_PASSWORD="${TEST_OS_INIT_PASSWORD:-test123456}"

ACTUATOR_BIN="${ACTUATOR_BIN:-${BIN_DIR}/mongo-dbactuator}"
WORK_DIR="${TEST_WORK_DIR:-/tmp/mongo-add-user-e2e-${PORT}}"
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
  netstat -ntpl 2>/dev/null | rg "${SECONDARY_PORT}" || true
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

assert_primary_noauth() {
  echo "==> Assert rs primary (noauth)"
  [[ "$($(mongo_shell_bin) --host 127.0.0.1 --port "${PORT}" --quiet --eval "rs.isMaster().ismaster")" == "true" ]]
}

assert_can_login_admin() {
  echo "==> Assert admin credential login ok"
  local result
  result="$($(mongo_shell_bin) -u "${ADMIN_USER}" -p "${ADMIN_PASS}" --authenticationDatabase=admin \
    --host 127.0.0.1 --port "${PORT}" --quiet --eval "db.runCommand({connectionStatus:1}).ok")"
  [[ "${result}" == "1" ]]
}

assert_can_login_user() {
  local username="$1"
  local password="$2"
  local auth_db="${3:-admin}"
  local target_port="${4:-${PORT}}"
  echo "==> Assert user credential login ok (${username}@${auth_db})"
  local result
  result="$($(mongo_shell_bin) -u "${username}" -p "${password}" --authenticationDatabase="${auth_db}" \
    --host 127.0.0.1 --port "${target_port}" --quiet --eval "db.runCommand({connectionStatus:1}).ok")"
  [[ "${result}" == "1" ]]
}

assert_admin_roles_root() {
  echo "==> Assert admin roles include root@admin"
  local roles
  roles="$($(mongo_shell_bin) -u "${ADMIN_USER}" -p "${ADMIN_PASS}" --authenticationDatabase=admin \
    --host 127.0.0.1 --port "${PORT}" --quiet \
    --eval "u=db.getSiblingDB('admin').getUser('${ADMIN_USER}'); print(u.roles.map(function(r){return r.role+'@'+r.db;}).sort().join(','))")"
  [[ "${roles}" == *"root@admin"* ]]
}

assert_expected_add_user_fail() {
  local payload_file="$1"
  echo "==> Scenario C: expect add_user failure for mismatched definition"
  set +e
  local output
  output="$(run_atom "e2e-add-user-fail-${PORT}" "add_user" "${payload_file}" 2>&1)"
  local exit_code=$?
  set -e

  if [[ ${exit_code} -eq 0 ]]; then
    echo "ERROR: expected add_user to fail, but it succeeded" >&2
    exit 1
  fi
  if ! echo "${output}" | rg -qi "already exists|does not match|roles"; then
    echo "ERROR: add_user failed but missing expected keywords in output" >&2
    echo "${output}" >&2
    exit 1
  fi
}

assert_add_user_should_succeed() {
  local payload_file="$1"
  run_atom "e2e-add-user-admin-repeat-${PORT}" "add_user" "${payload_file}"
}

assert_parallel_add_user_should_succeed_and_hit_already_exists() {
  local payload_file="$1"
  local pids=()
  local outputs=()
  local idx
  echo "==> Scenario J: parallel normal add_user should all succeed and hit already-exists branch"
  for idx in 1 2 3 4; do
    local out_file="${WORK_DIR}/parallel_add_user_${idx}.out"
    outputs+=("${out_file}")
    (
      run_atom "e2e-add-user-parallel-${PORT}-${idx}" "add_user" "${payload_file}"
    ) >"${out_file}" 2>&1 &
    pids+=("$!")
  done

  local wait_rc=0
  for idx in "${!pids[@]}"; do
    if ! wait "${pids[idx]}"; then
      echo "ERROR: parallel add_user run ${idx} failed" >&2
      wait_rc=1
    fi
  done
  if [[ "${wait_rc}" -ne 0 ]]; then
    for out in "${outputs[@]}"; do
      echo "---- ${out} ----" >&2
      cat "${out}" >&2
    done
    exit 1
  fi

  if ! rg -qi "already exists|definition matches exactly, continue|skip add_user" "${outputs[@]}"; then
    # Actuator detailed logs may be written to ROOT_DIR/logs instead of command stdout.
    if ! rg -qi "already exists|definition matches exactly, continue|skip add_user" "${ROOT_DIR}"/logs/mongo_actuator_*.log; then
      echo "ERROR: parallel scenario did not hit already-exists compatible path" >&2
      for out in "${outputs[@]}"; do
        echo "---- ${out} ----" >&2
        cat "${out}" >&2
      done
      exit 1
    fi
  fi
}

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

cat > "${WORK_DIR}/mongod_install_secondary.json" <<EOF
{
  "mediapkg": {
    "pkg": "${PKG_NAME}",
    "pkg_md5": "${PKG_MD5}"
  },
  "ip": "127.0.0.1",
  "port": ${SECONDARY_PORT},
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
  "ips": ["127.0.0.1:${PORT}", "127.0.0.1:${SECONDARY_PORT}"],
  "priority": {"127.0.0.1:${PORT}": 1, "127.0.0.1:${SECONDARY_PORT}": 0},
  "hidden": {"127.0.0.1:${PORT}": false, "127.0.0.1:${SECONDARY_PORT}": false}
}
EOF

cat > "${WORK_DIR}/add_user_ok_first.json" <<EOF
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

cat > "${WORK_DIR}/add_user_ok_repeat_same.json" <<EOF
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

cat > "${WORK_DIR}/add_user_fail_role_or_pass.json" <<EOF
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
      "privileges": ["readAnyDatabase"]
    }
  ]
}
EOF

cat > "${WORK_DIR}/add_user_admin_nonempty_first.json" <<EOF
{
  "ip": "127.0.0.1",
  "port": ${PORT},
  "instanceType": "mongod",
  "username": "testuser",
  "password": "test123456",
  "adminUsername": "${ADMIN_USER}",
  "adminPassword": "${ADMIN_PASS}",
  "authDb": "admin",
  "dbsPrivileges": [
    {
      "db": "admin",
      "privileges": ["readAnyDatabase"]
    }
  ]
}
EOF

cat > "${WORK_DIR}/add_user_admin_nonempty_repeat_same.json" <<EOF
{
  "ip": "127.0.0.1",
  "port": ${PORT},
  "instanceType": "mongod",
  "username": "testuser",
  "password": "test123456",
  "adminUsername": "${ADMIN_USER}",
  "adminPassword": "${ADMIN_PASS}",
  "authDb": "admin",
  "dbsPrivileges": [
    {
      "db": "admin",
      "privileges": ["readAnyDatabase"]
    }
  ]
}
EOF

cat > "${WORK_DIR}/add_user_bootstrap_no_authdb.json" <<EOF
{
  "ip": "127.0.0.1",
  "port": ${PORT},
  "instanceType": "mongod",
  "username": "defaultauthuser",
  "password": "test123456",
  "adminUsername": "",
  "adminPassword": "",
  "dbsPrivileges": [
    {
      "db": "admin",
      "privileges": ["readAnyDatabase"]
    }
  ]
}
EOF

cat > "${WORK_DIR}/add_user_appdb_first.json" <<EOF
{
  "ip": "127.0.0.1",
  "port": ${PORT},
  "instanceType": "mongod",
  "username": "appdbuser",
  "password": "test123456",
  "adminUsername": "${ADMIN_USER}",
  "adminPassword": "${ADMIN_PASS}",
  "authDb": "appdb",
  "dbsPrivileges": [
    {
      "db": "appdb",
      "privileges": ["readWrite"]
    }
  ]
}
EOF

cat > "${WORK_DIR}/add_user_admin_nonempty_fail_password.json" <<EOF
{
  "ip": "127.0.0.1",
  "port": ${PORT},
  "instanceType": "mongod",
  "username": "testuser",
  "password": "wrong-password",
  "adminUsername": "${ADMIN_USER}",
  "adminPassword": "${ADMIN_PASS}",
  "authDb": "admin",
  "dbsPrivileges": [
    {
      "db": "admin",
      "privileges": ["readAnyDatabase"]
    }
  ]
}
EOF

cat > "${WORK_DIR}/add_user_admin_nonempty_fail_role.json" <<EOF
{
  "ip": "127.0.0.1",
  "port": ${PORT},
  "instanceType": "mongod",
  "username": "testuser",
  "password": "test123456",
  "adminUsername": "${ADMIN_USER}",
  "adminPassword": "${ADMIN_PASS}",
  "authDb": "admin",
  "dbsPrivileges": [
    {
      "db": "admin",
      "privileges": ["dbAdminAnyDatabase"]
    }
  ]
}
EOF

cat > "${WORK_DIR}/add_user_admin_parallel_race.json" <<EOF
{
  "ip": "127.0.0.1",
  "port": ${PORT},
  "instanceType": "mongod",
  "username": "paralleluser",
  "password": "test123456",
  "adminUsername": "${ADMIN_USER}",
  "adminPassword": "${ADMIN_PASS}",
  "authDb": "admin",
  "dbsPrivileges": [
    {
      "db": "admin",
      "privileges": ["readAnyDatabase"]
    }
  ]
}
EOF

cat > "${WORK_DIR}/add_user_secondary_node_normal.json" <<EOF
{
  "ip": "127.0.0.1",
  "port": ${SECONDARY_PORT},
  "instanceType": "mongod",
  "username": "secondarynodeuser",
  "password": "test123456",
  "adminUsername": "${ADMIN_USER}",
  "adminPassword": "${ADMIN_PASS}",
  "authDb": "admin",
  "dbsPrivileges": [
    {
      "db": "admin",
      "privileges": ["readAnyDatabase"]
    }
  ]
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

cat > "${WORK_DIR}/mongo_deinstall_secondary.json" <<EOF
{
  "ip": "127.0.0.1",
  "port": ${SECONDARY_PORT},
  "setId": "${SET_ID}",
  "nodeInfo": ["127.0.0.1"],
  "instanceType": "mongod",
  "force": true,
  "renameDir": true
}
EOF

if [[ "${DEINSTALL_ONLY}" == "1" ]]; then
  echo "==> Deinstall-only mode"
  run_atom "e2e-deinstall-${PORT}" "mongo_deinstall" "${WORK_DIR}/mongo_deinstall.json"
  run_atom "e2e-deinstall-${SECONDARY_PORT}" "mongo_deinstall" "${WORK_DIR}/mongo_deinstall_secondary.json"
  cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
  echo "E2E PASSED (deinstall-only). Logs: ${LOG_SNAPSHOT_DIR}"
  exit 0
fi

echo "==> Setup mongo single-node rs"
run_os_init
run_atom "e2e-install-${PORT}" "mongod_install" "${WORK_DIR}/mongod_install.json"
run_atom "e2e-install-${SECONDARY_PORT}" "mongod_install" "${WORK_DIR}/mongod_install_secondary.json"
run_atom "e2e-init-rs-${PORT}" "init_replicaset" "${WORK_DIR}/init_replicaset.json"
assert_primary_noauth

echo "==> Scenario A: first add_user should succeed"
run_atom "e2e-add-user-first-${PORT}" "add_user" "${WORK_DIR}/add_user_ok_first.json"
assert_can_login_admin
assert_admin_roles_root

echo "==> Scenario B: repeat add_user with same definition should succeed"
run_atom "e2e-add-user-repeat-${PORT}" "add_user" "${WORK_DIR}/add_user_ok_repeat_same.json"
assert_can_login_admin
assert_admin_roles_root

echo "==> Scenario C: bootstrap repeat with mismatched roles should still succeed (auth-only semantics)"
run_atom "e2e-add-user-bootstrap-role-mismatch-${PORT}" "add_user" "${WORK_DIR}/add_user_fail_role_or_pass.json"
assert_can_login_admin

echo "==> Scenario D: first add_user with admin credentials should succeed"
run_atom "e2e-add-user-admin-first-${PORT}" "add_user" "${WORK_DIR}/add_user_admin_nonempty_first.json"
assert_can_login_user "testuser" "test123456" "admin"

echo "==> Scenario E: repeat add_user with admin credentials should succeed"
assert_add_user_should_succeed "${WORK_DIR}/add_user_admin_nonempty_repeat_same.json"
assert_can_login_user "testuser" "test123456" "admin"

echo "==> Scenario F: bootstrap add_user without authDb should default to admin and succeed"
run_atom "e2e-add-user-bootstrap-no-authdb-${PORT}" "add_user" "${WORK_DIR}/add_user_bootstrap_no_authdb.json"
assert_can_login_user "defaultauthuser" "test123456" "admin"

echo "==> Scenario G: add_user with authDb=appdb should succeed and be idempotent"
run_atom "e2e-add-user-appdb-first-${PORT}" "add_user" "${WORK_DIR}/add_user_appdb_first.json"
assert_can_login_user "appdbuser" "test123456" "appdb"
run_atom "e2e-add-user-appdb-repeat-${PORT}" "add_user" "${WORK_DIR}/add_user_appdb_first.json"
assert_can_login_user "appdbuser" "test123456" "appdb"

echo "==> Scenario H: add_user with admin credentials but mismatched password should fail"
assert_expected_add_user_fail "${WORK_DIR}/add_user_admin_nonempty_fail_password.json"

echo "==> Scenario I: add_user with admin credentials but mismatched roles should fail"
assert_expected_add_user_fail "${WORK_DIR}/add_user_admin_nonempty_fail_role.json"

assert_parallel_add_user_should_succeed_and_hit_already_exists "${WORK_DIR}/add_user_admin_parallel_race.json"
assert_can_login_user "paralleluser" "test123456" "admin"

echo "==> Scenario K: add_user via secondary node endpoint should succeed"
run_atom "e2e-add-user-via-secondary-${SECONDARY_PORT}" "add_user" "${WORK_DIR}/add_user_secondary_node_normal.json"
assert_can_login_user "secondarynodeuser" "test123456" "admin" "${PORT}"

if [[ "${KEEP_INSTANCE}" == "1" ]]; then
  cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
  echo "E2E PASSED (keep instance mode). Deinstall skipped. Logs: ${LOG_SNAPSHOT_DIR}"
  exit 0
fi

echo "==> Cleanup by mongo_deinstall"
run_atom "e2e-deinstall-${PORT}" "mongo_deinstall" "${WORK_DIR}/mongo_deinstall.json"
run_atom "e2e-deinstall-${SECONDARY_PORT}" "mongo_deinstall" "${WORK_DIR}/mongo_deinstall_secondary.json"

cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
echo "E2E PASSED. Logs: ${LOG_SNAPSHOT_DIR}"
