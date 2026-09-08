#!/usr/bin/env bash
# Deterministic unit tests for scripts/lib/probe-lifecycle-utils.sh.
#
# Run: scripts/tests/test-guard-lock.sh
# No root, no real probe binary and no real crontab required: crontab is mocked
# through PATH and every IP literal is a loopback address.

# Deliberately no "set -e": a failing assertion must not abort the whole run.
set -uo pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS_DIR="$(cd "${SELF_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${SCRIPTS_DIR}/../../../.." && pwd)"

TESTS_RUN=0
TESTS_FAILED=0

TMPROOT="$(mktemp -d)"
trap 'rm -rf "$TMPROOT"' EXIT

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
    local name="$1" want="$2" got="$3"
    if [ "$want" = "$got" ]; then
        ok "$name"
    else
        fail "$name" "want: [${want}] got: [${got}]"
    fi
}

assert_rc() {
    local name="$1" want="$2" got="$3"
    if [ "$want" = "$got" ]; then
        ok "$name"
    else
        fail "$name" "want rc: ${want} got rc: ${got}"
    fi
}

# --- mock crontab ---

MOCKBIN="${TMPROOT}/bin"
mkdir -p "$MOCKBIN"
export MOCK_CRONTAB_FILE="${TMPROOT}/crontab.store"
: > "$MOCK_CRONTAB_FILE"

cat > "${MOCKBIN}/crontab" <<'MOCK'
#!/usr/bin/env bash
store="${MOCK_CRONTAB_FILE}"
case "${1:-}" in
    -l)
        if [ -s "$store" ]; then
            cat "$store"
        else
            echo "no crontab for tester" >&2
            exit 1
        fi
        ;;
    -)
        cat > "$store"
        ;;
    *)
        exit 1
        ;;
esac
MOCK
chmod +x "${MOCKBIN}/crontab"
PATH="${MOCKBIN}:${PATH}"
export PATH

cron_lines() {
    local n
    # grep -c already prints 0 when nothing matches, and exits 1; a "|| echo 0"
    # here would emit a second line.
    n="$(grep -c '[^[:space:]]' "$MOCK_CRONTAB_FILE" 2>/dev/null)" || n=0
    echo "${n:-0}"
}

# --- load the libraries under test ---

LOG_FILE="${TMPROOT}/test.log"
: > "$LOG_FILE"
# shellcheck source=../lib/guard-utils.sh
source "${SCRIPTS_DIR}/lib/guard-utils.sh"
# shellcheck source=../lib/probe-lifecycle-utils.sh
source "${SCRIPTS_DIR}/lib/probe-lifecycle-utils.sh"

probe_apply_defaults >/dev/null 2>&1

echo "=== A. process classification (whitelist) ==="

check_kind() {
    local want="$1" cmdline="$2" got
    got="$(probe_cmdline_kind_from_args "$cmdline")"
    assert_eq "kind[${want}] ${cmdline}" "$want" "$got"
}

check_kind guard   "/opt/p/bin/dbha-probe daemon-start -c etc/probe.yaml"
check_kind worker  "/opt/p/bin/dbha-probe -c etc/probe.yaml"
check_kind worker  "/opt/p/bin/dbha-probe --config etc/probe.yaml"
check_kind worker  "/opt/p/bin/dbha-probe --config=etc/probe.yaml"
check_kind worker  "/opt/p/bin/dbha-probe"
# A path merely containing the word "ensure" must not read as the subcommand.
check_kind worker  "/opt/p/bin/dbha-probe -c /data/ensure/etc/probe.yaml"
check_kind unknown "/opt/p/bin/dbha-probe ensure -c etc/probe.yaml"
check_kind unknown "/opt/p/bin/dbha-probe ensure-keepalive --ping-http-addr 127.0.0.1:18080"
# The reason the whitelist exists: DBM runs gen-config right before start, and
# these must never be selected for TERM/KILL by stop-probe.sh.
check_kind unknown "/opt/p/bin/dbha-probe health -c etc/probe.yaml"
check_kind unknown "/opt/p/bin/dbha-probe gen-config -o etc/probe.yaml"
check_kind unknown "/opt/p/bin/dbha-probe reload -c etc/probe.yaml"
check_kind unknown "/opt/p/bin/dbha-probe version"
check_kind keepalive "/opt/p/bin/dbha-probe --ping-http-addr 127.0.0.1:18080"
check_kind keepalive "/opt/p/bin/dbha-probe --ping-http-addr=[::1]:18080"
# argv must never be glob-expanded against the cwd.
check_kind unknown "/opt/p/bin/dbha-probe *"

echo "=== B. locks ==="

LOCKDIR="${TMPROOT}/pids"
mkdir -p "$LOCKDIR"

# B1 flock mutual exclusion: a second holder in a separate process must fail.
if command -v flock >/dev/null 2>&1; then
    (
        probe_acquire_lock "${LOCKDIR}/b1.lock" 9 5 0 >/dev/null 2>&1 || exit 9
        # flock is per open-file-description, so a fresh open in another process
        # must be refused while we hold it.
        bash -c "
            LOG_FILE='${LOG_FILE}'
            source '${SCRIPTS_DIR}/lib/guard-utils.sh'
            source '${SCRIPTS_DIR}/lib/probe-lifecycle-utils.sh'
            probe_apply_defaults >/dev/null 2>&1
            probe_acquire_lock '${LOCKDIR}/b1.lock' 9 1 1 >/dev/null 2>&1
        " 9>&-
        exit $?
    )
    assert_rc "B1 flock refuses a second holder" 1 $?

    # B2 released lock is reusable.
    (
        probe_acquire_lock "${LOCKDIR}/b2.lock" 9 5 0 >/dev/null 2>&1 || exit 9
    )
    (
        probe_acquire_lock "${LOCKDIR}/b2.lock" 9 5 1 >/dev/null 2>&1 || exit 1
    )
    assert_rc "B2 lock reusable after holder exits" 0 $?
