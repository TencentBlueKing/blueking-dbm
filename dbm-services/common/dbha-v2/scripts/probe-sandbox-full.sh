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

python3 - <<'PY'
import json, urllib.request
req = json.load(urllib.request.urlopen("http://127.0.0.1:18090/admin/last-request"))
if req.get("client_id"):
    raise SystemExit(f"FAIL gen-config must leave client_id empty, got: {req.get('client_id')!r}")
if req.get("ip") != "127.0.0.1":
    raise SystemExit(f"FAIL gen-config last ip: {req.get('ip')!r}")
print("PASS gen-config GetProbeConfig left client_id empty")
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
try:
    import yaml
except ImportError:
    yaml = None
text = Path(sys.argv[1]).read_text()
if yaml is None:
    # Fallback: harvester section must not mention 13306; clearPorts may.
    harvester = text.split("harvester:", 1)[-1].split("\nlog:", 1)[0]
    if "13306" in harvester:
        raise SystemExit("FAIL clear-port left 13306 in harvester")
else:
    doc = yaml.safe_load(text)
    if doc.get("clearPorts") != [13306]:
        raise SystemExit("FAIL clearPorts not persisted: %r" % (doc.get("clearPorts"),))
    mysql = ((doc.get("harvester") or {}).get("mysql") or {})
    for ep in mysql.get("endpoints") or []:
        if "13306" in (ep.get("ports") or []) or "13306" in (ep.get("adminPorts") or []):
            raise SystemExit("FAIL clear-port left 13306 in mysql endpoints")
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
try:
    import yaml
except ImportError:
    yaml = None
text = Path(sys.argv[1]).read_text()
cleared = ("13306", "10000", "16379")
if yaml is None:
    harvester = text.split("harvester:", 1)[-1].split("\nlog:", 1)[0]
    for port in cleared:
        if port in harvester:
            raise SystemExit("FAIL multi clear-port left %s in harvester" % port)
else:
    doc = yaml.safe_load(text)
    if sorted(doc.get("clearPorts") or []) != [10000, 13306, 16379]:
        raise SystemExit("FAIL clearPorts not persisted: %r" % (doc.get("clearPorts"),))
    hv = doc.get("harvester") or {}
    for block in hv.values():
        if not isinstance(block, dict):
            continue
        for ep in block.get("endpoints") or []:
            ports = list(ep.get("ports") or []) + list(ep.get("adminPorts") or [])
            for port in cleared:
                if port in ports:
                    raise SystemExit("FAIL multi clear-port left %s in endpoints" % port)
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

# Independent periodic sync (plan A-9): does not depend on receiver reporting. Harvest
# Harvest above stays valid because -patch-yaml forces syncInterval to 0s when an admin
# block is present, and gen-config now writes that block on the very first run (rewriting an
# existing probe.yaml preserves or heals it).
echo "periodic admin sync" | tee -a "$RESULT"
python3 - <<'PY'
import json, urllib.request

http = "http://127.0.0.1:18090"
payload = json.load(urllib.request.urlopen(http + "/admin/payload"))
payload.setdefault("metadata", []).append({
    "ip": "127.0.0.1",
    "port": 13307,
    "cluster_type": "tendbha",
    "machine_type": "backend",
    "instance_role": "backend_master",
    "access_layer": "storage",
})
req = urllib.request.Request(
    http + "/admin/payload",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    if resp.status != 200:
        raise SystemExit(f"FAIL swap payload status: {resp.status}")
print("PASS mock payload now includes port 13307")
PY

python3 - "$CFG" <<'PY'
from pathlib import Path

path = Path(__import__("sys").argv[1])
text = path.read_text()
block = (
    "admin:\n"
    '  endpoints: ["127.0.0.1:19001"]\n'
    "  bkCloudID: 0\n"
    '  localIP: "127.0.0.1"\n'
    "  syncInterval: 10s\n"
)

def replace_top_level(doc, key, replacement):
    lines = doc.splitlines(keepends=True)
    start = None
    for i, line in enumerate(lines):
        if line.startswith(key + ":"):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j] and not lines[j].startswith(" ") and not lines[j].startswith("\t"):
            end = j
            break
    return "".join(lines[:start]) + replacement + "".join(lines[end:])

updated = replace_top_level(text, "admin", block)
if updated is None:
    if "\nharvester:\n" not in text:
        raise SystemExit("FAIL cannot insert admin block, harvester missing")
    updated = text.replace("\nharvester:\n", "\n" + block + "harvester:\n", 1)
path.write_text(updated)
print("PASS admin sync block set on probe.yaml")
PY

sync_before=$(curl -fsS "$HTTP/stats" | python3 -c "import json,sys; print(json.load(sys.stdin)['get_probe_config'])")
"$BIN" reload -c "$CFG"
python3 - "$CFG" "$sync_before" <<'PY'
import json, sys, time, urllib.request
from pathlib import Path

