#!/usr/bin/env bash
set -euo pipefail

# Local MongoShake DTS smoke (RS -> RS), no DBM Job:
# 1) actuator deploy source + empty target single-node replica sets
# 2) seed source user data
# 3) mongo-dbactuator mongoshake_collector start (collector.linux from /tmp/mongo-dts.tar.gz)
# 4) mongo-dbactuator mongoshake_collector wait_stop
# 5) compare document counts
# 6) deinstall unless --keep-instance
#
# Options:
#   --keep-instance    Keep MongoDB instances after sync (skip deinstall)
#   --deinstall-only   Only deinstall previous instances

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root (sudo)." >&2
  exit 1
fi

DATA_DIR="${TEST_DATA_DIR:-/data2}"
BACKUP_DIR="${TEST_BACKUP_DIR:-/data2}"
BIN_DIR="${TEST_BIN_DIR:-/data2}"
# Default to 4.4.30 to reuse existing /data2/mongodb media on local test hosts.
PKG_NAME="${TEST_MONGO_PKG_NAME:-mongodb-linux-x86_64-rhel70-4.4.30.tar.gz}"
PKG_MD5="${TEST_MONGO_PKG_MD5:-0856af7ed34231d4b533581c11d9ebe6}"
DB_VERSION="${TEST_MONGO_DB_VERSION:-4.4.30}"
ADMIN_USER="${TEST_ADMIN_USER:-dba}"
ADMIN_PASS="${TEST_ADMIN_PASS:-test123456}"
SRC_DTS_USER="${TEST_SRC_DTS_USER:-mongodts_src}"
SRC_DTS_PASS="${TEST_SRC_DTS_PASS:-xxxx}"
DST_DTS_USER="${TEST_DST_DTS_USER:-mongodts_dst}"
DST_DTS_PASS="${TEST_DST_DTS_PASS:-xxxx}"
OS_INIT_USER="${TEST_OS_INIT_USER:-mysql}"
OS_INIT_GROUP="${TEST_OS_INIT_GROUP:-mysql}"
OS_INIT_PASSWORD="${TEST_OS_INIT_PASSWORD:-test123456}"
DTS_TGZ="${TEST_MONGO_DTS_TGZ:-/tmp/mongo-dts.tar.gz}"

SRC_IP="${TEST_SRC_IP:-127.0.0.21}"
DST_IP="${TEST_DST_IP:-127.0.0.22}"
SRC_PORT="${TEST_SRC_PORT:-28217}"
DST_PORT="${TEST_DST_PORT:-28317}"
SRC_SET="${TEST_SRC_SET:-dtsSrcRs}"
DST_SET="${TEST_DST_SET:-dtsDstRs}"
FULL_PORT="${TEST_FULL_HTTP_PORT:-21100}"
INCR_PORT="${TEST_INCR_HTTP_PORT:-21101}"

ACTUATOR_BIN="${ACTUATOR_BIN:-${BIN_DIR}/mongo-dbactuator}"
WORK_DIR="${TEST_WORK_DIR:-/tmp/mongo-dts-local-rs}"
PKG_DIR="${WORK_DIR}/pkg"
# actuator 只接受 /data/mongo-dts/mongodts* 作为 workDir
SHAKE_DIR="${TEST_SHAKE_DIR:-/data/mongo-dts/mongodtse2e}"
LOG_SNAPSHOT_DIR="${WORK_DIR}/logs"
KEEP_INSTANCE="${KEEP_INSTANCE:-0}"
DEINSTALL_ONLY="${DEINSTALL_ONLY:-0}"

for arg in "$@"; do
  case "${arg}" in
    --keep-instance) KEEP_INSTANCE=1 ;;
    --deinstall-only) DEINSTALL_ONLY=1 ;;
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

mkdir -p "${WORK_DIR}" "${LOG_SNAPSHOT_DIR}" "${BIN_DIR}" "${SHAKE_DIR}"

