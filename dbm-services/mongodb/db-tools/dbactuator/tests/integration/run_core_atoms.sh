#!/usr/bin/env bash
# Local integration test: run every core MongoDB dbactuator atom job once.
#
# Scope (user-selected):
#   - Core deploy/RS/shard/user/upgrade/replace/deinstall jobs are required.
#   - Backup/PITR/dbmon/export jobs are explicitly skipped with reasons.
#   - Uses local MongoDB 4.4.30 media under /data/install.
#
# Usage:
#   sudo tests/integration/run_core_atoms.sh
#   sudo tests/integration/run_core_atoms.sh --preflight
#   sudo tests/integration/run_core_atoms.sh --cleanup-only
#   sudo tests/integration/run_core_atoms.sh --keep-on-failure
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib.sh
source "${SCRIPT_DIR}/lib.sh"
integration_lib_init

for arg in "$@"; do
  case "${arg}" in
    --preflight) PREFLIGHT_ONLY=1 ;;
    --cleanup-only) CLEANUP_ONLY=1 ;;
    --keep-on-failure) KEEP_ON_FAILURE=1 ;;
    -h|--help)
      sed -n '2,20p' "$0"
      exit 0
      ;;
    *)
      die "unknown argument: ${arg}"
      ;;
  esac
done

on_fail() {
  local code="$?"
  warn "integration failed (exit=${code})"
  collect_diagnostics || true
  if [[ "${KEEP_ON_FAILURE}" != "1" && "${CLEANUP_ONLY}" != "1" && "${PREFLIGHT_ONLY}" != "1" ]]; then
    cleanup_all_instances || true
  else
    warn "keeping instances; cleanup with: sudo $0 --cleanup-only (set TEST_RUN_DIR=${RUN_DIR})"
  fi
  restore_sysctl || true
  restore_profile_mongo_bin_dir || true
  exit "${code}"
}
on_exit() {
  # Always try to put /etc/profile back even on unexpected exits.
  restore_profile_mongo_bin_dir || true
}
trap on_fail ERR
trap on_exit EXIT

mkdir -p "${DATA_DIR}" "${BACKUP_DIR}" "${BIN_DIR}" "${WORK_DIR}" "${LOG_SNAPSHOT_DIR}"
: > "${COVERAGE_FILE}"
cat > "${STATE_FILE}" <<EOF
RUN_ID=${RUN_ID}
RUN_DIR=${RUN_DIR}
DATA_DIR=${DATA_DIR}
BACKUP_DIR=${BACKUP_DIR}
BIN_DIR=${BIN_DIR}
WORK_DIR=${WORK_DIR}
EOF

log "run_id=${RUN_ID}"
log "run_dir=${RUN_DIR}"

if ! preflight_checks; then
  die "preflight failed"
fi
if [[ "${PREFLIGHT_ONLY}" == "1" ]]; then
  log "preflight-only mode done"
  exit 0
fi

build_actuator
ensure_loopback_ips
adopt_profile_mongo_bin_dir

if [[ "${CLEANUP_ONLY}" == "1" ]]; then
  cleanup_all_instances
  collect_diagnostics
  restore_profile_mongo_bin_dir
  log "cleanup-only done"
  exit 0
fi

save_sysctl

# ---------------------------------------------------------------------------
# Phase 0: host prep + hello
# ---------------------------------------------------------------------------
run_os_init "node-os-init"
write_json "${WORK_DIR}/hello.json" "{\"ip\":\"${RS_IPS[0]}\",\"port\":${RS_PORTS[0]}}"
run_atom "core-it-hello" "mongodb_hello" "${WORK_DIR}/hello.json" "node-hello" "${OS_INIT_USER}"

