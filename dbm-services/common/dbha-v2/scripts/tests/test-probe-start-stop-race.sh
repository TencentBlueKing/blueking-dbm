#!/usr/bin/env bash
# End-to-end concurrency tests for start-probe.sh / stop-probe.sh.
#
# Run: scripts/tests/test-probe-start-stop-race.sh
# Requires a Go toolchain to build the stub binary in testdata/fake-probe.
# Missing go or a failed build exits 1. crontab is mocked through PATH, so the
# real user crontab is never touched.

# Deliberately no "set -e": a failing assertion must not abort the run, and
# cleanup must always execute.
set -uo pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$(cd "${SELF_DIR}/.." && pwd)"
MODULE_DIR="$(cd "${SCRIPTS_DIR}/.." && pwd)"

TESTS_RUN=0
TESTS_FAILED=0

ROOT=""
FAKE_BIN=""
EXPECTED_EXE=""

ok() {
    TESTS_RUN=$(( TESTS_RUN + 1 ))
    printf 'ok   %s\n' "$1"
}

fail() {
    TESTS_RUN=$(( TESTS_RUN + 1 ))
    TESTS_FAILED=$(( TESTS_FAILED + 1 ))
    printf 'FAIL %s\n' "$1"
    if [ -n "${2:-}" ]; then
        printf '     %s\n' "$2"
    fi
}

assert_eq() {
    if [ "$2" = "$3" ]; then
        ok "$1"
    else
        fail "$1" "want: [$2] got: [$3]"
    fi
}

# --- process inspection scoped to this test's binary ---

# Matches this install's live exe or a deleted-exe orphan of the same path.
# The tempdir prefix keeps us from touching a developer's real probe.
exe_belongs_here() {
    local pid="$1" exe
    exe="$(readlink -f "/proc/${pid}/exe" 2>/dev/null || true)"
    if [ "$exe" = "$EXPECTED_EXE" ]; then
        return 0
    fi
    exe="$(readlink "/proc/${pid}/exe" 2>/dev/null || true)"
    [ "${exe% (deleted)}" = "$EXPECTED_EXE" ]
}

# pids_of_kind <daemon-start|gen-config|worker>
pids_of_kind() {
    local want="$1" pid cmdline
    while IFS= read -r pid; do
        [ -n "$pid" ] || continue
        exe_belongs_here "$pid" || continue
        cmdline="$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)"
        case "$want" in
            daemon-start) case "$cmdline" in *daemon-start*) echo "$pid" ;; esac ;;
            gen-config)   case "$cmdline" in *gen-config*) echo "$pid" ;; esac ;;
            worker)
                case "$cmdline" in
                    *daemon-start*|*gen-config*|*ensure*) ;;
                    *) echo "$pid" ;;
                esac
                ;;
        esac
    done < <(pgrep -x dbha-probe 2>/dev/null || true)
}

count_of_kind() {
    pids_of_kind "$1" | grep -c '[0-9]' || true
}

cron_marker_count() {
    grep -c 'DBHA_V2_PROBE_GUARD' "${ROOT}/crontab.store" 2>/dev/null || true
}

intent_action() {
    awk '{print $2}' "${ROOT}/pids/probe.intent" 2>/dev/null || true
}

intent_ts() {
    awk '{print $1}' "${ROOT}/pids/probe.intent" 2>/dev/null || true
}

kill_test_procs() {
    local pid
    while IFS= read -r pid; do
        [ -n "$pid" ] || continue
        kill -KILL "$pid" 2>/dev/null || true
    done < <(
        for pid in $(pgrep -x dbha-probe 2>/dev/null || true); do
            if exe_belongs_here "$pid"; then
                echo "$pid"
            fi
        done
    )
}

# Replace the binary inode while a process is using it, producing a deleted-exe
# orphan whose recorded path still equals EXPECTED_EXE.
make_deleted_exe_orphan() {
    cp "$FAKE_BIN" "${ROOT}/bin/dbha-probe.bak"
    rm -f "$FAKE_BIN"
    cp "${ROOT}/bin/dbha-probe.bak" "$FAKE_BIN"
    chmod +x "$FAKE_BIN"
    rm -f "${ROOT}/bin/dbha-probe.bak"
}

cleanup() {
    if [ -n "$EXPECTED_EXE" ]; then
        kill_test_procs
    fi
    if [ -n "$ROOT" ] && [ -d "$ROOT" ]; then
        rm -rf "$ROOT"
    fi
}
trap cleanup EXIT

# --- build the stub and lay out a package-shaped install root ---

if ! command -v go >/dev/null 2>&1; then
    echo "FAIL: go toolchain not available, cannot build the probe stub" >&2
    exit 1
fi

ROOT="$(mktemp -d)"
mkdir -p "${ROOT}/bin" "${ROOT}/etc" "${ROOT}/pids" "${ROOT}/lib" "${ROOT}/logs"
FAKE_BIN="${ROOT}/bin/dbha-probe"

if ! (cd "$MODULE_DIR" && GOWORK=off go build -o "$FAKE_BIN" ./scripts/tests/testdata/fake-probe); then
    if ! (cd "${SELF_DIR}/testdata/fake-probe" && GOWORK=off go build -o "$FAKE_BIN" main.go); then
        echo "FAIL: cannot build the probe stub" >&2
        exit 1
    fi
