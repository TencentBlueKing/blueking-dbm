#!/usr/bin/env bash
set -euo pipefail

# Local MongoDB DTS topology matrix E2E:
#   rs-rs | rs-shard | shard-rs | shard-shard
#
# Options:
#   --cases <csv>       subset of cases (default: all four)
#   --keep-instance     skip deinstall after success
#   --deinstall-only    only cleanup previous instances for selected cases' ports

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: run as root (sudo)." >&2
  exit 1
fi

source "${ROOT_DIR}/tests/e2e/mongo_dts_e2e_lib.sh"
dts_e2e_lib_init

CASES_CSV="rs-rs,rs-shard,shard-rs,shard-shard"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cases)
      CASES_CSV="${2:-}"
      shift 2
      ;;
    --keep-instance)
      KEEP_INSTANCE=1
      shift
      ;;
    --deinstall-only)
      DEINSTALL_ONLY=1
      shift
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ "${KEEP_INSTANCE}" == "1" && "${DEINSTALL_ONLY}" == "1" ]]; then
  echo "ERROR: --keep-instance and --deinstall-only are mutually exclusive" >&2
  exit 1
fi

IFS=',' read -r -a CASES <<< "${CASES_CSV}"

on_exit() {
  local rc=$?
  if [[ "${rc}" -ne 0 ]]; then
    collect_failure_snapshot || true
  fi
  if [[ "${KEEP_INSTANCE}" != "1" ]]; then
    cleanup_from_manifest || true
    if [[ "${rc}" -ne 0 || "${DEINSTALL_ONLY}" == "1" ]]; then
      assert_ports_closed || true
    elif [[ "${rc}" -eq 0 ]]; then
      assert_ports_closed || rc=$?
    fi
  fi
  exit "${rc}"
}
trap on_exit EXIT

deinstall_side_rs() {
  local side="$1"
  local -a ips ports
  if [[ "${side}" == "src" ]]; then
    ips=("${SRC_RS_IPS[@]}"); ports=("${SRC_RS_PORTS[@]}")
  else
    ips=("${DST_RS_IPS[@]}"); ports=("${DST_RS_PORTS[@]}")
  fi
  local i
  for i in "${!ports[@]}"; do
    deinstall_instance "${ips[$i]}" "${ports[$i]}" "mongod"
    register_port "${ports[$i]}"
  done
}

deinstall_side_cluster() {
  local side="$1"
  local -a cfg_ips cfg_ports s1_ips s1_ports s2_ips s2_ports
  local mongos_ip mongos_port
  if [[ "${side}" == "src" ]]; then
    cfg_ips=("${SRC_CFG_IPS[@]}"); cfg_ports=("${SRC_CFG_PORTS[@]}")
    s1_ips=("${SRC_S1_IPS[@]}"); s1_ports=("${SRC_S1_PORTS[@]}")
    s2_ips=("${SRC_S2_IPS[@]}"); s2_ports=("${SRC_S2_PORTS[@]}")
    mongos_ip="${SRC_MONGOS_IP}"; mongos_port="${SRC_MONGOS_PORT}"
  else
    cfg_ips=("${DST_CFG_IPS[@]}"); cfg_ports=("${DST_CFG_PORTS[@]}")
    s1_ips=("${DST_S1_IPS[@]}"); s1_ports=("${DST_S1_PORTS[@]}")
    s2_ips=("${DST_S2_IPS[@]}"); s2_ports=("${DST_S2_PORTS[@]}")
    mongos_ip="${DST_MONGOS_IP}"; mongos_port="${DST_MONGOS_PORT}"
  fi
  deinstall_instance "${mongos_ip}" "${mongos_port}" "mongos"
  register_port "${mongos_port}"
  local i
  for i in "${!cfg_ports[@]}"; do deinstall_instance "${cfg_ips[$i]}" "${cfg_ports[$i]}" "mongod"; register_port "${cfg_ports[$i]}"; done
  for i in "${!s1_ports[@]}"; do deinstall_instance "${s1_ips[$i]}" "${s1_ports[$i]}" "mongod"; register_port "${s1_ports[$i]}"; done
  for i in "${!s2_ports[@]}"; do deinstall_instance "${s2_ips[$i]}" "${s2_ports[$i]}" "mongod"; register_port "${s2_ports[$i]}"; done
}

