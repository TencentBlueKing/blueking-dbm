#!/usr/bin/env bash
# probe-lifecycle-utils.sh - probe-only lifecycle concurrency helpers.
#
# Usage (probe scripts only, AFTER sourcing guard-utils.sh):
#   source "${SCRIPT_DIR}/lib/guard-utils.sh"
#   source "${SCRIPT_DIR}/lib/probe-lifecycle-utils.sh"
#
# This library is packaged with the probe only (see Makefile package-probe).
# It never redefines anything from guard-utils.sh: every function here is
# prefixed with probe_ so that the shared library and the server-side scripts
# that consume it stay byte-for-byte untouched.
#
# Compatibility baseline is bash 3.2: no mapfile/readarray, no declare -A,
# no dynamic "exec {fd}>", no ${var^^}, no ${EPOCHREALTIME}.
# External commands are limited to those the probe scripts already use.

# guard-utils.sh must be loaded first: we rely on log_msg, validate_pid_target,
# get_pid_starttime, is_pid_running, register_cron_guard, remove_cron_guard.
if [ -z "$(type -t log_msg)" ]; then
    echo "[ERROR] probe-lifecycle-utils.sh requires guard-utils.sh to be sourced first" >&2
    exit 1
fi

# Idempotent include: a second source must not re-run the readonly assignments
# below, which would print "readonly variable" errors for every constant.
if [ -n "${PROBE_LC_LOADED:-}" ]; then
    return 0 2>/dev/null || exit 0
fi
PROBE_LC_LOADED=1

# --- Tunables (env > conf file > default). Kept as plain vars for bash 3.2. ---

: "${DBHA_LOCK_WAIT:=}"
: "${DBHA_ENSURE_LOCK_WAIT:=}"
: "${DBHA_START_VERIFY_WAIT:=}"
: "${DBHA_SUPERSEDE_VERIFY_WAIT:=}"
: "${DBHA_CMD_TIMEOUT_ENSURE:=}"
: "${DBHA_CMD_TIMEOUT_STOP:=}"
: "${DBHA_INTENT_FENCE:=}"
: "${DBHA_LOCK_FORCE_MKDIR:=}"
: "${DBHA_REAP_DELETED_EXE:=}"

readonly PROBE_LC_DEFAULT_LOCK_WAIT=120
readonly PROBE_LC_DEFAULT_ENSURE_LOCK_WAIT=30
readonly PROBE_LC_DEFAULT_START_VERIFY_WAIT=10
readonly PROBE_LC_DEFAULT_SUPERSEDE_VERIFY_WAIT=5
readonly PROBE_LC_DEFAULT_CMD_TIMEOUT_ENSURE=60
readonly PROBE_LC_DEFAULT_CMD_TIMEOUT_STOP=45
# Stale mkdir-lock reclaim floor. Worst-case legitimate hold is ~70s (a full
# stop), so 300s never steals a live lock.
readonly PROBE_LC_STALE_FLOOR=300
# Intent timestamps further than this into the future mean a bad clock or a bad
# --intent-ts injection; the fence is then ignored rather than trusted.
readonly PROBE_LC_CLOCK_SKEW=5

# Runtime state.
PROBE_LC_MKDIR_LOCKS=()
PROBE_LC_LOCKS_RELEASED=0
PROBE_LC_LOCK_IMPL=""
PROBE_LC_TIMEOUT_BIN=""
PROBE_LC_QUIET=0

# Fence decision outputs, read by callers after probe_fence_decide.
PROBE_LC_FENCE_ACTION=""
PROBE_LC_FENCE_CRON=""
PROBE_LC_FENCE_LATEST_ACTION=""

# probe_lc_quiet <0|1>
# When 1, informational one-shot notices are suppressed. Used for --from-cron so
# that hosts whose crontab still runs start-probe.sh every minute do not get
# extra log lines (probe script logs have no rotation).
probe_lc_quiet() {
    PROBE_LC_QUIET="${1:-0}"
}

probe_lc_info() {
    if [ "$PROBE_LC_QUIET" -eq 0 ]; then
        log_msg "INFO" "$1"
    fi
}

probe_lc_warn() {
    if [ "$PROBE_LC_QUIET" -eq 0 ]; then
        log_msg "WARN" "$1"
    fi
}

# --- Config file (optional escape hatches) ---

# probe_load_lifecycle_conf <install_root>
# Reads etc/probe-lifecycle.conf when present. Deliberately does NOT source the
# file: only whitelisted keys with strictly numeric values are honoured, so a
# tampered file cannot execute code. Environment variables always win.
#
# Rationale: DBM dispatches bare "./stop-probe.sh" with no environment, and
# etc/dbha-v2.probe.rc.example is a render_configs.py template file, not a shell
# rc. Without this file the tunables would be unreachable in production.
probe_load_lifecycle_conf() {
    local install_root="$1"
    local conf="${install_root}/etc/probe-lifecycle.conf"
    local line key val

    [ -f "$conf" ] || return 0
    if [ -L "$conf" ]; then
        log_msg "WARN" "ignore lifecycle conf, reason: path is symlink, path: ${conf}"
        return 0
    fi

    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in
            ''|'#'*) continue ;;
        esac
        key="${line%%=*}"
        val="${line#*=}"
        # Trim surrounding blanks without invoking external commands.
        key="${key#"${key%%[![:space:]]*}"}"
        key="${key%"${key##*[![:space:]]}"}"
        val="${val#"${val%%[![:space:]]*}"}"
        val="${val%"${val##*[![:space:]]}"}"

        case "$key" in
            DBHA_LOCK_WAIT|DBHA_ENSURE_LOCK_WAIT|DBHA_START_VERIFY_WAIT|\
DBHA_SUPERSEDE_VERIFY_WAIT|DBHA_CMD_TIMEOUT_ENSURE|DBHA_CMD_TIMEOUT_STOP)
                case "$val" in
                    ''|*[!0-9]*)
                        log_msg "WARN" "ignore lifecycle conf entry, key: ${key}, reason: value not numeric"
                        continue
                        ;;
                esac
                ;;
            DBHA_INTENT_FENCE|DBHA_LOCK_FORCE_MKDIR|DBHA_REAP_DELETED_EXE)
                if [ "$val" != "0" ] && [ "$val" != "1" ]; then
                    log_msg "WARN" "ignore lifecycle conf entry, key: ${key}, reason: value not 0 or 1"
                    continue
                fi
                ;;
            *)
                log_msg "WARN" "ignore lifecycle conf entry, key: ${key}, reason: key not allowed"
                continue
                ;;
        esac

        # Environment takes precedence over the file.
        case "$key" in
            DBHA_LOCK_WAIT)             [ -n "$DBHA_LOCK_WAIT" ] || DBHA_LOCK_WAIT="$val" ;;
            DBHA_ENSURE_LOCK_WAIT)      [ -n "$DBHA_ENSURE_LOCK_WAIT" ] || DBHA_ENSURE_LOCK_WAIT="$val" ;;
            DBHA_START_VERIFY_WAIT)     [ -n "$DBHA_START_VERIFY_WAIT" ] || DBHA_START_VERIFY_WAIT="$val" ;;
            DBHA_SUPERSEDE_VERIFY_WAIT)  [ -n "$DBHA_SUPERSEDE_VERIFY_WAIT" ] || DBHA_SUPERSEDE_VERIFY_WAIT="$val" ;;
            DBHA_CMD_TIMEOUT_ENSURE)    [ -n "$DBHA_CMD_TIMEOUT_ENSURE" ] || DBHA_CMD_TIMEOUT_ENSURE="$val" ;;
            DBHA_CMD_TIMEOUT_STOP)      [ -n "$DBHA_CMD_TIMEOUT_STOP" ] || DBHA_CMD_TIMEOUT_STOP="$val" ;;
            DBHA_INTENT_FENCE)          [ -n "$DBHA_INTENT_FENCE" ] || DBHA_INTENT_FENCE="$val" ;;
            DBHA_LOCK_FORCE_MKDIR)      [ -n "$DBHA_LOCK_FORCE_MKDIR" ] || DBHA_LOCK_FORCE_MKDIR="$val" ;;
            DBHA_REAP_DELETED_EXE)      [ -n "$DBHA_REAP_DELETED_EXE" ] || DBHA_REAP_DELETED_EXE="$val" ;;
        esac
    done < "$conf"

    return 0
}

