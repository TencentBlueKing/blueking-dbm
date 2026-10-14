#!/usr/bin/env bash
# Shared helpers for MongoDB core atom integration tests.
# shellcheck disable=SC2034

set -euo pipefail

integration_lib_init() {
  ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  cd "${ROOT_DIR}"

  RUN_ID="${TEST_RUN_ID:-$(date +%Y%m%d%H%M%S)}"
  LAB_ROOT="${TEST_LAB_ROOT:-/data/mongo_actuator_lab}"
  RUN_DIR="${TEST_RUN_DIR:-${LAB_ROOT}/${RUN_ID}}"
  DATA_DIR="${TEST_DATA_DIR:-${RUN_DIR}/data}"
  BACKUP_DIR="${TEST_BACKUP_DIR:-${RUN_DIR}/backup}"
  BIN_DIR="${TEST_BIN_DIR:-${RUN_DIR}/bin}"
  WORK_DIR="${TEST_WORK_DIR:-${RUN_DIR}/work}"
  LOG_SNAPSHOT_DIR="${WORK_DIR}/logs"
  STATE_FILE="${WORK_DIR}/state.env"
  COVERAGE_FILE="${WORK_DIR}/coverage.tsv"
  ACTUATOR_BIN="${ACTUATOR_BIN:-${BIN_DIR}/mongo-dbactuator}"

  PKG_NAME="${TEST_MONGO_PKG_NAME:-mongodb-linux-x86_64-rhel70-4.4.30.tar.gz}"
  PKG_MD5="${TEST_MONGO_PKG_MD5:-0856af7ed34231d4b533581c11d9ebe6}"
  DB_VERSION="${TEST_MONGO_DB_VERSION:-4.4.30}"
  PKG_PATH="/data/install/${PKG_NAME}"

  OS_INIT_USER="${TEST_OS_INIT_USER:-mysql}"
  OS_INIT_GROUP="${TEST_OS_INIT_GROUP:-mysql}"
  OS_INIT_PASSWORD="${TEST_OS_INIT_PASSWORD:-test123456}"
  DBA_USER="${TEST_DBA_USER:-xuser1}"
  DBA_PASS="${TEST_DBA_PASS:-test123456}"
  APPDBA_PASS="${TEST_APPDBA_PASS:-test123456}"
  MONITOR_PASS="${TEST_MONITOR_PASS:-test123456}"
  APPMONITOR_PASS="${TEST_APPMONITOR_PASS:-test123456}"
  TEMP_USER="${TEST_TEMP_USER:-it_temp_user}"
  TEMP_PASS="${TEST_TEMP_PASS:-tempPass123}"

  KEY_FILE="${TEST_KEY_FILE:-ut-core-it-key-file}"
  RS_SET_ID="${TEST_RS_SET_ID:-itRsCore}"
  CFG_SET_ID="${TEST_CFG_SET_ID:-itCfg}"
  SHARD1_SET_ID="${TEST_SHARD1_SET_ID:-itS1}"
  SHARD2_SET_ID="${TEST_SHARD2_SET_ID:-itS2}"

  # Replica set sandbox: 3 members + 1 spare for replace.
  # Ports must stay in actuator range [27000, 29999].
  RS_IPS=("${TEST_RS_IP1:-127.0.0.71}" "${TEST_RS_IP2:-127.0.0.72}" "${TEST_RS_IP3:-127.0.0.73}" "${TEST_RS_IP4:-127.0.0.74}")
  RS_PORTS=("${TEST_RS_PORT1:-27517}" "${TEST_RS_PORT2:-27518}" "${TEST_RS_PORT3:-27519}" "${TEST_RS_PORT4:-27520}")

  # Sharded sandbox: configsvr x3, shard1 x3, shard2 x3, mongos x1.
  CFG_IPS=("${TEST_CFG_IP1:-127.0.0.81}" "${TEST_CFG_IP2:-127.0.0.82}" "${TEST_CFG_IP3:-127.0.0.83}")
  CFG_PORTS=("${TEST_CFG_PORT1:-27617}" "${TEST_CFG_PORT2:-27618}" "${TEST_CFG_PORT3:-27619}")
  SHARD1_IPS=("${TEST_SHARD1_IP1:-127.0.0.91}" "${TEST_SHARD1_IP2:-127.0.0.92}" "${TEST_SHARD1_IP3:-127.0.0.93}")
  SHARD1_PORTS=("${TEST_SHARD1_PORT1:-27717}" "${TEST_SHARD1_PORT2:-27718}" "${TEST_SHARD1_PORT3:-27719}")
  SHARD2_IPS=("${TEST_SHARD2_IP1:-127.0.0.94}" "${TEST_SHARD2_IP2:-127.0.0.95}" "${TEST_SHARD2_IP3:-127.0.0.96}")
  SHARD2_PORTS=("${TEST_SHARD2_PORT1:-27817}" "${TEST_SHARD2_PORT2:-27818}" "${TEST_SHARD2_PORT3:-27819}")
  MONGOS_IP="${TEST_MONGOS_IP:-127.0.0.97}"
  MONGOS_PORT="${TEST_MONGOS_PORT:-27917}"

  ALL_IPS=(
    "${RS_IPS[@]}" "${CFG_IPS[@]}" "${SHARD1_IPS[@]}" "${SHARD2_IPS[@]}" "${MONGOS_IP}"
  )
  ALL_PORTS=(
    "${RS_PORTS[@]}" "${CFG_PORTS[@]}" "${SHARD1_PORTS[@]}" "${SHARD2_PORTS[@]}" "${MONGOS_PORT}"
  )

  # shellcheck disable=SC2034
  CORE_RUN_JOBS=(
    os_mongo_init
    mongodb_hello
    mongod_install
    mongos_install
    init_replicaset
    add_user
    delete_user
    mongo_execute_script
    replicaset_stepdown
    mongod_node_hidden
    mongo_restart
    mongo_start
    mongodb_instance_op
    mongo_set_fcv
    mongo_upgrade_rs_protocol
    replace_package
    mongod_replace
    mongo_deferred_deinstall
    add_shard_to_cluster
    cluster_balancer
    remove_shard_from_cluster
    mongo_deinstall
  )

  # name|reason
  CORE_SKIP_JOBS=(
    "mongodb_backup|needs backup_client and backup system"
    "mongodb_restore|needs backup archive layout"
    "mongodb_pitr_restore|needs PITR archive tree"
    "mongodb_pitr_rebuild|needs src/dst cluster metadata and PITR restore"
    "mongodb_remove_ns|destructive data job, deferred to dedicated suite"
    "install_dbmon|needs dbmon/dbtools/toolkit media packages"
    "mongodb_data_export|needs BKRepo credentials"
  )

  KEEP_ON_FAILURE="${KEEP_ON_FAILURE:-0}"
  CLEANUP_ONLY="${CLEANUP_ONLY:-0}"
  PREFLIGHT_ONLY="${PREFLIGHT_ONLY:-0}"
  OLD_SWAPPINESS=""
  OLD_PID_MAX=""
  PROFILE_BIN_BACKUP=""
  declare -gA COVERED_JOBS=()
  declare -gA SKIPPED_JOBS=()
}