else
    ok "B1 flock refuses a second holder (skipped: no flock)"
    ok "B2 lock reusable after holder exits (skipped: no flock)"
fi

# B3 mkdir fallback mutual exclusion.
(
    DBHA_LOCK_FORCE_MKDIR=1
    probe_acquire_lock "${LOCKDIR}/b3.lock" 9 2 0 >/dev/null 2>&1 || exit 9
    # The placeholder now exists, so a second acquisition must be refused.
    probe_acquire_mkdir_lock "${LOCKDIR}/b3.lock" 1 1 >/dev/null 2>&1
    exit $?
)
assert_rc "B3 mkdir lock refuses a second holder" 1 $?

# B4 stale placeholder from a dead pid is reclaimed.
DEAD_LOCK="${LOCKDIR}/b4.lock"
mkdir -p "${DEAD_LOCK}.d"
# Start and reap a process so the pid is known-dead rather than guessed.
sleep 0 & dead_pid=$!
wait "$dead_pid" 2>/dev/null
echo "$dead_pid" > "${DEAD_LOCK}.d/pid"
probe_lc_now > "${DEAD_LOCK}.d/ts"
(
    DBHA_LOCK_FORCE_MKDIR=1
    probe_acquire_lock "$DEAD_LOCK" 9 3 0 >/dev/null 2>&1
    exit $?
)
assert_rc "B4 stale mkdir lock reclaimed from dead holder" 0 $?

# B5 a live holder must make the wait end on the deadline, not spin forever.
LIVE_LOCK="${LOCKDIR}/b5.lock"
mkdir -p "${LIVE_LOCK}.d"
echo "$$" > "${LIVE_LOCK}.d/pid"
probe_lc_now > "${LIVE_LOCK}.d/ts"
b5_start="$(date +%s)"
(
    DBHA_LOCK_FORCE_MKDIR=1
    probe_acquire_lock "$LIVE_LOCK" 9 2 0 >/dev/null 2>&1
    exit $?
)
b5_rc=$?
b5_elapsed=$(( $(date +%s) - b5_start ))
assert_rc "B5 blocked mkdir lock gives up instead of hanging" 1 "$b5_rc"
if [ "$b5_elapsed" -ge 1 ] && [ "$b5_elapsed" -le 8 ]; then
    ok "B5 wait respected the 2s budget (elapsed: ${b5_elapsed}s)"
else
    fail "B5 wait respected the 2s budget" "elapsed: ${b5_elapsed}s"
fi
rm -rf "${LIVE_LOCK}.d"

# B6 nested invocation is refused rather than deadlocking on itself.
(
    export DBHA_PROBE_ACTION_LOCK_HELD="${LOCKDIR}/b6.lock"
    probe_guard_nested_call "${LOCKDIR}/b6.lock" >/dev/null 2>&1
    exit $?
)
assert_rc "B6 nested invocation refused" 1 $?
(
    export DBHA_PROBE_ACTION_LOCK_HELD="${LOCKDIR}/other.lock"
    probe_guard_nested_call "${LOCKDIR}/b6.lock" >/dev/null 2>&1
    exit $?
)
assert_rc "B6 unrelated lock marker does not trigger" 0 $?

# B7 lock fds must not leak into children (they would pin the lock forever).
if command -v flock >/dev/null 2>&1; then
    b7_out="$(
        probe_acquire_lock "${LOCKDIR}/b7.lock" 9 5 0 >/dev/null 2>&1
        probe_run_without_lock_fds bash -c \
            'if [ -e /proc/self/fd/9 ]; then echo OPEN; else echo CLOSED; fi'
    )"
    assert_eq "B7 fd 9 closed for child processes" "CLOSED" "$b7_out"
else
    ok "B7 fd 9 closed for child processes (skipped: no flock)"
fi

echo "=== C. intent records ==="

INTENT="${TMPROOT}/probe.intent"
rm -f "$INTENT"

probe_read_intent "$INTENT" >/dev/null 2>&1
assert_rc "C1 missing intent file reports no record" 1 $?

now_ns="$(probe_now_ns)"
probe_write_intent "$INTENT" "$now_ns" "start" >/dev/null 2>&1
assert_eq "C2 write then read back" "${now_ns} start " "$(probe_read_intent "$INTENT" 2>/dev/null)"

# Monotonic: a slow earlier operation finishing last must not roll the record
# back, otherwise an in-between action would wrongly be allowed to proceed.
probe_write_intent "$INTENT" "$(( now_ns - 1000000000 ))" "stop" >/dev/null 2>&1
assert_eq "C3 older ts does not overwrite" "${now_ns} start " "$(probe_read_intent "$INTENT" 2>/dev/null)"

probe_write_intent "$INTENT" "$(( now_ns + 1000000000 ))" "stop" >/dev/null 2>&1
assert_eq "C4 newer ts overwrites" "$(( now_ns + 1000000000 )) stop " \
    "$(probe_read_intent "$INTENT" 2>/dev/null)"

# Clock skew guard: a far-future ts means a bad clock or a bad injection.
FUTURE="${TMPROOT}/future.intent"
printf '%s stop\n' "$(( now_ns + 3600000000000 ))" > "$FUTURE"
probe_read_intent "$FUTURE" >/dev/null 2>&1
assert_rc "C5 future ts record ignored" 1 $?

BAD="${TMPROOT}/bad.intent"
printf 'garbage-not-a-number stop\n' > "$BAD"
probe_read_intent "$BAD" >/dev/null 2>&1
assert_rc "C6 corrupted ts tolerated" 1 $?
printf '%s bogus-action\n' "$now_ns" > "$BAD"
probe_read_intent "$BAD" >/dev/null 2>&1
assert_rc "C7 unknown action tolerated" 1 $?
: > "$BAD"
probe_read_intent "$BAD" >/dev/null 2>&1
assert_rc "C8 empty intent file tolerated" 1 $?

