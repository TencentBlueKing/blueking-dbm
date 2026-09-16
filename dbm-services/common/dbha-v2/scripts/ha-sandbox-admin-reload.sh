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
  G_STARTUP=$(prom_gauge "$tmp" dbha_v2_admin_dbha_startup_time_sec)
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