fi

cp "${SCRIPTS_DIR}/start-probe.sh" "${SCRIPTS_DIR}/stop-probe.sh" "${ROOT}/"
cp "${SCRIPTS_DIR}/lib/guard-utils.sh" "${SCRIPTS_DIR}/lib/probe-lifecycle-utils.sh" "${ROOT}/lib/"
printf 'fake: true\n' > "${ROOT}/etc/probe.yaml"
EXPECTED_EXE="$(readlink -f "$FAKE_BIN")"

MOCKBIN="${ROOT}/mockbin"
mkdir -p "$MOCKBIN"
export MOCK_CRONTAB_FILE="${ROOT}/crontab.store"
: > "$MOCK_CRONTAB_FILE"
cat > "${MOCKBIN}/crontab" <<'MOCK'
#!/usr/bin/env bash
store="${MOCK_CRONTAB_FILE}"
case "${1:-}" in
    -l)
        if [ -s "$store" ]; then cat "$store"; else echo "no crontab" >&2; exit 1; fi ;;
    -)  cat > "$store" ;;
    *)  exit 1 ;;
esac
MOCK
chmod +x "${MOCKBIN}/crontab"

export PATH="${MOCKBIN}:${PATH}"
export DBHA_LOG_ROOT="${ROOT}/logs"
export XDG_STATE_HOME="${ROOT}/state"
PROBE_LOG="${ROOT}/logs/dbha-v2-probe.log"
KA_LOG="${ROOT}/logs/dbha-v2-keepalive.log"
# Keep the suite fast; the semantics under test do not depend on these budgets.
export DBHA_START_VERIFY_WAIT=8
export DBHA_ENSURE_LOCK_WAIT=3

hide_bin_without() {
    local d skip="$1" dir f b
    d="${ROOT}/hidebin"
    rm -rf "$d"
    mkdir -p "$d"
    for dir in /bin /usr/bin; do
        [ -d "$dir" ] || continue
        for f in "$dir"/*; do
            [ -x "$f" ] || continue
            b="${f##*/}"
            [ "$b" = "$skip" ] && continue
            [ -e "${d}/${b}" ] && continue
            ln -sf "$f" "${d}/${b}"
        done
    done
    printf '%s' "$d"
}

run_start() {
    ( cd "$ROOT" && ./start-probe.sh "$@" >/dev/null 2>&1 )
}

run_stop() {
    ( cd "$ROOT" && ./stop-probe.sh "$@" >/dev/null 2>&1 )
}

echo "=== T1 basic start ==="
run_start
assert_eq "T1 start exits 0" 0 $?
assert_eq "T1 exactly one guard running" 1 "$(count_of_kind daemon-start)"
assert_eq "T1 cron guard registered" 1 "$(cron_marker_count)"
assert_eq "T1 intent recorded as start" "start" "$(intent_action)"

echo "=== T2 repeated start is idempotent ==="
run_start
assert_eq "T2 second start exits 0" 0 $?
assert_eq "T2 still exactly one guard" 1 "$(count_of_kind daemon-start)"
assert_eq "T2 still one cron line" 1 "$(cron_marker_count)"

echo "=== T3 concurrent starts must not produce two guards ==="
run_stop >/dev/null 2>&1
for _ in 1 2 3 4; do
    run_start &
done
wait
assert_eq "T3 concurrent starts leave one guard" 1 "$(count_of_kind daemon-start)"
assert_eq "T3 concurrent starts leave one cron line" 1 "$(cron_marker_count)"

echo "=== T4 basic stop ==="
run_stop
assert_eq "T4 stop exits 0" 0 $?
assert_eq "T4 no guard left" 0 "$(count_of_kind daemon-start)"
assert_eq "T4 cron guard deregistered" 0 "$(cron_marker_count)"
assert_eq "T4 intent recorded as stop" "stop" "$(intent_action)"

echo "=== T5 stop is idempotent ==="
run_stop
assert_eq "T5 repeated stop exits 0" 0 $?
assert_eq "T5 still no guard" 0 "$(count_of_kind daemon-start)"

echo "=== T6 the reported scenario: start start stop where stop was requested first ==="
run_start
run_start
guard_before="$(pids_of_kind daemon-start | tr '\n' ' ')"
# An earlier originating time than the winning start: the fence must refuse to
# take down a probe that a later request asked to be running.
early_ts=$(( $(intent_ts) - 2000000000 ))
run_stop --intent-ts "$early_ts"
assert_eq "T6 superseded stop exits 1" 1 $?
assert_eq "T6 guard survived the superseded stop" 1 "$(count_of_kind daemon-start)"
assert_eq "T6 same guard pid, it was never restarted" "$guard_before" \
    "$(pids_of_kind daemon-start | tr '\n' ' ')"
assert_eq "T6 cron guard untouched by the superseded stop" 1 "$(cron_marker_count)"
assert_eq "T6 latest intent still start" "start" "$(intent_action)"
if grep -q 'operation superseded by later action' "$PROBE_LOG" 2>/dev/null \
        && grep -q 'blocking caller' "$PROBE_LOG" 2>/dev/null; then
    ok "T6 intercept log present"
