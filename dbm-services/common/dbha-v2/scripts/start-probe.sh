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
FROM_CRON=0

if [ ! -f "${SCRIPT_DIR}/lib/guard-utils.sh" ]; then
    echo "missing required script, path: ${SCRIPT_DIR}/lib/guard-utils.sh" >&2
    exit 1
fi
source "${SCRIPT_DIR}/lib/guard-utils.sh"

is_guard_pid() {
    local pid="$1"
    local cfg="$2"
    local args
    args="$(ps -o args= -p "$pid" 2>/dev/null || true)"
    [[ "$args" == *" daemon-start -c "*"$cfg"* ]]
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

    local expected_exe pids guards=() workers=() pid
    expected_exe="$(readlink -f "$BINARY_PATH")"
    local cron_cmd="cd \"${SCRIPT_DIR}\" && ./start-probe.sh --from-cron >>\"${LOG_ROOT}/dbha-v2-probe-cron.log\" 2>&1"
    pids="$(get_valid_pids "$PROC_NAME" "$expected_exe" || true)"

    while IFS= read -r pid; do
        [ -z "$pid" ] && continue
        if is_guard_pid "$pid" "$CONFIG_PATH"; then
            guards+=("$pid")
        else
            workers+=("$pid")
        fi
    done <<< "$pids"

    # Guard-first: if guard exists, keep current state and avoid duplicate daemon-start.
    if [ ${#guards[@]} -gt 0 ]; then
        log_msg "INFO" "guard already running, keep current state"
        if [ "$FROM_CRON" -eq 0 ]; then
            register_cron_guard "$cron_cmd" "$CRON_MARKER"
        fi
        exit 0
    fi

    # If only worker exists, terminate stale worker and recover to guard+worker shape.
    if [ ${#workers[@]} -gt 0 ]; then
        log_msg "WARN" "worker without guard detected, converting to guard+worker mode"
        local -a starttimes=()
        for pid in "${workers[@]}"; do
            starttimes+=("$(get_pid_starttime "$pid" 2>/dev/null || echo "")")
            signal_pid_safe "$pid" "TERM" "$PROC_NAME" "$expected_exe" || true
        done
        sleep 1
        for i in "${!workers[@]}"; do
            safe_kill_after_term "${workers[$i]}" "$PROC_NAME" "$expected_exe" "${starttimes[$i]}" || true
        done
    fi

    if "$BINARY_PATH" daemon-start -c "$CONFIG_PATH"; then
        log_msg "INFO" "daemon-start success"
        if [ "$FROM_CRON" -eq 0 ]; then
            register_cron_guard "$cron_cmd" "$CRON_MARKER"
        fi
        exit 0
    fi

    log_msg "ERROR" "daemon-start failed"
    exit 1
}

while [ $# -gt 0 ]; do
    case "$1" in
        --from-cron)
            FROM_CRON=1
            shift
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

main