# probe_apply_defaults
# Fills unset tunables and warns when the action-lock wait cannot cover a
# worst-case stop (otherwise concurrent starts would time out deterministically).
probe_apply_defaults() {
    [ -n "$DBHA_LOCK_WAIT" ] || DBHA_LOCK_WAIT="$PROBE_LC_DEFAULT_LOCK_WAIT"
    [ -n "$DBHA_ENSURE_LOCK_WAIT" ] || DBHA_ENSURE_LOCK_WAIT="$PROBE_LC_DEFAULT_ENSURE_LOCK_WAIT"
    [ -n "$DBHA_START_VERIFY_WAIT" ] || DBHA_START_VERIFY_WAIT="$PROBE_LC_DEFAULT_START_VERIFY_WAIT"
    [ -n "$DBHA_SUPERSEDE_VERIFY_WAIT" ] || DBHA_SUPERSEDE_VERIFY_WAIT="$PROBE_LC_DEFAULT_SUPERSEDE_VERIFY_WAIT"
    [ -n "$DBHA_CMD_TIMEOUT_ENSURE" ] || DBHA_CMD_TIMEOUT_ENSURE="$PROBE_LC_DEFAULT_CMD_TIMEOUT_ENSURE"
    [ -n "$DBHA_CMD_TIMEOUT_STOP" ] || DBHA_CMD_TIMEOUT_STOP="$PROBE_LC_DEFAULT_CMD_TIMEOUT_STOP"
    [ -n "$DBHA_INTENT_FENCE" ] || DBHA_INTENT_FENCE=1
    [ -n "$DBHA_REAP_DELETED_EXE" ] || DBHA_REAP_DELETED_EXE=1

    local need=$((DBHA_ENSURE_LOCK_WAIT + DBHA_CMD_TIMEOUT_STOP + 20))
    if [ "$DBHA_LOCK_WAIT" -lt "$need" ]; then
        log_msg "WARN" "action lock wait may be too short, lock_wait: ${DBHA_LOCK_WAIT}, suggested_min: ${need}"
    fi
    local supersede_need=$((DBHA_SUPERSEDE_VERIFY_WAIT + 20))
    if [ "$DBHA_LOCK_WAIT" -lt "$supersede_need" ]; then
        log_msg "WARN" "action lock wait may be too short for supersede verify"
        log_msg "WARN" "lock_wait: ${DBHA_LOCK_WAIT}, suggested_min: ${supersede_need}"
    fi

    if command -v timeout >/dev/null 2>&1; then
        PROBE_LC_TIMEOUT_BIN="timeout"
    else
        PROBE_LC_TIMEOUT_BIN=""
        log_msg "WARN" "timeout not available, binary calls run without an upper bound"
    fi
}

# probe_check_deps
# Fails fast with an explicit list instead of breaking obscurely mid-flow.
probe_check_deps() {
    local missing="" c
    for c in pgrep readlink awk crontab date; do
        command -v "$c" >/dev/null 2>&1 || missing="${missing}${c} "
    done
    if [ ! -d /proc ]; then
        missing="${missing}/proc "
    fi
    if [ -n "$missing" ]; then
        log_msg "ERROR" "missing required dependencies, items: ${missing% }"
        return 1
    fi
    return 0
}

# probe_install_root <binary_path>
# Mirrors Go process.InstallRoot(): dir(EvalSymlinks(exe))/.. so that the shell
# and the binary agree on pids/probe.ensure.lock. A mismatch here would make the
# mutual exclusion silently useless.
probe_install_root() {
    local bin="$1" exe
    exe="$(readlink -f "$bin" 2>/dev/null || true)"
    if [ -z "$exe" ]; then
        return 1
    fi
    echo "$(dirname "$(dirname "$exe")")"
}

# --- Locks ---

probe_lc_now() {
    date +%s
}

# probe_open_lock_fd <fd> <path>
# Fixed case branches because "exec {fd}>" needs bash 4.1.
probe_open_lock_fd() {
    local fd="$1" path="$2"
    case "$fd" in
        8)
            if ! exec 8>>"$path"; then
                log_msg "ERROR" "cannot open lock file, path: ${path}, hint: run as the deploy user"
                return 1
            fi
            ;;
        9)
            if ! exec 9>>"$path"; then
                log_msg "ERROR" "cannot open lock file, path: ${path}, hint: run as the deploy user"
                return 1
            fi
            ;;
        *)
            log_msg "ERROR" "unsupported lock fd, fd: ${fd}"
            return 1
            ;;
    esac
}

