#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")" || exit 1

readonly SCRIPT_DIR="$(pwd)"
readonly BINARY_PATH="./bin/dbha-probe"
readonly LOG_ROOT="${DBHA_LOG_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/logs}"
readonly RUNTIME_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/runtime"
readonly PID_FILE="${RUNTIME_DIR}/probe-keepalive.pid"
readonly ADDR_FILE="${RUNTIME_DIR}/probe-keepalive.addr"
readonly CRON_MARKER="DBHA_PROBE_KEEPALIVE_GUARD"
readonly STARTUP_CHECK_TRIES=15
readonly STOP_WAIT_TRIES=15

LOG_FILE="${LOG_ROOT}/dbha-v2-keepalive.log"
FROM_CRON=0
EXPECTED_EXE=""

if [ ! -f "${SCRIPT_DIR}/lib/guard-utils.sh" ]; then
    echo "missing required script, path: ${SCRIPT_DIR}/lib/guard-utils.sh" >&2
    exit 1
fi
source "${SCRIPT_DIR}/lib/guard-utils.sh"

usage() {
    echo "Usage: $0 --ping-http-addr <host:port> [--from-cron]"
    echo "  host:port format for IPv4/hostname (e.g. 127.0.0.1:18080)"
    echo "  [host]:port format for IPv6 (e.g. [::1]:18080)"
    echo "Example: $0 --ping-http-addr 127.0.0.1:18080"
}

PING_HTTP_ADDR=""

ensure_runtime_paths() {
    ensure_log_file "$LOG_FILE"
    mkdir -p -m 700 "$RUNTIME_DIR"
}