KA_INTENT="${TMPROOT}/ka.intent"
probe_write_intent "$KA_INTENT" "$now_ns" "start" "127.0.0.1:18080" >/dev/null 2>&1
assert_eq "C9 addr dimension persisted" "${now_ns} start 127.0.0.1:18080" \
    "$(probe_read_intent "$KA_INTENT" 2>/dev/null)"

echo "=== D. intent fence decisions ==="

# The fence reads real state through these helpers. Stubbing them keeps the
# decision table deterministic, and the whole section runs in a subshell so the
# real implementations survive for the sections below: re-sourcing the library
# would not restore them, since it is idempotent by design.
d_output="$(
FAKE_PIDS=""
FAKE_CRON=1
probe_get_pids() { if [ -n "$FAKE_PIDS" ]; then echo "$FAKE_PIDS"; fi; }
probe_keepalive_pids() { if [ -n "$FAKE_PIDS" ]; then echo "$FAKE_PIDS"; fi; }
probe_orphan_pids() { return 0; }
probe_keepalive_orphan_pids() { return 0; }
probe_cron_has_marker() { return "$FAKE_CRON"; }

fence_case() {
    local name="$1" rec_ts="$2" rec_action="$3" rec_addr="$4" my_ts="$5" my_action="$6"
    local pids="$7" cron_present="$8" my_addr="$9" want_action="${10}" want_cron="${11}"
    local want_latest="${12:-}"
    local f="${TMPROOT}/fence.intent"

    if [ "$rec_ts" = "-" ]; then
        rm -f "$f"
    else
        printf '%s %s %s\n' "$rec_ts" "$rec_action" "$rec_addr" > "$f"
    fi
    FAKE_PIDS="$pids"
    if [ "$cron_present" = "yes" ]; then FAKE_CRON=0; else FAKE_CRON=1; fi

    probe_fence_decide "$f" "$my_ts" "$my_action" "/opt/p/bin/dbha-probe" "MARKER" "$my_addr"
    assert_eq "${name} [action]" "$want_action" "$PROBE_LC_FENCE_ACTION"
    assert_eq "${name} [cron]" "$want_cron" "$PROBE_LC_FENCE_CRON"
    if [ -n "$want_latest" ]; then
        if [ "$want_latest" = "-" ]; then
            want_latest=""
        fi
        assert_eq "${name} [latest]" "$want_latest" "$PROBE_LC_FENCE_LATEST_ACTION"
    fi
}

T1="$(( now_ns - 5000000000 ))"
T2="$(( now_ns - 3000000000 ))"

fence_case "D1 no record" - - - "$T2" start "" no "" continue keep
fence_case "D2 older record" "$T1" stop "" "$T2" start "" no "" continue keep

# The scenario from the original report: start start stop where the stop was
# requested first but runs last. It must not take the probe down.
fence_case "D3 stop superseded by later start, probe up" \
    "$T2" start "" "$T1" stop "4242" yes "" yield_conflict keep start
# And the mirror image: a start that lost to a later stop must not restart it.
fence_case "D4 start superseded by later stop, probe down" \
    "$T2" stop "" "$T1" start "" no "" yield_conflict keep stop

# Superseded but the outcome already matches -> silent success (exit 0).
fence_case "D5 stop superseded by later stop, already stopped" \
    "$T2" stop "" "$T1" stop "" no "" yield_ok absent
fence_case "D6 start superseded by later start, already up" \
    "$T2" start "" "$T1" start "4242" no "" yield_ok present
# Conflicting action but our goal happens to hold: stay silent AND leave crontab
# alone, because touching it would contradict the latest intent.
fence_case "D7 stop superseded by later start, probe already down" \
    "$T2" start "" "$T1" stop "" no "" yield_ok keep
# Later run of the same action did not reach the goal either -> do the work.
fence_case "D8 same action, goal not reached, proceed" \
    "$T2" stop "" "$T1" stop "4242" yes "" continue keep
# stop is only "reached" when the cron guard is gone too, otherwise cron would
# revive the probe within a minute.
fence_case "D9 no process but cron still registered is not stopped" \
    "$T2" stop "" "$T1" stop "" yes "" continue keep
# keepalive: a different address is unrelated, not conflicting.
fence_case "D10 keepalive other addr is not a conflict" \
    "$T2" stop "127.0.0.1:19999" "$T1" start "" no "127.0.0.1:18080" continue keep
fence_case "D11 keepalive same addr conflicts" \
    "$T2" stop "127.0.0.1:18080" "$T1" start "" no "127.0.0.1:18080" yield_conflict keep stop

DBHA_INTENT_FENCE=0
fence_case "D12 fence disabled falls back to plain locking" \
    "$T2" start "" "$T1" stop "4242" yes "" continue keep -
DBHA_INTENT_FENCE=1

FAKE_PIDS=""
FAKE_CRON=1
w_start="$(date +%s)"
probe_wait_target_state start "/opt/p/bin/dbha-probe" "MARKER" "" 1
w_rc=$?
w_elapsed=$(( $(date +%s) - w_start ))
assert_rc "D13 wait_target_state times out when unmet" 1 "$w_rc"
if [ "$w_elapsed" -ge 1 ] && [ "$w_elapsed" -le 8 ]; then
    ok "D13 wait respected the 1s budget (elapsed: ${w_elapsed}s)"
else
    fail "D13 wait respected the 1s budget" "elapsed: ${w_elapsed}s"
fi
w_start="$(date +%s)"
probe_wait_target_state start "/opt/p/bin/dbha-probe" "MARKER" "" 0
w_rc=$?
w_elapsed=$(( $(date +%s) - w_start ))
assert_rc "D14 timeout 0 checks once and fails" 1 "$w_rc"
if [ "$w_elapsed" -le 1 ]; then
    ok "D14 timeout 0 returned immediately (elapsed: ${w_elapsed}s)"
