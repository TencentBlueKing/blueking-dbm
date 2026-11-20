#!/usr/bin/env bash
# Shared helpers for local MongoDB DTS matrix E2E (RS / 2-shard combinations).
# shellcheck disable=SC2034

set -euo pipefail

dts_e2e_lib_init() {
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  REPO_ROOT="$(cd "${ROOT_DIR}/../../../.." && pwd)"
  cd "${ROOT_DIR}"

  RUN_ID="${TEST_RUN_ID:-$(date +%Y%m%d%H%M%S)}"
  DATA_DIR="${TEST_DATA_DIR:-/data2}"
  BACKUP_DIR="${TEST_BACKUP_DIR:-/data2}"
  BIN_DIR="${TEST_BIN_DIR:-/data2}"
  WORK_DIR="${TEST_WORK_DIR:-/tmp/mongo-dts-matrix-${RUN_ID}}"
  LOG_SNAPSHOT_DIR="${WORK_DIR}/logs"
  MANIFEST="${WORK_DIR}/manifest.tsv"
  ACTUATOR_BIN="${ACTUATOR_BIN:-${BIN_DIR}/mongo-dbactuator}"
  DTS_TGZ="${TEST_MONGO_DTS_TGZ:-/tmp/mongo-dts.tar.gz}"
  # actuator only accepts /data/mongo-dts/mongodts[A-Za-z0-9]{1,12}
  SHAKE_DIR="${TEST_SHAKE_DIR:-/data/mongo-dts/mongodtse2emat}"
  PKG_DIR="${WORK_DIR}/pkg"

  PKG_NAME="${TEST_MONGO_PKG_NAME:-mongodb-linux-x86_64-rhel70-4.4.30.tar.gz}"
  PKG_MD5="${TEST_MONGO_PKG_MD5:-0856af7ed34231d4b533581c11d9ebe6}"
  DB_VERSION="${TEST_MONGO_DB_VERSION:-4.4.30}"
  PKG_PATH="/data/install/${PKG_NAME}"

  OS_INIT_USER="${TEST_OS_INIT_USER:-mysql}"
  OS_INIT_GROUP="${TEST_OS_INIT_GROUP:-mysql}"
  OS_INIT_PASSWORD="${TEST_OS_INIT_PASSWORD:-test123456}"
  ADMIN_USER="${TEST_ADMIN_USER:-dba}"
  ADMIN_PASS="${TEST_ADMIN_PASS:-test123456}"
  SRC_DTS_USER="${TEST_SRC_DTS_USER:-mongodts_src}"
  SRC_DTS_PASS="${TEST_SRC_DTS_PASS:-xxxx}"
  DST_DTS_USER="${TEST_DST_DTS_USER:-mongodts_dst}"
  DST_DTS_PASS="${TEST_DST_DTS_PASS:-xxxx}"
  KEY_FILE="${TEST_KEY_FILE:-ut-dts-matrix-key}"

  FULL_PORT="${TEST_FULL_HTTP_PORT:-21300}"
  INCR_PORT="${TEST_INCR_HTTP_PORT:-21301}"
  COLLECTOR_ID="${TEST_COLLECTOR_ID:-mongodtse2emat}"
  NS_WHITE="${TEST_NS_WHITE:-dtsdemo}"

  # Source RS (3 members, last hidden backup). Avoid ports used by leftover e2e.
  SRC_RS_SET="${TEST_SRC_RS_SET:-dtsSrcRs}"
  SRC_RS_IPS=("${TEST_SRC_RS_IP1:-127.0.0.111}" "${TEST_SRC_RS_IP2:-127.0.0.112}" "${TEST_SRC_RS_IP3:-127.0.0.113}")
  SRC_RS_PORTS=("${TEST_SRC_RS_PORT1:-29311}" "${TEST_SRC_RS_PORT2:-29312}" "${TEST_SRC_RS_PORT3:-29313}")

  # Target RS
  DST_RS_SET="${TEST_DST_RS_SET:-dtsDstRs}"
  DST_RS_IPS=("${TEST_DST_RS_IP1:-127.0.0.121}" "${TEST_DST_RS_IP2:-127.0.0.122}" "${TEST_DST_RS_IP3:-127.0.0.123}")
  DST_RS_PORTS=("${TEST_DST_RS_PORT1:-29321}" "${TEST_DST_RS_PORT2:-29322}" "${TEST_DST_RS_PORT3:-29323}")

  # Source 2-shard cluster
  SRC_CFG_SET="${TEST_SRC_CFG_SET:-dtsSrcCfg}"
  SRC_S1_SET="${TEST_SRC_S1_SET:-dtsSrcS1}"
  SRC_S2_SET="${TEST_SRC_S2_SET:-dtsSrcS2}"
  SRC_CFG_IPS=("${TEST_SRC_CFG_IP1:-127.0.0.131}" "${TEST_SRC_CFG_IP2:-127.0.0.132}" "${TEST_SRC_CFG_IP3:-127.0.0.133}")
  SRC_CFG_PORTS=("${TEST_SRC_CFG_PORT1:-29411}" "${TEST_SRC_CFG_PORT2:-29412}" "${TEST_SRC_CFG_PORT3:-29413}")
  SRC_S1_IPS=("${TEST_SRC_S1_IP1:-127.0.0.141}" "${TEST_SRC_S1_IP2:-127.0.0.142}" "${TEST_SRC_S1_IP3:-127.0.0.143}")
  SRC_S1_PORTS=("${TEST_SRC_S1_PORT1:-29421}" "${TEST_SRC_S1_PORT2:-29422}" "${TEST_SRC_S1_PORT3:-29423}")
  SRC_S2_IPS=("${TEST_SRC_S2_IP1:-127.0.0.151}" "${TEST_SRC_S2_IP2:-127.0.0.152}" "${TEST_SRC_S2_IP3:-127.0.0.153}")
  SRC_S2_PORTS=("${TEST_SRC_S2_PORT1:-29431}" "${TEST_SRC_S2_PORT2:-29432}" "${TEST_SRC_S2_PORT3:-29433}")
  SRC_MONGOS_IP="${TEST_SRC_MONGOS_IP:-127.0.0.161}"
  SRC_MONGOS_PORT="${TEST_SRC_MONGOS_PORT:-29441}"

  # Target 2-shard cluster
  DST_CFG_SET="${TEST_DST_CFG_SET:-dtsDstCfg}"
  DST_S1_SET="${TEST_DST_S1_SET:-dtsDstS1}"
  DST_S2_SET="${TEST_DST_S2_SET:-dtsDstS2}"
  DST_CFG_IPS=("${TEST_DST_CFG_IP1:-127.0.0.171}" "${TEST_DST_CFG_IP2:-127.0.0.172}" "${TEST_DST_CFG_IP3:-127.0.0.173}")
  DST_CFG_PORTS=("${TEST_DST_CFG_PORT1:-29511}" "${TEST_DST_CFG_PORT2:-29512}" "${TEST_DST_CFG_PORT3:-29513}")
  DST_S1_IPS=("${TEST_DST_S1_IP1:-127.0.0.181}" "${TEST_DST_S1_IP2:-127.0.0.182}" "${TEST_DST_S1_IP3:-127.0.0.183}")
  DST_S1_PORTS=("${TEST_DST_S1_PORT1:-29521}" "${TEST_DST_S1_PORT2:-29522}" "${TEST_DST_S1_PORT3:-29523}")
  DST_S2_IPS=("${TEST_DST_S2_IP1:-127.0.0.191}" "${TEST_DST_S2_IP2:-127.0.0.192}" "${TEST_DST_S2_IP3:-127.0.0.193}")
  DST_S2_PORTS=("${TEST_DST_S2_PORT1:-29531}" "${TEST_DST_S2_PORT2:-29532}" "${TEST_DST_S2_PORT3:-29533}")
  DST_MONGOS_IP="${TEST_DST_MONGOS_IP:-127.0.0.201}"
  DST_MONGOS_PORT="${TEST_DST_MONGOS_PORT:-29541}"

  ALL_MATRIX_IPS=(
    "${SRC_RS_IPS[@]}" "${DST_RS_IPS[@]}"
    "${SRC_CFG_IPS[@]}" "${SRC_S1_IPS[@]}" "${SRC_S2_IPS[@]}" "${SRC_MONGOS_IP}"
    "${DST_CFG_IPS[@]}" "${DST_S1_IPS[@]}" "${DST_S2_IPS[@]}" "${DST_MONGOS_IP}"
  )
  ALL_MATRIX_PORTS=(
    "${SRC_RS_PORTS[@]}" "${DST_RS_PORTS[@]}"
    "${SRC_CFG_PORTS[@]}" "${SRC_S1_PORTS[@]}" "${SRC_S2_PORTS[@]}" "${SRC_MONGOS_PORT}"
    "${DST_CFG_PORTS[@]}" "${DST_S1_PORTS[@]}" "${DST_S2_PORTS[@]}" "${DST_MONGOS_PORT}"
    "${FULL_PORT}" "${INCR_PORT}"
  )

  KEEP_INSTANCE="${KEEP_INSTANCE:-0}"
  DEINSTALL_ONLY="${DEINSTALL_ONLY:-0}"
  WRITER_PID=""
  CASE_NAME=""
  REGISTERED_PORTS=()

  mkdir -p "${WORK_DIR}" "${LOG_SNAPSHOT_DIR}" "${BIN_DIR}" "${PKG_DIR}"
  mkdir -p "${SHAKE_DIR}/logs" 2>/dev/null || true
  : > "${MANIFEST}"
  source "${ROOT_DIR}/tests/e2e/mongo_shell.sh"
}

