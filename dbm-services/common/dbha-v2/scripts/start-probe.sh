#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")" || exit 1

readonly SCRIPT_DIR="$(pwd)"
readonly LOG_ROOT="${DBHA_LOG_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/logs}"
readonly BINARY_PATH="./bin/dbha-probe"
readonly CONFIG_PATH="./etc/probe.yaml"
readonly CRON_MARKER="DBHA_V2_PROBE_GUARD"

LOG_FILE="${LOG_ROOT}/dbha-v2-probe.log"
FROM_CRON=0
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
    echo "Usage: $0 [--from-cron] [--intent-ts <nanoseconds>]"
    echo "  --intent-ts  originating request time; without it the fence compares"
    echo "               script start times (see scripts/README.md)"
}

# wait_for_guard <expected_exe>
# Bounded liveness check. Needed because "dbha-probe ensure" exits 0 both when
# it started the guard and when it skipped on lock contention, so a zero exit
# alone would let us report success for a probe that is not running.
wait_for_guard() {
    local expected_exe="$1"
    local deadline iter max_iter pids

    if [ "$DBHA_START_VERIFY_WAIT" -le 0 ]; then
        echo "skipped"
        return 0
    fi

    deadline=$(( $(date +%s) + DBHA_START_VERIFY_WAIT ))
    iter=0
    # Iteration cap alongside the deadline: a backwards clock step must not be
    # able to keep this loop running.
    max_iter=$(( DBHA_START_VERIFY_WAIT * 5 + 20 ))

    while :; do
        pids="$(probe_get_pids guard "$expected_exe" || true)"
        if [ -n "$pids" ]; then
            echo "$pids"
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

main() {
    ensure_log_file "$LOG_FILE"

    if [ ! -x "$BINARY_PATH" ]; then
        log_msg "ERROR" "binary missing, path: ${BINARY_PATH}"
        exit 1
    fi
    if [ ! -f "$CONFIG_PATH" ]; then
        log_msg "ERROR" "config missing, path: ${CONFIG_PATH}"
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

    # Quiet mode first: hosts whose crontab still runs this script every minute
    # must not gain extra log lines (probe script logs are never rotated).
    if [ "$FROM_CRON" -eq 1 ]; then
        probe_lc_quiet 1
    fi

    probe_load_lifecycle_conf "$install_root"
    probe_apply_defaults

    local action_lock ensure_lock intent_file
    action_lock="${install_root}/pids/probe.action.lock"
    ensure_lock="${install_root}/pids/probe.ensure.lock"
    intent_file="${install_root}/pids/probe.intent"

    # Guards against a constant edit that would make the script deadlock itself.
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

    # start must NOT hold the ensure lock: its own child "ensure" would then fail
    # to take it and skip, leaving the probe stopped.
    if [ "$FROM_CRON" -eq 1 ]; then
        # Non-blocking: cron retries every minute, so contention is not a failure
        # (same semantics as the Go ensure skipping on a held lock).
        if ! probe_acquire_lock "$action_lock" 9 "$DBHA_LOCK_WAIT" 1; then
            exit 0
        fi
    else
        if ! probe_acquire_lock "$action_lock" 9 "$DBHA_LOCK_WAIT" 0; then
            log_msg "ERROR" "cannot acquire action lock, path: ${action_lock}, waited: ${DBHA_LOCK_WAIT}"
            probe_state_snapshot "$expected_exe" "$intent_file" "$intent_ts"
            exit 1
        fi
    fi
    export DBHA_PROBE_ACTION_LOCK_HELD="$action_lock"

    if ! probe_reap_orphans "guard,worker" "$expected_exe"; then
        log_msg "ERROR" "deleted-exe orphans still running"
        probe_reconcile_cron_guard keep "$CRON_MARKER" "$cron_cmd"
        probe_state_snapshot "$expected_exe" "$intent_file" "$intent_ts"
        exit 1
    fi

    # cron-driven runs are self-healing, not user intent: they neither consult
    # nor update the fence.
    if [ "$FROM_CRON" -eq 0 ]; then
        probe_fence_decide "$intent_file" "$intent_ts" "start" "$expected_exe" "$CRON_MARKER"
        case "$PROBE_LC_FENCE_ACTION" in
            yield_ok)
                log_msg "INFO" "target state already reached, action: start"
                probe_reconcile_cron_guard "$PROBE_LC_FENCE_CRON" "$CRON_MARKER" "$cron_cmd"
                exit 0
                ;;
            yield_conflict)
                log_msg "WARN" "operation superseded by later action, action: start"
                probe_reconcile_cron_guard "$PROBE_LC_FENCE_CRON" "$CRON_MARKER" "$cron_cmd"
                if probe_wait_target_state "$PROBE_LC_FENCE_LATEST_ACTION" "$expected_exe" \
                        "$CRON_MARKER" "" "$DBHA_SUPERSEDE_VERIFY_WAIT"; then
                    log_msg "INFO" "latest intent state verified, action: ${PROBE_LC_FENCE_LATEST_ACTION}"
                    exit 0
                fi
                log_msg "ERROR" "latest intent state not reached, action: ${PROBE_LC_FENCE_LATEST_ACTION}"
                log_msg "ERROR" "waited: ${DBHA_SUPERSEDE_VERIFY_WAIT}"
                probe_state_snapshot "$expected_exe" "$intent_file" "$intent_ts"
                exit 1
                ;;
        esac
    fi

    local -a ensure_args=(ensure -c "$CONFIG_PATH")
    if [ "$FROM_CRON" -eq 1 ]; then
        ensure_args+=(--from-cron)
    fi

    # Lock fds are closed for the child: they carry no FD_CLOEXEC and would be
    # inherited by the daemonised guard, pinning the action lock forever.
    if ! probe_run_binary "$DBHA_CMD_TIMEOUT_ENSURE" "$BINARY_PATH" "${ensure_args[@]}"; then
        log_msg "ERROR" "ensure failed"
        # keep: never strip a possibly existing self-healing guard line just
        # because this attempt failed.
        probe_reconcile_cron_guard keep "$CRON_MARKER" "$cron_cmd"
        exit 1
    fi
    log_msg "INFO" "ensure success"

    local guard_pids
    guard_pids="$(wait_for_guard "$expected_exe" || true)"
    if [ -n "$guard_pids" ]; then
        if [ "$FROM_CRON" -eq 0 ]; then
            probe_reconcile_cron_guard present "$CRON_MARKER" "$cron_cmd"
            probe_write_intent "$intent_file" "$intent_ts" "start"
        fi
        exit 0
    fi

    if [ "$FROM_CRON" -eq 1 ]; then
        log_msg "WARN" "guard not observed after ensure, retrying on next cron tick"
        exit 0
    fi
    log_msg "ERROR" "guard not observed after ensure, verify_wait: ${DBHA_START_VERIFY_WAIT}"
    probe_state_snapshot "$expected_exe" "$intent_file" "$intent_ts"
    probe_reconcile_cron_guard keep "$CRON_MARKER" "$cron_cmd"
    exit 1
}

while [ $# -gt 0 ]; do
    case "$1" in
        --from-cron)
            FROM_CRON=1
            shift
            ;;
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