else
    fail "D14 timeout 0 returned immediately" "elapsed: ${w_elapsed}s"
fi
FAKE_PIDS="4242"
probe_wait_target_state start "/opt/p/bin/dbha-probe" "MARKER" "" 0
assert_rc "D15 timeout 0 succeeds when already reached" 0 $?

printf 'COUNTS %s %s\n' "$TESTS_RUN" "$TESTS_FAILED"
)"
printf '%s\n' "$d_output" | grep -v '^COUNTS '
TESTS_RUN="$(printf '%s\n' "$d_output" | awk '/^COUNTS /{print $2}')"
TESTS_FAILED="$(printf '%s\n' "$d_output" | awk '/^COUNTS /{print $3}')"

echo "=== E. crontab reconciliation ==="

: > "$MOCK_CRONTAB_FILE"
CRON_CMD="$(probe_cron_cmd "/data/dbha-v2-probe" "/data/logs")"

probe_reconcile_cron_guard present "E2E_MARKER" "$CRON_CMD" >/dev/null 2>&1
assert_eq "E1 present registers one line" "1" "$(cron_lines)"
probe_reconcile_cron_guard present "E2E_MARKER" "$CRON_CMD" >/dev/null 2>&1
assert_eq "E2 present is idempotent in content" "1" "$(cron_lines)"

probe_cron_has_marker "E2E_MARKER"
assert_rc "E3 marker detected" 0 $?

before="$(cat "$MOCK_CRONTAB_FILE")"
probe_reconcile_cron_guard keep "E2E_MARKER" "$CRON_CMD" >/dev/null 2>&1
assert_eq "E4 keep leaves crontab untouched" "$before" "$(cat "$MOCK_CRONTAB_FILE")"

probe_reconcile_cron_guard absent "E2E_MARKER" "$CRON_CMD" >/dev/null 2>&1
assert_eq "E5 absent removes the line" "0" "$(cron_lines)"

# An unrelated user line must survive both directions.
printf '0 3 * * * /usr/local/bin/user-backup.sh\n' > "$MOCK_CRONTAB_FILE"
probe_reconcile_cron_guard present "E2E_MARKER" "$CRON_CMD" >/dev/null 2>&1
assert_eq "E6 unrelated user line preserved on present" "2" "$(cron_lines)"
probe_reconcile_cron_guard absent "E2E_MARKER" "$CRON_CMD" >/dev/null 2>&1
assert_eq "E7 unrelated user line preserved on absent" "1" "$(cron_lines)"
grep -q 'user-backup' "$MOCK_CRONTAB_FILE"
assert_rc "E8 unrelated line content intact" 0 $?

# present without a command must refuse rather than write a broken cron line.
: > "$MOCK_CRONTAB_FILE"
probe_reconcile_cron_guard present "E2E_MARKER" "" >/dev/null 2>&1
assert_eq "E9 present with empty command writes nothing" "0" "$(cron_lines)"

echo "=== F. signal safety ==="

sleep 30 &
victim_pid=$!
# comm is "sleep", not dbha-*, so validation must refuse regardless of signal.
probe_signal_pid_safe "$victim_pid" "TERM" "dbha-probe" "/opt/p/bin/dbha-probe" >/dev/null 2>&1
assert_rc "F1 non-dbha process is never signalled" 1 $?
if kill -0 "$victim_pid" 2>/dev/null; then
    ok "F2 unrelated process still alive after refused signal"
else
    fail "F2 unrelated process still alive after refused signal"
fi
kill "$victim_pid" 2>/dev/null
wait "$victim_pid" 2>/dev/null

probe_signal_pid_safe 999999999 "TERM" "dbha-probe" "/opt/p/bin/dbha-probe" >/dev/null 2>&1
assert_rc "F3 non-existent pid refused" 1 $?

echo "=== G. keepalive addr matching ==="

# A real script file, not "sh -c ... --ping-http-addr ...": dash exec-optimises
# a single-command -c into the command itself, so the flags would never appear
# in /proc/<pid>/cmdline and the fixture would silently test nothing.
cat > "${TMPROOT}/fake-keepalive.sh" <<'FAKE'
#!/usr/bin/env bash
sleep 30
FAKE
chmod +x "${TMPROOT}/fake-keepalive.sh"
"${TMPROOT}/fake-keepalive.sh" --ping-http-addr 127.0.0.1:18080 &
ka_pid=$!
sleep 0.3
# Fixture self-check: without the flags in cmdline the assertions below would
# pass or fail for the wrong reason.
if tr '\0' ' ' < "/proc/${ka_pid}/cmdline" 2>/dev/null | grep -q -- '--ping-http-addr'; then
    ok "G0 fixture process carries the keepalive flag in cmdline"
else
    fail "G0 fixture process carries the keepalive flag in cmdline"
fi
probe_keepalive_pid_matches_addr "$ka_pid" "127.0.0.1:18080"
assert_rc "G1 matching addr detected" 0 $?
probe_keepalive_pid_matches_addr "$ka_pid" "127.0.0.1:19999"
assert_rc "G2 non-matching addr rejected" 1 $?
probe_keepalive_pid_matches_addr "$ka_pid" ""
assert_rc "G3 empty addr matches any keepalive" 0 $?
kill "$ka_pid" 2>/dev/null
wait "$ka_pid" 2>/dev/null

"${TMPROOT}/fake-keepalive.sh" --ping-http-addr=[::1]:18080 &
ka6_pid=$!
sleep 0.3
probe_keepalive_pid_matches_addr "$ka6_pid" "[::1]:18080"
assert_rc "G4 equals-form IPv6 addr detected" 0 $?
probe_keepalive_pid_matches_addr "$ka6_pid" "[::1]:19999"
assert_rc "G4 non-matching IPv6 addr rejected" 1 $?
kill "$ka6_pid" 2>/dev/null
wait "$ka6_pid" 2>/dev/null

echo "=== H. lifecycle conf parsing ==="