log() { echo "==> $*"; }
warn() { echo "WARN: $*" >&2; }
die() { echo "ERROR: $*" >&2; exit 1; }

write_json() {
  local out="$1"
  shift
  python3 - "$out" "$@" <<'PY'
import json, sys
out = sys.argv[1]
obj = json.loads(sys.argv[2])
with open(out, "w", encoding="utf-8") as f:
    json.dump(obj, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
}

# 与 actuator 一致：优先 mongosh，没有则用 mongo。
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../e2e" && pwd)/mongo_shell.sh"

mongo_eval() {
  local host="$1" port="$2" script="$3"
  shift 3 || true
  if [[ "${1:-}" == "--auth" ]]; then
    "$(mongo_shell_bin)" -u "${DBA_USER}" -p "${DBA_PASS}" --authenticationDatabase=admin \
      --host "${host}" --port "${port}" --quiet --eval "${script}"
  else
    "$(mongo_shell_bin)" --host "${host}" --port "${port}" --quiet --eval "${script}"
  fi
}

mark_covered() {
  local job="$1"
  COVERED_JOBS["${job}"]=1
  printf "%s\tRUN\t%s\n" "${job}" "$(date -Iseconds)" >> "${COVERAGE_FILE}"
}

mark_skipped() {
  local job="$1" reason="$2"
  SKIPPED_JOBS["${job}"]="${reason}"
  printf "%s\tSKIP\t%s\n" "${job}" "${reason}" >> "${COVERAGE_FILE}"
}

run_atom() {
  local uid="$1" atom="$2" payload_file="$3" node_id="$4"
  local run_as="${5:-}" rc=0
  log "atom=${atom} uid=${uid} node=${node_id}${run_as:+ as ${run_as}}"
  if [[ -n "${run_as}" ]]; then
    sudo -u "${run_as}" "${ACTUATOR_BIN}" \
      --uid="${uid}" \
      --root_id="core-it-${RUN_ID}" \
      --node_id="${node_id}" \
      --version_id="v1" \
      --atom-job-list="${atom}" \
      --payload_file="${payload_file}" \
      --data_dir="${DATA_DIR}" \
      --backup_dir="${BACKUP_DIR}" \
      --bin_dir="${BIN_DIR}" || rc=$?
  else
    "${ACTUATOR_BIN}" \
      --uid="${uid}" \
      --root_id="core-it-${RUN_ID}" \
      --node_id="${node_id}" \
      --version_id="v1" \
      --atom-job-list="${atom}" \
      --payload_file="${payload_file}" \
      --data_dir="${DATA_DIR}" \
      --backup_dir="${BACKUP_DIR}" \
      --bin_dir="${BIN_DIR}" || rc=$?
  fi
  [[ "${rc}" -eq 0 ]] || return "${rc}"
  mark_covered "${atom}"
}

run_os_init() {
  local node_id="$1"
  local payload="${WORK_DIR}/os_mongo_init.json"
  write_json "${payload}" "{\"user\":\"${OS_INIT_USER}\",\"password\":\"${OS_INIT_PASSWORD}\"}"
  log "atom=os_mongo_init node=${node_id}"
  "${ACTUATOR_BIN}" \
    --uid="core-it-os-init-${RUN_ID}" \
    --root_id="core-it-${RUN_ID}" \
    --node_id="${node_id}" \
    --version_id="v1" \
    --atom-job-list="os_mongo_init" \
    --payload_file="${payload}" \
    --data_dir="${DATA_DIR}" \
    --backup_dir="${BACKUP_DIR}" \
    --bin_dir="${BIN_DIR}" \
    --user="${OS_INIT_USER}" \
    --group="${OS_INIT_GROUP}"
  mark_covered "os_mongo_init"
}

ensure_loopback_ips() {
  local ip
  for ip in "${ALL_IPS[@]}"; do
    if ! ip -4 addr show lo | grep -q "inet ${ip}/"; then
      log "add loopback alias ${ip}"
      ip addr add "${ip}/8" dev lo || die "failed to add ${ip} on lo"
    fi
  done
}

wait_port_listen() {
  local port="$1" attempt=0
  while [[ ${attempt} -lt 60 ]]; do
    if netstat -ntpl 2>/dev/null | rg -q ":${port}[[:space:]]"; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 1
  done
  die "port ${port} not listening"
}

wait_port_stopped() {
  local port="$1" attempt=0
  while [[ ${attempt} -lt 60 ]]; do
    if ! netstat -ntpl 2>/dev/null | rg -q ":${port}[[:space:]]"; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 1
  done
  die "port ${port} still listening"
}

wait_rs_healthy() {
  local host="$1" port="$2" expect="$3" use_auth="${4:-0}" desc="${5:-rs}"
  log "wait ${desc} healthy expect=${expect} auth=${use_auth}"
  local attempt=0 total healthy auth_arg=()
  if [[ "${use_auth}" == "1" ]]; then
    auth_arg=(--auth)
  fi
  while [[ ${attempt} -lt 60 ]]; do
    total="$(mongo_eval "${host}" "${port}" "rs.status().members.length" ${auth_arg[@]+"${auth_arg[@]}"} 2>/dev/null | tr -d '[:space:]' || true)"
    healthy="$(mongo_eval "${host}" "${port}" "rs.status().members.filter(function(m){return m.stateStr==='PRIMARY'||m.stateStr==='SECONDARY';}).length" ${auth_arg[@]+"${auth_arg[@]}"} 2>/dev/null | tr -d '[:space:]' || true)"
    if [[ "${total}" == "${expect}" && "${healthy}" == "${expect}" ]]; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep 2
  done
  die "${desc} not healthy: total=${total:-?} healthy=${healthy:-?} expect=${expect}"
}

current_primary() {
  local host="$1" port="$2"
  mongo_eval "${host}" "${port}" "rs.isMaster().primary" --auth | tr -d '[:space:]'
}

collect_diagnostics() {
  log "collect diagnostics under ${LOG_SNAPSHOT_DIR}"
  mkdir -p "${LOG_SNAPSHOT_DIR}"
  cp -f "${ROOT_DIR}"/logs/mongo_actuator_*.log "${LOG_SNAPSHOT_DIR}/" 2>/dev/null || true
  {
    echo "# ports"
    for p in "${ALL_PORTS[@]}"; do
      netstat -ntpl 2>/dev/null | rg "${p}" || true
    done
    echo "# coverage"
    [[ -f "${COVERAGE_FILE}" ]] && cat "${COVERAGE_FILE}" || true
  } > "${LOG_SNAPSHOT_DIR}/topology.txt" || true
}

save_sysctl() {
  OLD_SWAPPINESS="$(sysctl -n vm.swappiness 2>/dev/null || echo "")"
  OLD_PID_MAX="$(sysctl -n kernel.pid_max 2>/dev/null || echo "")"
}

restore_sysctl() {
  if [[ -n "${OLD_SWAPPINESS}" ]]; then
    sysctl -w "vm.swappiness=${OLD_SWAPPINESS}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${OLD_PID_MAX}" ]]; then
    sysctl -w "kernel.pid_max=${OLD_PID_MAX}" >/dev/null 2>&1 || true
  fi
}