# probe_ensure_lock_holder_hint <lock_path>
# Best-effort clue for operators when ensure-lock acquisition degrades. Never
# fails the caller: scanning /proc can be expensive or restricted.
probe_ensure_lock_holder_hint() {
    local lock_path="$1"
    local hint=""

    hint="$(ls -l /proc/*/fd 2>/dev/null | grep -- "$lock_path" | head -n 3 | tr '\n' ';' || true)"
    if [ -n "$hint" ]; then
        log_msg "WARN" "ensure lock holders, path: ${lock_path}, clue: ${hint}"
    else
        log_msg "WARN" "ensure lock holders unknown, path: ${lock_path}, hint: check fuser or lsof"
    fi
    return 0
}

# probe_acquire_flock_lock <lock_path> <fd> <timeout> <nonblock>
probe_acquire_flock_lock() {
    local lock_path="$1" fd="$2" timeout="$3" nonblock="$4"

    probe_open_lock_fd "$fd" "$lock_path" || return 1

    if [ "$nonblock" = "1" ]; then
        flock -x -n "$fd" 2>/dev/null && return 0
        return 1
    fi
    flock -x -w "$timeout" "$fd" 2>/dev/null && return 0
    return 1
}

# probe_lc_reclaim_stale <lock_dir> <reap_dir> <holder>
# Removes a stale placeholder. Only touches the filesystem: the holder pid is
# never signalled, so a recycled pid belonging to an unrelated process is safe.
probe_lc_reclaim_stale() {
    local lock_dir="$1" reap_dir="$2" holder="$3"
    local holder2 reap_ts age

    if mkdir "$reap_dir" 2>/dev/null; then
        probe_lc_now > "${reap_dir}/ts" 2>/dev/null || true
        holder2="$(cat "${lock_dir}/pid" 2>/dev/null || true)"
        if [ "$holder2" = "$holder" ]; then
            rm -rf "$lock_dir" 2>/dev/null || true
            log_msg "WARN" "reclaimed stale lock, lock: ${lock_dir}, holder_pid: ${holder}"
        fi
        rm -rf "$reap_dir" 2>/dev/null || true
        return 0
    fi

    # Another reclaimer holds the reap mutex, or it was orphaned by a SIGKILL.
    reap_ts="$(cat "${reap_dir}/ts" 2>/dev/null || true)"
    case "$reap_ts" in
        ''|*[!0-9]*)
            rm -rf "$reap_dir" 2>/dev/null || true
            return 0
            ;;
    esac
    age=$(( $(probe_lc_now) - reap_ts ))
    if [ "$age" -gt "$PROBE_LC_STALE_FLOOR" ]; then
        rm -rf "$reap_dir" 2>/dev/null || true
        log_msg "WARN" "reclaimed orphaned reap mutex, path: ${reap_dir}"
    fi
    return 0
}

# probe_acquire_mkdir_lock <lock_path> <timeout> <nonblock>
# Fallback when flock(1) is absent. Only guarantees script<->script exclusion:
# it cannot interoperate with the Go side's flock(2).
probe_acquire_mkdir_lock() {
    local lock_path="$1" timeout="$2" nonblock="$3"
    local lock_dir="${lock_path}.d" reap_dir="${lock_path}.d.reap"
    local deadline iter max_iter holder lock_ts age stale threshold

    deadline=$(( $(probe_lc_now) + timeout ))
    iter=0
    # Both an iteration cap and a deadline: a backwards clock step could keep the
    # deadline unreachable forever, the cap is what actually prevents a hang.
    max_iter=$(( timeout * 5 + 20 ))
    threshold="$PROBE_LC_STALE_FLOOR"
    if [ "$DBHA_LOCK_WAIT" -gt "$threshold" ]; then
        threshold="$DBHA_LOCK_WAIT"
    fi

    while :; do
        if mkdir "$lock_dir" 2>/dev/null; then
            echo "$$" > "${lock_dir}/pid" 2>/dev/null || true
            probe_lc_now > "${lock_dir}/ts" 2>/dev/null || true
            PROBE_LC_MKDIR_LOCKS+=("$lock_dir")
            return 0
        fi

        holder="$(cat "${lock_dir}/pid" 2>/dev/null || true)"
        lock_ts="$(cat "${lock_dir}/ts" 2>/dev/null || true)"
        stale=0
        # An empty pid file means "mkdir done, pid not yet written": treat the
        # lock as live so we never steal a placeholder that is being set up.
        if [ -n "$holder" ]; then
            if ! is_pid_running "$holder"; then
                stale=1
            fi
            case "$lock_ts" in
                ''|*[!0-9]*) ;;
                *)
                    age=$(( $(probe_lc_now) - lock_ts ))
                    # Time-based fallback: guards against a recycled holder pid
                    # making is_pid_running true forever.
                    if [ "$age" -gt "$threshold" ]; then
                        stale=1
                    fi
                    ;;
            esac
        fi

        if [ "$stale" -eq 1 ]; then
            probe_lc_reclaim_stale "$lock_dir" "$reap_dir" "$holder"
        fi

        # Single backoff point: every branch above falls through to here, so no
        # path can spin without sleeping.
        iter=$(( iter + 1 ))
        if [ "$nonblock" = "1" ]; then
            return 1
        fi
        if [ "$iter" -ge "$max_iter" ]; then
            return 1
        fi
        if [ "$(probe_lc_now)" -ge "$deadline" ]; then
            return 1
        fi
        # Must really wait: busybox sleep rejects fractions, and "|| true" here
        # would silently turn this loop into a busy spin.
        sleep 0.2 || sleep 1
    done
}

# probe_acquire_lock <lock_path> <fd> <timeout> [nonblock]
probe_acquire_lock() {
    local lock_path="$1" fd="$2" timeout="$3" nonblock="${4:-0}"
    local lock_dir

    if [ -L "$lock_path" ]; then
        log_msg "ERROR" "lock path is symlink, path: ${lock_path}"
        return 1
    fi
    lock_dir="$(dirname "$lock_path")"
    if ! mkdir -p -m 755 "$lock_dir" 2>/dev/null; then
        log_msg "ERROR" "cannot create lock dir, path: ${lock_dir}, hint: run as the deploy user"
        return 1
    fi

    if [ "${DBHA_LOCK_FORCE_MKDIR:-0}" != "1" ] && command -v flock >/dev/null 2>&1; then
        if [ -z "$PROBE_LC_LOCK_IMPL" ]; then
            PROBE_LC_LOCK_IMPL="flock"
            probe_lc_info "lock impl: flock"
        fi
        if probe_acquire_flock_lock "$lock_path" "$fd" "$timeout" "$nonblock"; then
            return 0
        fi
        return 1
    fi

    if [ -z "$PROBE_LC_LOCK_IMPL" ]; then
        PROBE_LC_LOCK_IMPL="mkdir"
        log_msg "WARN" "lock impl: mkdir, note: no mutual exclusion against the Go ensure flock"
    fi
    probe_acquire_mkdir_lock "$lock_path" "$timeout" "$nonblock"
}

