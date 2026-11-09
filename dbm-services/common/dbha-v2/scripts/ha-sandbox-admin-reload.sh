#!/usr/bin/env bash
# Admin reload sandbox: mock etcd/MySQL + dbha-admin SIGHUP cases (no real etcd/mysqld).
set -euo pipefail

DBHA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT=/tmp/ha-sandbox
ADMIN="$ROOT/bin/dbha-admin"
MOCK="$ROOT/bin/dbha-ha-sandbox-mock"
CFG="$ROOT/etc/admin.yaml"
PIDF="$ROOT/pids/admin.pid"
MOCKPID="$ROOT/pids/mock.pid"
RESULT="$ROOT/results/admin-reload.txt"
HTTP_MOCK=http://127.0.0.1:18091
HTTP_APM=http://127.0.0.1:19090
WORKSPACE_WORK="$(cd "$DBHA_ROOT/.." && pwd)/go.work"

export CC="${CC:-clang}"
if [[ -f "$WORKSPACE_WORK" ]]; then
  export GOWORK="$WORKSPACE_WORK"
fi

mkdir -p "$ROOT"/{bin,etc,logs,pids,results,docs}
cd "$ROOT"

stop_pidfile() {
  local f="$1"
  if [[ -f "$f" ]]; then
    local pid
    pid=$(cat "$f" 2>/dev/null || true)
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      sleep 1
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$f"
  fi
}

cleanup() {
  "$ADMIN" stop -c "$CFG" 2>/dev/null || true
  stop_pidfile "$PIDF"
  stop_pidfile "$MOCKPID"
}
trap cleanup EXIT

stop_pidfile "$PIDF"
stop_pidfile "$MOCKPID"

{
  echo "=== ha sandbox admin reload $(date -Is) ==="
  echo "CC: $CC"
  echo "dbha_root: $DBHA_ROOT"
} | tee "$RESULT"

pass() {
  echo "PASS $1" | tee -a "$RESULT"
}

fail() {
  echo "FAIL $1" | tee -a "$RESULT"
  exit 1
}

wait_http() {
  local url="$1"
  local i
  for i in $(seq 1 50); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.2
  done
  return 1
}

tcp_ok() {
  local host="$1"
  local port="$2"
  timeout 1 bash -c "echo >/dev/tcp/${host}/${port}" 2>/dev/null
}

write_admin_yaml() {
  local apm_read="${1:-5s}"
  local grpc_max="${2:-10485760}"
  local web_write="${3:-5s}"
  local disc_user="${4:-}"
  local storage_user="${5:-sandbox}"
  local log_level="${6:-info}"
  local apm_listen="${7-127.0.0.1:19090}"
  cat >"$CFG" <<EOF
name: admin
version: sandbox
pidFile: ./pids/admin.pid
docFileDir: ./docs
discovery:
  endpoint: "127.0.0.1:12379"
  user: "${disc_user}"
  password: ""
  serviceTimerInterval: 3s
  serviceUpdateTimeout: 3s
apm:
  readTimeout: ${apm_read}
  writeTimeout: 5s
  listenAddress: "${apm_listen}"
grpc:
  listenAddress: "127.0.0.1:15051"
  serverPingTime: 5m
  pingTimeout: 10s
  keepAliveMinTime: 5m
  permitWithoutStream: true
  maxReceiveMessageSize: ${grpc_max}
  maxSendMessageSize: 10485760
web:
  listenAddress: "127.0.0.1:18080"
  readTimeout: 5s
  writeTimeout: ${web_write}
dbmApi: []
storage:
  endpoint: "127.0.0.1:23306"
  user: "${storage_user}"
  password: "sandbox-secret"
log:
  path: ./logs/admin.log
  level: ${log_level}
  fileCount: 10
  fileSize: 100
probeGse:
  endpoint: "127.0.0.1:0"
  dataID: 1
  connTimeout: 5s
probeMysql:
  user: sandbox
  password: sandbox-secret
  interval: 5s
  heartbeatInterval: 1s
  replDelayInterval: 5s
  timeout: 1s
probeRedis:
  user: sandbox
  password: sandbox-secret
  interval: 5s
  timeout: 1s
probeProxyAdmin:
  user: sandbox
  password: sandbox-secret
  interval: 5s
  heartbeatInterval: 1s
  replDelayInterval: 5s
  timeout: 1s
probeHarvesters: {}
probeMetadata:
  cacheMaxAge: 10m
  tombstoneAge: 24h
EOF
}

count_log() {
  local pat="$1"
  if [[ ! -f "$ROOT/logs/admin.log" ]]; then
    echo 0
    return
  fi
  grep -c "$pat" "$ROOT/logs/admin.log" || true
}

wait_log_gt() {
  local pat="$1"
  local prev="$2"
  local i
  for i in $(seq 1 40); do
    local now
    now=$(count_log "$pat")
    if [[ "$now" -gt "$prev" ]]; then
      return 0
    fi
    sleep 0.25
  done
  return 1
}

