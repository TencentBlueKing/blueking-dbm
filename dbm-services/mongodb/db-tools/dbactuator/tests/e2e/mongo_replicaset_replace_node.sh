#!/usr/bin/env bash
set -euo pipefail

# E2E node replace test for replica set:
# 1) create 3-node rs (node3 hidden)
# 2) create dba + extra users + replicaset_init scripts
# 3) install target mongod (node4)
# 4) run mongod_replace: source=node3 -> target=node4
# 5) assert node4 joined and node3 removed
# 6) deinstall instances

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root (sudo)." >&2
  exit 1
fi

DATA_DIR="${TEST_DATA_DIR:-/data2}"
BACKUP_DIR="${TEST_BACKUP_DIR:-/data2}"
BIN_DIR="${TEST_BIN_DIR:-/data2}"
SET_ID="${TEST_SET_ID:-utRsReplace}"
DBA_USER="${TEST_DBA_USER:-xuser1}"
DBA_PASS="${TEST_DBA_PASS:-test123456}"
APPDBA_PASS="${TEST_APPDBA_PASS:-test123456}"
MONITOR_PASS="${TEST_MONITOR_PASS:-test123456}"
APPMONITOR_PASS="${TEST_APPMONITOR_PASS:-test123456}"
PKG_NAME="${TEST_MONGO_PKG_NAME:-mongodb-linux-x86_64-rhel70-4.4.30.tar.gz}"
PKG_MD5="${TEST_MONGO_PKG_MD5:-0856af7ed34231d4b533581c11d9ebe6}"
DB_VERSION="${TEST_MONGO_DB_VERSION:-4.4.30}"
OS_INIT_USER="${TEST_OS_INIT_USER:-mysql}"
OS_INIT_GROUP="${TEST_OS_INIT_GROUP:-mysql}"
OS_INIT_PASSWORD="${TEST_OS_INIT_PASSWORD:-test123456}"

PORT1="${TEST_PORT1:-28117}"
PORT2="${TEST_PORT2:-28118}"
PORT3="${TEST_PORT3:-28119}"
PORT4="${TEST_PORT4:-28120}"
NODE1_IP="${TEST_NODE1_IP:-127.0.0.2}"
NODE2_IP="${TEST_NODE2_IP:-127.0.0.3}"
NODE3_IP="${TEST_NODE3_IP:-127.0.0.4}"
NODE4_IP="${TEST_NODE4_IP:-127.0.0.5}"
PORTS=("${PORT1}" "${PORT2}" "${PORT3}" "${PORT4}")
NODE_IPS=("${NODE1_IP}" "${NODE2_IP}" "${NODE3_IP}" "${NODE4_IP}")

ACTUATOR_BIN="${ACTUATOR_BIN:-${BIN_DIR}/mongo-dbactuator}"
WORK_DIR="${TEST_WORK_DIR:-/tmp/mongo-rs-replace-e2e-${PORT1}}"
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
  echo "==> Running ${atom} on ${node_id}"
  "${ACTUATOR_BIN}" \
    --uid="${uid}" \
    --root_id="e2e-root-rs-replace-${PORT1}" \
    --node_id="${node_id}" \
    --version_id="v1" \
    --atom-job-list="${atom}" \
    --payload_file="${payload_file}" \
    --data_dir="${DATA_DIR}" \
    --backup_dir="${BACKUP_DIR}" \
    --bin_dir="${BIN_DIR}"
}

run_os_init() {
  local node_id="$1"
  echo "==> Running os_mongo_init on ${node_id}"
  "${ACTUATOR_BIN}" \
    --uid="e2e-rs-replace-os-init-${PORT1}" \
    --root_id="e2e-root-rs-replace-${PORT1}" \
    --node_id="${node_id}" \
    --version_id="v1" \
    --atom-job-list="os_mongo_init" \
    --payload_file="${WORK_DIR}/os_mongo_init.json" \
    --data_dir="${DATA_DIR}" \
    --backup_dir="${BACKUP_DIR}" \
    --bin_dir="${BIN_DIR}" \
    --user="${OS_INIT_USER}" \
    --group="${OS_INIT_GROUP}"
}