# probe_release_locks
# Registered via trap. Preserves $? so that exit code 1 - the only signal
# callers get for failure - is never rewritten by cleanup.
probe_release_locks() {
    local rc=$?
    local d

    if [ "$PROBE_LC_LOCKS_RELEASED" = "1" ]; then
        return $rc
    fi
    PROBE_LC_LOCKS_RELEASED=1

    if [ "${#PROBE_LC_MKDIR_LOCKS[@]}" -gt 0 ]; then
        for d in "${PROBE_LC_MKDIR_LOCKS[@]}"; do
            [ -n "$d" ] || continue
            rm -rf "$d" 2>/dev/null || true
        done
    fi
    return $rc
}

# probe_install_lock_traps
# INT/TERM must exit explicitly, otherwise the script would resume after the
# handler. The released flag keeps the EXIT trap from cleaning up twice.
probe_install_lock_traps() {
    trap 'probe_release_locks' EXIT
    trap 'probe_release_locks; exit 130' INT
    trap 'probe_release_locks; exit 143' TERM
}

# probe_run_without_lock_fds <cmd...>
# Shell lock fds have no FD_CLOEXEC and would be inherited by the daemonised
# guard/worker, pinning the lock forever. Also clears the recursion marker so
# long-lived children do not carry a stale "lock held" flag.
probe_run_without_lock_fds() {
    DBHA_PROBE_ACTION_LOCK_HELD= "$@" 8>&- 9>&-
}

# probe_run_binary <timeout_sec> <cmd...>
probe_run_binary() {
    local tmo="$1"
    shift
    if [ -n "$PROBE_LC_TIMEOUT_BIN" ]; then
        DBHA_PROBE_ACTION_LOCK_HELD= "$PROBE_LC_TIMEOUT_BIN" "$tmo" "$@" 8>&- 9>&-
    else
        DBHA_PROBE_ACTION_LOCK_HELD= "$@" 8>&- 9>&-
    fi
}

# probe_guard_nested_call <lock_path>
# A wrapper that already holds the action lock and then calls start/stop would
# deadlock against itself until the timeout. Refuse instead of re-entering,
# because silent re-entry would break the exclusion guarantee.
probe_guard_nested_call() {
    local lock_path="$1"
    if [ "${DBHA_PROBE_ACTION_LOCK_HELD:-}" = "$lock_path" ]; then
        log_msg "ERROR" "nested invocation detected, lock: ${lock_path}, hint: nested calls are unsupported"
        return 1
    fi
    return 0
}

# --- Process classification ---

# probe_cmdline_kind_from_args <cmdline>
# Pure function (unit-testable). Order matches Go ClassifyProbeCmdline, but the
# worker rule is a WHITELIST rather than Go's fallthrough.
#
# Go treats anything that is not ensure/ensure-keepalive as a worker, so
# "dbha-probe health" and "dbha-probe gen-config" classify as workers there.
# This library is the only place that actually sends TERM/KILL, and DBM runs
# gen-config immediately before start-probe.sh, so a fallthrough rule would let
# a concurrent stop kill a config generation holding probe.yaml.lock.
# Keep this stricter than Go on purpose.
probe_cmdline_kind_from_args() {
    local cmdline="$1"
    local tok idx expect_value
    local -a toks=()

    # read -a splits on IFS without glob-expanding tokens like "*".
    IFS=' ' read -r -a toks <<< "$cmdline"
    if [ "${#toks[@]}" -eq 0 ]; then
        echo "unknown"
        return 0
    fi

    # Management entrypoints. Exact word match so that a path such as
    # -c /data/ensure/etc/probe.yaml is not mistaken for the ensure subcommand.
    for tok in "${toks[@]}"; do
        case "$tok" in
            ensure|ensure-keepalive)
                echo "unknown"
                return 0
                ;;
        esac
    done

    # Substring match, aligned with Go's strings.Contains for this flag.
    case "$cmdline" in
        *--ping-http-addr*)
            echo "keepalive"
            return 0
            ;;
    esac

    for tok in "${toks[@]}"; do
        if [ "$tok" = "daemon-start" ]; then
            echo "guard"
            return 0
        fi
    done

    # Worker whitelist: argv[0] plus config flags only. Any other token (a known
    # subcommand today, or one added later) yields unknown and is left alone.
    idx=0
    expect_value=0
    for tok in "${toks[@]}"; do
        idx=$(( idx + 1 ))
        if [ "$idx" -eq 1 ]; then
            continue
        fi
        if [ "$expect_value" -eq 1 ]; then
            expect_value=0
            continue
        fi
        case "$tok" in
            -c|--config)   expect_value=1 ;;
            --config=*)    ;;
            *)
                echo "unknown"
                return 0
                ;;
        esac
    done
    echo "worker"
}

# probe_cmdline_kind <pid>
# Reads /proc/<pid>/cmdline (NUL separated). Avoids ps so that stop-probe.sh
# keeps its current dependency set.
probe_cmdline_kind() {
    local pid="$1" raw
    raw="$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)"
    if [ -z "$raw" ]; then
        echo "unknown"
        return 0
    fi
    probe_cmdline_kind_from_args "$raw"
}

# probe_get_pids <kinds> <expected_exe>
# kinds is a comma separated list, e.g. "guard,worker" or "guard".
# Guards are printed before workers: TERM on a guard takes its worker down via
# guardStopChild, whereas hitting the worker first lets the guard restart it.
probe_get_pids() {
    local kinds="$1" expected_exe="$2"
    local pid kind
    local -a guards=() workers=() others=()

    # Process substitution, not "pgrep | while": a pipeline subshell would
    # discard the arrays.
    while IFS= read -r pid; do
        [ -n "$pid" ] || continue
        validate_pid_target "$pid" "dbha-probe" "$expected_exe" || continue
        kind="$(probe_cmdline_kind "$pid")"
        case ",${kinds}," in
            *",${kind},"*) ;;
            *) continue ;;
        esac
        case "$kind" in
            guard)  guards+=("$pid") ;;
            worker) workers+=("$pid") ;;
            *)      others+=("$pid") ;;
        esac
    done < <(pgrep -x dbha-probe 2>/dev/null || true)

    if [ "${#guards[@]}" -gt 0 ]; then
        printf '%s\n' "${guards[@]}"
    fi
    if [ "${#workers[@]}" -gt 0 ]; then
        printf '%s\n' "${workers[@]}"
    fi
    if [ "${#others[@]}" -gt 0 ]; then
        printf '%s\n' "${others[@]}"
    fi
    return 0
}