scrape_metrics() {
  curl -fsS "$HTTP_APM/metrics"
}

prom_gauge() {
  local file="$1"
  local name="$2"
  local labels="${3:-}"
  python3 - "$file" "$name" "$labels" <<'PY'
import re
import sys

path, name, raw = sys.argv[1], sys.argv[2], sys.argv[3]
want = {}
if raw.strip():
    for part in raw.split(","):
        key, val = part.split("=", 1)
        want[key.strip()] = val.strip().strip('"')
with open(path, encoding="utf-8") as handle:
    text = handle.read()
line_re = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{[^}]*\})?\s+(\S+)\s*$")
label_re = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)="([^"]*)"')
for line in text.splitlines():
    if line.startswith("#"):
        continue
    matched = line_re.match(line)
    if not matched or matched.group(1) != name:
        continue
    labels = dict(label_re.findall(matched.group(2) or ""))
    if all(labels.get(key) == val for key, val in want.items()):
        sys.stdout.write(matched.group(3))
        sys.exit(0)
PY
}

num_eq() {
  awk -v a="${1:-}" -v b="${2:-}" 'BEGIN { exit !((a + 0) == (b + 0)) }'
}

num_gt() {
  awk -v a="${1:-}" -v b="${2:-}" 'BEGIN { exit !((a + 0) > (b + 0)) }'
}

num_ge() {
  awk -v a="${1:-}" -v b="${2:-}" 'BEGIN { exit !((a + 0) >= (b + 0)) }'
}

dump_metrics() {
  local tag="$1"
  scrape_metrics >"$ROOT/results/metrics-${tag}.txt" 2>/dev/null || true
}

read_reload_gauges() {
  local blob="$1"
  local tmp
  tmp=$(mktemp)
  printf '%s\n' "$blob" >"$tmp"
  G_SUCCESS=$(prom_gauge "$tmp" dbha_v2_admin_config_reload_success)
  G_FAILURE=$(prom_gauge "$tmp" dbha_v2_admin_config_reload_failure)
  G_DURATION=$(prom_gauge "$tmp" dbha_v2_admin_config_reload_duration_ms)
  G_LAST=$(prom_gauge "$tmp" dbha_v2_admin_config_reload_last_success_unix)
  G_SLOT_OK=$(prom_gauge "$tmp" dbha_v2_admin_config_reload_slot_count result=success)
  G_SLOT_FAIL=$(prom_gauge "$tmp" dbha_v2_admin_config_reload_slot_count result=failure)
  G_STARTUP=$(prom_gauge "$tmp" dbha_v2_admin_dbha_startup_time_sec service_name=admin)
  rm -f "$tmp"
}

assert_reload_success_metrics() {
  local case_id="$1"
  local want_slots="$2"
  local prev_last="${3:-0}"
  local blob i
  for i in $(seq 1 20); do
    blob=$(scrape_metrics) || true
    read_reload_gauges "${blob:-}"
    if num_eq "${G_SUCCESS:-0}" 1 && num_eq "${G_FAILURE:-1}" 0 && num_gt "${G_LAST:-0}" "$prev_last"; then
      break
    fi
    sleep 0.25
  done
  dump_metrics "$case_id"
  num_eq "${G_SUCCESS:-}" 1 || fail "$case_id metrics success want 1 got ${G_SUCCESS:-}"
  num_eq "${G_FAILURE:-}" 0 || fail "$case_id metrics failure want 0 got ${G_FAILURE:-}"
  num_ge "${G_DURATION:-}" 0 || fail "$case_id metrics duration got ${G_DURATION:-}"
  num_gt "${G_LAST:-0}" "$prev_last" || fail "$case_id last_success_unix not increased, prev: $prev_last, got: ${G_LAST:-}"
  if [[ -n "$want_slots" ]]; then
    num_eq "${G_SLOT_OK:-}" "$want_slots" || fail "$case_id slot success want $want_slots got ${G_SLOT_OK:-}"
    num_eq "${G_SLOT_FAIL:-0}" 0 || fail "$case_id slot failure want 0 got ${G_SLOT_FAIL:-}"
  fi
}

assert_gauges_unchanged() {
  local case_id="$1"
  local prev_last="$2"
  local prev_success="$3"
  local prev_failure="$4"
  local blob
  blob=$(scrape_metrics) || fail "$case_id scrape metrics"
  read_reload_gauges "$blob"
  dump_metrics "$case_id"
  num_eq "${G_LAST:-0}" "$prev_last" || fail "$case_id last_success changed, prev: $prev_last, got: ${G_LAST:-}"
  num_eq "${G_SUCCESS:-}" "$prev_success" || fail "$case_id success changed, got: ${G_SUCCESS:-}"
  num_eq "${G_FAILURE:-}" "$prev_failure" || fail "$case_id failure changed, got: ${G_FAILURE:-}"
}