CONF_ROOT="${TMPROOT}/root"
mkdir -p "${CONF_ROOT}/etc"
cat > "${CONF_ROOT}/etc/probe-lifecycle.conf" <<'CONF'
# comment line
DBHA_LOCK_WAIT = 200
DBHA_ENSURE_LOCK_WAIT=15
DBHA_SUPERSEDE_VERIFY_WAIT=7
DBHA_REAP_DELETED_EXE=0
DBHA_CMD_TIMEOUT_STOP=not-a-number
EVIL_KEY=$(touch /tmp/dbha-pwned)
CONF
(
    DBHA_LOCK_WAIT=""
    DBHA_ENSURE_LOCK_WAIT=""
    DBHA_CMD_TIMEOUT_STOP=""
    DBHA_SUPERSEDE_VERIFY_WAIT=""
    DBHA_REAP_DELETED_EXE=""
    probe_load_lifecycle_conf "$CONF_ROOT" >/dev/null 2>&1
    [ "$DBHA_LOCK_WAIT" = "200" ] || exit 1
    [ "$DBHA_ENSURE_LOCK_WAIT" = "15" ] || exit 2
    # non-numeric value must be rejected, leaving the default to apply
    [ -z "$DBHA_CMD_TIMEOUT_STOP" ] || exit 3
    [ "$DBHA_SUPERSEDE_VERIFY_WAIT" = "7" ] || exit 4
    [ "$DBHA_REAP_DELETED_EXE" = "0" ] || exit 5
    exit 0
)
assert_rc "H1 whitelisted numeric keys loaded, bad values rejected" 0 $?
if [ -e /tmp/dbha-pwned ]; then
    fail "H2 conf file is parsed, never sourced" "command substitution executed"
    rm -f /tmp/dbha-pwned
else
    ok "H2 conf file is parsed, never sourced"
fi
(
    DBHA_LOCK_WAIT="999"
    probe_load_lifecycle_conf "$CONF_ROOT" >/dev/null 2>&1
    [ "$DBHA_LOCK_WAIT" = "999" ] || exit 1
    exit 0
)
assert_rc "H3 environment overrides the conf file" 0 $?

mkdir -p "${TMPROOT}/symlink-conf/etc"
ln -s "${CONF_ROOT}/etc/probe-lifecycle.conf" "${TMPROOT}/symlink-conf/etc/probe-lifecycle.conf"
(
    DBHA_LOCK_WAIT=""
    probe_load_lifecycle_conf "${TMPROOT}/symlink-conf" >/dev/null 2>&1
    [ -z "$DBHA_LOCK_WAIT" ] || exit 1
    exit 0
)
assert_rc "H4 symlink lifecycle conf is ignored" 0 $?

echo "=== I. isolation from shared code ==="

# The whole point of the new library: shared files stay byte-identical so the
# server scripts cannot regress.
for shared in scripts/lib/guard-utils.sh scripts/deploy.sh scripts/render_configs.py \
              scripts/start-server.sh scripts/stop-server.sh scripts/setup.sh; do
    if git -C "$REPO_ROOT" --no-pager diff --quiet -- "dbm-services/common/dbha-v2/${shared}" 2>/dev/null; then
        ok "I1 unchanged: ${shared}"
    else
        fail "I1 unchanged: ${shared}" "shared file was modified"
    fi
done

# Server scripts must not gain a dependency on the probe-only library.
if grep -l 'probe-lifecycle-utils' "${SCRIPTS_DIR}/start-server.sh" \
        "${SCRIPTS_DIR}/stop-server.sh" "${SCRIPTS_DIR}/setup.sh" >/dev/null 2>&1; then
    fail "I2 server scripts do not reference the probe library"
else
    ok "I2 server scripts do not reference the probe library"
fi

# Function name collisions would silently override shared behaviour.
guard_fns="$(grep -oE '^[a-z_][a-z0-9_]*\(\)' "${SCRIPTS_DIR}/lib/guard-utils.sh" | tr -d '()' | sort -u)"
probe_fns="$(grep -oE '^[a-z_][a-z0-9_]*\(\)' "${SCRIPTS_DIR}/lib/probe-lifecycle-utils.sh" \
    | tr -d '()' | sort -u)"
overlap="$(comm -12 <(echo "$guard_fns") <(echo "$probe_fns") | tr '\n' ' ')"
assert_eq "I3 no function name collision with guard-utils.sh" "" "${overlap// /}"

# Everything the new library exports must carry the probe_ prefix.
unprefixed="$(echo "$probe_fns" | grep -v '^probe_' | tr '\n' ' ')"
assert_eq "I4 all new functions use the probe_ prefix" "" "${unprefixed// /}"

echo "=== J. lock error paths and reclaim ==="

SYMLINK_LOCK="${LOCKDIR}/symlink.lock"
ln -s "${LOCKDIR}/b2.lock" "$SYMLINK_LOCK"
probe_acquire_lock "$SYMLINK_LOCK" 9 1 1 >/dev/null 2>&1
assert_rc "J1 symlink lock path is refused" 1 $?

EMPTY_LOCK="${LOCKDIR}/empty-pid.lock"
mkdir -p "${EMPTY_LOCK}.d"
: > "${EMPTY_LOCK}.d/pid"
probe_lc_now > "${EMPTY_LOCK}.d/ts"
j2_start="$(date +%s)"
(
    DBHA_LOCK_FORCE_MKDIR=1
    probe_acquire_lock "$EMPTY_LOCK" 9 2 0 >/dev/null 2>&1
    exit $?
)
j2_rc=$?
j2_elapsed=$(( $(date +%s) - j2_start ))
assert_rc "J2 empty pid file is treated as a live lock" 1 "$j2_rc"
if [ "$j2_elapsed" -ge 1 ] && [ "$j2_elapsed" -le 8 ]; then
    ok "J2 empty-pid wait respected the timeout (elapsed: ${j2_elapsed}s)"
