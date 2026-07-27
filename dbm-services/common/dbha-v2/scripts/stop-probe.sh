#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")" || exit 1

readonly SCRIPT_DIR="$(pwd)"
readonly LOG_ROOT="${DBHA_LOG_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/logs}"
readonly PROC_NAME="dbha-probe"
readonly BINARY_PATH="./bin/dbha-probe"
readonly CONFIG_PATH="./etc/probe.yaml"
readonly CRON_MARKER="DBHA_V2_PROBE_GUARD"

LOG_FILE="${LOG_ROOT}/dbha-v2-probe.log"

if [ ! -f "${SCRIPT_DIR}/lib/guard-utils.sh" ]; then
    echo "missing required script, path: ${SCRIPT_DIR}/lib/guard-utils.sh" >&2
    exit 1
fi
source "${SCRIPT_DIR}/lib/guard-utils.sh"

main() {
    ensure_log_file "$LOG_FILE"

    if [ ! -x "$BINARY_PATH" ]; then
        log_msg "ERROR" "binary missing, path: ${BINARY_PATH}"
        exit 1
    fi

    local expected_exe
    expected_exe="$(readlink -f "$BINARY_PATH")"

    log_msg "INFO" "stopping ${PROC_NAME}"
    "$BINARY_PATH" stop -c "$CONFIG_PATH" >/dev/null 2>&1 || true

    # TERM pass: record starttimes to detect PID recycling
    local -a term_pids=() term_starttimes=()
    local remaining pid
    remaining="$(get_valid_pids "$PROC_NAME" "$expected_exe" || true)"
    while IFS= read -r pid; do
        [ -z "$pid" ] && continue
        term_pids+=("$pid")
        term_starttimes+=("$(get_pid_starttime "$pid" 2>/dev/null || echo "")")
        signal_pid_safe "$pid" "TERM" "$PROC_NAME" "$expected_exe" || true
    done <<< "$remaining"

    sleep 1
    # KILL pass: verify PID not recycled before sending KILL
    for i in "${!term_pids[@]}"; do
        local term_pid="${term_pids[$i]}"
        if validate_pid_target "$term_pid" "$PROC_NAME" "$expected_exe"; then
            if ! wait_pid_exit "$term_pid" 10; then
                safe_kill_after_term "$term_pid" "$PROC_NAME" "$expected_exe" "${term_starttimes[$i]}" || true
            fi
        fi
    done

    remove_cron_guard "$CRON_MARKER"

    if [ -n "$(get_valid_pids "$PROC_NAME" "$expected_exe" || true)" ]; then
        log_msg "ERROR" "${PROC_NAME} still running after fallback"
        exit 1
    fi

    log_msg "INFO" "${PROC_NAME} stopped successfully"
}

main