read_grpc_gauges() {
  local blob="$1"
  local tmp
  tmp=$(mktemp)
  printf '%s\n' "$blob" >"$tmp"
  G_GRPC_HB_OK=$(prom_gauge "$tmp" dbha_v2_admin_grpc_requests_total 'method=Heartbeat,grpc_code=OK')
  G_GRPC_GPC_OK=$(prom_gauge "$tmp" dbha_v2_admin_grpc_requests_total 'method=GetProbeConfig,grpc_code=OK')
  G_GRPC_HB_ERR=$(prom_gauge "$tmp" dbha_v2_admin_grpc_request_errors_total method=Heartbeat)
  G_GRPC_GPC_ERR=$(prom_gauge "$tmp" dbha_v2_admin_grpc_request_errors_total method=GetProbeConfig)
  G_GRPC_HB_DUR=$(prom_gauge "$tmp" dbha_v2_admin_grpc_request_duration_ms_count method=Heartbeat)
  G_GRPC_GPC_DUR=$(prom_gauge "$tmp" dbha_v2_admin_grpc_request_duration_ms_count method=GetProbeConfig)
  G_GRPC_HB_REQSZ=$(prom_gauge "$tmp" dbha_v2_admin_grpc_request_size_bytes_count method=Heartbeat)
  G_GRPC_GPC_REQSZ=$(prom_gauge "$tmp" dbha_v2_admin_grpc_request_size_bytes_count method=GetProbeConfig)
  G_GRPC_HB_RESSZ=$(prom_gauge "$tmp" dbha_v2_admin_grpc_response_size_bytes_count method=Heartbeat)
  G_GRPC_GPC_RESSZ=$(prom_gauge "$tmp" dbha_v2_admin_grpc_response_size_bytes_count method=GetProbeConfig)
  G_GRPC_PROBE_FAIL=$(prom_gauge "$tmp" dbha_v2_admin_grpc_probe_config_result_total code=FAIL)
  G_GRPC_PROBE_NODATA=$(prom_gauge "$tmp" dbha_v2_admin_grpc_probe_config_result_total code=NO_DATA)
  G_GRPC_PROBE_SUCCESS=$(prom_gauge "$tmp" dbha_v2_admin_grpc_probe_config_result_total code=SUCCESS)
  rm -f "$tmp"
}

grpc_probe_result_sum() {
  awk -v a="${G_GRPC_PROBE_FAIL:-0}" -v b="${G_GRPC_PROBE_NODATA:-0}" -v c="${G_GRPC_PROBE_SUCCESS:-0}" \
    'BEGIN { printf "%d", a + b + c }'
}

call_admin_grpc() {
  local case_id="$1"
  local out
  out=$("$MOCK" --admin-grpc-addr 127.0.0.1:15051 2>&1) || fail "$case_id admin grpc client, out: $out"
  echo "$out" | grep -q "admin grpc heartbeat, grpc_code: OK" || fail "$case_id heartbeat log, out: $out"
  echo "$out" | grep -q "admin grpc get_probe_config, grpc_code: OK" || fail "$case_id get_probe_config log, out: $out"
}

assert_grpc_metrics_round() {
  local case_id="$1"
  local want_hb="$2"
  local want_gpc="$3"
  local want_result="$4"
  local blob i
  for i in $(seq 1 20); do
    blob=$(scrape_metrics) || true
    read_grpc_gauges "${blob:-}"
    if num_eq "${G_GRPC_HB_OK:-0}" "$want_hb" && num_eq "${G_GRPC_GPC_OK:-0}" "$want_gpc"; then
      break
    fi
    sleep 0.25
  done
  dump_metrics "$case_id"
  num_eq "${G_GRPC_HB_OK:-}" "$want_hb" || fail "$case_id Heartbeat OK want $want_hb got ${G_GRPC_HB_OK:-}"
  num_eq "${G_GRPC_GPC_OK:-}" "$want_gpc" || fail "$case_id GetProbeConfig OK want $want_gpc got ${G_GRPC_GPC_OK:-}"
  num_eq "${G_GRPC_HB_DUR:-}" "$want_hb" || fail "$case_id Heartbeat duration_count want $want_hb got ${G_GRPC_HB_DUR:-}"
  num_eq "${G_GRPC_GPC_DUR:-}" "$want_gpc" || fail "$case_id GetProbeConfig duration_count want $want_gpc got ${G_GRPC_GPC_DUR:-}"
  num_eq "${G_GRPC_HB_REQSZ:-}" "$want_hb" || fail "$case_id Heartbeat req_size_count want $want_hb got ${G_GRPC_HB_REQSZ:-}"
  num_eq "${G_GRPC_GPC_REQSZ:-}" "$want_gpc" || fail "$case_id GetProbeConfig req_size_count want $want_gpc got ${G_GRPC_GPC_REQSZ:-}"
  num_eq "${G_GRPC_HB_RESSZ:-}" "$want_hb" || fail "$case_id Heartbeat resp_size_count want $want_hb got ${G_GRPC_HB_RESSZ:-}"
  num_eq "${G_GRPC_GPC_RESSZ:-}" "$want_gpc" || fail "$case_id GetProbeConfig resp_size_count want $want_gpc got ${G_GRPC_GPC_RESSZ:-}"
  num_eq "${G_GRPC_HB_ERR:-0}" 0 || fail "$case_id Heartbeat errors want 0 got ${G_GRPC_HB_ERR:-}"
  num_eq "${G_GRPC_GPC_ERR:-0}" 0 || fail "$case_id GetProbeConfig errors want 0 got ${G_GRPC_GPC_ERR:-}"
  local got_result
  got_result=$(grpc_probe_result_sum)
  num_eq "$got_result" "$want_result" || fail "$case_id probe_config_result sum want $want_result got $got_result"
}

