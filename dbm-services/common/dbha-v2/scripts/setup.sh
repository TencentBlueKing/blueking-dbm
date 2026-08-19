#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")" || exit 1

ETC_DIR="./etc"
VERSION="__VERSION__"
COMMON_DONE=0
PROBE_INSTALL_DIR_DEFAULT="/usr/local/dbha-v2"

#---------------------------------------------------------------
# Helpers
#---------------------------------------------------------------
prompt() {
    local var_name="$1" prompt_msg="$2" default="$3"
    local input
    read -rp "  ${prompt_msg} [${default}]: " input
    printf -v "${var_name}" '%s' "${input:-$default}"
}

prompt_secret() {
    local var_name="$1" prompt_msg="$2" default="$3"
    local input
    read -rsp "  ${prompt_msg} [${default}]: " input
    echo
    printf -v "${var_name}" '%s' "${input:-$default}"
}

section() {
    echo ""
    echo "========================================"
    echo "  $1"
    echo "========================================"
}

validate_probe_install_dir() {
    local dir="$1"
    if [[ "${dir}" == *".."* ]]; then
        echo "  invalid probe install directory, errmsg: path traversal" >&2
        return 1
    fi
    if [[ ! "${dir}" =~ ^(/|~|\.) ]]; then
        echo "  invalid probe install directory, errmsg: invalid prefix" >&2
        return 1
    fi
    if [[ ! "${dir}" =~ ^[A-Za-z0-9_./~-]+$ ]]; then
        echo "  invalid probe install directory, errmsg: invalid character" >&2
        return 1
    fi
    return 0
}

prompt_probe_install_dir() {
    while true; do
        prompt PROBE_INSTALL_DIR "Probe install directory" \
            "${PROBE_INSTALL_DIR:-${PROBE_INSTALL_DIR_DEFAULT}}"
        if validate_probe_install_dir "${PROBE_INSTALL_DIR}"; then
            break
        fi
        echo "  please enter a valid probe install directory." >&2
    done
}

show_menu() {
    echo ""
    echo "┌──────────────────────────────────┐"
    echo "│       DBHA v2 Setup Wizard       │"
    echo "├──────────────────────────────────┤"
    echo "│  1) Setup all services           │"
    echo "│  2) Setup admin                  │"
    echo "│  3) Setup receiver               │"
    echo "│  4) Setup analysis               │"
    echo "│  5) Setup probe                  │"
    echo "│  6) Reconfigure common settings  │"
    echo "│  0) Exit                         │"
    echo "└──────────────────────────────────┘"
    echo ""
}

#---------------------------------------------------------------
# Collect functions
#---------------------------------------------------------------
collect_common() {
    section "Common Settings"
    prompt VERSION        "Version" \
        "${VERSION}"
    prompt LOCAL_IP       "Local IP address" \
        "${LOCAL_IP:-127.0.0.1}"
    prompt LOG_LEVEL      "Log level (debug/info/warn/error)" \
        "${LOG_LEVEL:-info}"
    prompt LOG_FILE_COUNT "Log file count" \
        "${LOG_FILE_COUNT:-10}"
    prompt LOG_FILE_SIZE  "Log file size (MB)" \
        "${LOG_FILE_SIZE:-100}"

    section "Etcd (Discovery)"
    prompt ETCD_ENDPOINT "Etcd endpoint" \
        "${ETCD_ENDPOINT:-http://127.0.0.1:2379}"
    prompt ETCD_USER     "Etcd user" \
        "${ETCD_USER:-root}"
    prompt_secret ETCD_PASSWORD "Etcd password" \
        "${ETCD_PASSWORD:-}"

    section "HADB MySQL (Storage)"
    prompt HADB_HOST "HADB MySQL host" \
        "${HADB_HOST:-127.0.0.1}"
    prompt HADB_PORT "HADB MySQL port" \
        "${HADB_PORT:-3306}"
    prompt HADB_USER "HADB MySQL user" \
        "${HADB_USER:-root}"
    prompt_secret HADB_PASSWORD "HADB MySQL password" \
        "${HADB_PASSWORD:-}"

    section "DBM API"
    prompt DBM_API_BASE "DBM API base URL" \
        "${DBM_API_BASE:-http://127.0.0.1:80}"
    prompt_secret DBM_API_TOKEN "DBM API token" \
        "${DBM_API_TOKEN:-}"

    section "DBHA v1 API"
    prompt DBHAV1_API_BASE "DBHA v1 API base URL" \
        "${DBHAV1_API_BASE:-http://127.0.0.1:8080}"
    prompt_secret DBHAV1_API_TOKEN "DBHA v1 API token" \
        "${DBHAV1_API_TOKEN:-}"

    HADB_ENDPOINT="tcp://${HADB_HOST}:${HADB_PORT}"
    COMMON_DONE=1
    echo ""
    echo "  Common settings configured."
}

