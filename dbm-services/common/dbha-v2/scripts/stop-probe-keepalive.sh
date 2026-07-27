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

if [ ! -f "${SCRIPT_DIR}/lib/guard-utils.sh" ]; then
    echo "missing required script, path: ${SCRIPT_DIR}/lib/guard-utils.sh" >&2
    exit 1
fi
source "${SCRIPT_DIR}/lib/guard-utils.sh"

ensure_runtime_paths() {
    ensure_log_file "$LOG_FILE"
    mkdir -p -m 700 "$RUNTIME_DIR"
}

is_keepalive_cmdline() {
    local pid="$1"
    local addr="${2:-}"
    local cmdline

    cmdline="$(ps -o args= -p "$pid" 2>/dev/null || true)"
    if [ -z "$cmdline" ]; then
        return 1
    fi

    if ! validate_pid_target "$pid" "*" "$EXPECTED_EXE"; then
        return 1
    fi
    if [[ "$cmdline" != *"--ping-http-addr"* ]]; then
        return 1
    fi

    if [ -n "$addr" ]; then
        # Use [[ ]] with quoted $addr for literal string matching (no glob expansion)
        if [[ "$cmdline" == *"--ping-http-addr ${addr}"* || "$cmdline" == *"--ping-http-addr=${addr}"* ]]; then
            return 0
        fi
        return 1
    fi

    return 0
}

list_running_pids() {
    local addr="${1:-}"
    local pid seen
    seen=" "

    for proc_name in dbha-keepalive dbha-probe; do
        while IFS= read -r pid; do
            if [ -z "$pid" ]; then
                continue
            fi
            if is_keepalive_cmdline "$pid" "$addr" && [[ "$seen" != *" ${pid} "* ]]; then
                echo "$pid"
                seen="${seen}${pid} "
            fi
        done < <(pgrep -x "$proc_name" || true)
    done
}

stop_pid_if_exists() {
    local pid="$1"
    if [ -z "$pid" ]; then
        return
    fi
    if ! is_pid_running "$pid"; then
        return 0
    fi

    local starttime
    starttime="$(get_pid_starttime "$pid" 2>/dev/null || echo "")"
    kill "$pid" >/dev/null 2>&1 || true
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

    log_msg "INFO" "stopping dbha-probe keepalive"

    local pid="" target_addr=""
    if [ -f "$PID_FILE" ]; then
        pid="$(tr -d ' \t\r\n' < "$PID_FILE")"
    fi
    if [ -f "$ADDR_FILE" ]; then
        target_addr="$(tr -d ' \t\r\n' < "$ADDR_FILE")"
    fi

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
        log_msg "ERROR" "keepalive still running after stop"
        exit 1
    fi

    remove_cron_guard "$CRON_MARKER"

    rm -f "$PID_FILE" "$ADDR_FILE"

    log_msg "INFO" "dbha-probe keepalive stopped and crontab guard removed, marker: ${CRON_MARKER}"
}

main