# ---------------------------------------------------------------------------
# Phase 1: replica-set sandbox (3 members + spare)
# ---------------------------------------------------------------------------
log "phase1: deploy 3-node replica set"
install_rs_members "${RS_SET_ID}" "" \
  "${RS_IPS[0]}" "${RS_PORTS[0]}" \
  "${RS_IPS[1]}" "${RS_PORTS[1]}" \
  "${RS_IPS[2]}" "${RS_PORTS[2]}"

init_rs_and_users "${RS_SET_ID}" false \
  "${RS_IPS[0]}" "${RS_PORTS[0]}" \
  "${RS_IPS[0]}:${RS_PORTS[0]}" \
  "${RS_IPS[1]}:${RS_PORTS[1]}" \
  "${RS_IPS[2]}:${RS_PORTS[2]}"

log "phase1: delete_user / add_user round-trip"
build_add_user_payload "${RS_IPS[0]}" "${RS_PORTS[0]}" "${TEMP_USER}" "${TEMP_PASS}" \
  "${WORK_DIR}/add_temp_user.json" "${DBA_USER}" "${DBA_PASS}"
run_atom "core-it-add-temp" "add_user" "${WORK_DIR}/add_temp_user.json" "node-${RS_PORTS[0]}"
write_json "${WORK_DIR}/del_temp_user.json" \
  "{\"ip\":\"${RS_IPS[0]}\",\"port\":${RS_PORTS[0]},\"instanceType\":\"mongod\",\"adminUsername\":\"${DBA_USER}\",\"adminPassword\":\"${DBA_PASS}\",\"username\":\"${TEMP_USER}\",\"authDb\":\"admin\"}"
run_atom "core-it-del-temp" "delete_user" "${WORK_DIR}/del_temp_user.json" "node-${RS_PORTS[0]}"

log "phase1: replicaset_stepdown"
PRIMARY="$(current_primary "${RS_IPS[0]}" "${RS_PORTS[0]}")"
PRIMARY_IP="${PRIMARY%:*}"
PRIMARY_PORT="${PRIMARY##*:}"
write_json "${WORK_DIR}/stepdown.json" \
  "{\"ip\":\"${PRIMARY_IP}\",\"port\":${PRIMARY_PORT},\"targetIP\":\"${PRIMARY_IP}\",\"adminUsername\":\"${DBA_USER}\",\"adminPassword\":\"${DBA_PASS}\"}"
run_atom "core-it-stepdown" "replicaset_stepdown" "${WORK_DIR}/stepdown.json" "node-${PRIMARY_PORT}"
wait_rs_healthy "${RS_IPS[0]}" "${RS_PORTS[0]}" 3 1 "rs-after-stepdown"

log "phase1: mongod_node_hidden unhide then re-hide node3"
PRIMARY="$(current_primary "${RS_IPS[0]}" "${RS_PORTS[0]}")"
PRIMARY_IP="${PRIMARY%:*}"
PRIMARY_PORT="${PRIMARY##*:}"
write_json "${WORK_DIR}/hidden_off.json" \
  "{\"ip\":\"${PRIMARY_IP}\",\"port\":${PRIMARY_PORT},\"hiddenip\":\"${RS_IPS[2]}\",\"hiddenport\":${RS_PORTS[2]},\"hidden\":false,\"adminUsername\":\"${DBA_USER}\",\"adminPassword\":\"${DBA_PASS}\"}"
run_atom "core-it-hidden-off" "mongod_node_hidden" "${WORK_DIR}/hidden_off.json" "node-${PRIMARY_PORT}"
write_json "${WORK_DIR}/hidden_on.json" \
  "{\"ip\":\"${PRIMARY_IP}\",\"port\":${PRIMARY_PORT},\"hiddenip\":\"${RS_IPS[2]}\",\"hiddenport\":${RS_PORTS[2]},\"hidden\":true,\"adminUsername\":\"${DBA_USER}\",\"adminPassword\":\"${DBA_PASS}\"}"
run_atom "core-it-hidden-on" "mongod_node_hidden" "${WORK_DIR}/hidden_on.json" "node-${PRIMARY_PORT}"

