#!/usr/bin/env bash
# Full-path sandbox test: mock admin/receiver/redis + probe gen-config/harvest/report.
set -euo pipefail

DBHA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ROOT=/tmp/probe-sandbox
BIN="$ROOT/bin/dbha-probe"
MOCK="$ROOT/bin/dbha-probe-sandbox-mock"
CFG="$ROOT/etc/probe.yaml"
CLEARED="$ROOT/etc/probe-cleared.yaml"
CLEARED_MULTI="$ROOT/etc/probe-cleared-multi.yaml"
PIDF="$ROOT/pids/probe.pid"
MOCKPID="$ROOT/pids/mock.pid"
RESULT="$ROOT/results/mock-full.txt"
HTTP=http://127.0.0.1:18090
WORKSPACE_WORK="$(cd "$DBHA_ROOT/.." && pwd)/go.work"

export CC="${CC:-clang}"
if [[ -f "$WORKSPACE_WORK" ]]; then
  export GOWORK="$WORKSPACE_WORK"
fi

mkdir -p "$ROOT"/{bin,etc,logs,pids,results}
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
  "$BIN" stop -c "$CFG" 2>/dev/null || true
  stop_pidfile "$PIDF"
  stop_pidfile "$MOCKPID"
}
trap cleanup EXIT

stop_pidfile "$PIDF"
stop_pidfile "$MOCKPID"

{
  echo "=== mock full-path sandbox $(date -Is) ==="
  echo "CC: $CC"
  echo "dbha_root: $DBHA_ROOT"
} | tee "$RESULT"

echo "build probe" | tee -a "$RESULT"
(cd "$DBHA_ROOT" && go build -o "$BIN" ./cmd/probe)

echo "build mock" | tee -a "$RESULT"
(cd "$DBHA_ROOT" && CGO_ENABLED=0 go build -o "$MOCK" ./tools/cmd/probe-sandbox-mock)

echo "start mock" | tee -a "$RESULT"
"$MOCK" \
  --admin-addr 127.0.0.1:19001 \
  --receiver-addr 127.0.0.1:19100 \
  --redis-addr 127.0.0.1:16379 \
  --http-addr 127.0.0.1:18090 \
  --dump "$ROOT/results/receiver.jsonl" \
  >"$ROOT/logs/mock.log" 2>&1 &
echo $! >"$MOCKPID"

for i in $(seq 1 30); do
  if curl -fsS "$HTTP/health" >/dev/null; then
    break
  fi
  sleep 0.2
done
curl -fsS "$HTTP/health" >/dev/null
echo "PASS mock health" | tee -a "$RESULT"

echo "gen-config" | tee -a "$RESULT"
"$BIN" gen-config \
  --admin-endpoints 127.0.0.1:19001 \
  --local-ip 127.0.0.1 \
  --cloud-id 0 \
  --output "$CFG" | tee -a "$RESULT"

python3 - "$CFG" <<'PY'
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
needles = ["13306", "16379", "10000", "15306", "mysqlProxyAdmin", "tendiscache"]
missing = [n for n in needles if n not in text]
if missing:
    raise SystemExit(f"FAIL gen-config missing: {missing}")
if "name: gse" not in text:
    raise SystemExit("FAIL gen-config reporter is not gse before patch")
print("PASS gen-config payload rendered")
PY

echo "gen-config --clear-port 13306" | tee -a "$RESULT"
"$BIN" gen-config \
  --admin-endpoints 127.0.0.1:19001 \
  --local-ip 127.0.0.1 \
  --cloud-id 0 \
  --clear-port 13306 \
  --output "$CLEARED" | tee -a "$RESULT"

python3 - "$CLEARED" <<'PY'
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
if "13306" in text:
    raise SystemExit("FAIL clear-port left 13306 in yaml")
if "16379" not in text:
    raise SystemExit("FAIL clear-port dropped redis port")
print("PASS clear-port dropped mysql data port only")
PY

echo "gen-config --clear-port 13306,10000;16379" | tee -a "$RESULT"
"$BIN" gen-config \
  --admin-endpoints 127.0.0.1:19001 \
  --local-ip 127.0.0.1 \
  --cloud-id 0 \
  --clear-port '13306,10000;16379' \
  --output "$CLEARED_MULTI" | tee -a "$RESULT"

