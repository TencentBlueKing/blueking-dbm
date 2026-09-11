#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")" || exit 1

readonly SCRIPT_DIR="$(pwd)"
readonly LOG_ROOT="${DBHA_LOG_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/logs}"
readonly PROC_NAME="dbha-probe"
readonly BINARY_PATH="./bin/dbha-probe"
readonly CONFIG_PATH="./etc/probe.yaml"
readonly CRON_MARKER="DBHA_V2_PROBE_GUARD"
readonly RESIDUE_RECHECK_WAIT=5

LOG_FILE="${LOG_ROOT}/dbha-v2-probe.log"
INTENT_TS_ARG=""

if [ ! -f "${SCRIPT_DIR}/lib/guard-utils.sh" ]; then
    echo "missing required script, path: ${SCRIPT_DIR}/lib/guard-utils.sh" >&2
    exit 1
fi
source "${SCRIPT_DIR}/lib/guard-utils.sh"

if [ ! -f "${SCRIPT_DIR}/lib/probe-lifecycle-utils.sh" ]; then
    echo "missing required script, path: ${SCRIPT_DIR}/lib/probe-lifecycle-utils.sh" >&2
    exit 1
fi
source "${SCRIPT_DIR}/lib/probe-lifecycle-utils.sh"

usage() {
    echo "Usage: $0 [--intent-ts <nanoseconds>]"
    echo "  --intent-ts  originating request time; without it the fence compares"
    echo "               script start times (see scripts/README.md)"
}

# recheck_residue <expected_exe>
# Bounded wait for the process table to settle. A single immediate check can
# report a residue for a process that is already exiting.
recheck_residue() {
    local expected_exe="$1"
    local deadline iter max_iter pids orphans

    deadline=$(( $(date +%s) + RESIDUE_RECHECK_WAIT ))
    iter=0
    max_iter=$(( RESIDUE_RECHECK_WAIT * 5 + 20 ))

    while :; do
        pids="$(probe_get_pids "guard,worker" "$expected_exe" || true)"
        orphans="$(probe_orphan_pids "guard,worker" "$expected_exe" || true)"
        if [ -z "$pids" ] && [ -z "$orphans" ]; then
            return 0
        fi
        iter=$(( iter + 1 ))
        if [ "$iter" -ge "$max_iter" ]; then
            break
        fi
        if [ "$(date +%s)" -ge "$deadline" ]; then
            break
        fi
        sleep 0.2 || sleep 1
    done
    return 1
}

# terminate_probe_procs <expected_exe>
terminate_probe_procs() {
    local expected_exe="$1"
    local -a term_pids=() term_starttimes=()
    local remaining pid i term_pid starttime

    # Only guard and worker. Management subcommands (health, gen-config, reload,
    # version) classify as unknown and are never signalled: DBM runs gen-config
    # right before start-probe.sh, and killing it would corrupt probe.yaml.
    # Guards are listed first so guardStopChild takes the worker down with them.
    remaining="$(probe_get_pids "guard,worker" "$expected_exe" || true)"

    while IFS= read -r pid; do
        if [ -z "$pid" ]; then
            continue
        fi
        starttime="$(get_pid_starttime "$pid" 2>/dev/null || echo "")"
        term_pids+=("$pid")
        term_starttimes+=("$starttime")
        # starttime is passed so a pid recycled between listing and signalling
        # cannot be hit.
        probe_signal_pid_safe "$pid" "TERM" "$PROC_NAME" "$expected_exe" "$starttime" || true
    done <<< "$remaining"

    remaining="$(probe_orphan_pids "guard,worker" "$expected_exe" || true)"
    while IFS= read -r pid; do
        if [ -z "$pid" ]; then
            continue
        fi
        starttime="$(get_pid_starttime "$pid" 2>/dev/null || echo "")"
        term_pids+=("$pid")
        term_starttimes+=("$starttime")
        probe_signal_orphan_pid "$pid" "TERM" "$PROC_NAME" "$expected_exe" "$starttime" || true
    done <<< "$remaining"

    if [ "${#term_pids[@]}" -eq 0 ]; then
        return 0
    fi

    sleep 1
    # Guarded by ${#} because "${!arr[@]}" on an empty array is unbound under
    # set -u on bash 3.2.
    for i in "${!term_pids[@]}"; do
        term_pid="${term_pids[$i]}"
        if probe_exe_deleted_matches "$term_pid" "$PROC_NAME" "$expected_exe"; then
            if ! wait_pid_exit "$term_pid" 10; then
                probe_signal_orphan_pid "$term_pid" "KILL" "$PROC_NAME" "$expected_exe" \
                    "${term_starttimes[$i]}" || true
            fi
            continue
        fi
        if validate_pid_target "$term_pid" "$PROC_NAME" "$expected_exe"; then
            if ! wait_pid_exit "$term_pid" 10; then
                safe_kill_after_term "$term_pid" "$PROC_NAME" "$expected_exe" "${term_starttimes[$i]}" || true
            fi
        fi
    done
    return 0
}