# Idempotent same-version path: FCV major.minor derived from DB_VERSION (e.g. 7.0.28 -> 7.0).
FCV_MM="$(echo "${DB_VERSION}" | awk -F. '{print $1"."$2}')"
log "phase1: mongo_set_fcv / mongo_upgrade_rs_protocol / replace_package (idempotent on ${DB_VERSION}, fcv=${FCV_MM})"
PRIMARY="$(current_primary "${RS_IPS[0]}" "${RS_PORTS[0]}")"
PRIMARY_IP="${PRIMARY%:*}"
PRIMARY_PORT="${PRIMARY##*:}"
write_json "${WORK_DIR}/set_fcv.json" \
  "{\"ip\":\"${PRIMARY_IP}\",\"port\":${PRIMARY_PORT},\"old_fcv\":\"${FCV_MM}\",\"new_fcv\":\"${FCV_MM}\",\"instanceType\":\"mongod\",\"adminUsername\":\"${DBA_USER}\",\"adminPassword\":\"${DBA_PASS}\"}"
run_atom "core-it-set-fcv" "mongo_set_fcv" "${WORK_DIR}/set_fcv.json" "node-${PRIMARY_PORT}"
write_json "${WORK_DIR}/upgrade_protocol.json" \
  "{\"ip\":\"${PRIMARY_IP}\",\"port\":${PRIMARY_PORT},\"instanceType\":\"mongod\",\"adminUsername\":\"${DBA_USER}\",\"adminPassword\":\"${DBA_PASS}\",\"targetProtocolVersion\":1}"
run_atom "core-it-upgrade-protocol" "mongo_upgrade_rs_protocol" "${WORK_DIR}/upgrade_protocol.json" "node-${PRIMARY_PORT}"
write_json "${WORK_DIR}/replace_package.json" \
  "{\"mediapkg\":{\"pkg\":\"${PKG_NAME}\",\"pkg_md5\":\"${PKG_MD5}\"},\"ip\":\"${RS_IPS[1]}\",\"port\":${RS_PORTS[1]},\"currentVersion\":\"${DB_VERSION}\",\"destVersion\":\"${DB_VERSION}\",\"instanceType\":\"mongod\"}"
run_atom "core-it-replace-pkg" "replace_package" "${WORK_DIR}/replace_package.json" "node-${RS_PORTS[1]}"

# Prefer a non-primary (hidden member) so graceful stop does not race stepDown freeze
# after the earlier replicaset_stepdown (only one other electable member may still be frozen).
log "phase1: mongodb_instance_op stop/start on hidden secondary + mongo_start + mongo_restart"
OP_IP="${RS_IPS[2]}"
OP_PORT="${RS_PORTS[2]}"
PRIMARY="$(current_primary "${RS_IPS[0]}" "${RS_PORTS[0]}")"
if [[ "${PRIMARY}" == "${OP_IP}:${OP_PORT}" ]]; then
  OP_IP="${RS_IPS[1]}"
  OP_PORT="${RS_PORTS[1]}"
fi
write_json "${WORK_DIR}/inst_stop.json" \
  "{\"ip\":\"${OP_IP}\",\"port\":${OP_PORT},\"adminUsername\":\"${DBA_USER}\",\"adminPassword\":\"${DBA_PASS}\",\"op\":\"stop\",\"gracefulStop\":true}"
run_atom "core-it-inst-stop" "mongodb_instance_op" "${WORK_DIR}/inst_stop.json" "node-${OP_PORT}" "${OS_INIT_USER}"
wait_port_stopped "${OP_PORT}"
write_json "${WORK_DIR}/mongo_start.json" \
  "{\"ip\":\"${OP_IP}\",\"port\":${OP_PORT},\"instanceType\":\"mongod\",\"auth\":true}"