# probe_keepalive_pid_matches_addr <pid> <addr>
# Single source of truth for keepalive addr matching, reading /proc so that the
# start and stop scripts cannot disagree (ps -o args= may truncate long argv).
probe_keepalive_pid_matches_addr() {
    local pid="$1" addr="$2" raw
    raw="$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)"
    [ -n "$raw" ] || return 1
    case "$raw" in
        *--ping-http-addr*) ;;
        *) return 1 ;;
    esac
    [ -n "$addr" ] || return 0
    case "$raw" in
        *"--ping-http-addr ${addr}"*|*"--ping-http-addr=${addr}"*) return 0 ;;
    esac
    return 1
}

# probe_keepalive_pids <expected_exe> [addr]
# Do not use `pgrep -x dbha-keepalive`. On Linux the keepalive process writes
# "dbha-keepalive\n" to /proc/self/comm (trailing newline is stored in the name),
# so pgrep exact-match never sees it. Scan /proc comm files instead, then apply
# the same validate_pid_target + addr checks. Also covers the rename window
# where comm is still dbha-probe, and the 15-char truncation of dbha-v2-keepalive.
probe_keepalive_pids() {
    local expected_exe="$1" addr="${2:-}"
    local pid comm seen=" " pid_dir

    for pid_dir in /proc/[0-9]*; do
        pid="${pid_dir#/proc/}"
        comm="$(tr -d '\r\n' < "${pid_dir}/comm" 2>/dev/null || true)"
        case "$comm" in
            dbha-keepalive|dbha-probe|dbha-v2-keepalive|dbha-v2-keepali) ;;
            *) continue ;;
        esac
        case "$seen" in
            *" ${pid} "*) continue ;;
        esac
        validate_pid_target "$pid" "*" "$expected_exe" || continue
        probe_keepalive_pid_matches_addr "$pid" "$addr" || continue
        echo "$pid"
        seen="${seen}${pid} "
    done
    return 0
}

# probe_signal_pid_safe <pid> <sig> <expected_name> <expected_exe> [expected_starttime]
# Parallel to guard-utils.sh signal_pid_safe, which is deliberately left
# untouched because start-server.sh and stop-server.sh call it with 4 args.
# Passing expected_starttime also covers the collect-to-signal reuse window.
probe_signal_pid_safe() {
    local pid="$1" sig="$2" expected_name="$3" expected_exe="$4"
    local expected_starttime="${5:-}"
    local now_starttime

    if ! validate_pid_target "$pid" "$expected_name" "$expected_exe"; then
        log_msg "WARN" "skip signal ${sig}, pid: ${pid}, reason: target validation failed"
        return 1
    fi
    if [ -n "$expected_starttime" ]; then
        now_starttime="$(get_pid_starttime "$pid" 2>/dev/null || true)"
        if [ "$now_starttime" != "$expected_starttime" ]; then
            log_msg "WARN" "skip signal ${sig}, pid: ${pid}, reason: starttime mismatch"
            return 1
        fi
    fi

    kill "-${sig}" "$pid" >/dev/null 2>&1 || true
    log_msg "INFO" "signal ${sig} sent, pid: ${pid}"
    return 0
}

# probe_exe_deleted_matches <pid> <expected_name> <expected_exe>
# Criteria 1-6 for a deleted-exe orphan of this install. The path comparison uses
# the raw /proc/<pid>/exe symlink (no -f): that is the only form that stays
# stable both when the install dir is gone and after it has been recreated.
probe_exe_deleted_matches() {
    local pid="$1" expected_name="$2" expected_exe="$3"
    local comm raw stripped

    [ -n "$expected_exe" ] || return 1
    is_pid_running "$pid" || return 1

    comm="$(tr -d '\r\n' < "/proc/${pid}/comm" 2>/dev/null || true)"
    if [[ "$comm" != dbha-* ]]; then
        return 1
    fi
    if [ "$expected_name" != "*" ] && [ "$comm" != "$expected_name" ]; then
        return 1
    fi

    raw="$(readlink "/proc/${pid}/exe" 2>/dev/null || true)"
    [ -n "$raw" ] || return 1
    case "$raw" in
        *" (deleted)") ;;
        *) return 1 ;;
    esac
    # Kernel appends " (deleted)" to the recorded path; that string is not a
    # real file. A live binary whose name ends with the same suffix would exist
    # at $raw and must not be treated as an orphan.
    if [ -e "$raw" ]; then
        return 1
    fi
    stripped="${raw% (deleted)}"
    [ "$stripped" = "$expected_exe" ]
}

# probe_orphan_pids <kinds> <expected_exe>
# kinds is a comma-separated list. Only guard, worker and keepalive are accepted;
# unknown (management subcommands) is never selected. Guards are printed first
# so TERM on a guard can take its worker down via guardStopChild.
probe_orphan_pids() {
    local kinds="$1" expected_exe="$2"
    local pid kind tok
    local -a guards=() workers=() keepalives=()

    [ -n "$expected_exe" ] || return 0

    for tok in ${kinds//,/ }; do
        case "$tok" in
            guard|worker|keepalive) ;;
            *)
                log_msg "WARN" "refuse orphan kind, kind: ${tok}"
                return 1
                ;;
        esac
    done

    while IFS= read -r pid; do
        [ -n "$pid" ] || continue
        probe_exe_deleted_matches "$pid" "dbha-probe" "$expected_exe" || continue
        kind="$(probe_cmdline_kind "$pid")"
        case ",${kinds}," in
            *",${kind},"*) ;;
            *) continue ;;
        esac
        case "$kind" in
            guard)     guards+=("$pid") ;;
            worker)    workers+=("$pid") ;;
            keepalive) keepalives+=("$pid") ;;
        esac
    done < <(pgrep -x dbha-probe 2>/dev/null || true)

    if [ "${#guards[@]}" -gt 0 ]; then
        printf '%s\n' "${guards[@]}"
    fi
    if [ "${#workers[@]}" -gt 0 ]; then
        printf '%s\n' "${workers[@]}"
    fi
    if [ "${#keepalives[@]}" -gt 0 ]; then
        printf '%s\n' "${keepalives[@]}"
    fi
    return 0
}

