#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")" || exit 1

readonly SCRIPT_DIR="$(pwd)"
readonly LOG_ROOT="${DBHA_LOG_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/logs}"
readonly SERVICES=(admin receiver analysis)
readonly CRON_MARKER_PREFIX="DBHA_V2_SERVER_GUARD"

LOG_FILE=""
FROM_CRON=0
TARGET_SERVICE=""

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

start_service_guard_mode() {
    local svc="$1"
    local bin="./bin/dbha-${svc}"
    local cfg="./etc/${svc}.yaml"
    local expected_name="dbha-${svc}"
    local expected_exe
    local pids guards=() workers=() pid

    LOG_FILE="${LOG_ROOT}/dbha-v2-${svc}.log"
    ensure_log_file "$LOG_FILE"

    if [ ! -x "$bin" ]; then
        log_msg "ERROR" "binary missing, path: ${bin}"
        return 1
    fi
    if [ ! -f "$cfg" ]; then
        log_msg "ERROR" "config missing, path: ${cfg}"
        return 1
    fi

    expected_exe="$(readlink -f "$bin")"
    pids="$(get_valid_pids "$expected_name" "$expected_exe" || true)"

    while IFS= read -r pid; do
        [ -z "$pid" ] && continue
        if is_guard_pid "$pid" "$cfg"; then
            guards+=("$pid")
        else
            workers+=("$pid")
        fi
    done <<< "$pids"

    local marker="${CRON_MARKER_PREFIX}_${svc^^}"
    local cron_cmd="cd \"${SCRIPT_DIR}\" && ./start-server.sh --from-cron --service \"${svc}\" >>\"${LOG_ROOT}/dbha-v2-${svc}-cron.log\" 2>&1"

    # Guard-first: if guard exists, keep current state and avoid duplicate daemon-start.
    if [ ${#guards[@]} -gt 0 ]; then
        log_msg "INFO" "guard already running, keep current state"
        if [ "$FROM_CRON" -eq 0 ]; then
            register_cron_guard "$cron_cmd" "$marker"
        fi
        return 0
    fi

    # If only worker exists, terminate stale worker and recover to guard+worker shape.
    if [ ${#workers[@]} -gt 0 ]; then
        log_msg "WARN" "worker without guard detected, converting to guard+worker mode"
        local -a starttimes=()
        for pid in "${workers[@]}"; do
            starttimes+=("$(get_pid_starttime "$pid" 2>/dev/null || echo "")")
            signal_pid_safe "$pid" "TERM" "$expected_name" "$expected_exe" || true
        done
        sleep 1
        for i in "${!workers[@]}"; do
            safe_kill_after_term "${workers[$i]}" "$expected_name" "$expected_exe" "${starttimes[$i]}" || true
        done
    fi

    if "$bin" daemon-start -c "$cfg"; then
        log_msg "INFO" "daemon-start success"
        if [ "$FROM_CRON" -eq 0 ]; then
            register_cron_guard "$cron_cmd" "$marker"
        fi
        return 0
    fi

    log_msg "ERROR" "daemon-start failed"
    return 1
}

main() {
    local fail_count=0

    while [ $# -gt 0 ]; do
        case "$1" in
            --from-cron)
                FROM_CRON=1
                shift
                ;;
            --service)
                if [ $# -lt 2 ] || [ -z "${2:-}" ] || [[ "${2:-}" == --* ]]; then
                    echo "Invalid --service argument, errmsg: empty service" >&2
                    exit 1
                fi
                TARGET_SERVICE="${2:-}"
                shift 2
                ;;
            *)
                echo "Unknown argument: $1" >&2
                exit 1
                ;;
        esac
    done

    if [ -n "$TARGET_SERVICE" ]; then
        if [[ ! " ${SERVICES[*]} " =~ " ${TARGET_SERVICE} " ]]; then
            echo "Unknown service: ${TARGET_SERVICE}" >&2
            exit 1
        fi
        start_service_guard_mode "$TARGET_SERVICE"
        return $?
    fi

    for svc in "${SERVICES[@]}"; do
        start_service_guard_mode "$svc" || fail_count=$((fail_count + 1))
    done

    if [ "$fail_count" -gt 0 ]; then
        return 1
    fi
}

main "$@"