else
    fail "T6 intercept log present"
fi

echo "=== T7 a stop requested later does win ==="
run_stop
assert_eq "T7 later stop exits 0" 0 $?
assert_eq "T7 guard stopped" 0 "$(count_of_kind daemon-start)"
assert_eq "T7 cron deregistered" 0 "$(cron_marker_count)"

echo "=== T8 mirror image: start superseded by a later stop ==="
early_ts=$(( $(intent_ts) - 2000000000 ))
run_start --intent-ts "$early_ts"
assert_eq "T8 superseded start exits 0" 0 $?
assert_eq "T8 probe stays down" 0 "$(count_of_kind daemon-start)"
assert_eq "T8 cron stays deregistered" 0 "$(cron_marker_count)"
if grep -q 'latest intent state verified' "$PROBE_LOG" 2>/dev/null; then
    ok "T8 latest intent verified log present"
else
    fail "T8 latest intent verified log present"
fi

echo "=== T9 superseded but outcome already matches is silent success ==="
# A later stop is on record and the probe is already down, so this stop has
# nothing to complain about: exit 0, not 3.
early_ts=$(( $(intent_ts) - 1000000000 ))
run_stop --intent-ts "$early_ts"
assert_eq "T9 superseded stop with matching outcome exits 0" 0 $?
assert_eq "T9 probe still down" 0 "$(count_of_kind daemon-start)"

echo "=== T10 management processes are never killed by stop ==="
run_start >/dev/null 2>&1
# disown so bash does not print a job-control notice when the fixture is killed.
( cd "$ROOT" && exec ./bin/dbha-probe gen-config >/dev/null 2>&1 ) &
disown $! 2>/dev/null || true
sleep 0.5
assert_eq "T10 gen-config fixture is running" 1 "$(count_of_kind gen-config)"
run_stop
assert_eq "T10 stop exits 0" 0 $?
assert_eq "T10 guard stopped" 0 "$(count_of_kind daemon-start)"
# The whole reason the classifier uses a whitelist: DBM runs gen-config right
# before start-probe.sh and it holds probe.yaml.lock.
assert_eq "T10 gen-config survived the stop" 1 "$(count_of_kind gen-config)"
kill_test_procs
sleep 0.3

echo "=== T11 an orphaned worker is cleaned up by stop ==="
: > "$MOCK_CRONTAB_FILE"
( cd "$ROOT" && exec ./bin/dbha-probe >/dev/null 2>&1 ) &
disown $! 2>/dev/null || true
sleep 0.5
assert_eq "T11 orphan worker fixture is running" 1 "$(count_of_kind worker)"
run_stop
assert_eq "T11 stop exits 0" 0 $?
assert_eq "T11 orphan worker terminated" 0 "$(count_of_kind worker)"

echo "=== T12 lock contention behaviour ==="
# Hold the action lock from outside and check both blocking and cron paths.
flock -x "${ROOT}/pids/probe.action.lock" -c 'sleep 6' &
holder=$!
sleep 0.5
DBHA_LOCK_WAIT=1 run_start
assert_eq "T12 interactive start fails when the lock is held" 1 $?
# cron runs every minute and will retry, so contention must not be an error.
DBHA_LOCK_WAIT=1 run_start --from-cron
assert_eq "T12 cron start exits 0 on contention" 0 $?
wait "$holder" 2>/dev/null

# Once the holder is gone the lock must be free again (trap released it).
if flock -x -n "${ROOT}/pids/probe.action.lock" -c true; then
    ok "T12 action lock released after the holder exited"
else
    fail "T12 action lock released after the holder exited"
fi

echo "=== T13 scripts release their locks on exit ==="
run_start
if flock -x -n "${ROOT}/pids/probe.action.lock" -c true; then
    ok "T13 action lock free after a successful start"
else
    fail "T13 action lock free after a successful start" "lock still held"
fi
run_stop
if flock -x -n "${ROOT}/pids/probe.action.lock" -c true; then
    ok "T13 action lock free after a successful stop"
else
    fail "T13 action lock free after a successful stop" "lock still held"
fi
if flock -x -n "${ROOT}/pids/probe.ensure.lock" -c true; then
    ok "T13 ensure lock free after a successful stop"
else
    fail "T13 ensure lock free after a successful stop" "lock still held"
fi

echo "=== T14 mkdir lock fallback keeps the same guarantees ==="
: > "$MOCK_CRONTAB_FILE"
DBHA_LOCK_FORCE_MKDIR=1 run_start
assert_eq "T14 start with the mkdir fallback exits 0" 0 $?
assert_eq "T14 one guard running" 1 "$(count_of_kind daemon-start)"
DBHA_LOCK_FORCE_MKDIR=1 run_stop
assert_eq "T14 stop with the mkdir fallback exits 0" 0 $?
assert_eq "T14 no guard left" 0 "$(count_of_kind daemon-start)"
if [ -d "${ROOT}/pids/probe.action.lock.d" ]; then
    fail "T14 mkdir lock placeholder removed on exit" "placeholder still present"