ADMIN_GRPC=127.0.0.1:15051
ADMIN_WEB=127.0.0.1:18080
HA_SERVERS_URL="http://$ADMIN_WEB/api/admin/meta/ha-servers"
REG_ROOT=/dbha/registry

skip() {
  echo "SKIP $1" | tee -a "$RESULT"
}

mock_ctl() {
  curl -fsS -X POST "$HTTP_MOCK/control/$1" >/dev/null
}

seed_kv() {
  curl -fsS -X PUT --data-binary "$2" "$HTTP_MOCK/control/etcd/kv?key=$1" >/dev/null
}

delete_kv() {
  curl -fsS -X DELETE "$HTTP_MOCK/control/etcd/kv?key=$1" >/dev/null
}

seed_ha_server() {
  local role="$1" id="$2" name="$3" ips="$4"
  seed_kv "$REG_ROOT/$role/self/$id" "{\"id\":\"$id\",\"name\":\"$name\",\"ips\":$ips,\
\"start_time\":\"2026-11-04T06:00:00Z\",\"updated_at\":\"2026-11-04T06:30:00Z\",\"uptime\":\"30 minutes\"}"
}

# list_ha_servers prints one JSON line comparing gRPC ListHaServers and GET meta/ha-servers.
list_ha_servers() {
  "$MOCK" --list-ha-servers --admin-grpc-addr "$ADMIN_GRPC" --admin-web-addr "$ADMIN_WEB" \
    2>>"$ROOT/logs/mock-client.log"
}

# ha_check evaluates a python expression over the list_ha_servers JSON (d); ids(p) lists role/id.
ha_check() {
  python3 - "$1" "$2" <<'PY'
import json
import sys

d = json.loads(sys.argv[1])


def ids(proto):
    return [s["role"] + "/" + s["id"] for s in d[proto]["servers"]]


ok = eval("(" + sys.argv[2] + ")", {"d": d, "ids": ids, "sorted": sorted, "set": set, "any": any, "all": all})
sys.exit(0 if ok else 1)
PY
}

ha_success_expr='d["grpc"]["grpc_code"] == "OK" and d["grpc"]["code"] == "HA_SERVER_LIST_SUCCESS"
  and d["grpc"]["errmsg"] == "success" and d["http"]["status"] == 200 and d["http"]["code"] == 0
  and d["http"]["message"] == "" and d["consistent"] is True'
ha_fail_expr='d["grpc"]["grpc_code"] == "OK" and d["grpc"]["code"] == "HA_SERVER_LIST_FAIL"
  and d["grpc"]["errmsg"] == "service discovery unavailable" and d["grpc"]["servers"] == []
  and d["grpc"]["ips"] == [] and d["http"]["status"] == 400 and d["http"]["code"] == 1
  and d["http"]["message"] == "service discovery unavailable" and d["http"]["raw_data"] == "\"\""'

list_ha_ok_count() {
  local tmp got
  tmp=$(mktemp)
  scrape_metrics >"$tmp" 2>/dev/null || true
  got=$(prom_gauge "$tmp" dbha_v2_admin_grpc_requests_total 'method=ListHaServers,grpc_code=OK')
  rm -f "$tmp"
  echo "${got:-0}"
}

echo "build admin" | tee -a "$RESULT"
(cd "$DBHA_ROOT" && go build -o "$ADMIN" ./cmd/admin)

echo "build mock" | tee -a "$RESULT"
(cd "$DBHA_ROOT" && CGO_ENABLED=0 go build -o "$MOCK" ./tools/cmd/ha-sandbox-mock)

echo "start mock" | tee -a "$RESULT"
"$MOCK" \
  --etcd-addr 127.0.0.1:12379 \
  --mysql-addr 127.0.0.1:23306 \
  --http-addr 127.0.0.1:18091 \
  >"$ROOT/logs/mock.log" 2>&1 &
echo $! >"$MOCKPID"

if wait_http "$HTTP_MOCK/health"; then
  pass "H01 mock health"
else
  fail "H01 mock health"
fi

write_admin_yaml
"$ADMIN" start -c "$CFG"

if wait_http "$HTTP_APM/health"; then
  pass "H02 admin start and apm health"