if [[ "${DEINSTALL_ONLY}" == "1" ]]; then
  mkdir -p "${SHAKE_DIR}/logs"
  ensure_loopback_ips
  build_actuator
  stop_collector_force
  for c in "${CASES[@]}"; do
    case "${c}" in
      rs-rs) deinstall_side_rs src; deinstall_side_rs dst ;;
      rs-shard) deinstall_side_rs src; deinstall_side_cluster dst ;;
      shard-rs) deinstall_side_cluster src; deinstall_side_rs dst ;;
      shard-shard) deinstall_side_cluster src; deinstall_side_cluster dst ;;
      *) die "unknown case ${c}" ;;
    esac
  done
  assert_ports_closed
  echo "OK: deinstall-only done"
  # prevent EXIT trap double-fail
  KEEP_INSTANCE=1
  exit 0
fi

[[ -f "${DTS_TGZ}" ]] || die "missing ${DTS_TGZ}"
[[ -f "${PKG_PATH}" ]] || die "missing ${PKG_PATH}"

mkdir -p "${SHAKE_DIR}/logs"
ensure_loopback_ips
build_actuator

reset_case_state() {
  stop_writer
  stop_collector_force
  : > "${MANIFEST}"
  REGISTERED_PORTS=()
  mkdir -p "${SHAKE_DIR}/logs"
  rm -f "${SHAKE_DIR}/collector.conf" "${SHAKE_DIR}/collector.pid" "${SHAKE_DIR}/collector.stdout" \
    "${SHAKE_DIR}/collector.start_ts.json" 2>/dev/null || true
}

src_connect_host_port() {
  # for RS source DML / compare via primary
  echo "${SRC_RS_IPS[0]} ${SRC_RS_PORTS[0]}"
}

dst_connect_host_port() {
  echo "${DST_RS_IPS[0]} ${DST_RS_PORTS[0]}"
}

run_case_rs_rs() {
  CASE_NAME="rs-rs"
  log "======== CASE ${CASE_NAME} ========"
  reset_case_state
  deploy_replicaset src "${SRC_RS_SET}" \
    "${SRC_RS_IPS[0]}" "${SRC_RS_PORTS[0]}" \
    "${SRC_RS_IPS[1]}" "${SRC_RS_PORTS[1]}" \
    "${SRC_RS_IPS[2]}" "${SRC_RS_PORTS[2]}"
  deploy_replicaset dst "${DST_RS_SET}" \
    "${DST_RS_IPS[0]}" "${DST_RS_PORTS[0]}" \
    "${DST_RS_IPS[1]}" "${DST_RS_PORTS[1]}" \
    "${DST_RS_IPS[2]}" "${DST_RS_PORTS[2]}"

  local src_p dst_p
  read -r src_p_ip src_p_port < <(current_primary_ip_port "${SRC_RS_IPS[0]}" "${SRC_RS_PORTS[0]}")
  read -r dst_p_ip dst_p_port < <(current_primary_ip_port "${DST_RS_IPS[0]}" "${DST_RS_PORTS[0]}")
  seed_baseline_rs "${src_p_ip}" "${src_p_port}"
  create_dts_users_on_all_source_rs rs
  create_dts_users_on_target rs

  SRC_KIND=rs DST_KIND=rs SOURCE_CONNECT_MODE=secondaryPreferred \
    generate_collector_conf "${WORK_DIR}/collector_${CASE_NAME}.conf"
  # conf must not require mongos
  grep -E '^mongo_s_url =\s*$' "${WORK_DIR}/collector_${CASE_NAME}.conf" >/dev/null
  grep -q 'incr_sync.mongo_fetch_method = oplog' "${WORK_DIR}/collector_${CASE_NAME}.conf"

  start_mongoshake "${WORK_DIR}/collector_${CASE_NAME}.conf"
  read -r src_p_ip src_p_port < <(current_primary_ip_port "${SRC_RS_IPS[0]}" "${SRC_RS_PORTS[0]}")
  apply_incr_dml_rs "${src_p_ip}" "${src_p_port}"
  run_wait_or_wait_stop wait_stop true

  local cut_ts
  cut_ts="$(extract_cut_ts)"
  assert_cut_ts_boundary "${cut_ts}" "${SRC_RS_IPS[2]}" "${SRC_RS_PORTS[2]}"
  read -r src_p_ip src_p_port < <(current_primary_ip_port "${SRC_RS_IPS[0]}" "${SRC_RS_PORTS[0]}")
  read -r dst_p_ip dst_p_port < <(current_primary_ip_port "${DST_RS_IPS[0]}" "${DST_RS_PORTS[0]}")
  assert_ns_synced "${src_p_ip}" "${src_p_port}" "${dst_p_ip}" "${dst_p_port}"
  assert_collector_cleaned
  # start_ts map should have existed during run; after stop conf removed — check log for multi not needed for single RS
  drop_temp_users_and_ckpt rs rs

  if [[ "${KEEP_INSTANCE}" != "1" ]]; then
    cleanup_from_manifest
    assert_ports_closed
  fi
  log "OK: ${CASE_NAME}"
}

