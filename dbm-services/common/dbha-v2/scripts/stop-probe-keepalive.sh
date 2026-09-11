#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")" || exit 1

readonly SCRIPT_DIR="$(pwd)"
readonly LOG_ROOT="${DBHA_LOG_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/logs}"
readonly RUNTIME_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/runtime"
readonly PID_FILE="${RUNTIME_DIR}/probe-keepalive.pid"
readonly ADDR_FILE="${RUNTIME_DIR}/probe-keepalive.addr"
readonly CRON_MARKER="DBHA_PROBE_KEEPALIVE_GUARD"
readonly BINARY_PATH="./bin/dbha-probe"
readonly STOP_WAIT_TRIES=15

LOG_FILE="${LOG_ROOT}/dbha-v2-keepalive.log"
EXPECTED_EXE=""
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

ensure_runtime_paths() {
    ensure_log_file "$LOG_FILE"
    mkdir -p -m 700 "$RUNTIME_DIR"
}

is_keepalive_cmdline() {
    local pid="$1"
    local addr="${2:-}"

    if ! validate_pid_target "$pid" "*" "$EXPECTED_EXE" \
            && ! probe_exe_deleted_matches "$pid" "*" "$EXPECTED_EXE"; then
        return 1
    fi
    # Reads /proc rather than "ps -o args=", which truncates long argv and could
    # make a long address look like a non-match. Shared with the start script so
    # both sides classify identically.
    probe_keepalive_pid_matches_addr "$pid" "$addr"
}

list_running_pids() {
    local addr="${1:-}" pid seen=" "
    while IFS= read -r pid; do
        [ -n "$pid" ] || continue
        case "$seen" in
            *" ${pid} "*) continue ;;
        esac
        echo "$pid"
        seen="${seen}${pid} "
    done < <(
        probe_keepalive_pids "$EXPECTED_EXE" "$addr"
        probe_keepalive_orphan_pids "$EXPECTED_EXE" "$addr"
    )
}

stop_pid_if_exists() {
    local pid="$1"
    if [ -z "$pid" ]; then
        return 0
    fi
    if ! is_pid_running "$pid"; then
        return 0
    fi

    local starttime
    starttime="$(get_pid_starttime "$pid" 2>/dev/null || echo "")"
    if probe_exe_deleted_matches "$pid" "*" "$EXPECTED_EXE"; then
        probe_signal_orphan_pid "$pid" "TERM" "*" "$EXPECTED_EXE" "$starttime" || true
        if ! wait_pid_exit "$pid" "$STOP_WAIT_TRIES"; then
            probe_signal_orphan_pid "$pid" "KILL" "*" "$EXPECTED_EXE" "$starttime" || true
            if ! wait_pid_exit "$pid" "$STOP_WAIT_TRIES"; then
                return 1
            fi
        fi
        return 0
    fi
    # Was a bare kill: the pid could have been recycled between listing and
    # signalling, letting the TERM land on an unrelated process.
    probe_signal_pid_safe "$pid" "TERM" "*" "$EXPECTED_EXE" "$starttime" || true
    if ! wait_pid_exit "$pid" "$STOP_WAIT_TRIES"; then
        safe_kill_after_term "$pid" "*" "$EXPECTED_EXE" "$starttime" || true
        if ! wait_pid_exit "$pid" "$STOP_WAIT_TRIES"; then
            return 1
        fi
    fi
    return 0
}