else
    fail "J2 empty-pid wait respected the timeout" "elapsed: ${j2_elapsed}s"
fi
rm -rf "${EMPTY_LOCK}.d"

REAP_LOCK="${LOCKDIR}/reap.lock"
REAP_DIR="${REAP_LOCK}.d.reap"
mkdir -p "${REAP_LOCK}.d" "$REAP_DIR"
echo "$$" > "${REAP_LOCK}.d/pid"
echo $(( $(probe_lc_now) - PROBE_LC_STALE_FLOOR - 10 )) > "${REAP_DIR}/ts"
probe_lc_reclaim_stale "${REAP_LOCK}.d" "$REAP_DIR" "$$" >/dev/null 2>&1
if [ -d "$REAP_DIR" ]; then
    fail "J3 orphaned reap mutex older than stale floor is removed"
else
    ok "J3 orphaned reap mutex older than stale floor is removed"
fi
rm -rf "${REAP_LOCK}.d"

probe_open_lock_fd 7 "${LOCKDIR}/fd7.lock" >/dev/null 2>&1
assert_rc "J4 unsupported lock fd is refused" 1 $?

echo "=== K. deps, timeout fallback, install root ==="

(
    PATH="$MOCKBIN"
    probe_check_deps >/dev/null 2>&1
    exit $?
)
assert_rc "K1 missing pgrep and friends fails deps check" 1 $?

(
    DBHA_LOCK_WAIT=""
    DBHA_ENSURE_LOCK_WAIT=""
    DBHA_START_VERIFY_WAIT=""
    DBHA_CMD_TIMEOUT_ENSURE=""
    DBHA_CMD_TIMEOUT_STOP=""
    PATH="$MOCKBIN"
    PROBE_LC_TIMEOUT_BIN="timeout"
    probe_apply_defaults >/dev/null 2>&1
    [ -z "$PROBE_LC_TIMEOUT_BIN" ] || exit 1
    out="$(probe_run_binary 2 echo ok)"
    [ "$out" = "ok" ] || exit 2
    exit 0
)
assert_rc "K2 timeout missing degrades probe_run_binary" 0 $?

(
    DBHA_LOCK_WAIT=1
    DBHA_ENSURE_LOCK_WAIT=30
    DBHA_CMD_TIMEOUT_STOP=45
    DBHA_START_VERIFY_WAIT=1
    DBHA_CMD_TIMEOUT_ENSURE=1
    log="$(mktemp "${TMPROOT}/warn.XXXXXX")"
    LOG_FILE="$log"
    probe_apply_defaults >/dev/null 2>&1
    grep -q 'action lock wait may be too short' "$log" || exit 1
    exit 0
)
assert_rc "K3 short lock wait only warns" 0 $?

(
    DBHA_LOCK_WAIT=10
    DBHA_ENSURE_LOCK_WAIT=1
    DBHA_CMD_TIMEOUT_STOP=1
    DBHA_SUPERSEDE_VERIFY_WAIT=30
    DBHA_START_VERIFY_WAIT=1
    DBHA_CMD_TIMEOUT_ENSURE=1
    log="$(mktemp "${TMPROOT}/warn.XXXXXX")"
    LOG_FILE="$log"
    probe_apply_defaults >/dev/null 2>&1
    grep -q 'supersede verify' "$log" || exit 1
    exit 0
)
assert_rc "K3b oversized SUPERSEDE_VERIFY_WAIT warns" 0 $?

probe_install_root "" >/dev/null 2>&1
assert_rc "K4 install root fails when readlink cannot resolve the path" 1 $?

echo "=== L. intent ts resolution and write failures ==="

got_ts="$(probe_resolve_intent_ts "" 2>/dev/null || true)"
case "$got_ts" in
    ''|*[!0-9]*) fail "L1 empty injection falls back to now" "got: ${got_ts}" ;;
    *) ok "L1 empty injection falls back to now" ;;
esac
got_ts="$(probe_resolve_intent_ts "abc" 2>/dev/null | grep -E '^[0-9]+$' | tail -n 1)"
case "$got_ts" in
    ''|*[!0-9]*) fail "L2 non-numeric injection falls back to now" "got: ${got_ts}" ;;
    *) ok "L2 non-numeric injection falls back to now" ;;
esac
got_ts="$(probe_resolve_intent_ts "0" 2>/dev/null | grep -E '^[0-9]+$' | tail -n 1)"
case "$got_ts" in
    ''|*[!0-9]*) fail "L3 zero injection falls back to now" "got: ${got_ts}" ;;
    *) ok "L3 zero injection falls back to now" ;;
esac
assert_eq "L4 numeric injection is kept" "1700000000000000000" \
    "$(probe_resolve_intent_ts "1700000000000000000" 2>/dev/null)"

FUTURE_INTENT="${TMPROOT}/future.intent"
printf '%s start \n' "$(probe_now_ns)" > "$FUTURE_INTENT"
future_ts="$(( $(probe_now_ns) + PROBE_LC_CLOCK_SKEW * 1000000000 + 2000000000 ))"
before="$(cat "$FUTURE_INTENT")"
probe_write_intent "$FUTURE_INTENT" "$future_ts" "stop" >/dev/null 2>&1
assert_eq "L5 future ts is not written" "$before" "$(cat "$FUTURE_INTENT")"

NOTDIR="${TMPROOT}/intent-not-a-dir"
touch "$NOTDIR"
probe_write_intent "${NOTDIR}/probe.intent" "$(probe_now_ns)" "start" >/dev/null 2>&1
assert_rc "L6 unwritable intent path does not fail the caller" 0 $?
if [ -e "${NOTDIR}/probe.intent" ]; then
    fail "L6 intent file was not created on a non-directory parent"
else
    ok "L6 intent file was not created on a non-directory parent"
fi