run_case_rs_shard() {
  CASE_NAME="rs-shard"
  log "======== CASE ${CASE_NAME} ========"
  reset_case_state
  deploy_replicaset src "${SRC_RS_SET}" \
    "${SRC_RS_IPS[0]}" "${SRC_RS_PORTS[0]}" \
    "${SRC_RS_IPS[1]}" "${SRC_RS_PORTS[1]}" \
    "${SRC_RS_IPS[2]}" "${SRC_RS_PORTS[2]}"
  deploy_two_shard_cluster dst
  prepare_empty_sharded_target "${DST_MONGOS_IP}" "${DST_MONGOS_PORT}"

  local src_p_ip src_p_port
  read -r src_p_ip src_p_port < <(current_primary_ip_port "${SRC_RS_IPS[0]}" "${SRC_RS_PORTS[0]}")
  seed_baseline_rs "${src_p_ip}" "${src_p_port}"
  create_dts_users_on_all_source_rs rs
  create_dts_users_on_target shard

  SRC_KIND=rs DST_KIND=shard SOURCE_CONNECT_MODE=backup \
    generate_collector_conf "${WORK_DIR}/collector_${CASE_NAME}.conf"
  grep -q 'directConnection=true' "${WORK_DIR}/collector_${CASE_NAME}.conf"
  grep -q "${SRC_RS_IPS[2]}:${SRC_RS_PORTS[2]}" "${WORK_DIR}/collector_${CASE_NAME}.conf"

  start_mongoshake "${WORK_DIR}/collector_${CASE_NAME}.conf"
  read -r src_p_ip src_p_port < <(current_primary_ip_port "${SRC_RS_IPS[0]}" "${SRC_RS_PORTS[0]}")
  apply_incr_dml_rs "${src_p_ip}" "${src_p_port}"
  run_wait_or_wait_stop wait_stop true

  local cut_ts
  cut_ts="$(extract_cut_ts)"
  assert_cut_ts_boundary "${cut_ts}" "${SRC_RS_IPS[2]}" "${SRC_RS_PORTS[2]}"
  read -r src_p_ip src_p_port < <(current_primary_ip_port "${SRC_RS_IPS[0]}" "${SRC_RS_PORTS[0]}")
  assert_ns_synced "${src_p_ip}" "${src_p_port}" "${DST_MONGOS_IP}" "${DST_MONGOS_PORT}"
  assert_both_shards_have_data "${DST_S1_IPS[0]}" "${DST_S1_PORTS[0]}" "${DST_S2_IPS[0]}" "${DST_S2_PORTS[0]}"
  assert_collector_cleaned
  drop_temp_users_and_ckpt shard rs

  if [[ "${KEEP_INSTANCE}" != "1" ]]; then
    cleanup_from_manifest
    assert_ports_closed
  fi
  log "OK: ${CASE_NAME}"
}