ensure_common() {
    if [ "${COMMON_DONE}" -eq 0 ]; then
        echo ""
        echo "  Common settings not yet configured."
        echo "  Please configure them first."
        collect_common
    fi
}

collect_admin() {
    section "Admin Service"
    prompt ADMIN_GRPC_PORT "gRPC listen port" \
        "${ADMIN_GRPC_PORT:-50051}"
    prompt ADMIN_WEB_PORT  "Web listen port" \
        "${ADMIN_WEB_PORT:-8089}"
    prompt ADMIN_APM_PORT  "APM listen port" \
        "${ADMIN_APM_PORT:-8081}"
}

collect_receiver() {
    section "Receiver Service"
    prompt RECV_APM_PORT "APM listen port" \
        "${RECV_APM_PORT:-8082}"

    echo ""
    echo "  -- Kafka source --"
    prompt KAFKA_ENDPOINT  "Kafka endpoint" \
        "${KAFKA_ENDPOINT:-127.0.0.1:9092}"
    prompt KAFKA_USER      "Kafka user" \
        "${KAFKA_USER:-}"
    prompt_secret KAFKA_PASSWORD "Kafka password" \
        "${KAFKA_PASSWORD:-}"
    prompt KAFKA_MECHANISM \
        "SASL mechanism (plaintext/scram-sha-256/scram-sha-512)" \
        "${KAFKA_MECHANISM:-plaintext}"
    prompt KAFKA_TOPICS \
        "Kafka topics (comma separated)" \
        "${KAFKA_TOPICS:-dbha}"
}

collect_analysis() {
    section "Analysis Service"
    prompt ANALYSIS_APM_PORT "APM listen port" \
        "${ANALYSIS_APM_PORT:-8083}"

    echo ""
    echo "  -- Database auth (for MySQL probing) --"
    prompt DB_MYSQL_USER "MySQL user" \
        "${DB_MYSQL_USER:-mysql}"
    prompt_secret DB_MYSQL_PASSWORD "MySQL password" \
        "${DB_MYSQL_PASSWORD:-}"
    prompt DB_PROXY_USER "Proxy user" \
        "${DB_PROXY_USER:-proxy}"
    prompt_secret DB_PROXY_PASSWORD "Proxy password" \
        "${DB_PROXY_PASSWORD:-}"

    echo ""
    echo "  -- SSH detector --"
    prompt SSH_PORT "SSH port"  "${SSH_PORT:-22}"
    prompt SSH_USER "SSH user"  "${SSH_USER:-root}"
    prompt_secret SSH_PASSWORD "SSH password" \
        "${SSH_PASSWORD:-}"

    echo ""
    echo "  -- Probe install path (for remote health check) --"
    prompt_probe_install_dir

    echo ""
    echo "  -- Monitor --"
    prompt MON_DATA_ID "Monitor data ID" \
        "${MON_DATA_ID:-0}"
    prompt_secret MON_ACCESS_TOKEN "Monitor access token" \
        "${MON_ACCESS_TOKEN:-}"
    prompt MON_BEAT "bkMonitorBeat path" \
        "${MON_BEAT:-}"
    prompt MON_ENDPOINT "bkMonitor endpoint" \
        "${MON_ENDPOINT:-127.0.0.1:9090}"
}