run_atom "core-it-mongo-start" "mongo_start" "${WORK_DIR}/mongo_start.json" "node-${OP_PORT}"
wait_port_listen "${OP_PORT}"
wait_rs_healthy "${RS_IPS[0]}" "${RS_PORTS[0]}" 3 1 "rs-after-start"

write_json "${WORK_DIR}/mongo_restart.json" \
  "{\"ip\":\"${OP_IP}\",\"port\":${OP_PORT},\"instanceType\":\"mongod\",\"auth\":true,\"cacheSizeGB\":0,\"mongoSConfDbOld\":\"\",\"mongoSConfDbNew\":\"\",\"adminUsername\":\"${DBA_USER}\",\"adminPassword\":\"${DBA_PASS}\",\"onlyChangeParam\":false}"
run_atom "core-it-mongo-restart" "mongo_restart" "${WORK_DIR}/mongo_restart.json" "node-${OP_PORT}"
wait_rs_healthy "${RS_IPS[0]}" "${RS_PORTS[0]}" 3 1 "rs-after-restart"

log "phase1: mongod_replace hidden node3 -> spare node4, then deferred_deinstall node3"
build_mongod_install_payload "${RS_IPS[3]}" "${RS_PORTS[3]}" "${RS_SET_ID}" "" \
  "${WORK_DIR}/mongod_install_${RS_PORTS[3]}.json"
run_atom "core-it-install-${RS_PORTS[3]}" "mongod_install" \
  "${WORK_DIR}/mongod_install_${RS_PORTS[3]}.json" "node-${RS_PORTS[3]}"
PRIMARY="$(current_primary "${RS_IPS[0]}" "${RS_PORTS[0]}")"
PRIMARY_IP="${PRIMARY%:*}"
PRIMARY_PORT="${PRIMARY##*:}"
write_json "${WORK_DIR}/mongod_replace.json" \
  "{\"ip\":\"${PRIMARY_IP}\",\"port\":${PRIMARY_PORT},\"sourceIP\":\"${RS_IPS[2]}\",\"sourcePort\":${RS_PORTS[2]},\"sourceDown\":false,\"adminUsername\":\"${DBA_USER}\",\"adminPassword\":\"${DBA_PASS}\",\"targetIP\":\"${RS_IPS[3]}\",\"targetPort\":${RS_PORTS[3]},\"targetPriority\":\"\",\"targetHidden\":\"\"}"
run_atom "core-it-replace" "mongod_replace" "${WORK_DIR}/mongod_replace.json" "node-${PRIMARY_PORT}"
wait_rs_healthy "${PRIMARY_IP}" "${PRIMARY_PORT}" 3 1 "rs-after-replace"

write_json "${WORK_DIR}/deferred_deinstall.json" \
  "{\"ip\":\"${RS_IPS[2]}\",\"port\":${RS_PORTS[2]},\"setId\":\"${RS_SET_ID}\",\"nodeInfo\":[\"${RS_IPS[0]}\",\"${RS_IPS[1]}\",\"${RS_IPS[2]}\",\"${RS_IPS[3]}\"],\"replicaSetPeers\":[\"${RS_IPS[0]}:${RS_PORTS[0]}\",\"${RS_IPS[1]}:${RS_PORTS[1]}\",\"${RS_IPS[3]}:${RS_PORTS[3]}\"],\"removedCheckAttempts\":30,\"removedCheckIntervalSec\":2,\"instanceType\":\"mongod\",\"renameDir\":true,\"adminUsername\":\"${DBA_USER}\",\"adminPassword\":\"${DBA_PASS}\"}"
run_atom "core-it-deferred-deinstall" "mongo_deferred_deinstall" \
  "${WORK_DIR}/deferred_deinstall.json" "node-${RS_PORTS[2]}"