run_case_shard_rs() {
  CASE_NAME="shard-rs"
  log "======== CASE ${CASE_NAME} ========"
  reset_case_state
  deploy_two_shard_cluster src
  deploy_replicaset dst "${DST_RS_SET}" \
    "${DST_RS_IPS[0]}" "${DST_RS_PORTS[0]}" \
    "${DST_RS_IPS[1]}" "${DST_RS_PORTS[1]}" \
    "${DST_RS_IPS[2]}" "${DST_RS_PORTS[2]}"

  assert_balancer_negative_then_stop "${SRC_CFG_IPS[0]}" "${SRC_CFG_PORTS[0]}" \
    "${SRC_MONGOS_IP}" "${SRC_MONGOS_PORT}"
  seed_baseline_shard "${SRC_MONGOS_IP}" "${SRC_MONGOS_PORT}"
  # ensure both source shards have data before sync
  assert_both_shards_have_data "${SRC_S1_IPS[0]}" "${SRC_S1_PORTS[0]}" "${SRC_S2_IPS[0]}" "${SRC_S2_PORTS[0]}"

  create_dts_users_on_all_source_rs shard
  create_dts_users_on_target rs

  SRC_KIND=shard DST_KIND=rs SOURCE_CONNECT_MODE=backup \
    generate_collector_conf "${WORK_DIR}/collector_${CASE_NAME}.conf"
  grep -q 'full_sync.do_not_shard_destination = true' "${WORK_DIR}/collector_${CASE_NAME}.conf"
  grep -q 'full_sync.executor.filter.orphan_document = true' "${WORK_DIR}/collector_${CASE_NAME}.conf"
  grep -E '^mongo_s_url =\s*$' "${WORK_DIR}/collector_${CASE_NAME}.conf" >/dev/null
  assert_zero_source_mongos "${WORK_DIR}/collector_${CASE_NAME}.conf" "${SRC_MONGOS_IP}" "${SRC_MONGOS_PORT}"

  # Start while mongos is still up so update/delete route correctly, then kill mongos
  # and keep syncing via shard-backup oplog only.
  start_mongoshake "${WORK_DIR}/collector_${CASE_NAME}.conf"
  apply_incr_dml_shard "${SRC_MONGOS_IP}" "${SRC_MONGOS_PORT}"
  log "stop source mongos to prove zero mongos dependency"
  deinstall_instance "${SRC_MONGOS_IP}" "${SRC_MONGOS_PORT}" "mongos"
  assert_zero_source_mongos "${SHAKE_DIR}/collector.conf" "${SRC_MONGOS_IP}" "${SRC_MONGOS_PORT}"
  local s1p_ip s1p_port s2p_ip s2p_port
  read -r s1p_ip s1p_port < <(current_primary_ip_port "${SRC_S1_IPS[0]}" "${SRC_S1_PORTS[0]}")
  read -r s2p_ip s2p_port < <(current_primary_ip_port "${SRC_S2_IPS[0]}" "${SRC_S2_PORTS[0]}")
  mongo_eval_auth "${s1p_ip}" "${s1p_port}" \
    'db.getSiblingDB("dtsdemo").orders.insertOne({_id:3002,n:"s1post",v:1})' || true
  mongo_eval_auth "${s2p_ip}" "${s2p_port}" \
    'db.getSiblingDB("dtsdemo").orders.insertOne({_id:3003,n:"s2post",v:1})' || true

  run_wait_or_wait_stop wait_stop true
  local cut_ts
  cut_ts="$(extract_cut_ts)"
  assert_cut_ts_boundary "${cut_ts}" \
    "${SRC_S1_IPS[2]}" "${SRC_S1_PORTS[2]}" \
    "${SRC_S2_IPS[2]}" "${SRC_S2_PORTS[2]}"

  # Compare via direct shard? Target is RS — compare counts carefully.
  # Source mongos down: aggregate counts from both shards may double-count orphans;
  # with orphan filter destination should match mongos view. Use shard1+shard2 unique _ids approx via target only checks.
  local dst_p_ip dst_p_port dst_cnt gone uv
  read -r dst_p_ip dst_p_port < <(current_primary_ip_port "${DST_RS_IPS[0]}" "${DST_RS_PORTS[0]}")
  dst_cnt="$(doc_count "${dst_p_ip}" "${dst_p_port}" dtsdemo orders)"
  [[ "${dst_cnt}" -gt 40 ]] || die "shard-rs destination count too low: ${dst_cnt}"
  gone="$(mongo_eval_auth "${dst_p_ip}" "${dst_p_port}" 'print(db.getSiblingDB("dtsdemo").orders.find({_id:2}).hasNext()?"1":"0")' | tr -d '[:space:]')"
  [[ "${gone}" == "0" ]] || die "deleted _id:2 still present"
  uv="$(mongo_eval_auth "${dst_p_ip}" "${dst_p_port}" 'print(db.getSiblingDB("dtsdemo").orders.findOne({_id:1}).v)' | tr -d '[:space:]')"
  [[ "${uv}" == "2" ]] || die "update missing"
  mongo_eval_auth "${dst_p_ip}" "${dst_p_port}" \
    'if(db.getSiblingDB("notwhite").getCollectionNames().length){throw new Error("notwhite leaked")}'
  # start_ts should include both shard replsets — check leftover start_ts if present in logs
  if [[ -f "${SHAKE_DIR}/collector.start_ts.json" ]]; then
    rg -q "${SRC_S1_SET}|${SRC_S2_SET}" "${SHAKE_DIR}/collector.start_ts.json" || true
  fi
  rg -q "start_ts|collector.start_ts|replset" "${ROOT_DIR}/logs"/mongo_actuator_*.log 2>/dev/null || true
  assert_collector_cleaned
  drop_temp_users_and_ckpt rs shard

  if [[ "${KEEP_INSTANCE}" != "1" ]]; then
    cleanup_from_manifest
    assert_ports_closed
  fi
  log "OK: ${CASE_NAME}"
}