# SetMongoBinDir refuses a different value when /etc/profile already exports MONGO_BIN_DIR.
# Temporarily point it at this run's BIN_DIR and restore on exit.
adopt_profile_mongo_bin_dir() {
  PROFILE_BIN_BACKUP="${WORK_DIR}/etc_profile_mongo_bin_dir.bak"
  grep -E '^export MONGO_BIN_DIR=' /etc/profile > "${PROFILE_BIN_BACKUP}" 2>/dev/null || true
  BIN_DIR="${BIN_DIR}" python3 - <<'PY'
from pathlib import Path
import os
bin_dir = os.environ["BIN_DIR"]
profile = Path("/etc/profile")
text = profile.read_text() if profile.exists() else ""
lines = text.splitlines(keepends=True)
out = []
replaced = False
for line in lines:
    if (not replaced) and line.startswith("export MONGO_BIN_DIR="):
        out.append(f'export MONGO_BIN_DIR="{bin_dir}"\n')
        replaced = True
    else:
        out.append(line)
if not replaced:
    if out and not out[-1].endswith("\n"):
        out[-1] += "\n"
    out.append(f'export MONGO_BIN_DIR="{bin_dir}"\n')
profile.write_text("".join(out))
PY
  log "adopted /etc/profile MONGO_BIN_DIR=${BIN_DIR}"
}