else
    ok "T14 mkdir lock placeholder removed on exit"
fi

echo "=== T15 concurrent start/stop mix converges ==="
: > "$MOCK_CRONTAB_FILE"
run_start >/dev/null 2>&1
# Everything below shares one originating timestamp except the last stop, which
# is strictly newer, so the converged state must be "stopped".
base_ts="$(intent_ts)"
run_start --intent-ts "$(( base_ts + 1000000000 ))" &
run_stop  --intent-ts "$(( base_ts + 2000000000 ))" &
run_start --intent-ts "$(( base_ts + 1500000000 ))" &
run_stop  --intent-ts "$(( base_ts + 3000000000 ))" &
wait
assert_eq "T15 converged to the latest intent (stop)" "stop" "$(intent_action)"
assert_eq "T15 no guard running" 0 "$(count_of_kind daemon-start)"
assert_eq "T15 cron deregistered" 0 "$(cron_marker_count)"

echo "=== T17 start-probe argument and missing-file paths ==="
( cd "$ROOT" && ./start-probe.sh --help >/dev/null 2>&1 )
assert_eq "T17 --help exits 0" 0 $?
( cd "$ROOT" && ./start-probe.sh --bogus >/dev/null 2>&1 )
assert_eq "T17 unknown argument exits 1" 1 $?
( cd "$ROOT" && ./start-probe.sh --intent-ts >/dev/null 2>&1 )
assert_eq "T17 empty --intent-ts exits 1" 1 $?
mv "${ROOT}/bin/dbha-probe" "${ROOT}/bin/dbha-probe.off"
( cd "$ROOT" && ./start-probe.sh >/dev/null 2>&1 )
assert_eq "T17 missing binary exits 1" 1 $?
mv "${ROOT}/bin/dbha-probe.off" "${ROOT}/bin/dbha-probe"
mv "${ROOT}/etc/probe.yaml" "${ROOT}/etc/probe.yaml.off"
( cd "$ROOT" && ./start-probe.sh >/dev/null 2>&1 )
assert_eq "T17 missing config exits 1" 1 $?
mv "${ROOT}/etc/probe.yaml.off" "${ROOT}/etc/probe.yaml"
( PATH="${MOCKBIN}:$(hide_bin_without pgrep)"; cd "$ROOT" && ./start-probe.sh >/dev/null 2>&1 )
assert_eq "T17 missing pgrep exits 1" 1 $?
rm -f "${ROOT}/pids/probe.action.lock"
ln -s "${ROOT}/pids/probe.ensure.lock" "${ROOT}/pids/probe.action.lock"
( cd "$ROOT" && ./start-probe.sh >/dev/null 2>&1 )
assert_eq "T17 symlink action lock exits 1" 1 $?
rm -f "${ROOT}/pids/probe.action.lock"

echo "=== T18 --from-cron success does not record intent or cron ==="
: > "$MOCK_CRONTAB_FILE"
run_stop >/dev/null 2>&1
stop_intent="$(intent_action)"
: > "$PROBE_LOG"
run_start --from-cron
assert_eq "T18 from-cron start exits 0" 0 $?
assert_eq "T18 from-cron start left one guard" 1 "$(count_of_kind daemon-start)"
assert_eq "T18 from-cron start did not register cron" 0 "$(cron_marker_count)"
assert_eq "T18 from-cron start did not rewrite intent" "$stop_intent" "$(intent_action)"
if grep -q 'lock impl:' "$PROBE_LOG" 2>/dev/null; then
    fail "T18 from-cron suppressed lock-impl info lines"
else
    ok "T18 from-cron suppressed lock-impl info lines"
fi
run_stop >/dev/null 2>&1

echo "=== T19 ensure failure and liveness check ==="
run_start >/dev/null 2>&1
assert_eq "T19 baseline cron present" 1 "$(cron_marker_count)"
: > "$PROBE_LOG"
FAKE_PROBE_ENSURE_FAIL=1 run_start
assert_eq "T19 ensure fail on a live guard still exits 1" 1 $?
assert_eq "T19 ensure fail kept the cron line" 1 "$(cron_marker_count)"
run_stop >/dev/null 2>&1
: > "$MOCK_CRONTAB_FILE"
: > "$PROBE_LOG"
FAKE_PROBE_ENSURE_FAIL=1 run_start
assert_eq "T19 ensure fail from a stopped probe exits 1" 1 $?
assert_eq "T19 ensure fail did not register cron" 0 "$(cron_marker_count)"
: > "$PROBE_LOG"
FAKE_PROBE_ENSURE_NO_SPAWN=1 DBHA_START_VERIFY_WAIT=1 run_start
assert_eq "T19 interactive start without an observed guard exits 1" 1 $?
if grep -q 'guard not observed after ensure' "$PROBE_LOG" 2>/dev/null; then
    ok "T19 interactive missing-guard path logged an error"
else
    fail "T19 interactive missing-guard path logged an error"
fi
: > "$PROBE_LOG"
FAKE_PROBE_ENSURE_NO_SPAWN=1 DBHA_START_VERIFY_WAIT=1 run_start --from-cron
assert_eq "T19 from-cron missing-guard exits 0" 0 $?
if grep -q 'guard not observed after ensure' "$PROBE_LOG" 2>/dev/null; then
    ok "T19 from-cron missing-guard path logged a warning"