path, before = Path(sys.argv[1]), int(sys.argv[2])
deadline = time.time() + 45
calls = before
while time.time() < deadline:
    stats = json.load(urllib.request.urlopen("http://127.0.0.1:18090/stats"))
    calls = stats.get("get_probe_config", 0)
    text = path.read_text()
    if calls > before and "13307" in text:
        print(f"PASS sync rewrote config from new payload, calls: {calls} before: {before}")
        break
    time.sleep(0.5)
else:
    raise SystemExit(
        f"FAIL sync did not apply port 13307, calls: {calls} before: {before}"
    )

text = path.read_text()
if "syncInterval: 10s" not in text:
    raise SystemExit("FAIL sync erased the admin block it needs to run again")
if "127.0.0.1:19001" not in text:
    raise SystemExit("FAIL sync erased the admin endpoints")
if "pidFile:" not in text:
    raise SystemExit("FAIL sync erased pidFile")
if "log:" not in text:
    raise SystemExit("FAIL sync erased the log block")
print("PASS locally owned fields survived the sync")
PY

python3 - "$ROOT/logs/probe.log" <<'PY'
import sys
from pathlib import Path
log = Path(sys.argv[1]).read_text()
if "config file updated from admin" not in log:
    raise SystemExit("FAIL probe log has no reload-after-write line")
if "sandbox-secret" in log:
    raise SystemExit("FAIL password leaked in probe log during sync")
print("PASS probe logged the config update without credentials")
PY

python3 - <<'PY'
import json, urllib.request
req = json.load(urllib.request.urlopen("http://127.0.0.1:18090/admin/last-request"))
if not req.get("client_id"):
    raise SystemExit("FAIL periodic sync GetProbeConfig left client_id empty")
if req.get("ip") != "127.0.0.1":
    raise SystemExit(f"FAIL periodic sync last ip: {req.get('ip')!r}")
print(f"PASS periodic sync sent client_id: {req['client_id']}")
PY

python3 - "$CFG" <<'PY'
import json, time, urllib.request
from pathlib import Path

path = Path(__import__("sys").argv[1])
before_text = path.read_text()
before_calls = json.load(urllib.request.urlopen("http://127.0.0.1:18090/stats")).get(
    "get_probe_config", 0
)
deadline = time.time() + 25
while time.time() < deadline:
    stats = json.load(urllib.request.urlopen("http://127.0.0.1:18090/stats"))
    if stats.get("get_probe_config", 0) > before_calls:
        after = path.read_text()
        if after != before_text:
            raise SystemExit("FAIL unchanged payload rewrote the config file")
        print("PASS unchanged payload left the config file untouched")
        break
    time.sleep(0.5)
else:
    raise SystemExit("FAIL no further sync round for convergence check")
PY

python3 - <<'PY'
import json, urllib.request
req = urllib.request.Request(
    "http://127.0.0.1:18090/admin/mode",
    data=json.dumps({"mode": "no_data"}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    body = json.load(resp)
if body.get("mode") != "no_data":
    raise SystemExit(f"FAIL set no_data mode, got: {body}")
print("PASS mock admin mode set to no_data")
PY

python3 - "$CFG" <<'PY'
import json, time, urllib.request
from pathlib import Path

path = Path(__import__("sys").argv[1])
before_text = path.read_text()
before_calls = json.load(urllib.request.urlopen("http://127.0.0.1:18090/stats")).get(
    "get_probe_config", 0
)
deadline = time.time() + 25
while time.time() < deadline:
    stats = json.load(urllib.request.urlopen("http://127.0.0.1:18090/stats"))
    if stats.get("get_probe_config", 0) > before_calls:
        after = path.read_text()
        if "13307" not in after:
            raise SystemExit("FAIL NO_DATA cleared the working config")
        if after != before_text:
            raise SystemExit("FAIL NO_DATA rewrote the config file")
        print("PASS NO_DATA kept the current config")
        break
    time.sleep(0.5)
else:
    raise SystemExit("FAIL no sync round after switching to NO_DATA")
PY

if ! kill -0 "$(cat "$PIDF")" 2>/dev/null; then
  echo "FAIL probe died during periodic sync" | tee -a "$RESULT"
  tail -n 40 "$ROOT/logs/probe.log" | tee -a "$RESULT" || true
  exit 1
fi
echo "PASS probe still running after periodic sync" | tee -a "$RESULT"

echo "log safety" | tee -a "$RESULT"
if grep -E 'sandbox-secret|password: ' "$ROOT/logs/probe.log" "$ROOT/logs/mock.log"; then
  echo "FAIL password leaked in logs" | tee -a "$RESULT"
  exit 1
fi
echo "PASS no password in logs" | tee -a "$RESULT"

trap - EXIT
cleanup
echo "=== ALL PASS ===" | tee -a "$RESULT"