else
  fail "H02 admin start and apm health, log: $(tail -n 20 "$ROOT/logs/admin.log" 2>/dev/null || true)"
fi

health_out=$("$ADMIN" health -c "$CFG" 2>/dev/null || true)
if echo "$health_out" | grep -qi running; then
  pass "H02 health running"
else
  fail "H02 health running, out: $health_out"
fi

start_blob=$(scrape_metrics) || fail "H02 scrape metrics"
read_reload_gauges "$start_blob"
dump_metrics H02
num_gt "${G_STARTUP:-0}" 0 || fail "H02 startup metric missing, got: ${G_STARTUP:-}"
pass "H15 startup metric dbha_startup_time_sec: ${G_STARTUP}"
LAST_BEFORE_RELOAD="${G_LAST:-0}"

if tcp_ok 127.0.0.1 15051 && tcp_ok 127.0.0.1 18080; then
  pass "H03 grpc and web listen"
else
  fail "H03 grpc and web listen"
fi

call_admin_grpc H19
assert_grpc_metrics_round H19 1 1 1
pass "H19 admin grpc metrics Heartbeat/GetProbeConfig OK:1 duration/size count:1 probe_result:1"

skip_before=$(count_log "skip reload")
reload_before=$(count_log "admin config snapshot reloaded")
sleep 1
"$ADMIN" reload -c "$CFG" || fail "H04 first reload cli"
if wait_log_gt "skip reload" "$skip_before" || wait_log_gt "admin config snapshot reloaded" "$reload_before"; then
  assert_reload_success_metrics H04 "" "$LAST_BEFORE_RELOAD"
  pass "H04 first sighup applied or skipped, last_success_unix: ${G_LAST}"
  LAST_BEFORE_RELOAD="$G_LAST"
else
  fail "H04 first sighup no log"
fi

skip_before=$(count_log "skip reload")
sleep 1
"$ADMIN" reload -c "$CFG" || fail "H05 second reload cli"
if wait_log_gt "skip reload" "$skip_before"; then
  assert_reload_success_metrics H05 0 "$LAST_BEFORE_RELOAD"
  pass "H05 second sighup skip, slot_success: ${G_SLOT_OK}"
  LAST_BEFORE_RELOAD="$G_LAST"
else
  fail "H05 second sighup skip"
fi

reload_before=$(count_log "admin config snapshot reloaded")
write_admin_yaml 5s 10485760 5s "" sandbox debug
sleep 1
"$ADMIN" reload -c "$CFG" || fail "H06 reload cli"
if wait_log_gt "admin config snapshot reloaded" "$reload_before"; then
  assert_reload_success_metrics H06 0 "$LAST_BEFORE_RELOAD"
  pass "H06 log.level debug, success: ${G_SUCCESS}, duration_ms: ${G_DURATION}"
  LAST_BEFORE_RELOAD="$G_LAST"
else
  fail "H06 log.level debug"
fi

reload_before=$(count_log "admin config snapshot reloaded")
write_admin_yaml 6s 10485760 5s "" sandbox debug
sleep 1
"$ADMIN" reload -c "$CFG" || fail "H07 reload cli"
if wait_log_gt "admin config snapshot reloaded" "$reload_before" && wait_http "$HTTP_APM/health"; then
  assert_reload_success_metrics H07 1 "$LAST_BEFORE_RELOAD"
  pass "H07 apm same-addr replace, slot_success: ${G_SLOT_OK}"
  LAST_BEFORE_RELOAD="$G_LAST"
else
  fail "H07 apm same-addr replace"
fi

reload_before=$(count_log "admin config snapshot reloaded")
write_admin_yaml 6s 10485761 5s "" sandbox debug
sleep 1
"$ADMIN" reload -c "$CFG" || fail "H08 reload cli"
if wait_log_gt "admin config snapshot reloaded" "$reload_before" && tcp_ok 127.0.0.1 15051; then
  assert_reload_success_metrics H08 1 "$LAST_BEFORE_RELOAD"
  pass "H08 grpc same-addr params, slot_success: ${G_SLOT_OK}"
  LAST_BEFORE_RELOAD="$G_LAST"
  call_admin_grpc H20
  assert_grpc_metrics_round H20 2 2 2
  pass "H20 grpc metrics after slot replace Heartbeat/GetProbeConfig OK:2"
else
  fail "H08 grpc same-addr params"
fi

reload_before=$(count_log "admin config snapshot reloaded")
write_admin_yaml 6s 10485761 6s "" sandbox debug
sleep 1
"$ADMIN" reload -c "$CFG" || fail "H09 reload cli"
if wait_log_gt "admin config snapshot reloaded" "$reload_before" && tcp_ok 127.0.0.1 18080; then
  assert_reload_success_metrics H09 1 "$LAST_BEFORE_RELOAD"
  pass "H09 web same-addr replace, slot_success: ${G_SLOT_OK}"
  LAST_BEFORE_RELOAD="$G_LAST"