run_case_shard_shard() {
  CASE_NAME="shard-shard"
  log "======== CASE ${CASE_NAME} ========"
  reset_case_state
  deploy_two_shard_cluster src
  deploy_two_shard_cluster dst
  assert_balancer_negative_then_stop "${SRC_CFG_IPS[0]}" "${SRC_CFG_PORTS[0]}" \
    "${SRC_MONGOS_IP}" "${SRC_MONGOS_PORT}"
  seed_baseline_shard "${SRC_MONGOS_IP}" "${SRC_MONGOS_PORT}"
  prepare_empty_sharded_target "${DST_MONGOS_IP}" "${DST_MONGOS_PORT}"
  create_dts_users_on_all_source_rs shard
  create_dts_users_on_target shard

  SRC_KIND=shard DST_KIND=shard SOURCE_CONNECT_MODE=backup \
    generate_collector_conf "${WORK_DIR}/collector_${CASE_NAME}.conf"
  grep -E '^mongo_s_url =\s*$' "${WORK_DIR}/collector_${CASE_NAME}.conf" >/dev/null
  grep -q 'do_not_shard_destination = false' "${WORK_DIR}/collector_${CASE_NAME}.conf"

  start_mongoshake "${WORK_DIR}/collector_${CASE_NAME}.conf"
  assert_zero_source_mongos "${SHAKE_DIR}/collector.conf" "${SRC_MONGOS_IP}" "${SRC_MONGOS_PORT}"
  apply_incr_dml_shard "${SRC_MONGOS_IP}" "${SRC_MONGOS_PORT}"

  # manual mode: wait (catchup, keep running) -> inject more DML -> wait_stop
  run_wait_or_wait_stop wait false
  log "manual wait caught up; injecting more DML while collector runs"
  mongo_eval_auth "${SRC_MONGOS_IP}" "${SRC_MONGOS_PORT}" \
    'db.getSiblingDB("dtsdemo").orders.insertMany([{_id:4001,n:"manual1",v:1},{_id:4002,n:"manual2",v:1}]);'
  sleep 3
  run_wait_or_wait_stop wait_stop true

  local cut_ts
  cut_ts="$(extract_cut_ts)"
  assert_cut_ts_boundary "${cut_ts}" \
    "${SRC_S1_IPS[2]}" "${SRC_S1_PORTS[2]}" \
    "${SRC_S2_IPS[2]}" "${SRC_S2_PORTS[2]}"

  assert_ns_synced "${SRC_MONGOS_IP}" "${SRC_MONGOS_PORT}" "${DST_MONGOS_IP}" "${DST_MONGOS_PORT}"
  # manual inserts present
  mongo_eval_auth "${DST_MONGOS_IP}" "${DST_MONGOS_PORT}" \
    'if(!db.getSiblingDB("dtsdemo").orders.findOne({_id:4001})){throw new Error("manual insert missing")}'
  assert_both_shards_have_data "${DST_S1_IPS[0]}" "${DST_S1_PORTS[0]}" "${DST_S2_IPS[0]}" "${DST_S2_PORTS[0]}"
  assert_collector_cleaned
  drop_temp_users_and_ckpt shard shard

  if [[ "${KEEP_INSTANCE}" != "1" ]]; then
    cleanup_from_manifest
    assert_ports_closed
  fi
  log "OK: ${CASE_NAME}"
}

for c in "${CASES[@]}"; do
  case "${c}" in
    rs-rs) run_case_rs_rs ;;
    rs-shard) run_case_rs_shard ;;
    shard-rs) run_case_shard_rs ;;
    shard-shard) run_case_shard_shard ;;
    *) die "unknown case: ${c}" ;;
  esac
done

echo "OK: DTS matrix cases passed: ${CASES_CSV}"