collect_probe() {
    section "Probe Service"
    prompt PROBE_REPORTER_NAME "Reporter name (gse/grpc)" \
        "${PROBE_REPORTER_NAME:-gse}"
    prompt PROBE_REPORTER_EP "Reporter endpoint" \
        "${PROBE_REPORTER_EP:-}"
    prompt PROBE_REPORTER_DATAID "Reporter data ID" \
        "${PROBE_REPORTER_DATAID:-0}"
    prompt DB_MYSQL_USER "MySQL user (harvester)" \
        "${DB_MYSQL_USER:-mysql}"
    prompt_secret DB_MYSQL_PASSWORD \
        "MySQL password (harvester)" \
        "${DB_MYSQL_PASSWORD:-}"
}

#---------------------------------------------------------------
# Generate functions
#---------------------------------------------------------------
generate_admin() {
    mkdir -p "${ETC_DIR}"
    cat > "${ETC_DIR}/admin.yaml" <<EOF
name: admin
version: ${VERSION}

pidFile: ./pids/admin.pid
docFileDir: ./docs

discovery:
  endpoint: ${ETCD_ENDPOINT}
  user: ${ETCD_USER}
  password: ${ETCD_PASSWORD}

apm:
  readTimeout: 10s
  writeTimeout: 10s
  listenAddress: ${LOCAL_IP}:${ADMIN_APM_PORT}

grpc:
  listenAddress: ${LOCAL_IP}:${ADMIN_GRPC_PORT}

web:
  listenAddress: ${LOCAL_IP}:${ADMIN_WEB_PORT}
  readTimeout: 5s
  writeTimeout: 5s

dbmApi:
  - name: metadata
    api: ${DBM_API_BASE}/apis/proxypass/dbmeta/dbha/instances
    method: post
    timeout: 10s
    token: "${DBM_API_TOKEN}"

  - name: updateStatus
    api: ${DBM_API_BASE}/apis/proxypass/dbmeta/dbha/update_status
    method: post
    timeout: 10s
    token: "${DBM_API_TOKEN}"

  - name: swapMySQLRole
    api: ${DBM_API_BASE}/apis/proxypass/dbmeta/dbha/swap_role
    method: post
    timeout: 10s
    token: "${DBM_API_TOKEN}"

  - name: swapTendisCluster
    api: ${DBM_API_BASE}/apis/proxypass/dbmeta/dbha/tendis_cluster_swap
    method: post
    timeout: 10s
    token: "${DBM_API_TOKEN}"

storage:
  endpoint: ${HADB_ENDPOINT}
  user: ${HADB_USER}
  password: ${HADB_PASSWORD}

log:
  path: ./logs/admin.log
  level: ${LOG_LEVEL}
  fileCount: ${LOG_FILE_COUNT}
  fileSize: ${LOG_FILE_SIZE}
EOF
    echo "  -> ${ETC_DIR}/admin.yaml"
}

generate_receiver() {
    mkdir -p "${ETC_DIR}"

    IFS=',' read -ra _TOPICS <<< "${KAFKA_TOPICS}"
    local topics_yaml=""
    for t in "${_TOPICS[@]}"; do
        t="$(echo "$t" | xargs)"
        topics_yaml="${topics_yaml}, \"${t}\""
    done
    topics_yaml="[${topics_yaml#, }]"

    cat > "${ETC_DIR}/receiver.yaml" <<EOF
name: receiver
version: ${VERSION}

pidFile: ./pids/receiver.pid

discovery:
  endpoint: ${ETCD_ENDPOINT}
  user: ${ETCD_USER}
  password: ${ETCD_PASSWORD}

apm:
  readTimeout: 10s
  writeTimeout: 10s
  listenAddress: ${LOCAL_IP}:${RECV_APM_PORT}

service:
  source:
    - name: kafka
      enable: true
      endpoint: ${KAFKA_ENDPOINT}
      user: ${KAFKA_USER}
      password: ${KAFKA_PASSWORD}
      netDialTimeout: 30s
      netReadTimeout: 30s
      netWriteTimeout: 30s
      mechanism: ${KAFKA_MECHANISM}
      topics: ${topics_yaml}

  sink:
    - name: mysql
      enable: true
      endpoint: ${HADB_HOST}:${HADB_PORT}
      user: ${HADB_USER}
      password: ${HADB_PASSWORD}

log:
  path: ./logs/receiver.log
  level: ${LOG_LEVEL}
  fileCount: ${LOG_FILE_COUNT}
  fileSize: ${LOG_FILE_SIZE}
EOF
    echo "  -> ${ETC_DIR}/receiver.yaml"
}