# ---------------------------------------------------------------------------
# Phase 2: sharded sandbox (cfg x3 + shard1 x3 + shard2 x3 + mongos)
# ---------------------------------------------------------------------------
log "phase2: deploy configsvr RS"
install_rs_members "${CFG_SET_ID}" "configsvr" \
  "${CFG_IPS[0]}" "${CFG_PORTS[0]}" \
  "${CFG_IPS[1]}" "${CFG_PORTS[1]}" \
  "${CFG_IPS[2]}" "${CFG_PORTS[2]}"
init_rs_and_users "${CFG_SET_ID}" true \
  "${CFG_IPS[0]}" "${CFG_PORTS[0]}" \
  "${CFG_IPS[0]}:${CFG_PORTS[0]}" \
  "${CFG_IPS[1]}:${CFG_PORTS[1]}" \
  "${CFG_IPS[2]}:${CFG_PORTS[2]}"

log "phase2: deploy shard1 RS"
install_rs_members "${SHARD1_SET_ID}" "shardsvr" \
  "${SHARD1_IPS[0]}" "${SHARD1_PORTS[0]}" \
  "${SHARD1_IPS[1]}" "${SHARD1_PORTS[1]}" \
  "${SHARD1_IPS[2]}" "${SHARD1_PORTS[2]}"
init_rs_and_users "${SHARD1_SET_ID}" false \
  "${SHARD1_IPS[0]}" "${SHARD1_PORTS[0]}" \
  "${SHARD1_IPS[0]}:${SHARD1_PORTS[0]}" \
  "${SHARD1_IPS[1]}:${SHARD1_PORTS[1]}" \
  "${SHARD1_IPS[2]}:${SHARD1_PORTS[2]}"

log "phase2: deploy shard2 RS"
install_rs_members "${SHARD2_SET_ID}" "shardsvr" \
  "${SHARD2_IPS[0]}" "${SHARD2_PORTS[0]}" \
  "${SHARD2_IPS[1]}" "${SHARD2_PORTS[1]}" \
  "${SHARD2_IPS[2]}" "${SHARD2_PORTS[2]}"
init_rs_and_users "${SHARD2_SET_ID}" false \
  "${SHARD2_IPS[0]}" "${SHARD2_PORTS[0]}" \
  "${SHARD2_IPS[0]}:${SHARD2_PORTS[0]}" \
  "${SHARD2_IPS[1]}:${SHARD2_PORTS[1]}" \
  "${SHARD2_IPS[2]}:${SHARD2_PORTS[2]}"

log "phase2: install mongos"
write_json "${WORK_DIR}/mongos_install.json" \
  "{\"mediapkg\":{\"pkg\":\"${PKG_NAME}\",\"pkg_md5\":\"${PKG_MD5}\"},\"ip\":\"${MONGOS_IP}\",\"port\":${MONGOS_PORT},\"dbVersion\":\"${DB_VERSION}\",\"instanceType\":\"mongos\",\"setId\":\"${CFG_SET_ID}\",\"keyFile\":\"${KEY_FILE}\",\"auth\":true,\"configDB\":[\"${CFG_IPS[0]}:${CFG_PORTS[0]}\",\"${CFG_IPS[1]}:${CFG_PORTS[1]}\",\"${CFG_IPS[2]}:${CFG_PORTS[2]}\"],\"dbConfig\":{\"slowOpThresholdMs\":200,\"destination\":\"file\"}}"
run_atom "core-it-mongos-install" "mongos_install" "${WORK_DIR}/mongos_install.json" "node-mongos"
wait_port_listen "${MONGOS_PORT}"

log "phase2: add both shards"
write_json "${WORK_DIR}/add_shard1.json" \
  "{\"ip\":\"${MONGOS_IP}\",\"port\":${MONGOS_PORT},\"adminUsername\":\"${DBA_USER}\",\"adminPassword\":\"${DBA_PASS}\",\"shards\":{\"${SHARD1_SET_ID}\":\"${SHARD1_IPS[0]}:${SHARD1_PORTS[0]},${SHARD1_IPS[1]}:${SHARD1_PORTS[1]}\"}}"