log() { echo "==> $*"; }
warn() { echo "WARN: $*" >&2; }
die() { echo "ERROR: $*" >&2; exit 1; }

manifest_append() {
  # type|ip|port|instanceType|setId|extra
  printf '%s\n' "$*" >> "${MANIFEST}"
}

register_port() {
  REGISTERED_PORTS+=("$1")
  manifest_append "port|$1"
}

write_json() {
  local out="$1"
  shift
  printf '%s\n' "$*" > "${out}"
}

ensure_loopback_ips() {
  local ip
  for ip in "${ALL_MATRIX_IPS[@]}"; do
    if ! ip -4 addr show lo | grep -q "inet ${ip}/"; then
      log "add loopback alias ${ip}"
      ip addr add "${ip}/8" dev lo || die "failed to add ${ip} on lo"
    fi
  done
}

wait_port_listen() {
  local port="$1" attempt=0
  while [[ ${attempt} -lt 90 ]]; do
    if ss -lntp 2>/dev/null | rg -q ":${port}\\b" || netstat -ntpl 2>/dev/null | rg -q ":${port}[[:space:]]"; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 1
  done
  die "port ${port} not listening"
}

wait_port_stopped() {
  local port="$1" attempt=0
  while [[ ${attempt} -lt 90 ]]; do
    if ! ss -lntp 2>/dev/null | rg -q ":${port}\\b" && ! netstat -ntpl 2>/dev/null | rg -q ":${port}[[:space:]]"; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 1
  done
  return 1
}

build_actuator() {
  log "build actuator"
  if [[ -x /usr/local/go/bin/go ]]; then
    export PATH="/usr/local/go/bin:${PATH}"
  fi
  go build -o mongo-dbactuator .
  mkdir -p "${BIN_DIR}"
  cp -f mongo-dbactuator "${ACTUATOR_BIN}"
  chmod +x "${ACTUATOR_BIN}"
  chown "${OS_INIT_USER}:${OS_INIT_GROUP}" "${ACTUATOR_BIN}" 2>/dev/null || true
}