# probe_keepalive_orphan_pids <expected_exe> [addr]
# Same comm scan as probe_keepalive_pids, then the deleted-exe criteria plus
# address matching. expected_name is "*" because keepalive rewrites comm.
probe_keepalive_orphan_pids() {
    local expected_exe="$1" addr="${2:-}"
    local pid comm seen=" " pid_dir

    [ -n "$expected_exe" ] || return 0

    for pid_dir in /proc/[0-9]*; do
        pid="${pid_dir#/proc/}"
        comm="$(tr -d '\r\n' < "${pid_dir}/comm" 2>/dev/null || true)"
        case "$comm" in
            dbha-keepalive|dbha-probe|dbha-v2-keepalive|dbha-v2-keepali) ;;
            *) continue ;;
        esac
        case "$seen" in
            *" ${pid} "*) continue ;;
        esac
        probe_exe_deleted_matches "$pid" "*" "$expected_exe" || continue
        probe_keepalive_pid_matches_addr "$pid" "$addr" || continue
        echo "$pid"
        seen="${seen}${pid} "
    done
    return 0
}

# probe_signal_orphan_pid <pid> <sig> <expected_name> <expected_exe> [starttime]
# Must not reuse probe_signal_pid_safe / safe_kill_after_term: those require a
# live exe path and would refuse every orphan. Rechecks criteria 1-6 and, when
# given, starttime, so a recycled pid is never signalled.
probe_signal_orphan_pid() {
    local pid="$1" sig="$2" expected_name="$3" expected_exe="$4"
    local expected_starttime="${5:-}"
    local now_starttime

    if ! probe_exe_deleted_matches "$pid" "$expected_name" "$expected_exe"; then
        log_msg "WARN" "skip signal ${sig}, pid: ${pid}, reason: orphan validation failed"
        return 1
    fi
    if [ -n "$expected_starttime" ]; then
        now_starttime="$(get_pid_starttime "$pid" 2>/dev/null || true)"
        if [ "$now_starttime" != "$expected_starttime" ]; then
            log_msg "WARN" "skip signal ${sig}, pid: ${pid}, reason: starttime mismatch"
            return 1
        fi
    fi

    kill "-${sig}" "$pid" >/dev/null 2>&1 || true
    log_msg "INFO" "signal ${sig} sent, pid: ${pid}"
    return 0
}

# probe_reap_orphans <kinds> <expected_exe>
# Garbage-collects deleted-exe orphans of this install. No-op (and silent) when
# none exist. With DBHA_REAP_DELETED_EXE=0 the pids are listed but not signalled.
probe_reap_orphans() {
    local kinds="$1" expected_exe="$2"
    local pids pid i remaining
    local -a term_pids=() term_starttimes=()

    pids="$(probe_orphan_pids "$kinds" "$expected_exe" || true)"
    [ -n "$pids" ] || return 0

    if [ "${DBHA_REAP_DELETED_EXE:-1}" != "1" ]; then
        probe_lc_warn "deleted-exe orphans present, reap disabled, pids: $(echo "$pids" | tr '\n' ' ')"
        return 0
    fi

    log_msg "WARN" "reaping deleted-exe orphans, kinds: ${kinds}, pids: $(echo "$pids" | tr '\n' ' ')"
    while IFS= read -r pid; do
        [ -n "$pid" ] || continue
        local st
        st="$(get_pid_starttime "$pid" 2>/dev/null || echo "")"
        term_pids+=("$pid")
        term_starttimes+=("$st")
        probe_signal_orphan_pid "$pid" "TERM" "dbha-probe" "$expected_exe" "$st" || true
    done <<< "$pids"

    sleep 1
    remaining="$(probe_orphan_pids "$kinds" "$expected_exe" || true)"
    if [ "${#term_pids[@]}" -gt 0 ]; then
        for i in "${!term_pids[@]}"; do
            pid="${term_pids[$i]}"
            case $'\n'"${remaining}"$'\n' in
                *$'\n'"${pid}"$'\n'*) ;;
                *) continue ;;
            esac
            probe_signal_orphan_pid "$pid" "KILL" "dbha-probe" "$expected_exe" \
                "${term_starttimes[$i]}" || true
        done
    fi
    remaining="$(probe_orphan_pids "$kinds" "$expected_exe" || true)"
    [ -z "$remaining" ]
}

# probe_reap_keepalive_orphans <expected_exe> <addr>
probe_reap_keepalive_orphans() {
    local expected_exe="$1" addr="${2:-}"
    local pids pid i remaining
    local -a term_pids=() term_starttimes=()

    pids="$(probe_keepalive_orphan_pids "$expected_exe" "$addr" || true)"
    [ -n "$pids" ] || return 0

    if [ "${DBHA_REAP_DELETED_EXE:-1}" != "1" ]; then
        probe_lc_warn "deleted-exe keepalive orphans present, reap disabled, pids: $(echo "$pids" | tr '\n' ' ')"
        return 0
    fi

    log_msg "WARN" "reaping deleted-exe keepalive orphans, addr: ${addr}, pids: $(echo "$pids" | tr '\n' ' ')"
    while IFS= read -r pid; do
        [ -n "$pid" ] || continue
        local st
        st="$(get_pid_starttime "$pid" 2>/dev/null || echo "")"
        term_pids+=("$pid")
        term_starttimes+=("$st")
        probe_signal_orphan_pid "$pid" "TERM" "*" "$expected_exe" "$st" || true
    done <<< "$pids"

    sleep 1
    remaining="$(probe_keepalive_orphan_pids "$expected_exe" "$addr" || true)"
    if [ "${#term_pids[@]}" -gt 0 ]; then
        for i in "${!term_pids[@]}"; do
            pid="${term_pids[$i]}"
            case $'\n'"${remaining}"$'\n' in
                *$'\n'"${pid}"$'\n'*) ;;
                *) continue ;;
            esac
            probe_signal_orphan_pid "$pid" "KILL" "*" "$expected_exe" \
                "${term_starttimes[$i]}" || true
        done
    fi
    remaining="$(probe_keepalive_orphan_pids "$expected_exe" "$addr" || true)"
    [ -z "$remaining" ]
}