else
    fail "T19 from-cron missing-guard path logged a warning"
fi
DBHA_START_VERIFY_WAIT=0 run_start
assert_eq "T19 VERIFY_WAIT=0 with a real ensure exits 0" 0 $?
assert_eq "T19 VERIFY_WAIT=0 left a guard running" 1 "$(count_of_kind daemon-start)"
run_stop >/dev/null 2>&1

echo "=== T20 yield_ok start restores a missing cron line ==="
run_start >/dev/null 2>&1
early_start_ts="$(intent_ts)"
: > "$MOCK_CRONTAB_FILE"
run_start --intent-ts "$(( early_start_ts - 2000000000 ))"
assert_eq "T20 superseded-but-matching start exits 0" 0 $?
assert_eq "T20 cron line restored" 1 "$(cron_marker_count)"
assert_eq "T20 guard still running" 1 "$(count_of_kind daemon-start)"
run_stop >/dev/null 2>&1

echo "=== T21 stop ensure-lock degrade, args, residue ==="
run_start >/dev/null 2>&1
: > "$PROBE_LOG"
flock -x "${ROOT}/pids/probe.ensure.lock" -c 'sleep 8' &
ensure_holder=$!
sleep 0.3
DBHA_ENSURE_LOCK_WAIT=1 run_stop
assert_eq "T21 stop exits 0 while ensure lock is held" 0 $?
assert_eq "T21 guard stopped despite ensure lock" 0 "$(count_of_kind daemon-start)"
if grep -q 'degraded to best-effort' "$PROBE_LOG" 2>/dev/null; then
    ok "T21 stop logged ensure-lock degrade"
else
    fail "T21 stop logged ensure-lock degrade"
fi
wait "$ensure_holder" 2>/dev/null || true

( cd "$ROOT" && ./stop-probe.sh --bogus >/dev/null 2>&1 )
assert_eq "T21 unknown stop argument exits 1" 1 $?
mv "${ROOT}/bin/dbha-probe" "${ROOT}/bin/dbha-probe.off"
( cd "$ROOT" && ./stop-probe.sh >/dev/null 2>&1 )
assert_eq "T21 stop with missing binary exits 1" 1 $?
mv "${ROOT}/bin/dbha-probe.off" "${ROOT}/bin/dbha-probe"
flock -x "${ROOT}/pids/probe.action.lock" -c 'sleep 6' &
stop_lock_holder=$!
sleep 0.3
DBHA_LOCK_WAIT=1 run_stop
assert_eq "T21 stop fails when the action lock is held" 1 $?
wait "$stop_lock_holder" 2>/dev/null || true

: > "$MOCK_CRONTAB_FILE"
FAKE_PROBE_IGNORE_TERM=1 run_start
assert_eq "T21 ignore-term start exits 0" 0 $?
sleep 0.4
assert_eq "T21 ignore-term fixture started" 1 "$(count_of_kind daemon-start)"
FAKE_PROBE_IGNORE_TERM=1 run_stop
assert_eq "T21 IGNORE_TERM guard is killed" 0 "$(count_of_kind daemon-start)"

: > "$MOCK_CRONTAB_FILE"
FAKE_PROBE_RESPAWN_ONCE=1 run_start
: > "$PROBE_LOG"
run_stop
assert_eq "T21 RESPAWN_ONCE stop exits 0" 0 $?
assert_eq "T21 RESPAWN_ONCE left no guard" 0 "$(count_of_kind daemon-start)"
assert_eq "T21 RESPAWN_ONCE removed cron" 0 "$(cron_marker_count)"
if grep -q 'residue detected after first stop pass' "$PROBE_LOG" 2>/dev/null; then
    ok "T21 RESPAWN_ONCE took the residue retry path"
else
    fail "T21 RESPAWN_ONCE took the residue retry path"
fi

: > "$MOCK_CRONTAB_FILE"
FAKE_PROBE_RESPAWN_ALWAYS=1 run_start
intent_before_always="$(intent_action)"
: > "$PROBE_LOG"
run_stop
assert_eq "T21 RESPAWN_ALWAYS stop exits 1" 1 $?
assert_eq "T21 RESPAWN_ALWAYS restored cron" 1 "$(cron_marker_count)"
assert_eq "T21 RESPAWN_ALWAYS did not record a successful stop" \
    "$intent_before_always" "$(intent_action)"
kill_test_procs
: > "$MOCK_CRONTAB_FILE"

echo "=== T22 fence disabled falls back to locking ==="
run_start >/dev/null 2>&1
early_ts="$(intent_ts)"
DBHA_INTENT_FENCE=0 run_stop --intent-ts "$(( early_ts - 2000000000 ))"
assert_eq "T22 older stop proceeds when the fence is off" 0 $?
assert_eq "T22 fence-off stop left no guard" 0 "$(count_of_kind daemon-start)"

