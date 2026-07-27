#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")" || exit 1

readonly SCRIPT_DIR="$(pwd)"
readonly BINARY_PATH="./bin/dbha-probe"
readonly LOG_ROOT="${DBHA_LOG_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/logs}"
readonly CRON_MARKER="DBHA_PROBE_KEEPALIVE_GUARD"

LOG_FILE="${LOG_ROOT}/dbha-v2-keepalive.log"
FROM_CRON=0

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

validate_ping_http_addr() {
    local addr="$1"
    local host port

    if [[ "$addr" == \[*\]:* ]]; then
        local inner="${addr#\[}"
        host="${inner%%\]*}"
        port="${addr##*\]:}"
    elif [[ "$addr" == *:* ]]; then
        host="${addr%:*}"
        port="${addr##*:}"
    else
        echo "Invalid --ping-http-addr, errmsg: must be host:port or [host]:port" >&2
        exit 1
    fi

    if [[ "$addr" != \[*\]* && "$host" == *:* ]]; then
        echo "Invalid --ping-http-addr, errmsg: IPv6 addresses must use bracketed format, e.g. [::1]:port" >&2
        exit 1
    fi

    if [ -z "$host" ] || [ -z "$port" ]; then
        echo "Invalid --ping-http-addr, errmsg: must be host:port or [host]:port" >&2
        exit 1
    fi

    if [[ "$addr" == \[*\]* ]]; then
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

    ensure_log_file "$LOG_FILE"

    local ensure_args=(ensure-keepalive --ping-http-addr "$PING_HTTP_ADDR")
    if [ "$FROM_CRON" -eq 1 ]; then
        ensure_args+=(--from-cron)
    fi

    if ! "$BINARY_PATH" "${ensure_args[@]}"; then
        log_msg "ERROR" "ensure-keepalive failed"
        exit 1
    fi

    if [ "$FROM_CRON" -eq 0 ]; then
        local cron_cmd="cd \"${SCRIPT_DIR}\" && ./bin/dbha-probe ensure-keepalive --ping-http-addr \"${PING_HTTP_ADDR}\" --from-cron >>\"${LOG_ROOT}/dbha-v2-keepalive-cron.log\" 2>&1"
        register_cron_guard "$cron_cmd" "$CRON_MARKER"
    fi

    log_msg "INFO" "dbha-probe keepalive ensured, addr: ${PING_HTTP_ADDR}"
    log_msg "INFO" "health check: curl http://${PING_HTTP_ADDR}/ping"
}

main "$@"
