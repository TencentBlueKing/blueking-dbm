#!/usr/bin/env bash
set -euo pipefail

# E2E deploy test for a minimal sharded cluster (install flow mirrors
# dbm-ui/backend/flow/engine/bamboo/scene/mongodb/mongodb_install.py cluster_install_flow):
# - parallel install configsvr RS (3 nodes, auth=true) -> init_replicaset
# - create dba -> mongo_execute_script create_extra_user -> mongo_execute_script replicaset_init (on configsvr RS)
# - parallel install shardsvr RS (3 nodes, auth=true) -> init_replicaset
# - create dba -> mongo_execute_script create_extra_user -> mongo_execute_script replicaset_init (on shardsvr RS)
# - install mongos (auth=true)
# - add shard to cluster (via mongos, using dba credentials)
# - assert shard count
# Skipped vs prod: plugin/media/dir creation, password service/meta/DNS/default user/cluster init/dbmon/balancer ops.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root (sudo)." >&2
  exit 1
fi

# /data2 defaults are only for local/CI test environments.
# Production deployments should use their actual mount points (commonly /data1 or /data).
DATA_DIR="${TEST_DATA_DIR:-/data2}"
BACKUP_DIR="${TEST_BACKUP_DIR:-/data2}"
BIN_DIR="${TEST_BIN_DIR:-/data2}"
PKG_NAME="${TEST_MONGO_PKG_NAME:-mongodb-linux-x86_64-rhel70-4.4.30.tar.gz}"
PKG_MD5="${TEST_MONGO_PKG_MD5:-0856af7ed34231d4b533581c11d9ebe6}"
DB_VERSION="${TEST_MONGO_DB_VERSION:-4.4.30}"
DBA_USER="${TEST_DBA_USER:-xuser1}"
DBA_PASS="${TEST_DBA_PASS:-test123456}"
APPDBA_PASS="${TEST_APPDBA_PASS:-test123456}"
MONITOR_PASS="${TEST_MONITOR_PASS:-test123456}"
APPMONITOR_PASS="${TEST_APPMONITOR_PASS:-test123456}"
KEEP_INSTANCE="${KEEP_INSTANCE:-0}"
DEINSTALL_ONLY="${DEINSTALL_ONLY:-0}"
OS_INIT_USER="${TEST_OS_INIT_USER:-mysql}"
OS_INIT_GROUP="${TEST_OS_INIT_GROUP:-mysql}"
OS_INIT_PASSWORD="${TEST_OS_INIT_PASSWORD:-test123456}"

CFG_SET_ID="${TEST_CFG_SET_ID:-cfg}"
SHARD_SET_ID="${TEST_SHARD_SET_ID:-rs0}"
CFG_PORTS=("${TEST_CFG_PORT1:-29017}" "${TEST_CFG_PORT2:-29018}" "${TEST_CFG_PORT3:-29019}")
SHARD_PORTS=("${TEST_SHARD_PORT1:-29117}" "${TEST_SHARD_PORT2:-29118}" "${TEST_SHARD_PORT3:-29119}")
MONGOS_PORT="${TEST_MONGOS_PORT:-29217}"
CFG_IPS=("${TEST_CFG_IP1:-127.0.0.11}" "${TEST_CFG_IP2:-127.0.0.12}" "${TEST_CFG_IP3:-127.0.0.13}")
SHARD_IPS=("${TEST_SHARD_IP1:-127.0.0.21}" "${TEST_SHARD_IP2:-127.0.0.22}" "${TEST_SHARD_IP3:-127.0.0.23}")
MONGOS_IP="${TEST_MONGOS_IP:-127.0.0.31}"
ALL_PORTS=("${CFG_PORTS[@]}" "${SHARD_PORTS[@]}" "${MONGOS_PORT}")

ACTUATOR_BIN="${ACTUATOR_BIN:-${BIN_DIR}/mongo-dbactuator}"
WORK_DIR="${TEST_WORK_DIR:-/tmp/mongo-sharded-e2e-${MONGOS_PORT}}"
LOG_SNAPSHOT_DIR="${WORK_DIR}/logs"

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
  for p in "${ALL_PORTS[@]}"; do
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
    --root_id="e2e-root-sharded-${MONGOS_PORT}" \
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
    --uid="e2e-sharded-os-init-${MONGOS_PORT}" \
    --root_id="e2e-root-sharded-${MONGOS_PORT}" \
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