validate_ping_http_addr() {
    local addr="$1"
    local host port

    # Support [IPv6]:port bracketed format
    if [[ "$addr" == \[*\]:* ]]; then
        local inner="${addr#\[}"
        host="${inner%%\]*}"
        port="${addr##*\]:}"
    elif [[ "$addr" == *:* ]]; then
        # Plain host:port format (IPv4/hostname)
        host="${addr%:*}"
        port="${addr##*:}"
    else
        echo "Invalid --ping-http-addr, errmsg: must be host:port or [host]:port" >&2
        exit 1
    fi

    # Reject bare IPv6 (colons in host without brackets)
    if [[ "$addr" != \[*\]* && "$host" == *:* ]]; then
        echo "Invalid --ping-http-addr, errmsg: IPv6 addresses must use bracketed format, e.g. [::1]:port" >&2
        exit 1
    fi

    if [ -z "$host" ] || [ -z "$port" ]; then
        echo "Invalid --ping-http-addr, errmsg: must be host:port or [host]:port" >&2
        exit 1
    fi

    if [[ "$addr" == \[*\]* ]]; then
        # Bracketed (IPv6) host: allow hex digits, colons, dots
        if [[ ! "$host" =~ ^[A-Za-z0-9.:]+$ ]]; then
            echo "Invalid --ping-http-addr, errmsg: invalid IPv6 host" >&2
            exit 1
        fi
    else
        if [[ ! "$host" =~ ^[A-Za-z0-9._-]+$ ]]; then
            echo "Invalid --ping-http-addr, errmsg: invalid host" >&2
            exit 1
        fi
    fi

    if [[ ! "$port" =~ ^[0-9]+$ ]]; then
        echo "Invalid --ping-http-addr, errmsg: invalid port" >&2
        exit 1
    fi

    if [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
        echo "Invalid --ping-http-addr, errmsg: port out of range" >&2
        exit 1
    fi
}

is_keepalive_cmdline() {
    local pid="$1"
    local addr="$2"
    local cmdline

    cmdline="$(ps -o args= -p "$pid" 2>/dev/null || true)"
    if [ -z "$cmdline" ]; then
        return 1
    fi

    if ! validate_pid_target "$pid" "*" "$EXPECTED_EXE"; then
        return 1
    fi

    # Use [[ ]] with quoted $addr for literal string matching (no glob expansion)
    if [[ "$cmdline" == *"--ping-http-addr ${addr}"* || "$cmdline" == *"--ping-http-addr=${addr}"* ]]; then
        return 0
    fi
    return 1
}

list_running_pids() {
    local addr="$1"
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

wait_keepalive_ready() {
    local pid="$1"
    local addr="$2"
    local i

    for ((i=0; i<STARTUP_CHECK_TRIES; i++)); do
        if ! is_pid_running "$pid"; then
            return 1
        fi
        if is_keepalive_cmdline "$pid" "$addr"; then
            return 0
        fi
        sleep 0.2
    done
    return 1
}

cleanup_state_files() {
    rm -f "$PID_FILE" "$ADDR_FILE"
}

main() {
    while [ $# -gt 0 ]; do
        case "$1" in
            --ping-http-addr)
                if [ $# -lt 2 ] || [ -z "${2:-}" ]; then
                    echo "Invalid --ping-http-addr, errmsg: empty value" >&2
                    usage
                    exit 1
                fi
                PING_HTTP_ADDR="$2"
                shift 2
                ;;
            --ping-http-addr=*)
                PING_HTTP_ADDR="${1#*=}"
                if [ -z "$PING_HTTP_ADDR" ]; then
                    echo "Invalid --ping-http-addr, errmsg: empty value" >&2
                    usage
                    exit 1
                fi
                shift
                ;;
            --from-cron)
                FROM_CRON=1
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                echo "Unknown argument: $1" >&2
                usage
                exit 1
                ;;
        esac
    done

    if [ -z "$PING_HTTP_ADDR" ]; then
        echo "Missing required argument --ping-http-addr" >&2
        usage
        exit 1
    fi

    validate_ping_http_addr "$PING_HTTP_ADDR"

    if [ ! -x "$BINARY_PATH" ]; then
        echo "dbha-probe binary not found or not executable, path: ${BINARY_PATH}" >&2
        exit 1
    fi

    EXPECTED_EXE="$(readlink -f "$BINARY_PATH")"
    ensure_runtime_paths

    local running_pids running_pid
    running_pids="$(list_running_pids "$PING_HTTP_ADDR" || true)"
    if [ -n "$running_pids" ]; then
        if [ "$FROM_CRON" -eq 1 ]; then
            log_msg "INFO" "keepalive already running, skip restart in cron"
            exit 0
        fi
        log_msg "INFO" "existing keepalive detected, restarting"
        while IFS= read -r running_pid; do
            [ -z "$running_pid" ] && continue
            if ! stop_pid_if_exists "$running_pid"; then
                log_msg "ERROR" "stop existing keepalive failed, pid: ${running_pid}"
                exit 1
            fi
        done <<< "$running_pids"

        if [ -n "$(list_running_pids "$PING_HTTP_ADDR" || true)" ]; then
            log_msg "ERROR" "restart aborted, keepalive still running after stop"
            exit 1
        fi
    fi

    log_msg "INFO" "starting dbha-probe keepalive in background, ping_http_addr: ${PING_HTTP_ADDR}"
    nohup "$BINARY_PATH" --ping-http-addr "$PING_HTTP_ADDR" >>"$LOG_FILE" 2>&1 &

    local PID
    PID=$!
    echo "$PID" > "$PID_FILE"
    echo "$PING_HTTP_ADDR" > "$ADDR_FILE"

    if ! wait_keepalive_ready "$PID" "$PING_HTTP_ADDR"; then
        log_msg "ERROR" "keepalive startup check failed, pid: ${PID}"
        stop_pid_if_exists "$PID" || true
        cleanup_state_files
        exit 1
    fi

    if [ "$FROM_CRON" -eq 0 ]; then
        local cron_cmd="cd \"${SCRIPT_DIR}\" && ./start-probe-keepalive.sh --ping-http-addr \"${PING_HTTP_ADDR}\" --from-cron >>\"${LOG_ROOT}/dbha-v2-keepalive-cron.log\" 2>&1"
        register_cron_guard "$cron_cmd" "$CRON_MARKER"
    fi

    log_msg "INFO" "dbha-probe keepalive started, pid: ${PID}"
    log_msg "INFO" "log file: ${LOG_FILE}"
    log_msg "INFO" "health check: curl http://${PING_HTTP_ADDR}/ping"
}

main "$@"