echo "=== T23 stop intercepts when only the cron marker remains ==="
run_start
kill_test_procs
sleep 0.3
assert_eq "T23 fixture has no guard" 0 "$(count_of_kind daemon-start)"
assert_eq "T23 fixture kept cron" 1 "$(cron_marker_count)"
cron_before="$(cron_marker_count)"
early_ts=$(( $(intent_ts) - 2000000000 ))
: > "$PROBE_LOG"
run_stop --intent-ts "$early_ts"
assert_eq "T23 stop with leftover cron exits 1" 1 $?
assert_eq "T23 crontab unchanged" "$cron_before" "$(cron_marker_count)"

echo "=== T24 start verify fails when latest stop state is not reached ==="
# Later intent is stop, but the cron marker is still present so stop is not reached.
now_ts="$(date +%s%N 2>/dev/null || echo "$(date +%s)000000000")"
printf '%s stop \n' "$now_ts" > "${ROOT}/pids/probe.intent"
: > "$PROBE_LOG"
DBHA_SUPERSEDE_VERIFY_WAIT=1 run_start --intent-ts "$(( now_ts - 2000000000 ))"
assert_eq "T24 superseded start with unmet stop exits 1" 1 $?
if grep -q 'latest intent state not reached' "$PROBE_LOG" 2>/dev/null; then
    ok "T24 unmet latest-intent log present"
else
    fail "T24 unmet latest-intent log present"
fi
DBHA_INTENT_FENCE=0 run_stop >/dev/null 2>&1
: > "$MOCK_CRONTAB_FILE"

echo "=== O deleted-exe orphans ==="
run_start
old_pid="$(pids_of_kind daemon-start | head -n 1)"
make_deleted_exe_orphan
run_start
assert_eq "O1 start after deleted exe exits 0" 0 $?
if exe_belongs_here "$old_pid"; then
    fail "O1 old guard pid is gone" "still a probe of this install: ${old_pid}"
else
    ok "O1 old guard pid is gone"
fi
assert_eq "O1 exactly one guard remains" 1 "$(count_of_kind daemon-start)"
new_pid="$(pids_of_kind daemon-start | head -n 1)"
if [ "$new_pid" = "$old_pid" ]; then
    fail "O1 remaining guard is a new process" "pid reused: ${old_pid}"
else
    ok "O1 remaining guard is a new process"
fi
kill_test_procs
: > "$MOCK_CRONTAB_FILE"

run_start
old_pid="$(pids_of_kind daemon-start | head -n 1)"
make_deleted_exe_orphan
run_stop
assert_eq "O2 stop of deleted-exe orphan exits 0" 0 $?
if exe_belongs_here "$old_pid"; then
    fail "O2 orphan is gone after stop"
else
    ok "O2 orphan is gone after stop"
fi
assert_eq "O2 no guard left" 0 "$(count_of_kind daemon-start)"
kill_test_procs
: > "$MOCK_CRONTAB_FILE"

FAKE_PROBE_IGNORE_TERM=1 run_start
old_pid="$(pids_of_kind daemon-start | head -n 1)"
make_deleted_exe_orphan
run_stop
assert_eq "O3 IGNORE_TERM orphan stop exits 0" 0 $?
if exe_belongs_here "$old_pid"; then
    fail "O3 IGNORE_TERM orphan was KILLed"
else
    ok "O3 IGNORE_TERM orphan was KILLed"
fi
kill_test_procs
: > "$MOCK_CRONTAB_FILE"

run_start
old_pid="$(pids_of_kind daemon-start | head -n 1)"
make_deleted_exe_orphan
rm -f "${ROOT}/pids/probe.pid"
: > "$PROBE_LOG"
DBHA_REAP_DELETED_EXE=0 run_start
assert_eq "O4 reap-disabled start exits 0" 0 $?
if exe_belongs_here "$old_pid"; then
    ok "O4 orphan still alive when reap is disabled"
else
    fail "O4 orphan still alive when reap is disabled"
fi
if grep -q 'reap disabled' "$PROBE_LOG" 2>/dev/null; then
    ok "O4 reap-disabled warning present"
else
    fail "O4 reap-disabled warning present"
fi
kill -KILL "$old_pid" 2>/dev/null || true
kill_test_procs
: > "$MOCK_CRONTAB_FILE"

run_start
old_pid="$(pids_of_kind daemon-start | head -n 1)"
make_deleted_exe_orphan
now_ts="$(date +%s%N 2>/dev/null || echo "$(date +%s)000000000")"
printf '%s stop \n' "$now_ts" > "${ROOT}/pids/probe.intent"
: > "$MOCK_CRONTAB_FILE"
: > "$PROBE_LOG"
run_start --intent-ts "$(( now_ts - 2000000000 ))"
assert_eq "O5 start after orphan+later-stop exits 0" 0 $?
if exe_belongs_here "$old_pid"; then
    fail "O5 orphan reaped before the fence"
else
    ok "O5 orphan reaped before the fence"
fi
if grep -q 'latest intent state verified' "$PROBE_LOG" 2>/dev/null; then
    ok "O5 fence verified stop after reap"
else
    fail "O5 fence verified stop after reap"
fi
kill_test_procs
: > "$MOCK_CRONTAB_FILE"