wait_rs_healthy_auth() {
  local host="$1"
  local port="$2"
  local attempt=0
  while [[ ${attempt} -lt 50 ]]; do
    local total healthy
    total="$($(mongo_shell_bin) -u "${DBA_USER}" -p "${DBA_PASS}" --authenticationDatabase=admin --host "${host}" --port "${port}" --quiet --eval "rs.status().members.length" || true)"
    healthy="$($(mongo_shell_bin) -u "${DBA_USER}" -p "${DBA_PASS}" --authenticationDatabase=admin --host "${host}" --port "${port}" --quiet --eval "rs.status().members.filter(function(m){return m.stateStr==='PRIMARY'||m.stateStr==='SECONDARY';}).length" || true)"
    if [[ "${total}" == "3" && "${healthy}" == "3" ]]; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 2
  done
  echo "ERROR: replica set not healthy(auth) within timeout" >&2
  exit 1
}

print_rs_status() {
  local host="$1"
  local port="$2"
  echo "==> Current rs members before replace (${host}:${port})"
  "$(mongo_shell_bin)" -u "${DBA_USER}" -p "${DBA_PASS}" --authenticationDatabase=admin \
    --host "${host}" --port "${port}" --quiet \
    --eval "rs.status().members.forEach(function(m){print(m.name + ' state=' + m.stateStr + ' health=' + m.health);})"
}