on_fail() {
  local exit_code="$?"
  echo "E2E failed, collecting logs..." >&2
  cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
  cp -f "${SHAKE_DIR}"/collector.* "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
  ss -lntp 2>/dev/null | rg "${SRC_PORT}|${DST_PORT}|${FULL_PORT}|${INCR_PORT}" || true
  echo "Logs saved under: ${LOG_SNAPSHOT_DIR}" >&2
  exit "${exit_code}"
}
trap on_fail ERR

source "${ROOT_DIR}/tests/e2e/mongo_shell.sh"

run_atom() {
  local uid="$1"
  local atom="$2"
  local payload_file="$3"
  local node_id="$4"
  echo "==> Running ${atom} on ${node_id}"
  "${ACTUATOR_BIN}" \
    --uid="${uid}" \
    --root_id="e2e-mongo-dts-local" \
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
    --uid="e2e-dts-os-init" \
    --root_id="e2e-mongo-dts-local" \
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

write_rs_payloads() {
  local role="$1" # src|dst
  local ip="$2"
  local port="$3"
  local set_id="$4"
  local prefix="${WORK_DIR}/${role}"

  cat > "${prefix}_mongod_install.json" <<EOF
{
  "mediapkg": {"pkg": "${PKG_NAME}", "pkg_md5": "${PKG_MD5}"},
  "ip": "${ip}",
  "port": ${port},
  "dbVersion": "${DB_VERSION}",
  "instanceType": "mongod",
  "setId": "${set_id}",
  "keyFile": "ut-dts-key-file",
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

  cat > "${prefix}_init_replicaset.json" <<EOF
{
  "ip": "${ip}",
  "port": ${port},
  "setId": "${set_id}",
  "configSvr": false,
  "ips": ["${ip}:${port}"],
  "priority": {"${ip}:${port}": 1},
  "hidden": {"${ip}:${port}": false}
}
EOF

  cat > "${prefix}_add_user.json" <<EOF
{
  "ip": "${ip}",
  "port": ${port},
  "instanceType": "mongod",
  "username": "${ADMIN_USER}",
  "password": "${ADMIN_PASS}",
  "adminUsername": "",
  "adminPassword": "",
  "authDb": "admin",
  "dbsPrivileges": [{"db": "admin", "privileges": ["root"]}]
}
EOF

  cat > "${prefix}_mongo_restart.json" <<EOF
{
  "ip": "${ip}",
  "port": ${port},
  "instanceType": "mongod",
  "auth": true,
  "setId": "${set_id}",
  "adminUsername": "${ADMIN_USER}",
  "adminPassword": "${ADMIN_PASS}",
  "cacheSizeGB": 1
}
EOF

  cat > "${prefix}_mongo_deinstall.json" <<EOF
{
  "ip": "${ip}",
  "port": ${port},
  "setId": "${set_id}",
  "nodeInfo": ["${ip}"],
  "instanceType": "mongod",
  "force": true,
  "renameDir": true
}
EOF
}

deploy_rs() {
  local role="$1"
  local ip="$2"
  local port="$3"
  local set_id="$4"
  write_rs_payloads "${role}" "${ip}" "${port}" "${set_id}"
  run_os_init "${role}-${ip}"
  run_atom "e2e-dts-${role}-install" "mongod_install" "${WORK_DIR}/${role}_mongod_install.json" "${role}-install"
  run_atom "e2e-dts-${role}-rs" "init_replicaset" "${WORK_DIR}/${role}_init_replicaset.json" "${role}-rs"
  run_atom "e2e-dts-${role}-user" "add_user" "${WORK_DIR}/${role}_add_user.json" "${role}-user"
  run_atom "e2e-dts-${role}-restart" "mongo_restart" "${WORK_DIR}/${role}_mongo_restart.json" "${role}-restart"
}

deinstall_rs() {
  local role="$1"
  local ip="$2"
  local port="$3"
  local set_id="$4"
  write_rs_payloads "${role}" "${ip}" "${port}" "${set_id}"
  run_atom "e2e-dts-${role}-deinstall" "mongo_deinstall" "${WORK_DIR}/${role}_mongo_deinstall.json" "${role}-deinstall" || true
}

mongo_eval() {
  local ip="$1"
  local port="$2"
  local js="$3"
  local shell
  shell="$(mongo_shell_bin)"
  "${shell}" --host "${ip}" --port "${port}" -u "${ADMIN_USER}" -p "${ADMIN_PASS}" --authenticationDatabase admin --quiet --eval "${js}"
}

stop_collector() {
  if [[ -f "${SHAKE_DIR}/collector.pid" ]]; then
    local pid
    pid="$(cat "${SHAKE_DIR}/collector.pid")"
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
      sleep 1
      kill -9 "${pid}" 2>/dev/null || true
    fi
  fi
}

if [[ "${DEINSTALL_ONLY}" == "1" ]]; then
  stop_collector
  deinstall_rs src "${SRC_IP}" "${SRC_PORT}" "${SRC_SET}"
  deinstall_rs dst "${DST_IP}" "${DST_PORT}" "${DST_SET}"
  echo "OK: deinstall-only done"
  exit 0
fi

if [[ ! -f "${DTS_TGZ}" ]]; then
  echo "ERROR: missing ${DTS_TGZ}" >&2
  exit 1
fi

echo "==> Building actuator"
go build -o mongo-dbactuator .
cp -f mongo-dbactuator "${ACTUATOR_BIN}"
chmod +x "${ACTUATOR_BIN}"

cat > "${WORK_DIR}/os_mongo_init.json" <<EOF
{"user": "${OS_INIT_USER}", "password": "${OS_INIT_PASSWORD}"}
EOF

echo "==> Deploy source RS ${SRC_IP}:${SRC_PORT}"
deploy_rs src "${SRC_IP}" "${SRC_PORT}" "${SRC_SET}"
echo "==> Deploy empty target RS ${DST_IP}:${DST_PORT}"
deploy_rs dst "${DST_IP}" "${DST_PORT}" "${DST_SET}"

echo "==> Seed source data"
mongo_eval "${SRC_IP}" "${SRC_PORT}" \
  'db.getSiblingDB("dtsdemo").orders.insertMany([{_id:1,n:"a"},{_id:2,n:"b"},{_id:3,n:"c"}]); db.getSiblingDB("dtsdemo").orders.createIndex({n:1});'

echo "==> Create MongoShake temp users"
mongo_eval "${SRC_IP}" "${SRC_PORT}" \
  "var a=db.getSiblingDB('admin'); try{a.dropUser('${SRC_DTS_USER}')}catch(e){}; a.createUser({user:'${SRC_DTS_USER}',pwd:'${SRC_DTS_PASS}',roles:[{role:'readAnyDatabase',db:'admin'},{role:'read',db:'local'},{role:'read',db:'config'},{role:'read',db:'admin'}]});"
mongo_eval "${DST_IP}" "${DST_PORT}" \
  "var a=db.getSiblingDB('admin'); try{a.dropUser('${DST_DTS_USER}')}catch(e){}; a.createUser({user:'${DST_DTS_USER}',pwd:'${DST_DTS_PASS}',roles:[{role:'readWriteAnyDatabase',db:'admin'},{role:'clusterManager',db:'admin'}]});"

mongo_uri() {
  printf '%s://%s:%s@%s:%s' "mongodb" "$1" "$2" "$3" "$4"
}
SRC_DTS_URI="$(mongo_uri "${SRC_DTS_USER}" "${SRC_DTS_PASS}" "${SRC_IP}" "${SRC_PORT}")"
DST_DTS_URI="$(mongo_uri "${DST_DTS_USER}" "${DST_DTS_PASS}" "${DST_IP}" "${DST_PORT}")"

echo "==> Unpack mongo-dts and start collector.linux"
rm -rf "${PKG_DIR}"
mkdir -p "${PKG_DIR}" "${SHAKE_DIR}/logs"
tar -xzf "${DTS_TGZ}" -C "${PKG_DIR}"
BIN="$(find "${PKG_DIR}" -type f -name collector.linux | head -1)"
if [[ -z "${BIN}" ]]; then
  echo "ERROR: collector.linux not found in ${DTS_TGZ}" >&2
  exit 1
fi
chmod +x "${BIN}"

cat > "${SHAKE_DIR}/collector.conf" <<EOF
conf.version = 14
id = mongodtslocal
master_quorum = false
full_sync.http_port = ${FULL_PORT}
incr_sync.http_port = ${INCR_PORT}
prom.http_port = -1
system_profile_port = -1
log.level = info
log.dir = ${SHAKE_DIR}/logs
sync_mode = all
mongo_urls = ${SRC_DTS_URI}
mongo_cs_url =
mongo_s_url =
mongo_connect_mode = secondaryPreferred
tunnel = direct
tunnel.address = ${DST_DTS_URI}
filter.namespace.black =
filter.namespace.white = dtsdemo
filter.ddl_enable = false
filter.pass.special.db =
transform.namespace =
checkpoint.storage.url = ${DST_DTS_URI}
checkpoint.storage.db = mongoshake
checkpoint.storage.collection = ckpt_mongodtslocal
checkpoint.start_position = 1970-01-01T00:00:00Z
full_sync.collection_exist_drop = false
incr_sync.mongo_fetch_method = change_stream
EOF

stop_collector
cat > "${WORK_DIR}/mongoshake_start.json" <<EOF
{
  "op": "start",
  "workDir": "${SHAKE_DIR}",
  "pkgPath": "${DTS_TGZ}",
  "confFile": "${SHAKE_DIR}/collector.conf"
}
EOF
echo "==> mongo-dbactuator mongoshake_collector start"
run_atom "e2e-dts-shake-start" "mongoshake_collector" "${WORK_DIR}/mongoshake_start.json" "shake-start"
if ! kill -0 "$(cat "${SHAKE_DIR}/collector.pid")" 2>/dev/null; then
  echo "ERROR: collector.linux exited immediately" >&2
  cat "${SHAKE_DIR}/collector.stdout" >&2 || true
  exit 1
fi

echo "==> mongo-dbactuator mongoshake_collector wait_stop"
cat > "${WORK_DIR}/mongoshake_wait.json" <<EOF
{
  "op": "wait_stop",
  "workDir": "${SHAKE_DIR}",
  "fullHttpPort": ${FULL_PORT},
  "incrHttpPort": ${INCR_PORT},
  "lagSeconds": 15,
  "stableRounds": 3,
  "pollSeconds": 5,
  "deadlineSeconds": 600,
  "removeConf": true
}
EOF
run_atom "e2e-dts-shake-wait" "mongoshake_collector" "${WORK_DIR}/mongoshake_wait.json" "shake-wait"

echo "==> Compare document counts"
SRC_COUNT="$(mongo_eval "${SRC_IP}" "${SRC_PORT}" 'print(db.getSiblingDB("dtsdemo").orders.countDocuments({}))')"
DST_COUNT="$(mongo_eval "${DST_IP}" "${DST_PORT}" 'print(db.getSiblingDB("dtsdemo").orders.countDocuments({}))')"
echo "src_count=${SRC_COUNT} dst_count=${DST_COUNT}"
if [[ "${SRC_COUNT}" != "3" || "${DST_COUNT}" != "3" ]]; then
  echo "ERROR: document count mismatch" >&2
  exit 1
fi

if [[ "${KEEP_INSTANCE}" == "1" ]]; then
  echo "OK: sync verified; instances kept (${SRC_IP}:${SRC_PORT} -> ${DST_IP}:${DST_PORT})"
  exit 0
fi

echo "==> Cleanup"
stop_collector
deinstall_rs src "${SRC_IP}" "${SRC_PORT}" "${SRC_SET}"
deinstall_rs dst "${DST_IP}" "${DST_PORT}" "${DST_SET}"
echo "OK: local MongoShake DTS RS->RS passed"