# --- Intent fence ---

# probe_now_ns
# date +%s%N degrades to second precision on implementations without %N.
probe_now_ns() {
    local ns
    ns="$(date +%s%N 2>/dev/null || true)"
    case "$ns" in
        ''|*[!0-9]*)
            log_msg "WARN" "nanosecond clock unavailable, intent precision reduced to seconds"
            echo "$(date +%s)000000000"
            ;;
        *) echo "$ns" ;;
    esac
}

# probe_resolve_intent_ts <injected>
# Priority: --intent-ts / DBHA_INTENT_TS, then the script start time.
# NOTE the semantics: without injection the fence compares SCRIPT START times,
# which only approximates "who was requested later".
probe_resolve_intent_ts() {
    local injected="${1:-}"
    if [ -z "$injected" ]; then
        injected="${DBHA_INTENT_TS:-}"
    fi
    case "$injected" in
        '') probe_now_ns; return 0 ;;
        *[!0-9]*)
            log_msg "WARN" "invalid intent ts injection, falling back to script start time"
            probe_now_ns
            return 0
            ;;
    esac
    if [ "$injected" = "0" ]; then
        log_msg "WARN" "invalid intent ts injection, falling back to script start time"
        probe_now_ns
        return 0
    fi
    echo "$injected"
}

# probe_read_intent <file>
# Prints "<ts> <action> [addr]" or nothing. Tolerates missing, empty, truncated
# and corrupted files, and ignores timestamps from the future (clock step back
# or a bad injection) so the fence degrades to plain mutual exclusion.
probe_read_intent() {
    local file="$1"
    local line ts action addr now
    local -a f=()

    [ -f "$file" ] || return 1
    IFS= read -r line < "$file" 2>/dev/null || true
    [ -n "$line" ] || return 1

    IFS=' ' read -r -a f <<< "$line"
    if [ "${#f[@]}" -lt 2 ]; then
        log_msg "WARN" "ignore malformed intent record, path: ${file}"
        return 1
    fi
    ts="${f[0]}"
    action="${f[1]}"
    addr="${f[2]:-}"

    case "$ts" in
        ''|*[!0-9]*)
            log_msg "WARN" "ignore malformed intent record, path: ${file}"
            return 1
            ;;
    esac
    if [ "$action" != "start" ] && [ "$action" != "stop" ]; then
        log_msg "WARN" "ignore malformed intent record, path: ${file}"
        return 1
    fi

    now="$(probe_now_ns)"
    if [ "$ts" -gt $(( now + PROBE_LC_CLOCK_SKEW * 1000000000 )) ]; then
        log_msg "WARN" "ignore intent record from the future, path: ${file}"
        return 1
    fi

    echo "${ts} ${action} ${addr}"
    return 0
}

# probe_write_intent <file> <ts> <action> [addr]
# Monotonic: only overwrites when our ts is newer, otherwise a slow stop(t1)
# finishing after stop(t2) would roll the record back and wrongly let an
# in-between start proceed. Never fails the caller: a successful operation must
# not be reported as failed just because the record could not be persisted.
probe_write_intent() {
    local file="$1" ts="$2" action="$3" addr="${4:-}"
    local existing existing_ts now tmp
    local -a f=()

    now="$(probe_now_ns)"
    if [ "$ts" -gt $(( now + PROBE_LC_CLOCK_SKEW * 1000000000 )) ]; then
        log_msg "WARN" "refuse to write intent from the future, path: ${file}"
        return 0
    fi

    existing="$(probe_read_intent "$file" || true)"
    if [ -n "$existing" ]; then
        IFS=' ' read -r -a f <<< "$existing"
        existing_ts="${f[0]}"
        if [ "$existing_ts" -ge "$ts" ]; then
            return 0
        fi
    fi

    tmp="${file}.tmp.$$"
    if ! printf '%s %s %s\n' "$ts" "$action" "$addr" > "$tmp" 2>/dev/null; then
        log_msg "WARN" "cannot write intent record, path: ${file}"
        rm -f "$tmp" 2>/dev/null || true
        return 0
    fi
    if ! mv -f "$tmp" "$file" 2>/dev/null; then
        log_msg "WARN" "cannot commit intent record, path: ${file}"
        rm -f "$tmp" 2>/dev/null || true
    fi
    return 0
}

# probe_cron_has_marker <marker>
probe_cron_has_marker() {
    local marker="$1"
    read_crontab | grep -q -- "$marker"
}

# probe_target_state_reached <action> <expected_exe> <marker> [addr]
# action=start -> a guard exists (same yardstick as the start success check).
# action=stop  -> no guard/worker AND no crontab marker. The marker matters:
#   without it, "process died right after start but the cron guard is still
#   there" would look stopped while cron revives it within a minute.
# For keepalive the process side is addr scoped.
probe_target_state_reached() {
    local action="$1" expected_exe="$2" marker="$3" addr="${4:-}"
    local pids

    if [ -n "$addr" ]; then
        pids="$(probe_keepalive_pids "$expected_exe" "$addr" || true)"
        if [ "$action" = "start" ]; then
            [ -n "$pids" ] && return 0
            return 1
        fi
        if [ -z "$pids" ] && ! probe_cron_has_marker "$marker"; then
            if [ "${DBHA_REAP_DELETED_EXE:-1}" = "1" ]; then
                pids="$(probe_keepalive_orphan_pids "$expected_exe" "$addr" || true)"
                [ -z "$pids" ] || return 1
            fi
            return 0
        fi
        return 1
    fi

    if [ "$action" = "start" ]; then
        pids="$(probe_get_pids guard "$expected_exe" || true)"
        [ -n "$pids" ] && return 0
        return 1
    fi

    pids="$(probe_get_pids "guard,worker" "$expected_exe" || true)"
    if [ -z "$pids" ] && ! probe_cron_has_marker "$marker"; then
        if [ "${DBHA_REAP_DELETED_EXE:-1}" = "1" ]; then
            pids="$(probe_orphan_pids "guard,worker" "$expected_exe" || true)"
            [ -z "$pids" ] || return 1
        fi
        return 0
    fi
    return 1
}

