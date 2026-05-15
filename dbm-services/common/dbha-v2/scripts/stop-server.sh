#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")" || exit 1

readonly SCRIPT_DIR="$(pwd)"
readonly LOG_ROOT="${DBHA_LOG_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/logs}"
readonly SERVICES=(admin receiver analysis)
readonly CRON_MARKER_PREFIX="DBHA_V2_SERVER_GUARD"

LOG_FILE=""

if [ ! -f "${SCRIPT_DIR}/lib/guard-utils.sh" ]; then
    echo "missing required script, path: ${SCRIPT_DIR}/lib/guard-utils.sh" >&2
    exit 1
fi
source "${SCRIPT_DIR}/lib/guard-utils.sh"

main() {
    local fail_count=0
    local -a term_pids=() term_starttimes=()
    local pids pid expected_exe term_pid

    for svc in "${SERVICES[@]}"; do
        local bin="./bin/dbha-${svc}"
        local cfg="./etc/${svc}.yaml"
        local expected_name="dbha-${svc}"

        LOG_FILE="${LOG_ROOT}/dbha-v2-${svc}.log"
        ensure_log_file "$LOG_FILE"

        if [ ! -x "$bin" ]; then
            log_msg "ERROR" "binary missing, path: ${bin}"
            fail_count=$((fail_count + 1))
            continue
        fi

        expected_exe="$(readlink -f "$bin")"
        log_msg "INFO" "stopping ${expected_name}"
        "$bin" stop -c "$cfg" >/dev/null 2>&1 || true

        # TERM pass: record starttimes to detect PID recycling
        term_pids=()
        term_starttimes=()
        pids="$(get_valid_pids "$expected_name" "$expected_exe" || true)"
        while IFS= read -r pid; do
            [ -z "$pid" ] && continue
            term_pids+=("$pid")
            term_starttimes+=("$(get_pid_starttime "$pid" 2>/dev/null || echo "")")
            signal_pid_safe "$pid" "TERM" "$expected_name" "$expected_exe" || true
        done <<< "$pids"

        sleep 1
        # KILL pass: verify PID not recycled before sending KILL
        for i in "${!term_pids[@]}"; do
            term_pid="${term_pids[$i]}"
            if ! wait_pid_exit "$term_pid" 10; then
                safe_kill_after_term "$term_pid" "$expected_name" "$expected_exe" "${term_starttimes[$i]}" || true
            fi
        done

        remove_cron_guard "${CRON_MARKER_PREFIX}_${svc^^}"

        if [ -n "$(get_valid_pids "$expected_name" "$expected_exe" || true)" ]; then
            log_msg "ERROR" "${expected_name} still running after fallback"
            fail_count=$((fail_count + 1))
        else
            log_msg "INFO" "${expected_name} stopped successfully"
        fi
    done

    if [ "$fail_count" -gt 0 ]; then
        exit 1
    fi
}

main