write_json "${WORK_DIR}/add_shard2.json" \
  "{\"ip\":\"${MONGOS_IP}\",\"port\":${MONGOS_PORT},\"adminUsername\":\"${DBA_USER}\",\"adminPassword\":\"${DBA_PASS}\",\"shards\":{\"${SHARD2_SET_ID}\":\"${SHARD2_IPS[0]}:${SHARD2_PORTS[0]},${SHARD2_IPS[1]}:${SHARD2_PORTS[1]}\"}}"
run_atom "core-it-add-shard1" "add_shard_to_cluster" "${WORK_DIR}/add_shard1.json" "node-mongos"
run_atom "core-it-add-shard2" "add_shard_to_cluster" "${WORK_DIR}/add_shard2.json" "node-mongos"
shard_count="$(mongo_eval "${MONGOS_IP}" "${MONGOS_PORT}" "db.getSiblingDB('config').shards.countDocuments({})" --auth | tr -d '[:space:]')"
[[ "${shard_count}" == "2" ]] || die "expected 2 shards, got ${shard_count}"

log "phase2: cluster_balancer open/close"
write_json "${WORK_DIR}/balancer_on.json" \
  "{\"ip\":\"${MONGOS_IP}\",\"port\":${MONGOS_PORT},\"open\":true,\"waitForBalance\":false,\"adminUsername\":\"${DBA_USER}\",\"adminPassword\":\"${DBA_PASS}\"}"
write_json "${WORK_DIR}/balancer_off.json" \
  "{\"ip\":\"${MONGOS_IP}\",\"port\":${MONGOS_PORT},\"open\":false,\"adminUsername\":\"${DBA_USER}\",\"adminPassword\":\"${DBA_PASS}\"}"
run_atom "core-it-balancer-on" "cluster_balancer" "${WORK_DIR}/balancer_on.json" "node-mongos"
run_atom "core-it-balancer-off" "cluster_balancer" "${WORK_DIR}/balancer_off.json" "node-mongos"

log "phase2: seed tiny collection then remove empty shard2"
mongo_eval "${MONGOS_IP}" "${MONGOS_PORT}" \
  "db.getSiblingDB('itdb').demo.insertOne({x:1}); db.getSiblingDB('itdb').demo.countDocuments({})" --auth >/dev/null
write_json "${WORK_DIR}/remove_shard2.json" \
  "{\"ip\":\"${MONGOS_IP}\",\"port\":${MONGOS_PORT},\"adminUsername\":\"${DBA_USER}\",\"adminPassword\":\"${DBA_PASS}\",\"shards\":[\"${SHARD2_SET_ID}\"],\"dbVersion\":\"${DB_VERSION}\",\"maxWaitSec\":600,\"pollSec\":5}"
run_atom "core-it-remove-shard2" "remove_shard_from_cluster" "${WORK_DIR}/remove_shard2.json" "node-mongos"
shard_count="$(mongo_eval "${MONGOS_IP}" "${MONGOS_PORT}" "db.getSiblingDB('config').shards.countDocuments({})" --auth | tr -d '[:space:]')"
[[ "${shard_count}" == "1" ]] || die "expected 1 shard after remove, got ${shard_count}"

# ---------------------------------------------------------------------------
# Phase 3: teardown + coverage
# ---------------------------------------------------------------------------
log "phase3: deinstall remaining instances"
for i in 0 1 3; do
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

for entry in "${CORE_SKIP_JOBS[@]}"; do
  mark_skipped "${entry%%|*}" "${entry#*|}"
done
verify_coverage
collect_diagnostics
restore_sysctl
restore_profile_mongo_bin_dir

log "CORE ATOM INTEGRATION PASSED"
log "coverage: ${COVERAGE_FILE}"
log "logs: ${LOG_SNAPSHOT_DIR}"
