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
    if [ ! -f "$CONFIG_PATH" ]; then
        log_msg "ERROR" "config missing, path: ${CONFIG_PATH}"
        exit 1
    fi

    local cron_cmd="cd \"${SCRIPT_DIR}\" && ./bin/dbha-probe ensure -c etc/probe.yaml --from-cron >>\"${LOG_ROOT}/dbha-v2-probe-cron.log\" 2>&1"
    local ensure_args=(ensure -c "$CONFIG_PATH")
    if [ "$FROM_CRON" -eq 1 ]; then
        ensure_args+=(--from-cron)
    fi

    if "$BINARY_PATH" "${ensure_args[@]}"; then
        log_msg "INFO" "ensure success"
        if [ "$FROM_CRON" -eq 0 ]; then
            register_cron_guard "$cron_cmd" "$CRON_MARKER"
        fi
        exit 0
    fi

    log_msg "ERROR" "ensure failed"
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