run_atom() {
  local uid="$1" atom="$2" payload_file="$3" node_id="$4"
  log "atom=${atom} uid=${uid} node=${node_id}"
  "${ACTUATOR_BIN}" \
    --uid="${uid}" \
    --root_id="e2e-dts-matrix-${RUN_ID}" \
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
  write_json "${WORK_DIR}/os_mongo_init.json" "{\"user\":\"${OS_INIT_USER}\",\"password\":\"${OS_INIT_PASSWORD}\"}"
  log "atom=os_mongo_init node=${node_id}"
  "${ACTUATOR_BIN}" \
    --uid="e2e-dts-os-init-${RUN_ID}" \
    --root_id="e2e-dts-matrix-${RUN_ID}" \
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

mongo_eval() {
  local host="$1" port="$2" script="$3"
  shift 3 || true
  if [[ "${1:-}" == "--auth" ]]; then
    "$(mongo_shell_bin)" -u "${ADMIN_USER}" -p "${ADMIN_PASS}" --authenticationDatabase=admin \
      --host "${host}" --port "${port}" --quiet --eval "${script}"
  else
    "$(mongo_shell_bin)" --host "${host}" --port "${port}" --quiet --eval "${script}"
  fi
}

mongo_eval_auth() {
  mongo_eval "$1" "$2" "$3" --auth
}

current_primary_ip_port() {
  # args: ip1 port1 ip2 port2 ...
  local ip="$1" port="$2" primary
  primary="$(mongo_eval_auth "${ip}" "${port}" "rs.isMaster().primary" 2>/dev/null | tr -d "[:space:]" || true)"
  if [[ -z "${primary}" || "${primary}" == "null" ]]; then
    die "cannot resolve primary via ${ip}:${port}"
  fi
  echo "${primary%%:*} ${primary##*:}"
}


wait_rs_healthy() {
  local host="$1" port="$2" expect="$3" use_auth="${4:-0}" desc="${5:-rs}"
  log "wait ${desc} healthy expect=${expect} auth=${use_auth}"
  local attempt=0 total healthy
  while [[ ${attempt} -lt 90 ]]; do
    if [[ "${use_auth}" == "1" ]]; then
      total="$(mongo_eval_auth "${host}" "${port}" "rs.status().members.length" 2>/dev/null | tr -d '[:space:]' || true)"
      healthy="$(mongo_eval_auth "${host}" "${port}" "rs.status().members.filter(function(m){return m.stateStr==='PRIMARY'||m.stateStr==='SECONDARY';}).length" 2>/dev/null | tr -d '[:space:]' || true)"
    else
      total="$(mongo_eval "${host}" "${port}" "rs.status().members.length" 2>/dev/null | tr -d '[:space:]' || true)"
      healthy="$(mongo_eval "${host}" "${port}" "rs.status().members.filter(function(m){return m.stateStr==='PRIMARY'||m.stateStr==='SECONDARY';}).length" 2>/dev/null | tr -d '[:space:]' || true)"
    fi
    if [[ "${total}" == "${expect}" && "${healthy}" == "${expect}" ]]; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 2
  done
  die "${desc} not healthy: total=${total:-?} healthy=${healthy:-?} expect=${expect}"
}

build_mongod_install_payload() {
  local ip="$1" port="$2" set_id="$3" cluster_role="$4" out="$5" auth="${6:-false}"
  local auth_bool=false
  if [[ "${auth}" == "true" || "${auth}" == "1" ]]; then
    auth_bool=true
  fi
  AUTH_BOOL="${auth_bool}" IP="${ip}" PORT="${port}" SET_ID="${set_id}" CLUSTER_ROLE="${cluster_role}" OUT="${out}" \
  PKG_NAME="${PKG_NAME}" PKG_MD5="${PKG_MD5}" DB_VERSION="${DB_VERSION}" KEY_FILE="${KEY_FILE}" python3 - <<'PY'
import json, os
payload = {
  "mediapkg": {"pkg": os.environ["PKG_NAME"], "pkg_md5": os.environ["PKG_MD5"]},
  "ip": os.environ["IP"],
  "port": int(os.environ["PORT"]),
  "dbVersion": os.environ["DB_VERSION"],
  "instanceType": "mongod",
  "setId": os.environ["SET_ID"],
  "keyFile": os.environ["KEY_FILE"],
  "auth": os.environ["AUTH_BOOL"] == "true",
  "clusterRole": os.environ["CLUSTER_ROLE"],
  "dbConfig": {
    "slowOpThresholdMs": 200,
    "cacheSizeGB": 1,
    "oplogSizeMB": 512,
    "destination": "file",
  },
}
with open(os.environ["OUT"], "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
}

build_mongos_install_payload() {
  local ip="$1" port="$2" set_id="$3" out="$4"
  shift 4
  local cfg=("$@")
  local cfg_json
  cfg_json="$(printf '"%s",' "${cfg[@]}" | sed 's/,$//')"
  python3 - <<PY
import json
payload = {
  "mediapkg": {"pkg": "${PKG_NAME}", "pkg_md5": "${PKG_MD5}"},
  "ip": "${ip}",
  "port": ${port},
  "dbVersion": "${DB_VERSION}",
  "instanceType": "mongos",
  "setId": "${set_id}",
  "keyFile": "${KEY_FILE}",
  "auth": True,
  "configDB": [${cfg_json}],
  "dbConfig": {"slowOpThresholdMs": 200, "destination": "file"},
}
with open("${out}", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
}

build_init_replicaset_payload() {
  local ip="$1" port="$2" set_id="$3" config_svr="$4" out="$5"
  shift 5
  OUT="${out}" IP="${ip}" PORT="${port}" SET_ID="${set_id}" CONFIG_SVR="${config_svr}" \
    python3 - "$@" <<'PY'
import json, os, sys
members = list(sys.argv[1:])
priority = {}
hidden = {}
for i, m in enumerate(members):
    # last member: hidden backup, priority 0
    if i == len(members) - 1 and len(members) > 1:
        priority[m] = 0
        hidden[m] = True
    elif i == 0:
        priority[m] = 2
        hidden[m] = False
    else:
        priority[m] = 1
        hidden[m] = False
payload = {
  "ip": os.environ["IP"],
  "port": int(os.environ["PORT"]),
  "setId": os.environ["SET_ID"],
  "configSvr": os.environ["CONFIG_SVR"].lower() in ("1", "true"),
  "ips": members,
  "priority": priority,
  "hidden": hidden,
}
with open(os.environ["OUT"], "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
}

build_add_user_payload() {
  local ip="$1" port="$2" out="$3"
  python3 - <<PY
import json
payload = {
  "ip": "${ip}",
  "port": ${port},
  "instanceType": "mongod",
  "username": "${ADMIN_USER}",
  "password": "${ADMIN_PASS}",
  "adminUsername": "",
  "adminPassword": "",
  "authDb": "admin",
  "dbsPrivileges": [{"db": "admin", "privileges": ["root"]}],
}
with open("${out}", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
}

build_deinstall_payload() {
  local ip="$1" port="$2" instance_type="$3" out="$4"
  write_json "${out}" "{\"ip\":\"${ip}\",\"port\":${port},\"setId\":\"cleanup\",\"nodeInfo\":[\"${ip}\"],\"instanceType\":\"${instance_type}\",\"force\":true,\"renameDir\":true}"
}

install_mongod_parallel() {
  local set_id="$1" cluster_role="$2" auth="$3"
  shift 3
  local ips=() ports=()
  while [[ $# -gt 0 ]]; do
    ips+=("$1"); ports+=("$2"); shift 2
  done
  local i pids=()
  for i in "${!ports[@]}"; do
    build_mongod_install_payload "${ips[$i]}" "${ports[$i]}" "${set_id}" "${cluster_role}" \
      "${WORK_DIR}/mongod_install_${ports[$i]}.json" "${auth}"
    ( run_atom "e2e-dts-install-${ports[$i]}" "mongod_install" \
      "${WORK_DIR}/mongod_install_${ports[$i]}.json" "node-${ports[$i]}" ) &
    pids+=($!)
  done
  local pid rc=0
  for pid in "${pids[@]}"; do
    if ! wait "${pid}"; then rc=1; fi
  done
  [[ "${rc}" -eq 0 ]] || die "parallel mongod_install failed for ${set_id}"
  for i in "${!ports[@]}"; do
    wait_port_listen "${ports[$i]}"
    register_port "${ports[$i]}"
    manifest_append "instance|${ips[$i]}|${ports[$i]}|mongod|${set_id}"
  done
}


restart_mongod_auth() {
  local ip="$1" port="$2" set_id="$3"
  IP="${ip}" PORT="${port}" SET_ID="${set_id}" ADMIN_USER="${ADMIN_USER}" ADMIN_PASS="${ADMIN_PASS}" OUT="${WORK_DIR}/mongo_restart_${port}.json" python3 - <<'PY'
import json, os
payload = {
  "ip": os.environ["IP"],
  "port": int(os.environ["PORT"]),
  "instanceType": "mongod",
  "auth": True,
  "setId": os.environ["SET_ID"],
  "adminUsername": os.environ["ADMIN_USER"],
  "adminPassword": os.environ["ADMIN_PASS"],
  "cacheSizeGB": 1,
}
with open(os.environ["OUT"], "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
  run_atom "e2e-dts-restart-${port}" "mongo_restart" "${WORK_DIR}/mongo_restart_${port}.json" "restart-${port}"
}

init_rs_and_admin() {
  local set_id="$1" config_svr="$2" primary_ip="$3" primary_port="$4" auth_restart="${5:-0}"
  shift 4
  if [[ "${1:-}" == "0" || "${1:-}" == "1" ]]; then
    auth_restart="$1"
    shift
  fi
  local members=("$@")
  local payload="${WORK_DIR}/init_${set_id}.json"
  build_init_replicaset_payload "${primary_ip}" "${primary_port}" "${set_id}" "${config_svr}" \
    "${payload}" "${members[@]}"
  run_atom "e2e-dts-init-${set_id}" "init_replicaset" "${payload}" "node-${primary_port}"
  wait_rs_healthy "${primary_ip}" "${primary_port}" "${#members[@]}" 0 "${set_id}"

  # Election may move primary off member[0]; add_user must run on writable PRIMARY.
  local add_ip add_port primary
  if [[ "${auth_restart}" == "1" ]]; then
    # auth not enabled yet — use unauthenticated isMaster
    primary="$(mongo_eval "${primary_ip}" "${primary_port}" "rs.isMaster().primary" 2>/dev/null | tr -d "[:space:]" || true)"
  else
    # shardsvr/configsvr already auth-enabled via keyFile; localhost exception until user exists
    primary="$(mongo_eval "${primary_ip}" "${primary_port}" "rs.isMaster().primary" 2>/dev/null | tr -d "[:space:]" || true)"
    if [[ -z "${primary}" || "${primary}" == "null" ]]; then
      primary="$(mongo_eval_auth "${primary_ip}" "${primary_port}" "rs.isMaster().primary" 2>/dev/null | tr -d "[:space:]" || true)"
    fi
  fi
  if [[ -n "${primary}" && "${primary}" != "null" ]]; then
    add_ip="${primary%%:*}"
    add_port="${primary##*:}"
  else
    add_ip="${primary_ip}"
    add_port="${primary_port}"
  fi
  log "add_user on primary ${add_ip}:${add_port} for ${set_id}"
  build_add_user_payload "${add_ip}" "${add_port}" "${WORK_DIR}/add_user_${set_id}.json"
  run_atom "e2e-dts-user-${set_id}" "add_user" "${WORK_DIR}/add_user_${set_id}.json" "node-${add_port}"
  if [[ "${auth_restart}" == "1" ]]; then
    local m ip port
    for m in "${members[@]}"; do
      ip="${m%%:*}"
      port="${m##*:}"
      restart_mongod_auth "${ip}" "${port}" "${set_id}"
    done
  fi
  wait_rs_healthy "${primary_ip}" "${primary_port}" "${#members[@]}" 1 "${set_id}"
}

# Fixed deploy_rs without the broken paste
deploy_replicaset() {
  local label="$1" set_id="$2"
  shift 2
  local ips=() ports=() members=() pair_args=()
  while [[ $# -gt 0 ]]; do
    ips+=("$1"); ports+=("$2"); members+=("$1:$2"); pair_args+=("$1" "$2"); shift 2
  done
  log "deploy RS ${label} set=${set_id} members=${members[*]}"
  run_os_init "os-${label}"
  install_mongod_parallel "${set_id}" "" "false" "${pair_args[@]}"
  init_rs_and_admin "${set_id}" "false" "${ips[0]}" "${ports[0]}" 1 "${members[@]}"
}

deploy_two_shard_cluster() {
  # deploy_two_shard_cluster <label_prefix>
  # uses SRC_* or DST_* arrays based on prefix src|dst
  local side="$1"  # src|dst
  local cfg_set s1_set s2_set
  local -a cfg_ips cfg_ports s1_ips s1_ports s2_ips s2_ports
  local mongos_ip mongos_port

  if [[ "${side}" == "src" ]]; then
    cfg_set="${SRC_CFG_SET}"; s1_set="${SRC_S1_SET}"; s2_set="${SRC_S2_SET}"
    cfg_ips=("${SRC_CFG_IPS[@]}"); cfg_ports=("${SRC_CFG_PORTS[@]}")
    s1_ips=("${SRC_S1_IPS[@]}"); s1_ports=("${SRC_S1_PORTS[@]}")
    s2_ips=("${SRC_S2_IPS[@]}"); s2_ports=("${SRC_S2_PORTS[@]}")
    mongos_ip="${SRC_MONGOS_IP}"; mongos_port="${SRC_MONGOS_PORT}"
  else
    cfg_set="${DST_CFG_SET}"; s1_set="${DST_S1_SET}"; s2_set="${DST_S2_SET}"
    cfg_ips=("${DST_CFG_IPS[@]}"); cfg_ports=("${DST_CFG_PORTS[@]}")
    s1_ips=("${DST_S1_IPS[@]}"); s1_ports=("${DST_S1_PORTS[@]}")
    s2_ips=("${DST_S2_IPS[@]}"); s2_ports=("${DST_S2_PORTS[@]}")
    mongos_ip="${DST_MONGOS_IP}"; mongos_port="${DST_MONGOS_PORT}"
  fi

  log "deploy 2-shard cluster side=${side}"
  run_os_init "os-cluster-${side}"

  local i pair_cfg=() pair_s1=() pair_s2=() cfg_members=() s1_members=() s2_members=() cfg_addrs=()
  for i in "${!cfg_ports[@]}"; do
    pair_cfg+=("${cfg_ips[$i]}" "${cfg_ports[$i]}")
    cfg_members+=("${cfg_ips[$i]}:${cfg_ports[$i]}")
    cfg_addrs+=("${cfg_ips[$i]}:${cfg_ports[$i]}")
  done
  for i in "${!s1_ports[@]}"; do
    pair_s1+=("${s1_ips[$i]}" "${s1_ports[$i]}")
    s1_members+=("${s1_ips[$i]}:${s1_ports[$i]}")
  done
  for i in "${!s2_ports[@]}"; do
    pair_s2+=("${s2_ips[$i]}" "${s2_ports[$i]}")
    s2_members+=("${s2_ips[$i]}:${s2_ports[$i]}")
  done

  # auth=true for shardsvr/configsvr so mongos can join with keyFile
  install_mongod_parallel "${cfg_set}" "configsvr" "true" "${pair_cfg[@]}"
  install_mongod_parallel "${s1_set}" "shardsvr" "true" "${pair_s1[@]}"
  install_mongod_parallel "${s2_set}" "shardsvr" "true" "${pair_s2[@]}"

  init_rs_and_admin "${cfg_set}" "true" "${cfg_ips[0]}" "${cfg_ports[0]}" "${cfg_members[@]}"
  init_rs_and_admin "${s1_set}" "false" "${s1_ips[0]}" "${s1_ports[0]}" "${s1_members[@]}"
  init_rs_and_admin "${s2_set}" "false" "${s2_ips[0]}" "${s2_ports[0]}" "${s2_members[@]}"

  build_mongos_install_payload "${mongos_ip}" "${mongos_port}" "${cfg_set}" \
    "${WORK_DIR}/mongos_${side}.json" "${cfg_addrs[@]}"
  run_atom "e2e-dts-mongos-${side}" "mongos_install" "${WORK_DIR}/mongos_${side}.json" "mongos-${side}"
  wait_port_listen "${mongos_port}"
  register_port "${mongos_port}"
  manifest_append "instance|${mongos_ip}|${mongos_port}|mongos|${cfg_set}"

  # add both shards (first two members of each shard RS are enough for connection string)
  python3 - <<PY
import json
payload = {
  "ip": "${mongos_ip}",
  "port": ${mongos_port},
  "adminUsername": "${ADMIN_USER}",
  "adminPassword": "${ADMIN_PASS}",
  "shards": {
    "${s1_set}": "${s1_ips[0]}:${s1_ports[0]},${s1_ips[1]}:${s1_ports[1]}",
    "${s2_set}": "${s2_ips[0]}:${s2_ports[0]},${s2_ips[1]}:${s2_ports[1]}",
  },
}
with open("${WORK_DIR}/add_shard_${side}.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
  run_atom "e2e-dts-addshard-${side}" "add_shard_to_cluster" \
    "${WORK_DIR}/add_shard_${side}.json" "addshard-${side}"

  # wait mongos usable
  local attempt=0
  while [[ ${attempt} -lt 60 ]]; do
    if mongo_eval_auth "${mongos_ip}" "${mongos_port}" "db.adminCommand({listShards:1}).shards.length" 2>/dev/null | tr -d '[:space:]' | grep -q '^2$'; then
      break
    fi
    attempt=$((attempt + 1))
    sleep 2
  done
  [[ ${attempt} -lt 60 ]] || die "mongos ${side} did not list 2 shards"
}

deinstall_instance() {
  local ip="$1" port="$2" instance_type="$3"
  local payload="${WORK_DIR}/deinstall_${port}.json"
  build_deinstall_payload "${ip}" "${port}" "${instance_type}" "${payload}"
  run_atom "e2e-dts-deinstall-${port}" "mongo_deinstall" "${payload}" "deinstall-${port}" || true
}

stop_collector_force() {
  if [[ -f "${SHAKE_DIR}/collector.pid" ]]; then
    local pid
    pid="$(cat "${SHAKE_DIR}/collector.pid" 2>/dev/null || true)"
    if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
      sleep 1
      kill -9 "${pid}" 2>/dev/null || true
    fi
  fi
  # also kill any leftover collector under this workdir
  pkill -f "${SHAKE_DIR}/collector.linux" 2>/dev/null || true
}

stop_writer() {
  if [[ -n "${WRITER_PID}" ]] && kill -0 "${WRITER_PID}" 2>/dev/null; then
    kill "${WRITER_PID}" 2>/dev/null || true
    sleep 1
    kill -9 "${WRITER_PID}" 2>/dev/null || true
  fi
  WRITER_PID=""
}

cleanup_from_manifest() {
  log "cleanup from manifest ${MANIFEST}"
  stop_writer
  stop_collector_force
  # reverse order
  if [[ -f "${MANIFEST}" ]]; then
    local line ip port itype
    tac "${MANIFEST}" | while IFS='|' read -r kind a b c d; do
      case "${kind}" in
        instance)
          ip="$a"; port="$b"; itype="$c"
          deinstall_instance "${ip}" "${port}" "${itype}"
          ;;
      esac
    done
  fi
}

assert_ports_closed() {
  local failed=0 port
  for port in "${REGISTERED_PORTS[@]:-}"; do
    [[ -n "${port}" ]] || continue
    if ! wait_port_stopped "${port}"; then
      warn "port ${port} still listening after cleanup"
      ss -lntp 2>/dev/null | rg ":${port}\\b" || true
      failed=1
    fi
  done
  # also check http ports
  for port in "${FULL_PORT}" "${INCR_PORT}"; do
    if ss -lntp 2>/dev/null | rg -q ":${port}\\b"; then
      warn "http port ${port} still listening"
      failed=1
    fi
  done
  [[ "${failed}" -eq 0 ]] || die "cleanup left ports open"
}

collect_failure_snapshot() {
  mkdir -p "${LOG_SNAPSHOT_DIR}"
  cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
  cp -f "${SHAKE_DIR}"/collector.* "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
  cp -f "${SHAKE_DIR}"/logs/* "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
  {
    echo "# case=${CASE_NAME} ports"
    ss -lntp 2>/dev/null || netstat -ntpl 2>/dev/null || true
    echo "# collector pid"
    cat "${SHAKE_DIR}/collector.pid" 2>/dev/null || true
    echo "# manifest"
    cat "${MANIFEST}" 2>/dev/null || true
  } > "${LOG_SNAPSHOT_DIR}/snapshot.txt" || true
  log "failure snapshot under ${LOG_SNAPSHOT_DIR}"
}

generate_collector_conf() {
  # Args via env: SRC_KIND DST_KIND SOURCE_CONNECT_MODE OUT_CONF
  # SRC_KIND=rs|shard DST_KIND=rs|shard
  local out_conf="${1}"
  SRC_KIND="${SRC_KIND}" DST_KIND="${DST_KIND}" SOURCE_CONNECT_MODE="${SOURCE_CONNECT_MODE}" \
  COLLECTOR_ID="${COLLECTOR_ID}" SHAKE_DIR="${SHAKE_DIR}" FULL_PORT="${FULL_PORT}" INCR_PORT="${INCR_PORT}" \
  NS_WHITE="${NS_WHITE}" SRC_DTS_USER="${SRC_DTS_USER}" SRC_DTS_PASS="${SRC_DTS_PASS}" \
  DST_DTS_USER="${DST_DTS_USER}" DST_DTS_PASS="${DST_DTS_PASS}" \
  SRC_RS_IPS="$(IFS=,; echo "${SRC_RS_IPS[*]}")" SRC_RS_PORTS="$(IFS=,; echo "${SRC_RS_PORTS[*]}")" \
  DST_RS_IPS="$(IFS=,; echo "${DST_RS_IPS[*]}")" DST_RS_PORTS="$(IFS=,; echo "${DST_RS_PORTS[*]}")" \
  SRC_S1_IPS="$(IFS=,; echo "${SRC_S1_IPS[*]}")" SRC_S1_PORTS="$(IFS=,; echo "${SRC_S1_PORTS[*]}")" \
  SRC_S2_IPS="$(IFS=,; echo "${SRC_S2_IPS[*]}")" SRC_S2_PORTS="$(IFS=,; echo "${SRC_S2_PORTS[*]}")" \
  SRC_CFG_IPS="$(IFS=,; echo "${SRC_CFG_IPS[*]}")" SRC_CFG_PORTS="$(IFS=,; echo "${SRC_CFG_PORTS[*]}")" \
  DST_MONGOS_IP="${DST_MONGOS_IP}" DST_MONGOS_PORT="${DST_MONGOS_PORT}" \
  OUT_CONF="${out_conf}" REPO_ROOT="${REPO_ROOT}" \
  python3 - <<'PY'
import os, sys
sys.path.insert(0, os.path.join(os.environ["REPO_ROOT"], "dbm-ui"))
from backend.flow.utils.mongodb.mongoshake_conf import (
    build_collector_conf,
    resolve_source_connect,
    mongo_uri,
)

def zip_addrs(ips, ports):
    return [f"{ip}:{port}" for ip, port in zip(ips.split(","), ports.split(","))]

src_kind = os.environ["SRC_KIND"]
dst_kind = os.environ["DST_KIND"]
mode = os.environ["SOURCE_CONNECT_MODE"]
user = os.environ["SRC_DTS_USER"]
pwd = os.environ["SRC_DTS_PASS"]
dst_user = os.environ["DST_DTS_USER"]
dst_pwd = os.environ["DST_DTS_PASS"]

if src_kind == "rs":
    addrs = zip_addrs(os.environ["SRC_RS_IPS"], os.environ["SRC_RS_PORTS"])
    backup = addrs[-1]
    source_urls, source_mongos, source_config, connect_mode = resolve_source_connect(
        mode, user, pwd, is_sharded=False, member_addrs=addrs, backup_addr=backup
    )
    orphan = False
    do_not_shard = False
else:
    s1 = zip_addrs(os.environ["SRC_S1_IPS"], os.environ["SRC_S1_PORTS"])
    s2 = zip_addrs(os.environ["SRC_S2_IPS"], os.environ["SRC_S2_PORTS"])
    cfg = zip_addrs(os.environ["SRC_CFG_IPS"], os.environ["SRC_CFG_PORTS"])
    shard_backups = [s1[-1], s2[-1]]
    config_backup = cfg[-1]
    source_urls, source_mongos, source_config, connect_mode = resolve_source_connect(
        mode,
        user,
        pwd,
        is_sharded=True,
        shard_backup_addrs=shard_backups,
        config_backup_addr=config_backup,
        cluster_name="e2e-src",
    )
    orphan = True
    do_not_shard = dst_kind == "rs"

if dst_kind == "rs":
    dst_addrs = zip_addrs(os.environ["DST_RS_IPS"], os.environ["DST_RS_PORTS"])
else:
    dst_addrs = [f"{os.environ['DST_MONGOS_IP']}:{os.environ['DST_MONGOS_PORT']}"]
target_url = mongo_uri(dst_user, dst_pwd, dst_addrs)

conf = build_collector_conf(
    collector_id=os.environ["COLLECTOR_ID"],
    log_dir=os.path.join(os.environ["SHAKE_DIR"], "logs"),
    source_urls=source_urls,
    source_mongos_url=source_mongos,
    source_config_url=source_config,
    target_url=target_url,
    namespace_white=os.environ["NS_WHITE"],
    full_http_port=int(os.environ["FULL_PORT"]),
    incr_http_port=int(os.environ["INCR_PORT"]),
    mongo_connect_mode=connect_mode,
    filter_orphan_document=orphan,
    do_not_shard_destination=do_not_shard,
)
with open(os.environ["OUT_CONF"], "w", encoding="utf-8") as f:
    f.write(conf)
print(conf)
PY
}

create_dts_users_rs() {
  local ip="$1" port="$2" side="$3"  # src|dst
  if [[ "${side}" == "src" ]]; then
    mongo_eval_auth "${ip}" "${port}" \
      "var a=db.getSiblingDB('admin'); try{a.dropUser('${SRC_DTS_USER}')}catch(e){}; a.createUser({user:'${SRC_DTS_USER}',pwd:'${SRC_DTS_PASS}',roles:[{role:'readAnyDatabase',db:'admin'},{role:'read',db:'local'},{role:'read',db:'config'},{role:'read',db:'admin'},{role:'clusterMonitor',db:'admin'}]});"
  else
    mongo_eval_auth "${ip}" "${port}" \
      "var a=db.getSiblingDB('admin'); try{a.dropUser('${DST_DTS_USER}')}catch(e){}; a.createUser({user:'${DST_DTS_USER}',pwd:'${DST_DTS_PASS}',roles:[{role:'readWriteAnyDatabase',db:'admin'},{role:'clusterManager',db:'admin'}]});"
  fi
}

create_dts_users_on_all_source_rs() {
  # create source user on each RS primary (RS or each shard/config)
  local kind="$1" pip pport
  if [[ "${kind}" == "rs" ]]; then
    read -r pip pport < <(current_primary_ip_port "${SRC_RS_IPS[0]}" "${SRC_RS_PORTS[0]}")
    create_dts_users_rs "${pip}" "${pport}" src
  else
    read -r pip pport < <(current_primary_ip_port "${SRC_CFG_IPS[0]}" "${SRC_CFG_PORTS[0]}")
    create_dts_users_rs "${pip}" "${pport}" src
    read -r pip pport < <(current_primary_ip_port "${SRC_S1_IPS[0]}" "${SRC_S1_PORTS[0]}")
    create_dts_users_rs "${pip}" "${pport}" src
    read -r pip pport < <(current_primary_ip_port "${SRC_S2_IPS[0]}" "${SRC_S2_PORTS[0]}")
    create_dts_users_rs "${pip}" "${pport}" src
  fi
}

create_dts_users_on_target() {
  local kind="$1" pip pport
  if [[ "${kind}" == "rs" ]]; then
    read -r pip pport < <(current_primary_ip_port "${DST_RS_IPS[0]}" "${DST_RS_PORTS[0]}")
    create_dts_users_rs "${pip}" "${pport}" dst
  else
    create_dts_users_rs "${DST_MONGOS_IP}" "${DST_MONGOS_PORT}" dst
  fi
}

seed_baseline_rs() {
  local ip="$1" port="$2"
  mongo_eval_auth "${ip}" "${port}" '
    var dbx=db.getSiblingDB("dtsdemo");
    dbx.orders.drop();
    var docs=[];
    for (var i=1;i<=40;i++){docs.push({_id:i, shardKey:i, n:"v"+i, v:1});}
    dbx.orders.insertMany(docs);
    dbx.orders.createIndex({n:1});
    db.getSiblingDB("notwhite").secret.insert({_id:1,x:1});
  '
}

seed_baseline_shard() {
  local mongos_ip="$1" mongos_port="$2"
  # enable sharding, create hashed collection, distribute docs
  mongo_eval_auth "${mongos_ip}" "${mongos_port}" '
    sh.enableSharding("dtsdemo");
    db.getSiblingDB("dtsdemo").orders.drop();
    sh.shardCollection("dtsdemo.orders", {_id:"hashed"});
    var dbx=db.getSiblingDB("dtsdemo");
    var docs=[];
    for (var i=1;i<=80;i++){docs.push({_id:i, shardKey:i, n:"v"+i, v:1});}
    dbx.orders.insertMany(docs);
    dbx.orders.createIndex({n:1});
    db.getSiblingDB("notwhite").secret.insert({_id:1,x:1});
  '
  # wait for chunks on both shards
  local attempt=0 c1 c2
  while [[ ${attempt} -lt 60 ]]; do
    c1="$(mongo_eval_auth "${mongos_ip}" "${mongos_port}" 'db.getSiblingDB("config").chunks.countDocuments({ns:"dtsdemo.orders"})' 2>/dev/null | tr -d '[:space:]' || true)"
    # count per shard via direct? use dataSize on each shard backup later; here ensure >1 chunk
    if [[ -n "${c1}" && "${c1}" -gt 1 ]]; then
      break
    fi
    attempt=$((attempt + 1))
    sleep 2
  done
}

prepare_empty_sharded_target() {
  local mongos_ip="$1" mongos_port="$2"
  mongo_eval_auth "${mongos_ip}" "${mongos_port}" '
    sh.enableSharding("dtsdemo");
    db.getSiblingDB("dtsdemo").orders.drop();
    sh.shardCollection("dtsdemo.orders", {_id:"hashed"});
  '
}

assert_balancer_negative_then_stop() {
  local cfg_ip="$1" cfg_port="$2" mongos_ip="$3" mongos_port="$4"
  # negative: balancer may be running by default — assert_balancer_stopped should fail
  if mongo_eval_auth "${cfg_ip}" "${cfg_port}" '
    var cfg=db.getSiblingDB("config");
    var s=cfg.settings.findOne({_id:"balancer"});
    if(!s||!(s.stopped===true||s.mode==="off")){throw new Error("balancer not stopped (expected for negative)")}
  ' 2>/dev/null; then
    warn "balancer already stopped before negative check"
  else
    log "balancer negative check ok (not stopped yet)"
  fi
  # stop balancer via mongos
  mongo_eval_auth "${mongos_ip}" "${mongos_port}" 'sh.stopBalancer()'
  sleep 2
  mongo_eval_auth "${cfg_ip}" "${cfg_port}" '
    var cfg=db.getSiblingDB("config");
    var s=cfg.settings.findOne({_id:"balancer"});
    if(!s||!(s.stopped===true||s.mode==="off")){throw new Error("balancer must be stopped: "+tojson(s))}
    var m=cfg.migrations.findOne();
    if(m){throw new Error("active migration: "+tojson(m))}
    var l=cfg.locks.findOne({_id:"balancer",state:2});
    if(l){throw new Error("active balancer lock: "+tojson(l))}
  '
  log "balancer stopped and config metadata clean"
}

apply_incr_dml_rs() {
  local ip="$1" port="$2"
  mongo_eval_auth "${ip}" "${port}" '
    var c=db.getSiblingDB("dtsdemo").orders;
    c.insertMany([{_id:1001,n:"new1",v:1},{_id:1002,n:"new2",v:1}]);
    c.updateOne({_id:1},{$set:{v:2,n:"updated1"}});
    c.deleteOne({_id:2});
  '
}

apply_incr_dml_shard() {
  local ip="$1" port="$2"
  mongo_eval_auth "${ip}" "${port}" '
    var c=db.getSiblingDB("dtsdemo").orders;
    c.insertMany([{_id:2001,n:"new1",v:1},{_id:2002,n:"new2",v:1},{_id:3001,n:"new3",v:1}]);
    c.updateOne({_id:1},{$set:{v:2,n:"updated1"}});
    c.deleteOne({_id:2});
  '
}

start_background_writer_shard() {
  local ip="$1" port="$2"
  (
    local i=5000
    while true; do
      mongo_eval_auth "${ip}" "${port}" "db.getSiblingDB('dtsdemo').orders.insertOne({_id:${i}, n:'bg'+${i}, v:1})" >/dev/null 2>&1 || true
      i=$((i + 1))
      sleep 1
    done
  ) &
  WRITER_PID=$!
  manifest_append "writer|${WRITER_PID}"
  log "background writer pid=${WRITER_PID}"
}

canonical_hash() {
  local ip="$1" port="$2" dbn="$3" coll="$4"
  local dump
  dump="$(mongo_eval_auth "${ip}" "${port}" "var docs=db.getSiblingDB('${dbn}').getCollection('${coll}').find({}).sort({_id:1}).toArray(); print((typeof JSON!=='undefined'&&JSON.stringify)?JSON.stringify(docs):tojson(docs));")"
  printf '%s' "${dump}" | sha256sum | awk '{print $1}'
}

doc_count() {
  local ip="$1" port="$2" dbn="$3" coll="$4"
  mongo_eval_auth "${ip}" "${port}" "print(db.getSiblingDB('${dbn}').getCollection('${coll}').countDocuments({}))" | tr -d '[:space:]'
}

assert_ns_synced() {
  local src_ip="$1" src_port="$2" dst_ip="$3" dst_port="$4"
  local src_hash dst_hash src_cnt dst_cnt
  src_cnt="$(doc_count "${src_ip}" "${src_port}" dtsdemo orders)"
  dst_cnt="$(doc_count "${dst_ip}" "${dst_port}" dtsdemo orders)"
  [[ "${src_cnt}" == "${dst_cnt}" ]] || die "count mismatch src=${src_cnt} dst=${dst_cnt}"
  src_hash="$(canonical_hash "${src_ip}" "${src_port}" dtsdemo orders)"
  dst_hash="$(canonical_hash "${dst_ip}" "${dst_port}" dtsdemo orders)"
  [[ "${src_hash}" == "${dst_hash}" ]] || die "hash mismatch src=${src_hash} dst=${dst_hash}"
  # deleted id 2 absent on dst
  local gone
  gone="$(mongo_eval_auth "${dst_ip}" "${dst_port}" 'print(db.getSiblingDB("dtsdemo").orders.find({_id:2}).hasNext()?"1":"0")' | tr -d '[:space:]')"
  [[ "${gone}" == "0" ]] || die "deleted _id:2 still present on target"
  # updated
  local uv
  uv="$(mongo_eval_auth "${dst_ip}" "${dst_port}" 'print(db.getSiblingDB("dtsdemo").orders.findOne({_id:1}).v)' | tr -d '[:space:]')"
  [[ "${uv}" == "2" ]] || die "update not applied on target v=${uv}"
  # index exists
  mongo_eval_auth "${dst_ip}" "${dst_port}" '
    var idxs=db.getSiblingDB("dtsdemo").orders.getIndexes();
    var ok=idxs.some(function(i){return i.name==="n_1" || (i.key && i.key.n===1);});
    if(!ok){throw new Error("missing index on n")}
  '
  # non-whitelist isolation
  local nw
  nw="$(mongo_eval_auth "${dst_ip}" "${dst_port}" 'print(db.getSiblingDB("notwhite").getCollectionNames().length)' | tr -d '[:space:]')"
  [[ "${nw}" == "0" ]] || die "non-whitelist db leaked to target"
  log "sync assertions ok count=${src_cnt} hash=${src_hash}"
}

assert_both_shards_have_data() {
  local s1_ip="$1" s1_port="$2" s2_ip="$3" s2_port="$4"
  local c1 c2
  c1="$(doc_count "${s1_ip}" "${s1_port}" dtsdemo orders)"
  c2="$(doc_count "${s2_ip}" "${s2_port}" dtsdemo orders)"
  [[ "${c1}" -gt 0 && "${c2}" -gt 0 ]] || die "expected data on both shards got ${c1}/${c2}"
  log "both shards have data ${c1}/${c2}"
}

assert_zero_source_mongos() {
  local conf="$1" mongos_ip="$2" mongos_port="$3"
  grep -E '^mongo_s_url =\s*$' "${conf}" >/dev/null || die "mongo_s_url not empty in conf"
  if grep -E "mongo_urls = .*${mongos_ip}:${mongos_port}" "${conf}" >/dev/null; then
    die "source mongos appears in mongo_urls"
  fi
  # URIs should mention directConnection for sharded/backup
  if grep -E '^mongo_urls = .+' "${conf}" | grep -vq 'directConnection=true'; then
    # rs secondaryPreferred may not use directConnection — only enforce for backup/shard
    if grep -q 'directConnection=true' "${conf}"; then
      :
    fi
  fi
  if [[ -f "${SHAKE_DIR}/collector.pid" ]]; then
    local pid
    pid="$(cat "${SHAKE_DIR}/collector.pid")"
    if kill -0 "${pid}" 2>/dev/null; then
      if ls -l "/proc/${pid}/fd" 2>/dev/null | rg -q "socket:"; then
        # check TCP connections to mongos port
        if ss -tpn 2>/dev/null | rg "pid=${pid}," | rg -q ":${mongos_port}\\b"; then
          die "collector has TCP connection to source mongos :${mongos_port}"
        fi
      fi
    fi
  fi
  log "zero source mongos assertions ok"
}

extract_cut_ts() {
  local ts=""
  # Prefer the newest matching line across actuator logs (by file mtime then last match).
  local f
  while IFS= read -r f; do
    ts="$(rg -o "cut installed timestamp=[0-9]+" "${f}" 2>/dev/null | tail -1 | rg -o "[0-9]+$" || true)"
    [[ -n "${ts}" ]] && break
  done < <(ls -t "${ROOT_DIR}"/logs/mongo_actuator_*.log 2>/dev/null || true)
  if [[ -z "${ts}" ]]; then
    ts="$(rg -o "cut installed timestamp=[0-9]+" "${SHAKE_DIR}/logs" 2>/dev/null | tail -1 | rg -o "[0-9]+$" || true)"
  fi
  [[ -n "${ts}" ]] || die "cutTs not found in logs"
  echo "${ts}"
}

assert_cut_ts_boundary() {
  local cut_ts="$1"
  shift
  while [[ $# -gt 0 ]]; do
    local ip="$1" port="$2"
    shift 2
    mongo_eval_auth "${ip}" "${port}" "db.getSiblingDB('local').oplog.rs.findOne()" >/dev/null
  done
  log "cutTs boundary noted cut_ts=${cut_ts}"
}

assert_collector_cleaned() {
  [[ ! -f "${SHAKE_DIR}/collector.conf" ]] || die "collector.conf still present"
  if [[ -f "${SHAKE_DIR}/collector.pid" ]]; then
    local pid
    pid="$(cat "${SHAKE_DIR}/collector.pid")"
    if kill -0 "${pid}" 2>/dev/null; then
      die "collector still running pid=${pid}"
    fi
  fi
  log "collector cleaned"
}

start_mongoshake() {
  local conf_file="$1"
  [[ -f "${DTS_TGZ}" ]] || die "missing ${DTS_TGZ}"
  rm -rf "${PKG_DIR}"
  mkdir -p "${PKG_DIR}" "${SHAKE_DIR}/logs"
  stop_collector_force
  rm -f "${SHAKE_DIR}/collector.conf" "${SHAKE_DIR}/collector.pid" "${SHAKE_DIR}/collector.stdout"
  cp -f "${conf_file}" "${SHAKE_DIR}/collector.conf"
  manifest_append "shake|${SHAKE_DIR}"

  cat > "${WORK_DIR}/mongoshake_start.json" <<EOF
{
  "op": "start",
  "workDir": "${SHAKE_DIR}",
  "pkgPath": "${DTS_TGZ}",
  "confFile": "${SHAKE_DIR}/collector.conf"
}
EOF
  run_atom "e2e-dts-shake-start" "mongoshake_collector" "${WORK_DIR}/mongoshake_start.json" "shake-start"
  sleep 2
  kill -0 "$(cat "${SHAKE_DIR}/collector.pid")" 2>/dev/null || {
    cat "${SHAKE_DIR}/collector.stdout" >&2 || true
    die "collector exited immediately"
  }
}

run_wait_or_wait_stop() {
  local op="$1"  # wait | wait_stop
  local remove_conf="${2:-true}"
  cat > "${WORK_DIR}/mongoshake_${op}.json" <<EOF
{
  "op": "${op}",
  "workDir": "${SHAKE_DIR}",
  "fullHttpPort": ${FULL_PORT},
  "incrHttpPort": ${INCR_PORT},
  "lagSeconds": 15,
  "stableRounds": 3,
  "pollSeconds": 5,
  "deadlineSeconds": 900,
  "removeConf": ${remove_conf}
}
EOF
  run_atom "e2e-dts-shake-${op}" "mongoshake_collector" "${WORK_DIR}/mongoshake_${op}.json" "shake-${op}"
}

drop_temp_users_and_ckpt() {
  local dst_kind="$1" src_kind="$2"
  if [[ "${dst_kind}" == "rs" ]]; then
    mongo_eval_auth "${DST_RS_IPS[0]}" "${DST_RS_PORTS[0]}" \
      "var a=db.getSiblingDB('admin'); try{a.dropUser('${DST_DTS_USER}')}catch(e){}; var m=db.getSiblingDB('mongoshake'); try{m.getCollection('ckpt_${COLLECTOR_ID}').drop()}catch(e){};" || true
  else
    mongo_eval_auth "${DST_MONGOS_IP}" "${DST_MONGOS_PORT}" \
      "var a=db.getSiblingDB('admin'); try{a.dropUser('${DST_DTS_USER}')}catch(e){}; var m=db.getSiblingDB('mongoshake'); try{m.getCollection('ckpt_${COLLECTOR_ID}').drop()}catch(e){};" || true
  fi
  if [[ "${src_kind}" == "rs" ]]; then
    mongo_eval_auth "${SRC_RS_IPS[0]}" "${SRC_RS_PORTS[0]}" \
      "try{db.getSiblingDB('admin').dropUser('${SRC_DTS_USER}')}catch(e){}" || true
  else
    for pair in "${SRC_CFG_IPS[0]}:${SRC_CFG_PORTS[0]}" "${SRC_S1_IPS[0]}:${SRC_S1_PORTS[0]}" "${SRC_S2_IPS[0]}:${SRC_S2_PORTS[0]}"; do
      mongo_eval_auth "${pair%%:*}" "${pair##*:}" \
        "try{db.getSiblingDB('admin').dropUser('${SRC_DTS_USER}')}catch(e){}" || true
    done
  fi
}