main() {
    if [ ! -x "$BINARY_PATH" ]; then
        echo "dbha-probe binary not found or not executable, path: ${BINARY_PATH}" >&2
        exit 1
    fi

    EXPECTED_EXE="$(readlink -f "$BINARY_PATH")"
    ensure_runtime_paths

    if ! probe_check_deps; then
        exit 1
    fi

    local install_root
    install_root="$(probe_install_root "$BINARY_PATH" || true)"
    if [ -z "$install_root" ]; then
        log_msg "ERROR" "cannot resolve install root, path: ${BINARY_PATH}"
        exit 1
    fi

    probe_load_lifecycle_conf "$install_root"
    probe_apply_defaults

    local action_lock ensure_lock intent_file
    action_lock="${RUNTIME_DIR}/probe-keepalive.action.lock"
    ensure_lock="${RUNTIME_DIR}/probe-keepalive.ensure.lock"
    intent_file="${RUNTIME_DIR}/probe-keepalive.intent"

    if [ "$action_lock" = "$ensure_lock" ]; then
        log_msg "ERROR" "action lock and ensure lock must differ, path: ${action_lock}"
        exit 1
    fi
    if ! probe_guard_nested_call "$action_lock"; then
        exit 1
    fi

    probe_install_lock_traps

    local intent_ts
    intent_ts="$(probe_resolve_intent_ts "$INTENT_TS_ARG")"

    if ! probe_acquire_lock "$action_lock" 9 "$DBHA_LOCK_WAIT" 0; then
        log_msg "ERROR" "cannot acquire action lock, path: ${action_lock}, waited: ${DBHA_LOCK_WAIT}"
        exit 1
    fi
    export DBHA_PROBE_ACTION_LOCK_HELD="$action_lock"

    log_msg "INFO" "stopping dbha-probe keepalive"

    # Read under the lock: these files are rewritten by concurrent operations.
    local pid="" target_addr=""
    if [ -f "$PID_FILE" ]; then
        pid="$(tr -d ' \t\r\n' < "$PID_FILE")"
    fi
    if [ -f "$ADDR_FILE" ]; then
        target_addr="$(tr -d ' \t\r\n' < "$ADDR_FILE")"
    fi

    probe_reap_keepalive_orphans "$EXPECTED_EXE" "$target_addr" || true

    # Without a recorded address the guard line cannot be rebuilt, so cron
    # reconciliation towards "present" degrades to keep (absent still works,
    # it only needs the marker). Without addr the fence also cannot tell which
    # instance is the target, so it is skipped rather than mis-applied.
    local cron_cmd=""
    if [ -n "$target_addr" ]; then
        cron_cmd="$(probe_keepalive_cron_cmd "$SCRIPT_DIR" "$LOG_ROOT" "$target_addr")"
        probe_fence_decide "$intent_file" "$intent_ts" "stop" "$EXPECTED_EXE" "$CRON_MARKER" "$target_addr"
        case "$PROBE_LC_FENCE_ACTION" in
            yield_ok)
                log_msg "INFO" "target state already reached, action: stop, addr: ${target_addr}"
                probe_reconcile_cron_guard "$PROBE_LC_FENCE_CRON" "$CRON_MARKER" "$cron_cmd"
                exit 0
                ;;
            yield_conflict)
                log_msg "WARN" "operation superseded by later action, action: stop, addr: ${target_addr}"
                probe_reconcile_cron_guard "$PROBE_LC_FENCE_CRON" "$CRON_MARKER" "$cron_cmd"
                log_msg "ERROR" "stop not applied and probe not down, blocking caller"
                log_msg "ERROR" "latest_action: ${PROBE_LC_FENCE_LATEST_ACTION}"
                probe_state_snapshot "$EXPECTED_EXE" "$intent_file" "$intent_ts"
                exit 1
                ;;
        esac
    else
        log_msg "WARN" "keepalive addr file missing, skipping intent fence, path: ${ADDR_FILE}"
    fi

    # Best effort, same rationale as stop-probe.sh: a stuck ensure lock must
    # never make stop permanently impossible.
    if ! probe_acquire_lock "$ensure_lock" 8 "$DBHA_ENSURE_LOCK_WAIT" 0; then
        log_msg "WARN" "ensure lock not acquired, degraded to best-effort, path: ${ensure_lock}"
        probe_ensure_lock_holder_hint "$ensure_lock"
    fi

    # Deregister before killing so a cron tick cannot restart keepalive behind us.
    probe_reconcile_cron_guard absent "$CRON_MARKER" "$cron_cmd"

    if [ -n "$pid" ] && is_keepalive_cmdline "$pid" "$target_addr"; then
        log_msg "INFO" "stop keepalive by pid file, pid: ${pid}"
        if ! stop_pid_if_exists "$pid"; then
            log_msg "ERROR" "stop keepalive failed, pid: ${pid}"
        fi
    fi

    local running_pids running_pid
    running_pids="$(list_running_pids "$target_addr" || true)"
    while IFS= read -r running_pid; do
        [ -z "$running_pid" ] && continue
        if [ "$running_pid" = "$pid" ]; then
            continue
        fi
        log_msg "INFO" "stop keepalive by fallback detection, pid: ${running_pid}"
        if ! stop_pid_if_exists "$running_pid"; then
            log_msg "ERROR" "stop keepalive failed, pid: ${running_pid}"
        fi
    done <<< "$running_pids"

    local remaining_pids
    remaining_pids="$(list_running_pids "$target_addr" || true)"
    if [ -n "$remaining_pids" ]; then
        # Restore the guard line when we can rebuild it. Without .addr the cron
        # command is unknown, so present would write a broken line: keep instead.
        if [ -n "$cron_cmd" ]; then
            probe_reconcile_cron_guard present "$CRON_MARKER" "$cron_cmd"
        else
            log_msg "WARN" "cannot restore keepalive cron, reason: addr missing"
            probe_reconcile_cron_guard keep "$CRON_MARKER" "$cron_cmd"
        fi
        log_msg "ERROR" "keepalive still running after stop"
        probe_state_snapshot "$EXPECTED_EXE" "$intent_file" "$intent_ts"
        exit 1
    fi

    rm -f "$PID_FILE" "$ADDR_FILE"

    probe_write_intent "$intent_file" "$intent_ts" "stop" "$target_addr"

    log_msg "INFO" "dbha-probe keepalive stopped and crontab guard removed, marker: ${CRON_MARKER}"
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