python3 - "$CLEARED_MULTI" <<'PY'
import sys
from pathlib import Path
text = Path(sys.argv[1]).read_text()
for port in ("13306", "10000", "16379"):
    if port in text:
        raise SystemExit(f"FAIL multi clear-port left {port} in yaml")
if "15306" not in text:
    raise SystemExit("FAIL multi clear-port dropped proxy admin port 15306")
if "mysqlProxyAdmin" not in text:
    raise SystemExit("FAIL multi clear-port dropped mysqlProxyAdmin harvester")
if "tendiscache" in text:
    raise SystemExit("FAIL multi clear-port left redis harvester")
print("PASS multi clear-port dropped 13306,10000,16379 and kept 15306")
PY

"$MOCK" -patch-yaml "$CFG" --receiver-addr 127.0.0.1:19100 \
  --log-path "$ROOT/logs/probe.log" | tee -a "$RESULT"

: >"$ROOT/logs/probe.log"
echo "start probe" | tee -a "$RESULT"
"$BIN" start -c "$CFG" | tee -a "$RESULT"
for i in $(seq 1 25); do
  if [[ -f "$PIDF" ]] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
    break
  fi
  sleep 0.2
done
if [[ ! -f "$PIDF" ]] || ! kill -0 "$(cat "$PIDF")" 2>/dev/null; then
  echo "FAIL probe did not stay running" | tee -a "$RESULT"
  tail -n 40 "$ROOT/logs/probe.log" | tee -a "$RESULT" || true
  exit 1
fi
"$BIN" health | tee -a "$RESULT"

echo "wait harvest + report" | tee -a "$RESULT"
python3 - <<'PY'
import json, time, urllib.request

http = "http://127.0.0.1:18090"
deadline = time.time() + 25
redis_ok = mysql_fail = False
last_push = 0
while time.time() < deadline:
    stats = json.load(urllib.request.urlopen(http + "/stats"))
    last_push = stats.get("push", 0)
    payloads = json.load(urllib.request.urlopen(http + "/last"))
    for raw in payloads:
        p = json.loads(raw) if isinstance(raw, str) else raw
        db = p.get("db_type_name")
        port = p.get("db_port")
        data = p.get("data") or {}
        events = p.get("events") or []
        names = [e.get("name") for e in events if isinstance(e, dict)]
        if db == "redis" and port == 16379 and data.get("tendiscache_status"):
            redis_ok = True
        if db == "mysql" and "dbha_detect_db_failure" in names:
            mysql_fail = True
    if redis_ok and mysql_fail:
        break
    time.sleep(0.5)

print(f"push_count: {last_push} redis_ok: {redis_ok} mysql_fail: {mysql_fail}")
if not redis_ok:
    raise SystemExit("FAIL redis success harvest was not reported")
if not mysql_fail:
    raise SystemExit("FAIL mysql detect-failure was not reported")
print("PASS harvest reported to mock receiver")
PY

echo "reload after gen-config patch" | tee -a "$RESULT"
"$BIN" gen-config \
  --admin-endpoints 127.0.0.1:19001 \
  --local-ip 127.0.0.1 \
  --cloud-id 0 \
  --output "$CFG" >/dev/null
"$MOCK" -patch-yaml "$CFG" --receiver-addr 127.0.0.1:19100 \
  --log-path "$ROOT/logs/probe.log" >/dev/null
before=$(curl -fsS "$HTTP/stats" | python3 -c "import json,sys; print(json.load(sys.stdin)['push'])")
"$BIN" reload -c "$CFG"
python3 - "$before" <<'PY'
import json, time, urllib.request, sys
before = int(sys.argv[1])
deadline = time.time() + 20
while time.time() < deadline:
    stats = json.load(urllib.request.urlopen("http://127.0.0.1:18090/stats"))
    if stats.get("push", 0) > before:
        print(f"PASS reload still reporting, push: {stats['push']} before: {before}")
        raise SystemExit(0)
    time.sleep(0.5)
raise SystemExit("FAIL no new reports after reload")
PY

echo "log safety" | tee -a "$RESULT"
if grep -E 'sandbox-secret|password: ' "$ROOT/logs/probe.log" "$ROOT/logs/mock.log"; then
  echo "FAIL password leaked in logs" | tee -a "$RESULT"
  exit 1
fi
echo "PASS no password in logs" | tee -a "$RESULT"

trap - EXIT
cleanup
echo "=== ALL PASS ===" | tee -a "$RESULT"