generate_analysis() {
    mkdir -p "${ETC_DIR}"
    cat > "${ETC_DIR}/analysis.yaml" <<EOF
name: analysis
version: ${VERSION}

pidFile: ./pids/analysis.pid

discovery:
  endpoint: ${ETCD_ENDPOINT}
  user: ${ETCD_USER}
  password: ${ETCD_PASSWORD}

apm:
  readTimeout: 10s
  writeTimeout: 10s
  listenAddress: ${LOCAL_IP}:${ANALYSIS_APM_PORT}

workflow:
  lockBusinessWaitTimeout: 5s
  scanTimeout: 60s
  scanInterval: 3s
  updateDbmCacheInterval: 10s
  readDbMetaOffsetDuration: -24h
  readDbMetricOffsetDuration: -60s
  readDbEventOffsetDuration: -10m
  enableSwitching: true
  switchflow:
    hostLevelSwitchMaxHostNum: 32
    hostLevelSwitchMaxInstanceNum: 64
    clusterLevelSwitchMaxClusterNum: 32
    clusterLevelSwitchMaxInstanceNum: 64
    dbmApiMaxConcurrentRequests: 8
    switchLogWriteTimeout: 1s
    dbConnectTimeout: 3s
    clusterLockTimeout: 60s
    execSqlTimeout: 6s
    slaveAllowedIgnoreCheckSum: false
    slaveAllowedIgnoreSlaveDelay: false
    slaveAllowedSlowBytes: 0
    slaveAllowedMaxChecksumFailCnt: 2
    slaveAllowedMaxHeartbeatDelay: 600

  dbmApiMetadata:
    api: ${DBM_API_BASE}/apis/proxypass/dbmeta/dbha/instances
    timeout: 10s
    token: "${DBM_API_TOKEN}"

  dbmApiUpdateStatus:
    api: ${DBM_API_BASE}/apis/proxypass/dbmeta/dbha/update_status
    timeout: 10s
    token: "${DBM_API_TOKEN}"

  dbmApiSwapMysqlRole:
    api: ${DBM_API_BASE}/apis/proxypass/dbmeta/dbha/swap_role
    timeout: 10s
    token: "${DBM_API_TOKEN}"

  dbmApiSwapTendisCluster:
    api: ${DBM_API_BASE}/apis/proxypass/dbmeta/dbha/tendis_cluster_swap
    timeout: 10s
    token: "${DBM_API_TOKEN}"

  dbmApiDomainGet:
    api: ${DBM_API_BASE}/apis/proxypass/dns/domain/get/
    timeout: 10s
    token: "${DBM_API_TOKEN}"

  dbmApiDomainDelete:
    api: ${DBM_API_BASE}/apis/proxypass/dns/domain/delete/
    timeout: 10s
    token: "${DBM_API_TOKEN}"

  dbmApiCLBDeregister:
    api: ${DBM_API_BASE}/apis/proxypass/clb_deregister_part_target/
    timeout: 10s
    token: "${DBM_API_TOKEN}"

  dbmApiPolarisUnbind:
    api: ${DBM_API_BASE}/apis/proxypass/polaris_unbind_part_targets/
    timeout: 10s
    token: "${DBM_API_TOKEN}"

  dbmApiDumperSwitch:
    api: ${DBM_API_BASE}/apis/proxypass/dumper/switch/
    timeout: 10s
    token: "${DBM_API_TOKEN}"

  dbhav1ApiBlackWhitelistGet:
    api: ${DBHAV1_API_BASE}/blackwhitelist/
    timeout: 10s
    token: "${DBHAV1_API_TOKEN}"

database:
  mysql:
    user: "${DB_MYSQL_USER}"
    password: "${DB_MYSQL_PASSWORD}"
    proxyUser: "${DB_PROXY_USER}"
    proxyPassword: "${DB_PROXY_PASSWORD}"

detector:
  checkProbeProcessCmd: "cd ${PROBE_INSTALL_DIR} && ./bin/dbha-probe health -j"
  ssh:
    port: ${SSH_PORT}
    user: ${SSH_USER}
    password: ${SSH_PASSWORD}
    timeout: 10s

monitor:
  dataID: ${MON_DATA_ID}
  timeout: 10s
  accessToken: "${MON_ACCESS_TOKEN}"
  bkMonitorBeat: "${MON_BEAT}"
  bkMonitorEndpoint: ${MON_ENDPOINT}

storage:
  endpoint: ${HADB_ENDPOINT}
  user: ${HADB_USER}
  password: ${HADB_PASSWORD}

log:
  path: ./logs/analysis.log
  level: ${LOG_LEVEL}
  fileCount: ${LOG_FILE_COUNT}
  fileSize: ${LOG_FILE_SIZE}
EOF
    echo "  -> ${ETC_DIR}/analysis.yaml"
}