else
  fail "H09 web same-addr replace"
fi

reload_before=$(count_log "admin config snapshot reloaded")
write_admin_yaml 6s 10485761 6s sandbox-etcd sandbox debug
sleep 1
"$ADMIN" reload -c "$CFG" || fail "H10 reload cli"
if wait_log_gt "admin config snapshot reloaded" "$reload_before"; then
  assert_reload_success_metrics H10 1 "$LAST_BEFORE_RELOAD"
  pass "H10 discovery coexist, slot_success: ${G_SLOT_OK}"
  LAST_BEFORE_RELOAD="$G_LAST"
else
  fail "H10 discovery coexist"
fi

reload_before=$(count_log "admin config snapshot reloaded")
write_admin_yaml 6s 10485761 6s sandbox-etcd sandbox2 debug
sleep 1
"$ADMIN" reload -c "$CFG" || fail "H11 reload cli"
if wait_log_gt "admin config snapshot reloaded" "$reload_before"; then
  assert_reload_success_metrics H11 1 "$LAST_BEFORE_RELOAD"
  pass "H11 storage coexist, slot_success: ${G_SLOT_OK}"
  LAST_BEFORE_RELOAD="$G_LAST"
else
  fail "H11 storage coexist"
fi

bad="$ROOT/etc/admin-bad.yaml"
cp "$CFG" "$bad"
printf '\n{{broken' >>"$bad"
H12_LAST="$LAST_BEFORE_RELOAD"
H12_SUCCESS="${G_SUCCESS:-1}"
H12_FAILURE="${G_FAILURE:-0}"
if "$ADMIN" reload -c "$bad"; then
  fail "H12 corrupt yaml should fail cli"
else
  assert_gauges_unchanged H12 "$H12_LAST" "$H12_SUCCESS" "$H12_FAILURE"
  pass "H12 corrupt yaml cli rejected, metrics unchanged"
fi
health_out=$("$ADMIN" health -c "$CFG" 2>/dev/null || true)
echo "$health_out" | grep -qi running || fail "H12 process died"

sleep 1
if "$ADMIN" reload -c "$ROOT/etc/missing-admin.yaml"; then
  echo "$("$ADMIN" health -c "$CFG" 2>/dev/null || true)" | grep -qi running || fail "H13 process died"
  assert_reload_success_metrics H13 "" "$LAST_BEFORE_RELOAD"
  pass "H13 missing file still signals, last_success_unix: ${G_LAST}"
  LAST_BEFORE_RELOAD="$G_LAST"
else
  fail "H13 missing file cli should still signal"
fi

H14_LAST="$LAST_BEFORE_RELOAD"
H14_SUCCESS="${G_SUCCESS:-1}"
H14_FAILURE="${G_FAILURE:-0}"
write_admin_yaml 6s 10485761 6s sandbox-etcd sandbox2 debug ""
if "$ADMIN" reload -c "$CFG"; then
  fail "H14 empty apm listen should fail cli"
else
  write_admin_yaml 6s 10485761 6s sandbox-etcd sandbox2 debug
  assert_gauges_unchanged H14 "$H14_LAST" "$H14_SUCCESS" "$H14_FAILURE"
  pass "H14 empty listen cli rejected, metrics unchanged"
fi

validate_before=$(count_log "validate admin config failed")
write_admin_yaml 6s 10485761 6s sandbox-etcd sandbox2 debug ""
sleep 1
kill -HUP "$(cat "$PIDF")"
if wait_log_gt "validate admin config failed" "$validate_before"; then
  fail_blob=""
  for i in $(seq 1 20); do
    fail_blob=$(scrape_metrics) || true
    read_reload_gauges "${fail_blob:-}"
    if num_eq "${G_FAILURE:-0}" 1 && num_eq "${G_SUCCESS:-1}" 0; then
      break
    fi
    sleep 0.25
  done
  dump_metrics H15-fail
  num_eq "${G_SUCCESS:-}" 0 || fail "H15 fail path success want 0 got ${G_SUCCESS:-}"
  num_eq "${G_FAILURE:-}" 1 || fail "H15 fail path failure want 1 got ${G_FAILURE:-}"
  num_eq "${G_LAST:-0}" "$LAST_BEFORE_RELOAD" || fail "H15 fail path last_success changed"
  pass "H15 validate failure metrics success:0 failure:1 last unchanged"
else
  fail "H15 validate failure log missing"
fi

write_admin_yaml 6s 10485761 6s sandbox-etcd sandbox2 debug
sleep 1
skip_before=$(count_log "skip reload")
kill -HUP "$(cat "$PIDF")"
if wait_log_gt "skip reload" "$skip_before"; then
  assert_reload_success_metrics H15-recover 0 "$LAST_BEFORE_RELOAD"
  pass "H15 recover success last_success_unix: ${G_LAST} duration_ms: ${G_DURATION}"
  LAST_BEFORE_RELOAD="$G_LAST"