echo "=== K keepalive lifecycle ==="
: > "$MOCK_CRONTAB_FILE"
KA_ADDR="127.0.0.1:18080"
KA_RUNTIME="${XDG_STATE_HOME}/dbha-v2/runtime"
KA_INTENT="${KA_RUNTIME}/probe-keepalive.intent"

ka_count() {
    local pid exe cmdline n=0
    for pid in $(pgrep -x dbha-probe 2>/dev/null || true); do
        exe="$(readlink -f "/proc/${pid}/exe" 2>/dev/null || true)"
        [ "$exe" = "$EXPECTED_EXE" ] || continue
        cmdline="$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)"
        case "$cmdline" in
            *ensure-keepalive*) ;;
            *--ping-http-addr*"${1:-}"*) n=$(( n + 1 )) ;;
        esac
    done
    echo "$n"
}

ka_cron_count() {
    grep -c 'DBHA_PROBE_KEEPALIVE_GUARD' "${ROOT}/crontab.store" 2>/dev/null || true
}

run_ka_start() {
    ( cd "$ROOT" && ./start-probe-keepalive.sh "$@" >/dev/null 2>&1 )
}

run_ka_stop() {
    ( cd "$ROOT" && ./stop-probe-keepalive.sh "$@" >/dev/null 2>&1 )
}

cp "${SCRIPTS_DIR}/start-probe-keepalive.sh" "${SCRIPTS_DIR}/stop-probe-keepalive.sh" "${ROOT}/"

run_ka_start --ping-http-addr "$KA_ADDR"
assert_eq "K1 keepalive start exits 0" 0 $?
assert_eq "K1 one keepalive process running" 1 "$(ka_count "$KA_ADDR")"
assert_eq "K1 keepalive cron registered" 1 "$(ka_cron_count)"
assert_eq "K1 intent recorded with addr" "start ${KA_ADDR}" \
    "$(awk '{print $2, $3}' "$KA_INTENT" 2>/dev/null || true)"

run_ka_start --ping-http-addr "$KA_ADDR"
assert_eq "K2 repeated keepalive start exits 0" 0 $?
assert_eq "K2 still one keepalive process" 1 "$(ka_count "$KA_ADDR")"

# Same fence semantics as the probe: an earlier request must not undo a later one.
ka_ts="$(awk '{print $1}' "$KA_INTENT" 2>/dev/null || echo 0)"
run_ka_stop --intent-ts "$(( ka_ts - 2000000000 ))"
assert_eq "K3 superseded keepalive stop exits 1" 1 $?
assert_eq "K3 keepalive survived the superseded stop" 1 "$(ka_count "$KA_ADDR")"
assert_eq "K3 keepalive cron untouched" 1 "$(ka_cron_count)"

run_ka_stop
assert_eq "K4 keepalive stop exits 0" 0 $?
assert_eq "K4 keepalive stopped" 0 "$(ka_count "$KA_ADDR")"
assert_eq "K4 keepalive cron deregistered" 0 "$(ka_cron_count)"
if [ -f "${KA_RUNTIME}/probe-keepalive.pid" ]; then
    fail "K4 keepalive state files removed" "pid file still present"
else
    ok "K4 keepalive state files removed"
fi

run_ka_stop
assert_eq "K5 repeated keepalive stop exits 0" 0 $?

# A keepalive operation must not disturb the probe guard: they use different
# locks, markers and intent files.
run_start >/dev/null 2>&1
run_ka_start --ping-http-addr "$KA_ADDR" >/dev/null 2>&1
assert_eq "K6 probe guard unaffected by keepalive start" 1 "$(count_of_kind daemon-start)"
run_ka_stop >/dev/null 2>&1
assert_eq "K6 probe guard unaffected by keepalive stop" 1 "$(count_of_kind daemon-start)"
assert_eq "K6 probe cron line still present" 1 "$(cron_marker_count)"
run_stop >/dev/null 2>&1

echo "=== K7 keepalive argument, fence-skip and degrade paths ==="
( cd "$ROOT" && ./start-probe-keepalive.sh >/dev/null 2>&1 )
assert_eq "K7 missing --ping-http-addr exits 1" 1 $?
( cd "$ROOT" && ./start-probe-keepalive.sh --ping-http-addr 'not-host-port' >/dev/null 2>&1 )
assert_eq "K7 invalid addr exits 1" 1 $?
( cd "$ROOT" && ./start-probe-keepalive.sh --ping-http-addr '::1:18080' >/dev/null 2>&1 )
assert_eq "K7 unbracketed IPv6 addr exits 1" 1 $?
run_ka_start --ping-http-addr=[::1]:18081
assert_eq "K7 IPv6 equals-form start exits 0" 0 $?
assert_eq "K7 IPv6 keepalive running" 1 "$(ka_count "[::1]:18081")"
run_ka_stop
assert_eq "K7 IPv6 keepalive stopped" 0 "$(ka_count "[::1]:18081")"