generate_probe() {
    mkdir -p "${ETC_DIR}"
    cat > "${ETC_DIR}/probe.yaml" <<EOF
name: probe
version: ${VERSION}

pidFile: ./pids/probe.pid

reporter:
  name: ${PROBE_REPORTER_NAME}
  endpoint: "${PROBE_REPORTER_EP}"
  dataID: ${PROBE_REPORTER_DATAID}
  connTimeout: 5s

harvester:
  mysql:
    user: "${DB_MYSQL_USER}"
    password: "${DB_MYSQL_PASSWORD}"
    interval: 20s
    endpoints: []

  redis:
    password: ""
    interval: 20s
    timeout: 5s
    endpoints: []

log:
  path: ./logs/probe.log
  level: ${LOG_LEVEL}
  fileCount: ${LOG_FILE_COUNT}
  fileSize: ${LOG_FILE_SIZE}
EOF
    echo "  -> ${ETC_DIR}/probe.yaml"
    echo ""
    echo "  NOTE: probe.yaml harvester endpoints are empty."
    echo "        Edit etc/probe.yaml to add MySQL/Redis"
    echo "        instances to probe."
}

#---------------------------------------------------------------
# Setup orchestrators
#---------------------------------------------------------------
setup_all() {
    collect_common
    collect_admin
    collect_receiver
    collect_analysis
    collect_probe

    section "Generating all configuration files"
    generate_admin
    generate_receiver
    generate_analysis
    generate_probe
    echo ""
    echo "  All configuration files generated in ${ETC_DIR}/"
}

setup_admin() {
    ensure_common
    collect_admin
    section "Generating admin configuration"
    generate_admin
}

setup_receiver() {
    ensure_common
    collect_receiver
    section "Generating receiver configuration"
    generate_receiver
}

setup_analysis() {
    ensure_common
    collect_analysis
    section "Generating analysis configuration"
    generate_analysis
}

setup_probe() {
    ensure_common
    collect_probe
    section "Generating probe configuration"
    generate_probe
}

#---------------------------------------------------------------
# Main loop
#---------------------------------------------------------------
while true; do
    show_menu
    read -rp "  Select an option: " choice
    case "${choice}" in
        1) setup_all ;;
        2) setup_admin ;;
        3) setup_receiver ;;
        4) setup_analysis ;;
        5) setup_probe ;;
        6) collect_common ;;
        0)
            echo ""
            echo "  Bye."
            echo ""
            exit 0
            ;;
        *)
            echo ""
            echo "  Invalid option: ${choice}"
            ;;
    esac
done