before_cron="$(cat "$MOCK_CRONTAB_FILE")"
probe_reconcile_cron_guard bogus "E2E_MARKER" "echo hi" >/dev/null 2>&1
assert_eq "L7 unknown cron state leaves crontab unchanged" "$before_cron" \
    "$(cat "$MOCK_CRONTAB_FILE")"

echo "=== M. live process helpers (compiled stub) ==="

STUB="${TMPROOT}/stub-root"
mkdir -p "${STUB}/bin" "${STUB}/pids"
MODULE_DIR="$(cd "${SCRIPTS_DIR}/.." && pwd)"
stub_built=0
if command -v go >/dev/null 2>&1; then
    if (cd "$MODULE_DIR" && go build -o "${STUB}/bin/dbha-probe" \
            ./scripts/tests/testdata/fake-probe 2>/dev/null); then
        stub_built=1
    elif (cd "${SCRIPTS_DIR}/tests/testdata/fake-probe" && \
            go build -o "${STUB}/bin/dbha-probe" main.go 2>/dev/null); then
        stub_built=1
    fi
fi
if [ "$stub_built" -eq 1 ]; then
    stub_exe="$(readlink -f "${STUB}/bin/dbha-probe")"
    ( cd "$STUB" && exec ./bin/dbha-probe daemon-start -c etc/probe.yaml >/dev/null 2>&1 ) &
    guard_live=$!
    ( cd "$STUB" && exec ./bin/dbha-probe >/dev/null 2>&1 ) &
    worker_live=$!
    sleep 0.4
    kind_g="$(probe_cmdline_kind "$guard_live")"
    kind_w="$(probe_cmdline_kind "$worker_live")"
    assert_eq "M1 live daemon-start classifies as guard" "guard" "$kind_g"
    assert_eq "M2 live argv-only process classifies as worker" "worker" "$kind_w"
    first="$(probe_get_pids "guard,worker" "$stub_exe" | head -n 1)"
    assert_eq "M3 get_pids lists the guard first" "$guard_live" "$first"

    export XDG_STATE_HOME="${STUB}/state"
    mkdir -p "${STUB}/state/dbha-v2/runtime"
    ( cd "$STUB" && exec ./bin/dbha-probe --ping-http-addr 127.0.0.1:18080 >/dev/null 2>&1 ) &
    ka_live=$!
    sleep 0.3
    ka_found="$(probe_keepalive_pids "$stub_exe" "127.0.0.1:18080" || true)"
    case "$ka_found" in
        *"${ka_live}"*) ok "M4 keepalive_pids finds the process via /proc comm" ;;
        *) fail "M4 keepalive_pids finds the process via /proc comm" "pids: ${ka_found}" ;;
    esac
    pgrep_ka="$(pgrep -x dbha-keepalive 2>/dev/null || true)"
    case "$pgrep_ka" in
        *"${ka_live}"*)
            fail "M5 pgrep -x dbha-keepalive does not see the stub" \
                "unexpected pid: ${pgrep_ka}"
            ;;
        *) ok "M5 pgrep -x dbha-keepalive does not see the stub" ;;
    esac
    probe_signal_pid_safe "$guard_live" "TERM" "dbha-probe" "$stub_exe" \
        "not-the-real-starttime" >/dev/null 2>&1
    assert_rc "M6 starttime mismatch refuses the signal" 1 $?
    if kill -0 "$guard_live" 2>/dev/null; then
        ok "M6 guard still alive after starttime mismatch"
    else
        fail "M6 guard still alive after starttime mismatch"
    fi
    kill -KILL "$guard_live" "$worker_live" "$ka_live" 2>/dev/null || true
    wait "$guard_live" "$worker_live" "$ka_live" 2>/dev/null || true
else
    ok "M1 live daemon-start classifies as guard (skipped: no go stub)"
    ok "M2 live argv-only process classifies as worker (skipped: no go stub)"
    ok "M3 get_pids lists the guard first (skipped: no go stub)"
    ok "M4 keepalive_pids finds the process via /proc comm (skipped: no go stub)"
    ok "M5 pgrep -x dbha-keepalive does not see the stub (skipped: no go stub)"
    ok "M6 starttime mismatch refuses the signal (skipped: no go stub)"
    ok "M6 guard still alive after starttime mismatch (skipped: no go stub)"
fi

echo "=== N. deleted-exe orphans ==="