run_ka_start --ping-http-addr "$KA_ADDR"
flock -x "${KA_RUNTIME}/probe-keepalive.action.lock" -c 'sleep 6' &
ka_lock_holder=$!
sleep 0.3
DBHA_LOCK_WAIT=1 run_ka_start --ping-http-addr "$KA_ADDR"
assert_eq "K7 interactive keepalive start fails on lock contention" 1 $?
DBHA_LOCK_WAIT=1 run_ka_start --from-cron --ping-http-addr "$KA_ADDR"
assert_eq "K7 from-cron keepalive start exits 0 on contention" 0 $?
wait "$ka_lock_holder" 2>/dev/null || true
run_ka_stop >/dev/null 2>&1

: > "$MOCK_CRONTAB_FILE"
run_ka_stop >/dev/null 2>&1
ka_intent_before="$(awk '{print $2}' "$KA_INTENT" 2>/dev/null || true)"
run_ka_start --from-cron --ping-http-addr "$KA_ADDR"
assert_eq "K7 from-cron keepalive start exits 0" 0 $?
assert_eq "K7 from-cron keepalive did not rewrite intent" "$ka_intent_before" \
    "$(awk '{print $2}' "$KA_INTENT" 2>/dev/null || true)"
run_ka_stop >/dev/null 2>&1

run_ka_start --ping-http-addr "$KA_ADDR"
rm -f "${KA_RUNTIME}/probe-keepalive.pid"
run_ka_stop
assert_eq "K7 stop without pid file still exits 0" 0 $?
assert_eq "K7 fallback scan stopped keepalive" 0 "$(ka_count "$KA_ADDR")"

run_ka_start --ping-http-addr "$KA_ADDR"
ka_ts="$(awk '{print $1}' "$KA_INTENT" 2>/dev/null || echo 0)"
rm -f "${KA_RUNTIME}/probe-keepalive.addr"
: > "$KA_LOG"
run_ka_stop --intent-ts "$(( ka_ts - 2000000000 ))"
assert_eq "K7 stop without addr file skips the fence and exits 0" 0 $?
assert_eq "K7 keepalive was stopped despite an older intent" 0 "$(ka_count "$KA_ADDR")"
if grep -q 'keepalive addr file missing, skipping intent fence' "$KA_LOG" 2>/dev/null; then
    ok "K7 missing-addr path logged skip-fence"
else
    fail "K7 missing-addr path logged skip-fence"
fi

run_ka_start --ping-http-addr "$KA_ADDR"
: > "$KA_LOG"
flock -x "${KA_RUNTIME}/probe-keepalive.ensure.lock" -c 'sleep 8' &
ka_ensure_holder=$!
sleep 0.3
DBHA_ENSURE_LOCK_WAIT=1 run_ka_stop
assert_eq "K7 keepalive stop exits 0 while ensure lock is held" 0 $?
assert_eq "K7 keepalive stopped despite ensure lock" 0 "$(ka_count "$KA_ADDR")"
if grep -q 'degraded to best-effort' "$KA_LOG" 2>/dev/null; then
    ok "K7 keepalive stop logged ensure-lock degrade"
else
    fail "K7 keepalive stop logged ensure-lock degrade"
fi
wait "$ka_ensure_holder" 2>/dev/null || true

: > "$MOCK_CRONTAB_FILE"
run_ka_start --ping-http-addr "$KA_ADDR"
assert_eq "K7 cron present before ensure-fail" 1 "$(ka_cron_count)"
FAKE_PROBE_ENSURE_FAIL=1 run_ka_start --ping-http-addr "$KA_ADDR"
assert_eq "K7 ensure-keepalive fail exits 1" 1 $?
assert_eq "K7 ensure-keepalive fail kept cron" 1 "$(ka_cron_count)"
run_ka_stop >/dev/null 2>&1

: > "$MOCK_CRONTAB_FILE"
FAKE_PROBE_RESPAWN_ALWAYS=1 run_ka_start --ping-http-addr "$KA_ADDR"
rm -f "${KA_RUNTIME}/probe-keepalive.addr"
: > "$KA_LOG"
run_ka_stop
assert_eq "K7 missing-addr residue stop exits 1" 1 $?
assert_eq "K7 absent already dropped the cron line before residue" 0 "$(ka_cron_count)"
if grep -q 'cannot restore keepalive cron, reason: addr missing' "$KA_LOG" 2>/dev/null; then
    ok "K7 missing-addr residue logged keep (cannot rebuild cron)"
else
    fail "K7 missing-addr residue logged keep (cannot rebuild cron)"
fi
if grep -E 'ensure-keepalive --ping-http-addr[[:space:]]*$' "${ROOT}/crontab.store" \
        >/dev/null 2>&1; then
    fail "K7 missing-addr residue did not write a broken cron command"
else
    ok "K7 missing-addr residue did not write a broken cron command"
fi
kill_test_procs

echo "=== T16 server-side scripts still parse and stay independent ==="
for f in start-server.sh stop-server.sh lib/guard-utils.sh setup.sh deploy.sh; do
    if bash -n "${SCRIPTS_DIR}/${f}" 2>/dev/null; then
        ok "T16 syntax ok: ${f}"
    else
        fail "T16 syntax ok: ${f}"
    fi
done

echo
echo "tests run: ${TESTS_RUN}, failed: ${TESTS_FAILED}"
[ "$TESTS_FAILED" -eq 0 ]
