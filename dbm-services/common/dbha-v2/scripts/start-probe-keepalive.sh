#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")" || exit 1

readonly SCRIPT_DIR="$(pwd)"
readonly BINARY_PATH="./bin/dbha-probe"
readonly LOG_ROOT="${DBHA_LOG_ROOT:-${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/logs}"
# Must match keepaliveRuntimeDir() in internal/probe/cmds/ensure.go, otherwise
# the shell and the binary would take different ensure locks.
readonly RUNTIME_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/dbha-v2/runtime"
readonly CRON_MARKER="DBHA_PROBE_KEEPALIVE_GUARD"

LOG_FILE="${LOG_ROOT}/dbha-v2-keepalive.log"
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
    echo "Usage: $0 --ping-http-addr <host:port> [--from-cron] [--intent-ts <nanoseconds>]"
    echo "  host:port format for IPv4/hostname (e.g. 127.0.0.1:18080)"
    echo "  [host]:port format for IPv6 (e.g. [::1]:18080)"
    echo "  --intent-ts  originating request time; without it the fence compares"
    echo "               script start times (see scripts/README.md)"
    echo "Example: $0 --ping-http-addr 127.0.0.1:18080"
}

PING_HTTP_ADDR=""

# wait_for_keepalive <expected_exe> <addr>
# ensure-keepalive exits 0 both when it started the process and when it skipped
# on lock contention, so a zero exit alone does not prove the target state.
wait_for_keepalive() {
    local expected_exe="$1" addr="$2"
    local deadline iter max_iter pids

    if [ "$DBHA_START_VERIFY_WAIT" -le 0 ]; then
        echo "skipped"
        return 0
    fi

    deadline=$(( $(date +%s) + DBHA_START_VERIFY_WAIT ))
    iter=0
    max_iter=$(( DBHA_START_VERIFY_WAIT * 5 + 20 ))

    while :; do
        pids="$(probe_keepalive_pids "$expected_exe" "$addr" || true)"
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

    if [ "$FROM_CRON" -eq 1 ]; then
        probe_lc_quiet 1
    fi

    probe_load_lifecycle_conf "$install_root"
    probe_apply_defaults

    if ! mkdir -p -m 700 "$RUNTIME_DIR"; then
        log_msg "ERROR" "cannot create runtime dir, path: ${RUNTIME_DIR}"
        exit 1
    fi

    local action_lock ensure_lock intent_file
    # One action lock for all addresses: crontab and the intent record are
    # shared resources, so per-addr locks would not protect them.
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

    local intent_ts cron_cmd
    intent_ts="$(probe_resolve_intent_ts "$INTENT_TS_ARG")"
    cron_cmd="$(probe_keepalive_cron_cmd "$SCRIPT_DIR" "$LOG_ROOT" "$PING_HTTP_ADDR")"

    if [ "$FROM_CRON" -eq 1 ]; then
        if ! probe_acquire_lock "$action_lock" 9 "$DBHA_LOCK_WAIT" 1; then
            exit 0
        fi
    else
        if ! probe_acquire_lock "$action_lock" 9 "$DBHA_LOCK_WAIT" 0; then
            log_msg "ERROR" "cannot acquire action lock, path: ${action_lock}, waited: ${DBHA_LOCK_WAIT}"
            exit 1
        fi
    fi
    export DBHA_PROBE_ACTION_LOCK_HELD="$action_lock"

    if ! probe_reap_keepalive_orphans "$expected_exe" "$PING_HTTP_ADDR"; then
        log_msg "ERROR" "deleted-exe keepalive orphans still running, addr: ${PING_HTTP_ADDR}"
        probe_reconcile_cron_guard keep "$CRON_MARKER" "$cron_cmd"
        probe_state_snapshot "$expected_exe" "$intent_file" "$intent_ts"
        exit 1
    fi

    if [ "$FROM_CRON" -eq 0 ]; then
        # addr scoped: an operation on a different address is unrelated, not a
        # conflicting intent.
        probe_fence_decide "$intent_file" "$intent_ts" "start" "$expected_exe" \
            "$CRON_MARKER" "$PING_HTTP_ADDR"
        case "$PROBE_LC_FENCE_ACTION" in
            yield_ok)
                log_msg "INFO" "target state already reached, action: start, addr: ${PING_HTTP_ADDR}"
                probe_reconcile_cron_guard "$PROBE_LC_FENCE_CRON" "$CRON_MARKER" "$cron_cmd"
                exit 0
                ;;
            yield_conflict)
                log_msg "WARN" "operation superseded by later action, action: start, addr: ${PING_HTTP_ADDR}"
                probe_reconcile_cron_guard "$PROBE_LC_FENCE_CRON" "$CRON_MARKER" "$cron_cmd"
                if probe_wait_target_state "$PROBE_LC_FENCE_LATEST_ACTION" "$expected_exe" \
                        "$CRON_MARKER" "$PING_HTTP_ADDR" "$DBHA_SUPERSEDE_VERIFY_WAIT"; then
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

    local ensure_args=(ensure-keepalive --ping-http-addr "$PING_HTTP_ADDR")
    if [ "$FROM_CRON" -eq 1 ]; then
        ensure_args+=(--from-cron)
    fi

    if ! probe_run_binary "$DBHA_CMD_TIMEOUT_ENSURE" "$BINARY_PATH" "${ensure_args[@]}"; then
        log_msg "ERROR" "ensure-keepalive failed"
        probe_reconcile_cron_guard keep "$CRON_MARKER" "$cron_cmd"
        exit 1
    fi

    local ka_pids
    ka_pids="$(wait_for_keepalive "$expected_exe" "$PING_HTTP_ADDR" || true)"
    if [ -z "$ka_pids" ]; then
        if [ "$FROM_CRON" -eq 1 ]; then
            log_msg "WARN" "keepalive not observed after ensure, retrying on next cron tick"
            exit 0
        fi
        log_msg "ERROR" "keepalive not observed after ensure, addr: ${PING_HTTP_ADDR}"
        probe_state_snapshot "$expected_exe" "$intent_file" "$intent_ts"
        probe_reconcile_cron_guard keep "$CRON_MARKER" "$cron_cmd"
        exit 1
    fi

    if [ "$FROM_CRON" -eq 0 ]; then
        probe_reconcile_cron_guard present "$CRON_MARKER" "$cron_cmd"
        probe_write_intent "$intent_file" "$intent_ts" "start" "$PING_HTTP_ADDR"
    fi

    log_msg "INFO" "dbha-probe keepalive ensured, addr: ${PING_HTTP_ADDR}"
    log_msg "INFO" "health check: curl http://${PING_HTTP_ADDR}/ping"
}

main "$@"