else
  fail "H15 recover skip missing"
fi

if grep -q sandbox-secret "$ROOT/logs/admin.log" 2>/dev/null; then
  fail "H16 secret leaked in admin log"
else
  pass "H16 no sandbox-secret in logs"
fi

# ---- S series: GET /api/admin/meta/ha-servers + gRPC ListHaServers ----
s_out=$(list_ha_servers) || fail "S01 list ha servers, out: ${s_out:-}"
ha_check "$s_out" "$ha_success_expr" || fail "S01 list ha servers not success, out: $s_out"
if ha_check "$s_out" 'any(s["role"] == "admin" and len(s["ips"]) > 0 for s in d["grpc"]["servers"])'; then
  pass "S01 admin self registration listed with non-empty ips"
else
  skip "S01 admin self registration has no ip (GetLocalIPs empty in this env), admin role covered by S02"
fi

seed_ha_server admin admin-s02 admin '["127.0.0.1"]'
seed_ha_server analysis analysis-s02 analysis '["::1","127.0.0.1"]'
seed_ha_server receiver receiver-s02 receiver '["::1"]'
seed_ha_server receiver receiver-s04 receiver '["127.0.0.1"]'
S08_BEFORE=$(list_ha_ok_count)
s_out=$(list_ha_servers) || fail "S02 list ha servers, out: ${s_out:-}"
ha_check "$s_out" "$ha_success_expr" || fail "S02 not success or grpc/http differ, out: $s_out"
ha_check "$s_out" 'all(x in ids("grpc") for x in ["admin/admin-s02", "analysis/analysis-s02",
  "receiver/receiver-s02", "receiver/receiver-s04"])' || fail "S02 seeded servers missing, out: $s_out"
ha_check "$s_out" '[s for s in d["http"]["servers"] if s["id"] == "analysis-s02"][0] == {"role": "analysis",
  "id": "analysis-s02", "ips": ["127.0.0.1", "::1"], "start_time": "2026-11-04T14:00:00+08:00",
  "updated_at": "2026-11-04T14:30:00+08:00", "uptime": "30 minutes"}' || fail "S02 analysis-s02 fields, out: $s_out"
ha_check "$s_out" 'd["http"]["ips"] == sorted(set(d["http"]["ips"])) and "127.0.0.1" in d["http"]["ips"]
  and "::1" in d["http"]["ips"]' || fail "S02 top-level ips not sorted/deduplicated, out: $s_out"
ha_check "$s_out" '[ {"admin": 0, "analysis": 1, "receiver": 2}[s["role"]] for s in d["grpc"]["servers"]] ==
  sorted({"admin": 0, "analysis": 1, "receiver": 2}[s["role"]] for s in d["grpc"]["servers"])' \
  || fail "S02 role order, out: $s_out"
pass "S02 three roles listed, grpc and http identical"

S08_AFTER=$(list_ha_ok_count)
S08_WANT=$((${S08_BEFORE%.*} + 1))
num_eq "$S08_AFTER" "$S08_WANT" || fail "S08 ListHaServers OK want $S08_WANT got $S08_AFTER"
pass "S08 grpc_requests_total{method=ListHaServers,grpc_code=OK}: $S08_BEFORE -> $S08_AFTER"

seed_kv "$REG_ROOT/analysis/self/analysis-s03-empty" ""
seed_kv "$REG_ROOT/analysis/self/analysis-s03-badjson" "{bad"
seed_ha_server receiver receiver-s03-mismatch analysis '["127.0.0.1"]'
seed_ha_server probe probe-s03 probe '["127.0.0.1"]'
seed_ha_server analysis analysis-s03-noip analysis '[""]'
s_out=$(list_ha_servers) || fail "S03 list ha servers, out: ${s_out:-}"
ha_check "$s_out" "$ha_success_expr" || fail "S03 not success, out: $s_out"
ha_check "$s_out" 'not any("s03" in x for x in ids("grpc") + ids("http"))' || fail "S03 invalid listed, out: $s_out"
ha_check "$s_out" '"analysis/analysis-s02" in ids("http")' || fail "S03 valid record dropped, out: $s_out"
"$ADMIN" health -c "$CFG" 2>/dev/null | grep -qi running || fail "S03 admin not running"
pass "S03 invalid registrations skipped, admin running"

delete_kv "$REG_ROOT/receiver/self/receiver-s04"
s_out=$(list_ha_servers) || fail "S04 list ha servers, out: ${s_out:-}"
ha_check "$s_out" "$ha_success_expr" || fail "S04 not success, out: $s_out"
ha_check "$s_out" '"receiver/receiver-s04" not in ids("grpc") and "receiver/receiver-s02" in ids("grpc")' \
  || fail "S04 deleted receiver still listed, out: $s_out"
pass "S04 deleted receiver disappears"