if [ "${stub_built:-0}" -eq 1 ]; then
    stub_exe="$(readlink -f "${STUB}/bin/dbha-probe")"
    : > "$MOCK_CRONTAB_FILE"

    ( cd "$STUB" && exec ./bin/dbha-probe daemon-start -c etc/probe.yaml >/dev/null 2>&1 ) &
    n_guard=$!
    sleep 0.3
    cp "$stub_exe" "${STUB}/bin/dbha-probe.bak"
    rm -f "${STUB}/bin/dbha-probe"
    cp "${STUB}/bin/dbha-probe.bak" "${STUB}/bin/dbha-probe"
    chmod +x "${STUB}/bin/dbha-probe"
    orphans="$(probe_orphan_pids "guard,worker" "$stub_exe" || true)"
    case "$orphans" in
        *"${n_guard}"*) ok "N1 deleted-exe guard is enumerated" ;;
        *) fail "N1 deleted-exe guard is enumerated" "pids: ${orphans}" ;;
    esac
    probe_target_state_reached stop "$stub_exe" "E2E_MARKER" ""
    assert_rc "N1 stop not reached while orphan lives" 1 $?
    probe_orphan_pids unknown "$stub_exe" >/dev/null 2>&1
    assert_rc "N1 unknown kind is refused" 1 $?
    empty="$(probe_orphan_pids "guard,worker" "" || true)"
    assert_eq "N1 empty expected_exe enumerates nothing" "" "$empty"

    OTHER="${TMPROOT}/other-root"
    mkdir -p "${OTHER}/bin"
    cp "${STUB}/bin/dbha-probe.bak" "${OTHER}/bin/dbha-probe"
    chmod +x "${OTHER}/bin/dbha-probe"
    ( cd "$OTHER" && exec ./bin/dbha-probe daemon-start -c etc/probe.yaml >/dev/null 2>&1 ) &
    other_pid=$!
    sleep 0.3
    rm -f "${OTHER}/bin/dbha-probe"
    other_hit="$(probe_orphan_pids "guard,worker" "$stub_exe" || true)"
    case "$other_hit" in
        *"${other_pid}"*) fail "N2 other install root is not matched" "pids: ${other_hit}" ;;
        *) ok "N2 other install root is not matched" ;;
    esac
    kill -KILL "$other_pid" 2>/dev/null || true

    FORGED="${TMPROOT}/forged"
    mkdir -p "$FORGED"
    cp "${STUB}/bin/dbha-probe.bak" "${FORGED}/dbha-probe (deleted)"
    chmod +x "${FORGED}/dbha-probe (deleted)"
    ( cd "$FORGED" && exec "./dbha-probe (deleted)" daemon-start -c etc/probe.yaml >/dev/null 2>&1 ) &
    forged_pid=$!
    sleep 0.3
    forged_exe="$(readlink -f "${FORGED}/dbha-probe (deleted)")"
    probe_exe_deleted_matches "$forged_pid" "*" "$forged_exe"
    assert_rc "N3 live file named with (deleted) is not an orphan" 1 $?
    kill -KILL "$forged_pid" 2>/dev/null || true

    ( cd "$STUB" && exec ./bin/dbha-probe gen-config >/dev/null 2>&1 ) &
    health_pid=$!
    sleep 0.3
    rm -f "${STUB}/bin/dbha-probe"
    cp "${STUB}/bin/dbha-probe.bak" "${STUB}/bin/dbha-probe"
    chmod +x "${STUB}/bin/dbha-probe"
    health_hit="$(probe_orphan_pids "guard,worker" "$stub_exe" || true)"
    case "$health_hit" in
        *"${health_pid}"*) fail "N4 deleted-exe gen-config is not selected" "pids: ${health_hit}" ;;
        *) ok "N4 deleted-exe gen-config is not selected" ;;
    esac
    kill -KILL "$health_pid" 2>/dev/null || true

    SLEEPDIR="${TMPROOT}/sleep-del"
    mkdir -p "$SLEEPDIR"
    cp /bin/sleep "${SLEEPDIR}/notdbha"
    chmod +x "${SLEEPDIR}/notdbha"
    "${SLEEPDIR}/notdbha" 60 &
    sleep_pid=$!
    sleep 0.2
    sleep_exe="$(readlink -f "${SLEEPDIR}/notdbha")"
    rm -f "${SLEEPDIR}/notdbha"
    probe_exe_deleted_matches "$sleep_pid" "dbha-probe" "$sleep_exe"
    assert_rc "N5 comm without dbha- prefix is rejected" 1 $?
    kill -KILL "$sleep_pid" 2>/dev/null || true

    DBHA_REAP_DELETED_EXE=0
    if kill -0 "$n_guard" 2>/dev/null; then
        probe_reap_orphans "guard,worker" "$stub_exe" >/dev/null 2>&1
        assert_rc "N6 reap disabled returns 0" 0 $?
        if kill -0 "$n_guard" 2>/dev/null; then
            ok "N6 reap disabled leaves the orphan running"
        else
            fail "N6 reap disabled leaves the orphan running"
        fi
    else
        fail "N6 fixture orphan still alive before disabled reap"
    fi
    DBHA_REAP_DELETED_EXE=1
    probe_reap_orphans "guard,worker" "$stub_exe" >/dev/null 2>&1
    assert_rc "N7 reap clears the orphan" 0 $?
    if kill -0 "$n_guard" 2>/dev/null; then
        fail "N7 orphan gone after reap"
        kill -KILL "$n_guard" 2>/dev/null || true
    else
        ok "N7 orphan gone after reap"
    fi
    probe_target_state_reached stop "$stub_exe" "E2E_MARKER" ""
    assert_rc "N7 stop reached after orphan gone" 0 $?

    export XDG_STATE_HOME="${STUB}/state"
    mkdir -p "${STUB}/state/dbha-v2/runtime"
    ( cd "$STUB" && exec ./bin/dbha-probe --ping-http-addr 127.0.0.1:18080 >/dev/null 2>&1 ) &
    n_ka=$!
    sleep 0.3
    rm -f "${STUB}/bin/dbha-probe"
    cp "${STUB}/bin/dbha-probe.bak" "${STUB}/bin/dbha-probe"
    chmod +x "${STUB}/bin/dbha-probe"
    ka_hit="$(probe_keepalive_orphan_pids "$stub_exe" "127.0.0.1:18080" || true)"
    case "$ka_hit" in
        *"${n_ka}"*) ok "N8 keepalive orphan matches addr" ;;
        *) fail "N8 keepalive orphan matches addr" "pids: ${ka_hit}" ;;
    esac
    ka_miss="$(probe_keepalive_orphan_pids "$stub_exe" "127.0.0.1:19999" || true)"
    case "$ka_miss" in
        *"${n_ka}"*) fail "N8 keepalive orphan rejects other addr" ;;
        *) ok "N8 keepalive orphan rejects other addr" ;;
    esac
    probe_reap_keepalive_orphans "$stub_exe" "127.0.0.1:18080" >/dev/null 2>&1
    if kill -0 "$n_ka" 2>/dev/null; then
        fail "N8 keepalive orphan reaped"
        kill -KILL "$n_ka" 2>/dev/null || true
    else
        ok "N8 keepalive orphan reaped"
    fi
    rm -f "${STUB}/bin/dbha-probe.bak"
else
    ok "N1-N8 skipped: no go stub"
fi

echo
echo "tests run: ${TESTS_RUN}, failed: ${TESTS_FAILED}"
[ "$TESTS_FAILED" -eq 0 ]