build_mongo_execute_script_json() {
  local out_json="$1"
  local script_file="$2"
  local script_name="$3"
  local exec_ip="$4"
  local exec_port="$5"
  SCRIPT_FILE="${script_file}" OUT_JSON="${out_json}" SCRIPT_NAME="${script_name}" \
    EXEC_IP="${exec_ip}" EXEC_PORT="${exec_port}" EXEC_DBA_USER="${DBA_USER}" EXEC_DBA_PASS="${DBA_PASS}" python3 - <<'PY'
import json
import os

with open(os.environ["SCRIPT_FILE"], encoding="utf-8") as f:
    script = f.read()
payload = {
    "ip": os.environ["EXEC_IP"],
    "port": int(os.environ["EXEC_PORT"]),
    "script": script,
    "type": "replicaset",
    "scriptName": os.environ["SCRIPT_NAME"],
    "secondary": False,
    "adminUsername": os.environ["EXEC_DBA_USER"],
    "adminPassword": os.environ["EXEC_DBA_PASS"],
    "repoUrl": "",
    "repoUsername": "",
    "repoToken": "",
    "repoProject": "",
    "repoRepo": "",
    "repoPath": "",
}
with open(os.environ["OUT_JSON"], "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)
    f.write("\n")
PY
}

echo "==> Building actuator"
go build -o mongo-dbactuator .
cp -f mongo-dbactuator "${ACTUATOR_BIN}"
chmod +x "${ACTUATOR_BIN}"

echo "==> Preparing payloads"
cat > "${WORK_DIR}/os_mongo_init.json" <<EOF
{
  "user": "${OS_INIT_USER}",
  "password": "${OS_INIT_PASSWORD}"
}
EOF

for idx in "${!PORTS[@]}"; do
  p="${PORTS[$idx]}"
  ip="${NODE_IPS[$idx]}"
  cat > "${WORK_DIR}/mongod_install_${p}.json" <<EOF
{
  "mediapkg": { "pkg": "${PKG_NAME}", "pkg_md5": "${PKG_MD5}" },
  "ip": "${ip}",
  "port": ${p},
  "dbVersion": "${DB_VERSION}",
  "instanceType": "mongod",
  "setId": "${SET_ID}",
  "keyFile": "ut-real-key-file",
  "auth": true,
  "clusterRole": "",
  "dbConfig": {
    "slowOpThresholdMs": 200,
    "cacheSizeGB": 1,
    "oplogSizeMB": 500,
    "destination": "file"
  }
}
EOF

  cat > "${WORK_DIR}/mongo_deinstall_${p}.json" <<EOF
{
  "ip": "${ip}",
  "port": ${p},
  "setId": "${SET_ID}",
  "nodeInfo": ["${ip}"],
  "instanceType": "mongod",
  "force": true,
  "renameDir": true
}
EOF
done

cat > "${WORK_DIR}/init_replicaset.json" <<EOF
{
  "ip": "${NODE1_IP}",
  "port": ${PORT1},
  "setId": "${SET_ID}",
  "configSvr": false,
  "ips": ["${NODE1_IP}:${PORT1}", "${NODE2_IP}:${PORT2}", "${NODE3_IP}:${PORT3}"],
  "priority": {"${NODE1_IP}:${PORT1}": 2, "${NODE2_IP}:${PORT2}": 1, "${NODE3_IP}:${PORT3}": 0},
  "hidden": {"${NODE1_IP}:${PORT1}": false, "${NODE2_IP}:${PORT2}": false, "${NODE3_IP}:${PORT3}": true}
}
EOF

cat > "${WORK_DIR}/add_user.json" <<EOF
{
  "ip": "${NODE1_IP}",
  "port": ${PORT1},
  "instanceType": "mongod",
  "username": "${DBA_USER}",
  "password": "${DBA_PASS}",
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

cat > "${WORK_DIR}/mongo_extra_user.js" <<EOF
db = db.getSiblingDB('admin');
var v = db.version();
var main = v.slice(0,3);
var float_main = parseFloat(main);
var num = db.system.users.count({'_id' : 'admin.yuser1'});
if (num == 0) {
    if (float_main >= 2.6) {
        db.createUser({user:'yuser1',pwd:'${APPDBA_PASS}',
        roles:[{role:'userAdminAnyDatabase',db:'admin'},{role:'dbAdminAnyDatabase',db:'admin'},
        {role:'readWriteAnyDatabase',db:'admin'},{role:'clusterAdmin',db:'admin'}]});
    } else {
        db.addUser({user:'yuser1',pwd:'${APPDBA_PASS}',
        roles:['userAdminAnyDatabase','dbAdminAnyDatabase','readWriteAnyDatabase','clusterAdmin']});
    }
}
var num =  db.system.users.count({'_id' : 'admin.xuser2'});
if (num == 0) {
    if (float_main >= 2.6) {
        db.createUser({user:'xuser2',pwd:'${MONITOR_PASS}',
        roles:[{role:'backup',db:'admin'},{role:'clusterMonitor',db:'admin'},
        {role:'readAnyDatabase',db:'admin'},{role:'hostManager',db:'admin'}]});
    } else {
        db.addUser({user:'xuser2',pwd:'${MONITOR_PASS}',
        roles:['clusterAdmin','readAnyDatabase','dbAdminAnyDatabase','userAdminAnyDatabase']});
    }
}
var num =  db.system.users.count({'_id' : 'admin.yuser2'});
if (num == 0) {
    if (float_main >= 2.6) {
        db.createUser({user:'yuser2',pwd:'${APPMONITOR_PASS}',
        roles:[{role:'backup',db:'admin'},{role:'clusterMonitor',db:'admin'},
        {role:'readAnyDatabase',db:'admin'},{role:'hostManager',db:'admin'}]});
    } else {
        db.addUser({user:'yuser2',pwd:'${APPMONITOR_PASS}',
        roles:['clusterAdmin', 'readAnyDatabase', 'dbAdminAnyDatabase', 'userAdminAnyDatabase']});
    }
}
EOF

cat > "${WORK_DIR}/mongo_replicaset_init.js" <<'EOF'
db = db.getSiblingDB('admin');
var num = db.system.roles.count({'_id':'admin.applyOps'});
if (num == 0) {
    db.createRole({role:'applyOps',privileges:[{resource:{anyResource:true},actions:['anyAction']}],roles:['root']});
    db.grantRolesToUser('xuser1',[{role:'applyOps',db:'admin'}]);
    db.grantRolesToUser('yuser1',[{role:'applyOps',db:'admin'}]);
}
var num = db.system.roles.count({'_id':'admin.heartbeatOps'});
if (num == 0) {
    db.createRole({role:'heartbeatOps',privileges:[{resource:{db:'admin',collection:'gcs_heartbeat'},
actions:['find','insert','update','remove']}],roles:[]});
    db.grantRolesToUser('xuser2',[{role:'heartbeatOps',db:'admin'}]);
}
var v = db.version();
if (v.match(/^3\./)) {
    db.system.version.insert({ '_id' : 'authSchema', 'currentVersion' : 3 });
}
EOF

build_mongo_execute_script_json "${WORK_DIR}/mongo_execute_script_extra_user.json" \
  "${WORK_DIR}/mongo_extra_user.js" "create_extra_user" "${NODE1_IP}" "${PORT1}"
build_mongo_execute_script_json "${WORK_DIR}/mongo_execute_script_init_set.json" \
  "${WORK_DIR}/mongo_replicaset_init.js" "replicaset_init" "${NODE1_IP}" "${PORT1}"

cat > "${WORK_DIR}/mongod_replace.json" <<EOF
{
  "ip": "${NODE1_IP}",
  "port": ${PORT1},
  "sourceIP": "${NODE3_IP}",
  "sourcePort": ${PORT3},
  "sourceDown": false,
  "adminUsername": "${DBA_USER}",
  "adminPassword": "${DBA_PASS}",
  "targetIP": "${NODE4_IP}",
  "targetPort": ${PORT4},
  "targetPriority": "",
  "targetHidden": ""
}
EOF

if [[ "${DEINSTALL_ONLY}" == "1" ]]; then
  echo "==> Deinstall-only mode"
  for p in "${PORTS[@]}"; do
    run_atom "e2e-rs-replace-deinstall-${p}" "mongo_deinstall" "${WORK_DIR}/mongo_deinstall_${p}.json" "e2e-node-${p}"
  done
  cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
  echo "E2E PASSED (deinstall-only). Logs: ${LOG_SNAPSHOT_DIR}"
  exit 0
fi

echo "==> Install base 3-node rs"
run_os_init "e2e-node-${PORT1}"
for p in "${PORT1}" "${PORT2}" "${PORT3}"; do
  run_atom "e2e-rs-replace-install-${p}" "mongod_install" "${WORK_DIR}/mongod_install_${p}.json" "e2e-node-${p}"
done

echo "==> Init replica set"
run_atom "e2e-rs-replace-init-${PORT1}" "init_replicaset" "${WORK_DIR}/init_replicaset.json" "e2e-node-${PORT1}"

echo "==> Add dba and init scripts"
run_atom "e2e-rs-replace-add-user-${PORT1}" "add_user" "${WORK_DIR}/add_user.json" "e2e-node-${PORT1}"
run_atom "e2e-rs-replace-extra-user-${PORT1}" "mongo_execute_script" \
  "${WORK_DIR}/mongo_execute_script_extra_user.json" "e2e-node-${PORT1}"
run_atom "e2e-rs-replace-init-set-${PORT1}" "mongo_execute_script" \
  "${WORK_DIR}/mongo_execute_script_init_set.json" "e2e-node-${PORT1}"
wait_rs_healthy_auth "${NODE1_IP}" "${PORT1}"

echo "==> Install target node"
run_atom "e2e-rs-replace-install-${PORT4}" "mongod_install" "${WORK_DIR}/mongod_install_${PORT4}.json" "e2e-node-${PORT4}"

print_rs_status "${NODE1_IP}" "${PORT1}"

echo "==> Replace source(hidden) node with target"
run_atom "e2e-rs-replace-run-${PORT1}" "mongod_replace" "${WORK_DIR}/mongod_replace.json" "e2e-node-${PORT1}"

echo "==> Assert replace result"
members="$($(mongo_shell_bin) -u "${DBA_USER}" -p "${DBA_PASS}" --authenticationDatabase=admin --host "${NODE1_IP}" --port "${PORT1}" --quiet --eval "rs.status().members.map(function(m){return m.name + ':' + m.stateStr;}).join(',')")"
if [[ "${members}" != *"${NODE4_IP}:${PORT4}"* ]]; then
  echo "ERROR: target node not found in rs.status(): ${members}" >&2
  exit 1
fi
if [[ "${members}" == *"${NODE3_IP}:${PORT3}"* ]]; then
  echo "ERROR: source node still exists in rs.status(): ${members}" >&2
  exit 1
fi

if [[ "${KEEP_INSTANCE}" == "1" ]]; then
  cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
  echo "E2E PASSED (keep instance mode). Deinstall skipped. Logs: ${LOG_SNAPSHOT_DIR}"
  exit 0
fi

echo "==> Deinstall all 4 nodes"
for p in "${PORTS[@]}"; do
  run_atom "e2e-rs-replace-deinstall-${p}" "mongo_deinstall" "${WORK_DIR}/mongo_deinstall_${p}.json" "e2e-node-${p}"
done

cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
echo "E2E PASSED. Logs: ${LOG_SNAPSHOT_DIR}"