restore_profile_mongo_bin_dir() {
  [[ -n "${PROFILE_BIN_BACKUP:-}" && -f "${PROFILE_BIN_BACKUP}" ]] || return 0
  local backup_path="${PROFILE_BIN_BACKUP}"
  PROFILE_BIN_BACKUP=""
  PROFILE_BIN_BACKUP="${backup_path}" python3 - <<'PY'
from pathlib import Path
import os
backup = Path(os.environ["PROFILE_BIN_BACKUP"])
profile = Path("/etc/profile")
old = backup.read_text().splitlines()
old_line = old[0] if old else ""
lines = profile.read_text().splitlines(keepends=True) if profile.exists() else []
out = []
replaced = False
for line in lines:
    if line.startswith("export MONGO_BIN_DIR="):
        if old_line and not replaced:
            out.append(old_line if old_line.endswith("\n") else old_line + "\n")
            replaced = True
        # drop extra MONGO_BIN_DIR lines we may have touched
        continue
    out.append(line)
if old_line and not replaced:
    if out and not out[-1].endswith("\n"):
        out[-1] += "\n"
    out.append(old_line if old_line.endswith("\n") else old_line + "\n")
profile.write_text("".join(out))
PY
  log "restored /etc/profile MONGO_BIN_DIR"
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
  # Allow non-root jobs (mongodb_hello / instance_op) to execute the binary.
  chmod 755 "${BIN_DIR}" "${RUN_DIR}" "${LAB_ROOT}" 2>/dev/null || true
  chown "${OS_INIT_USER}:${OS_INIT_GROUP}" "${ACTUATOR_BIN}" 2>/dev/null || true
}