# probe_wait_target_state <action> <expected_exe> <marker> <addr> <timeout>
# Polls probe_target_state_reached. timeout<=0 checks once. Deadline and
# iteration cap both apply so a backwards clock cannot hang the caller.
probe_wait_target_state() {
    local action="$1" expected_exe="$2" marker="$3" addr="${4:-}" timeout="${5:-0}"
    local deadline iter max_iter

    if [ "$timeout" -le 0 ]; then
        probe_target_state_reached "$action" "$expected_exe" "$marker" "$addr"
        return $?
    fi

    deadline=$(( $(probe_lc_now) + timeout ))
    iter=0
    max_iter=$(( timeout * 5 + 20 ))
    while :; do
        if probe_target_state_reached "$action" "$expected_exe" "$marker" "$addr"; then
            return 0
        fi
        iter=$(( iter + 1 ))
        if [ "$iter" -ge "$max_iter" ]; then
            return 1
        fi
        if [ "$(probe_lc_now)" -ge "$deadline" ]; then
            return 1
        fi
        sleep 0.2 || sleep 1
    done
}

# probe_fence_decide <intent_file> <my_ts> <my_action> <expected_exe> <marker> [addr]
# Sets PROBE_LC_FENCE_ACTION to continue|yield_ok|yield_conflict,
# PROBE_LC_FENCE_CRON to present|absent|keep, and PROBE_LC_FENCE_LATEST_ACTION
# to the later record's action (empty when not superseded).
#
# Decision is by RESULT, not by action: if the goal is already met the caller
# exits 0 silently even when a conflicting action superseded it.
# Callers treat yield_conflict asymmetrically: stop intercepts with exit 1,
# start verifies the latest intent state and then exits 0 or 1.
#
# The cron direction, however, follows the LATEST INTENT: yielding to a
# conflicting action must never touch crontab, otherwise a start that yields to
# a later stop could re-register the guard line and let cron keep a probe alive
# that was last asked to stop - breaking "later initiator wins".
probe_fence_decide() {
    local intent_file="$1" my_ts="$2" my_action="$3" expected_exe="$4" marker="$5" addr="${6:-}"
    local record rec_ts rec_action rec_addr
    local -a f=()

    PROBE_LC_FENCE_ACTION="continue"
    PROBE_LC_FENCE_CRON="keep"
    PROBE_LC_FENCE_LATEST_ACTION=""

    if [ "${DBHA_INTENT_FENCE:-1}" != "1" ]; then
        return 0
    fi

    record="$(probe_read_intent "$intent_file" || true)"
    [ -n "$record" ] || return 0

    IFS=' ' read -r -a f <<< "$record"
    rec_ts="${f[0]}"
    rec_action="${f[1]}"
    rec_addr="${f[2]:-}"

    # Not superseded.
    if [ "$rec_ts" -le "$my_ts" ]; then
        return 0
    fi
    # keepalive: operations on a different addr are unrelated, not conflicting.
    if [ -n "$addr" ] && [ -n "$rec_addr" ] && [ "$rec_addr" != "$addr" ]; then
        return 0
    fi

    PROBE_LC_FENCE_LATEST_ACTION="$rec_action"

    if probe_target_state_reached "$my_action" "$expected_exe" "$marker" "$addr"; then
        PROBE_LC_FENCE_ACTION="yield_ok"
        if [ "$rec_action" = "$my_action" ]; then
            # Same direction: safe to reconcile towards our own goal, and useful
            # when the later run succeeded but was SIGKILLed before reconciling.
            if [ "$my_action" = "start" ]; then
                PROBE_LC_FENCE_CRON="present"
            else
                PROBE_LC_FENCE_CRON="absent"
            fi
        else
            PROBE_LC_FENCE_CRON="keep"
        fi
        return 0
    fi

    # Goal not met. A later run of the SAME action did not actually reach the
    # goal either, so our direction still stands: fall through and do the work.
    if [ "$rec_action" = "$my_action" ]; then
        return 0
    fi

    PROBE_LC_FENCE_ACTION="yield_conflict"
    PROBE_LC_FENCE_CRON="keep"
    return 0
}

# --- crontab guard reconciliation ---

# probe_cron_cmd <script_dir> <log_root>
probe_cron_cmd() {
    local script_dir="$1" log_root="$2"
    printf '%s' "cd \"${script_dir}\" && ./bin/dbha-probe ensure -c etc/probe.yaml --from-cron"
    printf '%s' " >>\"${log_root}/dbha-v2-probe-cron.log\" 2>&1"
}

# probe_keepalive_cron_cmd <script_dir> <log_root> <addr>
probe_keepalive_cron_cmd() {
    local script_dir="$1" log_root="$2" addr="$3"
    printf '%s' "cd \"${script_dir}\" && ./bin/dbha-probe ensure-keepalive --ping-http-addr \"${addr}\""
    printf '%s' " --from-cron >>\"${log_root}/dbha-v2-keepalive-cron.log\" 2>&1"
}

# probe_reconcile_cron_guard <present|absent|keep> <marker> [cron_cmd]
# The single crontab mutation entry point for the probe scripts. Always called
# while holding the action lock so concurrent read-modify-write cannot clash.
#
# present delegates to register_cron_guard, whose existing behaviour is to strip
# same-marker lines and append: the result is idempotent in CONTENT (and repairs
# drifted guard lines), not a skip. absent delegates to remove_cron_guard.
probe_reconcile_cron_guard() {
    local state="$1" marker="$2" cron_cmd="${3:-}"

    case "$state" in
        keep)
            return 0
            ;;
        present)
            if [ -z "$cron_cmd" ]; then
                log_msg "WARN" "skip cron reconcile, marker: ${marker}, reason: empty cron command"
                return 0
            fi
            register_cron_guard "$cron_cmd" "$marker"
            ;;
        absent)
            remove_cron_guard "$marker"
            ;;
        *)
            log_msg "WARN" "unknown cron reconcile state, state: ${state}"
            return 0
            ;;
    esac
    return 0
}

# probe_state_snapshot <expected_exe> <intent_file> <my_ts>
# Printed before a non-zero exit. The DBM wrappers run under "set -e", so once a
# script exits non-zero the following health / ps diagnostics never run and this
# is the only on-host evidence an operator gets.
probe_state_snapshot() {
    local expected_exe="$1" intent_file="$2" my_ts="$3"
    local procs intent

    procs="$(pgrep -x dbha-probe 2>/dev/null | tr '\n' ' ' || true)"
    intent="$(probe_read_intent "$intent_file" 2>/dev/null || true)"
    log_msg "INFO" "state snapshot, intent_ts: ${my_ts}, recorded_intent: ${intent:-none}"
    log_msg "INFO" "state snapshot, dbha_probe_pids: ${procs:-none}, expected_exe: ${expected_exe}"
}