wait_rs_healthy_noauth() {
  local host="$1"
  local port="$2"
  local desc="$3"
  echo "==> Wait ${desc} healthy (noauth)"
  local attempt=0
  while [[ ${attempt} -lt 40 ]]; do
    local total healthy
    total="$($(mongo_shell_bin) --host "${host}" --port "${port}" --quiet --eval "rs.status().members.length" || true)"
    healthy="$($(mongo_shell_bin) --host "${host}" --port "${port}" --quiet --eval "rs.status().members.filter(function(m){return m.stateStr==='PRIMARY'||m.stateStr==='SECONDARY';}).length" || true)"
    if [[ "${total}" == "3" && "${healthy}" == "3" ]]; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 2
  done
  echo "ERROR: ${desc} not healthy within timeout" >&2
  exit 1
}

wait_rs_healthy_auth() {
  local host="$1"
  local port="$2"
  local desc="$3"
  echo "==> Wait ${desc} healthy (auth)"
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
  echo "ERROR: ${desc} not healthy(auth) within timeout" >&2
  exit 1
}

# Build mongo_execute_script payload JSON (script body must be JSON-escaped).
build_mongo_execute_script_json() {
  local out_json="$1"
  local script_file="$2"
  local script_name="$3"
  local exec_ip="$4"
  local port="$5"
  SCRIPT_FILE="${script_file}" OUT_JSON="${out_json}" SCRIPT_NAME="${script_name}" \
    EXEC_IP="${exec_ip}" EXEC_PORT="${port}" EXEC_DBA_USER="${DBA_USER}" EXEC_DBA_PASS="${DBA_PASS}" python3 - <<'PY'
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

for idx in "${!CFG_PORTS[@]}"; do
  p="${CFG_PORTS[$idx]}"
  ip="${CFG_IPS[$idx]}"
  cat > "${WORK_DIR}/cfg_mongod_install_${p}.json" <<EOF
{
  "mediapkg": { "pkg": "${PKG_NAME}", "pkg_md5": "${PKG_MD5}" },
  "ip": "${ip}",
  "port": ${p},
  "dbVersion": "${DB_VERSION}",
  "instanceType": "mongod",
  "setId": "${CFG_SET_ID}",
  "keyFile": "ut-sharded-key-file",
  "auth": true,
  "clusterRole": "configsvr",
  "dbConfig": { "slowOpThresholdMs": 200, "cacheSizeGB": 1, "oplogSizeMB": 500, "destination": "file" }
}
EOF
done

for idx in "${!SHARD_PORTS[@]}"; do
  p="${SHARD_PORTS[$idx]}"
  ip="${SHARD_IPS[$idx]}"
  cat > "${WORK_DIR}/shard_mongod_install_${p}.json" <<EOF
{
  "mediapkg": { "pkg": "${PKG_NAME}", "pkg_md5": "${PKG_MD5}" },
  "ip": "${ip}",
  "port": ${p},
  "dbVersion": "${DB_VERSION}",
  "instanceType": "mongod",
  "setId": "${SHARD_SET_ID}",
  "keyFile": "ut-sharded-key-file",
  "auth": true,
  "clusterRole": "shardsvr",
  "dbConfig": { "slowOpThresholdMs": 200, "cacheSizeGB": 1, "oplogSizeMB": 500, "destination": "file" }
}
EOF
done

cat > "${WORK_DIR}/cfg_init_replicaset.json" <<EOF
{
  "ip": "${CFG_IPS[0]}",
  "port": ${CFG_PORTS[0]},
  "setId": "${CFG_SET_ID}",
  "configSvr": true,
  "ips": ["${CFG_IPS[0]}:${CFG_PORTS[0]}", "${CFG_IPS[1]}:${CFG_PORTS[1]}", "${CFG_IPS[2]}:${CFG_PORTS[2]}"],
  "priority": {"${CFG_IPS[0]}:${CFG_PORTS[0]}": 2, "${CFG_IPS[1]}:${CFG_PORTS[1]}": 1, "${CFG_IPS[2]}:${CFG_PORTS[2]}": 0},
  "hidden": {"${CFG_IPS[0]}:${CFG_PORTS[0]}": false, "${CFG_IPS[1]}:${CFG_PORTS[1]}": false, "${CFG_IPS[2]}:${CFG_PORTS[2]}": true}
}
EOF

cat > "${WORK_DIR}/shard_init_replicaset.json" <<EOF
{
  "ip": "${SHARD_IPS[0]}",
  "port": ${SHARD_PORTS[0]},
  "setId": "${SHARD_SET_ID}",
  "configSvr": false,
  "ips": ["${SHARD_IPS[0]}:${SHARD_PORTS[0]}", "${SHARD_IPS[1]}:${SHARD_PORTS[1]}", "${SHARD_IPS[2]}:${SHARD_PORTS[2]}"],
  "priority": {"${SHARD_IPS[0]}:${SHARD_PORTS[0]}": 2, "${SHARD_IPS[1]}:${SHARD_PORTS[1]}": 1, "${SHARD_IPS[2]}:${SHARD_PORTS[2]}": 0},
  "hidden": {"${SHARD_IPS[0]}:${SHARD_PORTS[0]}": false, "${SHARD_IPS[1]}:${SHARD_PORTS[1]}": false, "${SHARD_IPS[2]}:${SHARD_PORTS[2]}": true}
}
EOF

cat > "${WORK_DIR}/mongos_install.json" <<EOF
{
  "mediapkg": { "pkg": "${PKG_NAME}", "pkg_md5": "${PKG_MD5}" },
  "ip": "${MONGOS_IP}",
  "port": ${MONGOS_PORT},
  "dbVersion": "${DB_VERSION}",
  "instanceType": "mongos",
  "setId": "${CFG_SET_ID}",
  "keyFile": "ut-sharded-key-file",
  "auth": true,
  "configDB": ["${CFG_IPS[0]}:${CFG_PORTS[0]}", "${CFG_IPS[1]}:${CFG_PORTS[1]}", "${CFG_IPS[2]}:${CFG_PORTS[2]}"],
  "dbConfig": { "slowOpThresholdMs": 200, "destination": "file" }
}
EOF

cat > "${WORK_DIR}/cfg_add_user.json" <<EOF
{
  "ip": "${CFG_IPS[0]}",
  "port": ${CFG_PORTS[0]},
  "instanceType": "mongod",
  "username": "${DBA_USER}",
  "password": "${DBA_PASS}",
  "adminUsername": "",
  "adminPassword": "",
  "authDb": "admin",
  "dbsPrivileges": [
    { "db": "admin", "privileges": ["root"] }
  ]
}
EOF

cat > "${WORK_DIR}/shard_add_user.json" <<EOF
{
  "ip": "${SHARD_IPS[0]}",
  "port": ${SHARD_PORTS[0]},
  "instanceType": "mongod",
  "username": "${DBA_USER}",
  "password": "${DBA_PASS}",
  "adminUsername": "",
  "adminPassword": "",
  "authDb": "admin",
  "dbsPrivileges": [
    { "db": "admin", "privileges": ["root"] }
  ]
}
EOF

# JS bodies from dbm-ui/backend/flow/utils/mongodb/mongodb_script_template.py
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

build_mongo_execute_script_json "${WORK_DIR}/cfg_mongo_execute_script_extra_user.json" \
  "${WORK_DIR}/mongo_extra_user.js" "create_extra_user" "${CFG_IPS[0]}" "${CFG_PORTS[0]}"
build_mongo_execute_script_json "${WORK_DIR}/cfg_mongo_execute_script_init_set.json" \
  "${WORK_DIR}/mongo_replicaset_init.js" "replicaset_init" "${CFG_IPS[0]}" "${CFG_PORTS[0]}"
build_mongo_execute_script_json "${WORK_DIR}/shard_mongo_execute_script_extra_user.json" \
  "${WORK_DIR}/mongo_extra_user.js" "create_extra_user" "${SHARD_IPS[0]}" "${SHARD_PORTS[0]}"
build_mongo_execute_script_json "${WORK_DIR}/shard_mongo_execute_script_init_set.json" \
  "${WORK_DIR}/mongo_replicaset_init.js" "replicaset_init" "${SHARD_IPS[0]}" "${SHARD_PORTS[0]}"

cat > "${WORK_DIR}/add_shard.json" <<EOF
{
  "ip": "${MONGOS_IP}",
  "port": ${MONGOS_PORT},
  "adminUsername": "${DBA_USER}",
  "adminPassword": "${DBA_PASS}",
  "shards": {
    "${SHARD_SET_ID}": "${SHARD_IPS[0]}:${SHARD_PORTS[0]},${SHARD_IPS[1]}:${SHARD_PORTS[1]}"
  }
}
EOF

for idx in "${!ALL_PORTS[@]}"; do
  p="${ALL_PORTS[$idx]}"
  ip="${MONGOS_IP}"
  if [[ ${idx} -lt 3 ]]; then
    ip="${CFG_IPS[$idx]}"
  elif [[ ${idx} -lt 6 ]]; then
    ip="${SHARD_IPS[$((idx-3))]}"
  fi
  instance_type="mongod"
  if [[ "${p}" == "${MONGOS_PORT}" ]]; then
    instance_type="mongos"
  fi
  cat > "${WORK_DIR}/mongo_deinstall_${p}.json" <<EOF
{
  "ip": "${ip}",
  "port": ${p},
  "setId": "cleanup",
  "nodeInfo": ["${ip}"],
  "instanceType": "${instance_type}",
  "force": true,
  "renameDir": true
}
EOF
done

if [[ "${DEINSTALL_ONLY}" == "1" ]]; then
  echo "==> Deinstall-only mode"
  for p in "${CFG_PORTS[@]}"; do
    run_atom "e2e-sharded-cfg-deinstall-${p}" "mongo_deinstall" "${WORK_DIR}/mongo_deinstall_${p}.json" "e2e-node-cfg-${p}"
  done
  for p in "${SHARD_PORTS[@]}"; do
    run_atom "e2e-sharded-shard-deinstall-${p}" "mongo_deinstall" "${WORK_DIR}/mongo_deinstall_${p}.json" "e2e-node-shard-${p}"
  done
  run_atom "e2e-sharded-mongos-deinstall-${MONGOS_PORT}" "mongo_deinstall" "${WORK_DIR}/mongo_deinstall_${MONGOS_PORT}.json" "e2e-node-mongos-${MONGOS_PORT}"
  cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
  echo "E2E PASSED (deinstall-only). Logs: ${LOG_SNAPSHOT_DIR}"
  exit 0
fi

echo "==> Install config server RS nodes"
run_os_init "e2e-node-cfg-${CFG_PORTS[0]}"
cfg_install_pids=()
for p in "${CFG_PORTS[@]}"; do
  ( run_atom "e2e-sharded-cfg-install-${p}" "mongod_install" "${WORK_DIR}/cfg_mongod_install_${p}.json" "e2e-node-cfg-${p}" ) &
  cfg_install_pids+=($!)
done
for pid in "${cfg_install_pids[@]}"; do
  wait "${pid}"
done

echo "==> Init config server RS"
run_atom "e2e-sharded-cfg-init-${CFG_PORTS[0]}" "init_replicaset" "${WORK_DIR}/cfg_init_replicaset.json" "e2e-node-cfg-${CFG_PORTS[0]}"
wait_rs_healthy_noauth "${CFG_IPS[0]}" "${CFG_PORTS[0]}" "config RS"

echo "==> Config RS: create dba user"
run_atom "e2e-sharded-cfg-add-user-${CFG_PORTS[0]}" "add_user" "${WORK_DIR}/cfg_add_user.json" "e2e-node-cfg-${CFG_PORTS[0]}"
echo "==> Config RS: mongo_execute_script create_extra_user"
run_atom "e2e-sharded-cfg-exec-extra-user-${CFG_PORTS[0]}" "mongo_execute_script" \
  "${WORK_DIR}/cfg_mongo_execute_script_extra_user.json" "e2e-node-cfg-${CFG_PORTS[0]}"
echo "==> Config RS: mongo_execute_script replicaset_init"
run_atom "e2e-sharded-cfg-exec-init-set-${CFG_PORTS[0]}" "mongo_execute_script" \
  "${WORK_DIR}/cfg_mongo_execute_script_init_set.json" "e2e-node-cfg-${CFG_PORTS[0]}"
wait_rs_healthy_auth "${CFG_IPS[0]}" "${CFG_PORTS[0]}" "config RS"

echo "==> Install shard RS nodes"
shard_install_pids=()
for p in "${SHARD_PORTS[@]}"; do
  ( run_atom "e2e-sharded-shard-install-${p}" "mongod_install" "${WORK_DIR}/shard_mongod_install_${p}.json" "e2e-node-shard-${p}" ) &
  shard_install_pids+=($!)
done
for pid in "${shard_install_pids[@]}"; do
  wait "${pid}"
done

echo "==> Init shard RS"
run_atom "e2e-sharded-shard-init-${SHARD_PORTS[0]}" "init_replicaset" "${WORK_DIR}/shard_init_replicaset.json" "e2e-node-shard-${SHARD_PORTS[0]}"
wait_rs_healthy_noauth "${SHARD_IPS[0]}" "${SHARD_PORTS[0]}" "shard RS"

echo "==> Shard RS: create dba user"
run_atom "e2e-sharded-shard-add-user-${SHARD_PORTS[0]}" "add_user" "${WORK_DIR}/shard_add_user.json" "e2e-node-shard-${SHARD_PORTS[0]}"
echo "==> Shard RS: mongo_execute_script create_extra_user"
run_atom "e2e-sharded-shard-exec-extra-user-${SHARD_PORTS[0]}" "mongo_execute_script" \
  "${WORK_DIR}/shard_mongo_execute_script_extra_user.json" "e2e-node-shard-${SHARD_PORTS[0]}"
echo "==> Shard RS: mongo_execute_script replicaset_init"
run_atom "e2e-sharded-shard-exec-init-set-${SHARD_PORTS[0]}" "mongo_execute_script" \
  "${WORK_DIR}/shard_mongo_execute_script_init_set.json" "e2e-node-shard-${SHARD_PORTS[0]}"
wait_rs_healthy_auth "${SHARD_IPS[0]}" "${SHARD_PORTS[0]}" "shard RS"

echo "==> Install mongos"
run_atom "e2e-sharded-mongos-install-${MONGOS_PORT}" "mongos_install" "${WORK_DIR}/mongos_install.json" "e2e-node-mongos-${MONGOS_PORT}"

echo "==> Add shard RS to cluster"
run_atom "e2e-sharded-add-shard-${MONGOS_PORT}" "add_shard_to_cluster" "${WORK_DIR}/add_shard.json" "e2e-node-mongos-${MONGOS_PORT}"

echo "==> Assert shard count"
shard_count="$($(mongo_shell_bin) -u "${DBA_USER}" -p "${DBA_PASS}" --authenticationDatabase=admin --host "${MONGOS_IP}" --port "${MONGOS_PORT}" --quiet --eval "db.getSiblingDB('config').shards.count()")"
if [[ "${shard_count}" != "1" ]]; then
  echo "ERROR: expected shard count 1, got ${shard_count}" >&2
  exit 1
fi

if [[ "${KEEP_INSTANCE}" == "1" ]]; then
  cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
  echo "E2E PASSED (keep instance mode). Deinstall skipped. Logs: ${LOG_SNAPSHOT_DIR}"
  exit 0
fi

echo "==> Deinstall all nodes"
for p in "${CFG_PORTS[@]}"; do
  run_atom "e2e-sharded-cfg-deinstall-${p}" "mongo_deinstall" "${WORK_DIR}/mongo_deinstall_${p}.json" "e2e-node-cfg-${p}"
done
for p in "${SHARD_PORTS[@]}"; do
  run_atom "e2e-sharded-shard-deinstall-${p}" "mongo_deinstall" "${WORK_DIR}/mongo_deinstall_${p}.json" "e2e-node-shard-${p}"
done
run_atom "e2e-sharded-mongos-deinstall-${MONGOS_PORT}" "mongo_deinstall" "${WORK_DIR}/mongo_deinstall_${MONGOS_PORT}.json" "e2e-node-mongos-${MONGOS_PORT}"

cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
echo "E2E PASSED. Logs: ${LOG_SNAPSHOT_DIR}"