list_registered_jobs() {
  "${ACTUATOR_BIN}" debug --list 2>/dev/null | awk 'NF && $0 !~ /^debug/ {print $1}' | sort -u
}

preflight_checks() {
  local ok=1
  [[ "${EUID}" -eq 0 ]] || { warn "must run as root"; ok=0; }
  command -v go >/dev/null || { warn "go not found"; ok=0; }
  command -v python3 >/dev/null || { warn "python3 not found"; ok=0; }
  command -v rg >/dev/null || { warn "rg not found"; ok=0; }
  command -v netstat >/dev/null || { warn "netstat not found"; ok=0; }
  command -v ip >/dev/null || { warn "ip not found"; ok=0; }
  id "${OS_INIT_USER}" >/dev/null 2>&1 || { warn "os user ${OS_INIT_USER} missing"; ok=0; }
  [[ -f "${PKG_PATH}" ]] || { warn "package missing: ${PKG_PATH}"; ok=0; }
  if [[ -f "${PKG_PATH}" ]]; then
    local md5
    md5="$(md5sum "${PKG_PATH}" | awk '{print $1}')"
    [[ "${md5}" == "${PKG_MD5}" ]] || { warn "package md5 mismatch: got ${md5} want ${PKG_MD5}"; ok=0; }
  fi
  mkdir -p "${LAB_ROOT}" 2>/dev/null || { warn "cannot create ${LAB_ROOT}"; ok=0; }
  if [[ "${ok}" -eq 1 ]]; then
    log "preflight ok"
    return 0
  fi
  return 1
}

write_deinstall_payload() {
  local ip="$1" port="$2" instance_type="$3" out="$4"
  write_json "${out}" "{\"ip\":\"${ip}\",\"port\":${port},\"setId\":\"cleanup\",\"nodeInfo\":[\"${ip}\"],\"instanceType\":\"${instance_type}\",\"force\":true,\"renameDir\":true}"
}

deinstall_instance() {
  local ip="$1" port="$2" instance_type="$3"
  local payload="${WORK_DIR}/deinstall_${port}.json"
  write_deinstall_payload "${ip}" "${port}" "${instance_type}" "${payload}"
  run_atom "core-it-deinstall-${port}" "mongo_deinstall" "${payload}" "node-${port}"
}

cleanup_all_instances() {
  log "cleanup all instances"
  local i
  for i in "${!RS_PORTS[@]}"; do
    deinstall_instance "${RS_IPS[$i]}" "${RS_PORTS[$i]}" "mongod"
  done
  for i in "${!CFG_PORTS[@]}"; do
    deinstall_instance "${CFG_IPS[$i]}" "${CFG_PORTS[$i]}" "mongod"
  done
  for i in "${!SHARD1_PORTS[@]}"; do
    deinstall_instance "${SHARD1_IPS[$i]}" "${SHARD1_PORTS[$i]}" "mongod"
  done
  for i in "${!SHARD2_PORTS[@]}"; do
    deinstall_instance "${SHARD2_IPS[$i]}" "${SHARD2_PORTS[$i]}" "mongod"
  done
  deinstall_instance "${MONGOS_IP}" "${MONGOS_PORT}" "mongos"
}