main() {
    ensure_log_file "$LOG_FILE"

    if [ ! -x "$BINARY_PATH" ]; then
        log_msg "ERROR" "binary missing, path: ${BINARY_PATH}"
        exit 1
    fi

    if ! probe_check_deps; then
        exit 1
    fi

    local install_root expected_exe
    install_root="$(probe_install_root "$BINARY_PATH" || true)"
    if [ -z "$install_root" ]; then
        log_msg "ERROR" "cannot resolve install root, path: ${BINARY_PATH}"
        exit 1
    fi
    expected_exe="$(readlink -f "$BINARY_PATH")"

    probe_load_lifecycle_conf "$install_root"
    probe_apply_defaults

    local action_lock ensure_lock intent_file
    action_lock="${install_root}/pids/probe.action.lock"
    ensure_lock="${install_root}/pids/probe.ensure.lock"
    intent_file="${install_root}/pids/probe.intent"

    if [ "$action_lock" = "$ensure_lock" ]; then
        log_msg "ERROR" "action lock and ensure lock must differ, path: ${action_lock}"
        exit 1
    fi
    if ! probe_guard_nested_call "$action_lock"; then
        exit 1
    fi

    probe_install_lock_traps

    local intent_ts cron_cmd
    intent_ts="$(probe_resolve_intent_ts "$INTENT_TS_ARG")"
    cron_cmd="$(probe_cron_cmd "$SCRIPT_DIR" "$LOG_ROOT")"

    # Lock order is always action then ensure, matching start-probe.sh, so the
    # two scripts cannot deadlock against each other.
    if ! probe_acquire_lock "$action_lock" 9 "$DBHA_LOCK_WAIT" 0; then
        log_msg "ERROR" "cannot acquire action lock, path: ${action_lock}, waited: ${DBHA_LOCK_WAIT}"
        probe_state_snapshot "$expected_exe" "$intent_file" "$intent_ts"
        exit 1
    fi
    export DBHA_PROBE_ACTION_LOCK_HELD="$action_lock"

    probe_reap_orphans "guard,worker" "$expected_exe" || true

    probe_fence_decide "$intent_file" "$intent_ts" "stop" "$expected_exe" "$CRON_MARKER"
    case "$PROBE_LC_FENCE_ACTION" in
        yield_ok)
            log_msg "INFO" "target state already reached, action: stop"
            probe_reconcile_cron_guard "$PROBE_LC_FENCE_CRON" "$CRON_MARKER" "$cron_cmd"
            exit 0
            ;;
        yield_conflict)
            log_msg "WARN" "operation superseded by later action, action: stop"
            probe_reconcile_cron_guard "$PROBE_LC_FENCE_CRON" "$CRON_MARKER" "$cron_cmd"
            log_msg "ERROR" "stop not applied and probe not down, blocking caller"
            log_msg "ERROR" "latest_action: ${PROBE_LC_FENCE_LATEST_ACTION}"
            probe_state_snapshot "$expected_exe" "$intent_file" "$intent_ts"
            exit 1
            ;;
    esac

    # Best effort by design. Holding it blocks a concurrent "ensure" from
    # resurrecting the probe mid-stop, but it must never be mandatory: with
    # EnvGuardProcess=1 the ensure process becomes the long-lived guard and
    # keeps this lock for its whole lifetime, which would make stop fail
    # forever. Degrading only widens the race that already exists today.
    if ! probe_acquire_lock "$ensure_lock" 8 "$DBHA_ENSURE_LOCK_WAIT" 0; then
        log_msg "WARN" "ensure lock not acquired, degraded to best-effort, path: ${ensure_lock}"
        probe_ensure_lock_holder_hint "$ensure_lock"
    fi

    log_msg "INFO" "stopping ${PROC_NAME}"

    # Deregister before killing: while processes are being terminated, a cron
    # tick must not start a new guard behind us.
    probe_reconcile_cron_guard absent "$CRON_MARKER" "$cron_cmd"

    probe_run_binary "$DBHA_CMD_TIMEOUT_STOP" "$BINARY_PATH" stop -c "$CONFIG_PATH" >/dev/null 2>&1 || true

    terminate_probe_procs "$expected_exe"

    # Bounded retry: one extra TERM/KILL round if anything is still alive, then
    # wait again. Covers races where a worker was restarted while the first
    # round was still signalling the old guard.
    if ! recheck_residue "$expected_exe"; then
        log_msg "WARN" "residue detected after first stop pass, retrying one more round"
        terminate_probe_procs "$expected_exe"
        if ! recheck_residue "$expected_exe"; then
            # Restore the guard line. Leaving "processes alive, no cron" would
            # mean nothing revives the probe if it later dies, and it would
            # silently contradict compare_probe_config.py. This also fixes the
            # previous behaviour of dropping cron before the residue check.
            probe_reconcile_cron_guard present "$CRON_MARKER" "$cron_cmd"
            log_msg "ERROR" "${PROC_NAME} still running after fallback"
            probe_state_snapshot "$expected_exe" "$intent_file" "$intent_ts"
            exit 1
        fi
    fi

    probe_write_intent "$intent_file" "$intent_ts" "stop"
    log_msg "INFO" "${PROC_NAME} stopped successfully"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --intent-ts)
            if [ $# -lt 2 ] || [ -z "${2:-}" ]; then
                echo "Invalid --intent-ts, errmsg: empty value" >&2
                exit 1
            fi
            INTENT_TS_ARG="$2"
            shift 2
            ;;
        --intent-ts=*)
            INTENT_TS_ARG="${1#*=}"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

main