mock_ctl mysql/stop || fail "S05 stop mysql mock"
s_out=$(list_ha_servers) || fail "S05 list ha servers, out: ${s_out:-}"
ha_check "$s_out" "$ha_success_expr" || fail "S05 new api must succeed without mysql, out: $s_out"
s05_strategy=$(curl -s -o /dev/null -w '%{http_code}' "http://$ADMIN_WEB/api/admin/strategies/" || true)
[[ "$s05_strategy" != "200" ]] || fail "S05 strategy api should fail without mysql, status: $s05_strategy"
s05_gpc=$("$MOCK" --admin-grpc-addr "$ADMIN_GRPC" 2>&1 || true)
if echo "$s05_gpc" | grep -q "code: PROBE_CONFIG_SUCCESS"; then
  fail "S05 GetProbeConfig should not succeed without mysql, out: $s05_gpc"
fi
pass "S05 mysql down: ha-servers success, strategy status: $s05_strategy, GetProbeConfig not SUCCESS"

storage_fail_before=$(count_log "admin resource reload failed, slot: storage")
write_admin_yaml 6s 10485761 6s sandbox-etcd sandbox3 debug
sleep 1
"$ADMIN" reload -c "$CFG" || fail "S05 storage reload cli"
s05_during=$(list_ha_servers || true)
[[ -n "$s05_during" ]] && ha_check "$s05_during" "$ha_success_expr" \
  || fail "S05 ha-servers must succeed during storage reload, out: ${s05_during:-}"
wait_log_gt "admin resource reload failed, slot: storage" "$storage_fail_before" \
  || fail "S05 storage reload should fail while mysql is down"
s_out=$(list_ha_servers) || fail "S05 list after storage reload, out: ${s_out:-}"
ha_check "$s_out" "$ha_success_expr" || fail "S05 ha-servers must succeed after storage reload, out: $s_out"
"$ADMIN" health -c "$CFG" 2>/dev/null | grep -qi running || fail "S05 admin not running after storage reload"
write_admin_yaml 6s 10485761 6s sandbox-etcd sandbox2 debug
mock_ctl mysql/start || fail "S05 start mysql mock"
pass "S05 storage reload with mysql down: ha-servers success during and after reload"

mock_ctl etcd/stop || fail "S06 stop etcd mock"
s_out=$(list_ha_servers) || fail "S06 list ha servers, out: ${s_out:-}"
ha_check "$s_out" "$ha_fail_expr" || fail "S06 etcd down must be FAIL/400, out: $s_out"
mock_ctl etcd/start || fail "S06 start etcd mock"
s06_ok=0
for i in $(seq 1 20); do
  s_out=$(list_ha_servers || true)
  if [[ -n "$s_out" ]] && ha_check "$s_out" "$ha_success_expr"; then
    s06_ok=1
    break
  fi
  sleep 1
done
[[ "$s06_ok" == 1 ]] || fail "S06 not recovered after etcd restart, out: ${s_out:-}"
pass "S06 etcd down FAIL/400 code 1, recovered after restart"

reload_before=$(count_log "admin config snapshot reloaded")
write_admin_yaml 6s 10485761 6s "" sandbox2 debug
sleep 1
"$ADMIN" reload -c "$CFG" || fail "S07 reload cli"
s07_during=$(list_ha_servers || true)
if [[ -n "$s07_during" ]]; then
  ha_check "$s07_during" 'd["grpc"]["code"] in ("HA_SERVER_LIST_SUCCESS", "HA_SERVER_LIST_FAIL")' \
    || fail "S07 during reload invalid response, out: $s07_during"
fi
wait_log_gt "admin config snapshot reloaded" "$reload_before" || fail "S07 discovery reload log missing"
s_out=$(list_ha_servers) || fail "S07 list ha servers, out: ${s_out:-}"
ha_check "$s_out" "$ha_success_expr" || fail "S07 not success after reload, out: $s_out"
ha_check "$s_out" '"analysis/analysis-s02" in ids("grpc") and "receiver/receiver-s02" in ids("http")' \
  || fail "S07 seeded servers missing after reload, out: $s_out"
pass "S07 discovery reload keeps ha-servers available"

if grep -q sandbox-secret "$ROOT/logs/admin.log" "$ROOT/logs/mock-client.log" 2>/dev/null; then
  fail "S09 secret leaked in logs"
fi
grep -q "list ha servers failed, errmsg: " "$ROOT/logs/admin.log" || fail "S09 errmsg log format missing"
if grep "list ha servers failed" "$ROOT/logs/admin.log" | grep -qE "error: |err=|%v"; then
  fail "S09 list ha servers log format"
fi
pass "S09 ha-servers logs use errmsg format, no secret"

"$ADMIN" stop -c "$CFG" || true
sleep 1
health_out=$("$ADMIN" health -c "$CFG" 2>/dev/null || true)
if echo "$health_out" | grep -qi running; then
  fail "H17 still running after stop"
else
  pass "H17 stop via pid"
fi

pass "H18 mock-only deps"
echo "ALL PASS" | tee -a "$RESULT"