verify_coverage() {
  log "verify registered job coverage"
  local registered missing=0 job reason
  mapfile -t registered < <(list_registered_jobs)
  declare -A expected=()
  for job in "${CORE_RUN_JOBS[@]}"; do
    expected["${job}"]=RUN
  done
  for entry in "${CORE_SKIP_JOBS[@]}"; do
    job="${entry%%|*}"
    reason="${entry#*|}"
    expected["${job}"]=SKIP
    if [[ -z "${SKIPPED_JOBS[${job}]:-}" ]]; then
      mark_skipped "${job}" "${reason}"
    fi
  done

  for job in "${registered[@]}"; do
    if [[ -z "${expected[${job}]:-}" ]]; then
      warn "registered job {$job} is not classified in RUN/SKIP lists"
      missing=1
      continue
    fi
    if [[ "${expected[${job}]}" == "RUN" && -z "${COVERED_JOBS[${job}]:-}" ]]; then
      warn "core job ${job} was not executed"
      missing=1
    fi
  done
  for job in "${!expected[@]}"; do
    local found=0
    for r in "${registered[@]}"; do
      [[ "${r}" == "${job}" ]] && found=1 && break
    done
    if [[ "${found}" -eq 0 ]]; then
      warn "classified job ${job} is not registered in actuator"
      missing=1
    fi
  done
  [[ "${missing}" -eq 0 ]] || die "coverage verification failed; see ${COVERAGE_FILE}"
  log "coverage ok: $(printf '%s ' "${CORE_RUN_JOBS[@]}")"
  log "skipped: $(printf '%s ' "${!SKIPPED_JOBS[@]}")"
}

build_mongod_install_payload() {
  local ip="$1" port="$2" set_id="$3" role="$4" out="$5"
  cat > "${out}" <<EOF
{
  "mediapkg": {"pkg": "${PKG_NAME}", "pkg_md5": "${PKG_MD5}"},
  "ip": "${ip}",
  "port": ${port},
  "dbVersion": "${DB_VERSION}",
  "instanceType": "mongod",
  "setId": "${set_id}",
  "keyFile": "${KEY_FILE}",
  "auth": true,
  "clusterRole": "${role}",
  "dbConfig": {
    "slowOpThresholdMs": 200,
    "cacheSizeGB": 1,
    "oplogSizeMB": 256,
    "destination": "file"
  }
}
EOF
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
    priority[m] = 2 if i == 0 else (0 if i == len(members) - 1 and len(members) > 1 else 1)
    hidden[m] = bool(i == len(members) - 1 and len(members) > 1)
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
  local ip="$1" port="$2" username="$3" password="$4" out="$5"
  local admin_user="${6:-}"
  local admin_pass="${7:-}"
  python3 - <<PY
import json
payload = {
  "ip": "${ip}",
  "port": ${port},
  "instanceType": "mongod",
  "username": "${username}",
  "password": "${password}",
  "adminUsername": "${admin_user}",
  "adminPassword": "${admin_pass}",
  "authDb": "admin",
  "dbsPrivileges": [{"db": "admin", "privileges": ["root"]}],
}
with open("${out}", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
}

# mongo_execute_script chowns ExecuteDir in Init before createScriptFile;
# production downloads the package first. Local ScriptFile=false needs mkdir.
ensure_execute_script_dir() {
  local task_id="$1"
  local exec_dir="/data/install/dbactuator-${task_id}"
  mkdir -p "${exec_dir}"
  chown -R "${OS_INIT_USER}:${OS_INIT_GROUP}" "${exec_dir}"
}

build_execute_script_payload() {
  local out_json="$1" script_file="$2" script_name="$3" exec_ip="$4" exec_port="$5"
  local task_id="core-it-${RUN_ID}-${script_name}-${exec_port}"
  ensure_execute_script_dir "${task_id}"
  SCRIPT_FILE="${script_file}" OUT_JSON="${out_json}" SCRIPT_NAME="${script_name}" \
    EXEC_IP="${exec_ip}" EXEC_PORT="${exec_port}" EXEC_DBA_USER="${DBA_USER}" EXEC_DBA_PASS="${DBA_PASS}" \
    TASK_ID="${task_id}" DB_VERSION="${DB_VERSION}" \
    python3 - <<'PY'
import json, os
with open(os.environ["SCRIPT_FILE"], encoding="utf-8") as f:
    script = f.read()
payload = {
    "ip": os.environ["EXEC_IP"],
    "port": int(os.environ["EXEC_PORT"]),
    "script": script,
    "type": "replicaset",
    "scriptName": os.environ["SCRIPT_NAME"],
    "taskid": os.environ["TASK_ID"],
    "scriptFile": False,
    "adminUsername": os.environ["EXEC_DBA_USER"],
    "adminPassword": os.environ["EXEC_DBA_PASS"],
    "dbVersion": os.environ["DB_VERSION"],
    "repoUrl": "",
    "repoUsername": "",
    "repoToken": "",
    "repoProject": "",
    "repoRepo": "",
    "repoPath": "",
}
with open(os.environ["OUT_JSON"], "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)
    f.write("\n")
PY
}

write_extra_user_js() {
  local out="$1"
  cat > "${out}" <<EOF
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
}

write_replicaset_init_js() {
  local out="$1"
  cat > "${out}" <<'EOF'
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
EOF
}

install_rs_members() {
  local set_id="$1" role="$2"
  shift 2
  local ips=() ports=()
  # args: ip1 port1 ip2 port2 ...
  while [[ $# -gt 0 ]]; do
    ips+=("$1"); ports+=("$2"); shift 2
  done
  local i pids=()
  for i in "${!ports[@]}"; do
    build_mongod_install_payload "${ips[$i]}" "${ports[$i]}" "${set_id}" "${role}" \
      "${WORK_DIR}/mongod_install_${ports[$i]}.json"
    ( run_atom "core-it-install-${ports[$i]}" "mongod_install" \
      "${WORK_DIR}/mongod_install_${ports[$i]}.json" "node-${ports[$i]}" ) &
    pids+=($!)
  done
  local pid rc=0
  for pid in "${pids[@]}"; do
    if ! wait "${pid}"; then
      rc=1
    fi
  done
  [[ "${rc}" -eq 0 ]] || die "parallel mongod_install failed"
  COVERED_JOBS["mongod_install"]=1
}

init_rs_and_users() {
  local set_id="$1" config_svr="$2" primary_ip="$3" primary_port="$4"
  shift 4
  local members=("$@")
  local payload="${WORK_DIR}/init_${set_id}.json"
  build_init_replicaset_payload "${primary_ip}" "${primary_port}" "${set_id}" "${config_svr}" \
    "${payload}" "${members[@]}"
  run_atom "core-it-init-${set_id}" "init_replicaset" "${payload}" "node-${primary_port}"
  wait_rs_healthy "${primary_ip}" "${primary_port}" "${#members[@]}" 0 "${set_id}"

  build_add_user_payload "${primary_ip}" "${primary_port}" "${DBA_USER}" "${DBA_PASS}" \
    "${WORK_DIR}/add_user_${set_id}.json"
  run_atom "core-it-add-user-${set_id}" "add_user" "${WORK_DIR}/add_user_${set_id}.json" "node-${primary_port}"

  write_extra_user_js "${WORK_DIR}/extra_user_${set_id}.js"
  write_replicaset_init_js "${WORK_DIR}/rs_init_${set_id}.js"
  build_execute_script_payload "${WORK_DIR}/exec_extra_${set_id}.json" \
    "${WORK_DIR}/extra_user_${set_id}.js" "create_extra_user" "${primary_ip}" "${primary_port}"
  build_execute_script_payload "${WORK_DIR}/exec_rs_init_${set_id}.json" \
    "${WORK_DIR}/rs_init_${set_id}.js" "replicaset_init" "${primary_ip}" "${primary_port}"
  run_atom "core-it-exec-extra-${set_id}" "mongo_execute_script" \
    "${WORK_DIR}/exec_extra_${set_id}.json" "node-${primary_port}"
  run_atom "core-it-exec-rsinit-${set_id}" "mongo_execute_script" \
    "${WORK_DIR}/exec_rs_init_${set_id}.json" "node-${primary_port}"
  wait_rs_healthy "${primary_ip}" "${primary_port}" "${#members[@]}" 1 "${set_id}"
}
