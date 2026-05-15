#!/usr/bin/env bash
# guard-utils.sh - Shared functions for dbha-v2 service guard scripts
# Usage: source "${SCRIPT_DIR}/lib/guard-utils.sh"
#
# Required globals (set by caller before calling any function):
#   LOG_FILE - path to the log file for log_msg / ensure_log_file

# --- Crontab helpers ---

read_crontab() {
    crontab -l 2>/dev/null || true
}

# register_cron_guard <cron_cmd> <marker>
# Registers a cron guard line. The caller constructs the full cron_cmd string
# (including log redirection). The marker is used for idempotency.
register_cron_guard() {
    local cron_cmd="$1"
    local marker="$2"
    local cron_line existing updated

    cron_line="* * * * * ${cron_cmd} # ${marker}"

    existing="$(read_crontab | grep -v "$marker" || true)"
    if [ -n "$existing" ]; then
        updated="${existing}"$'\n'"${cron_line}"
    else
        updated="${cron_line}"
    fi

    printf '%s\n' "$updated" | crontab -
    log_msg "INFO" "cron guard registered, marker: ${marker}"
}

# remove_cron_guard <marker>
# Removes all cron lines matching the given marker by filtering then writing back.
# This function does not perform full crontab deletion.
remove_cron_guard() {
    local marker="$1"
    local existing filtered

    existing="$(read_crontab)"
    filtered="$(printf '%s\n' "$existing" | grep -v "$marker" || true)"

    # After marker removal, either non-empty lines remain or the user crontab
    # becomes empty. Use an explicit branch so empty input is not implicit.
    if printf '%s\n' "$filtered" | grep -q '[^[:space:]]'; then
        printf '%s\n' "$filtered" | crontab -
    else
        printf '\n' | crontab -
    fi
    log_msg "INFO" "cron guard removed, marker: ${marker}"
}

# --- Logging ---

# log_msg <level> <msg>
# Requires caller to set LOG_FILE before calling.
log_msg() {
    local level="$1"
    local msg="$2"
    local ts line
    ts="$(date '+%Y-%m-%d %H:%M:%S')"
    line="[${ts}] [${level}] ${msg}"
    echo "$line"
    echo "$line" >> "$LOG_FILE"
}

# --- Path/log initialization ---

# ensure_log_file <logfile>
# Creates parent directory and log file with secure permissions.
# Uses echo >&2 for symlink error (not log_msg) because log_msg would try
# to write to the potentially-symlinked file.
ensure_log_file() {
    local logfile="$1"
    mkdir -p -m 700 "$(dirname "$logfile")"
    if [ -L "$logfile" ]; then
        echo "[ERROR] log file is symlink, path: ${logfile}" >&2
        exit 1
    fi
    touch "$logfile"
    chmod 600 "$logfile"
}

# --- PID helpers ---

is_pid_running() {
    local pid="$1"
    kill -0 "$pid" 2>/dev/null
}

# validate_pid_target <pid> <expected_name> <expected_exe>
# Verifies pid is alive, comm matches dbha-* prefix and expected_name,
# and exe symlink matches expected_exe.
# Use expected_name="*" to match any dbha-* comm (for keepalive scripts
# that accept both dbha-keepalive and dbha-probe process names).
validate_pid_target() {
    local pid="$1"
    local expected_name="$2"
    local expected_exe="$3"
    local comm exe

    if ! is_pid_running "$pid"; then
        return 1
    fi

    comm="$(tr -d '\r\n' < "/proc/${pid}/comm" 2>/dev/null || true)"
    if [[ "$comm" != dbha-* ]]; then
        return 1
    fi
    if [ "$expected_name" != "*" ] && [ "$comm" != "$expected_name" ]; then
        return 1
    fi

    exe="$(readlink -f "/proc/${pid}/exe" 2>/dev/null || true)"
    if [ -z "$exe" ] || [ "$exe" != "$expected_exe" ]; then
        return 1
    fi

    return 0
}

# get_valid_pids <expected_name> <expected_exe>
# Prints validated PIDs, one per line.
get_valid_pids() {
    local expected_name="$1"
    local expected_exe="$2"
    local pid

    pgrep -x "$expected_name" 2>/dev/null | while IFS= read -r pid; do
        if validate_pid_target "$pid" "$expected_name" "$expected_exe"; then
            echo "$pid"
        fi
    done
}

# signal_pid_safe <pid> <sig> <expected_name> <expected_exe>
# Sends signal only after validating the target PID.
signal_pid_safe() {
    local pid="$1"
    local sig="$2"
    local expected_name="$3"
    local expected_exe="$4"

    if ! validate_pid_target "$pid" "$expected_name" "$expected_exe"; then
        log_msg "WARN" "skip signal ${sig}, pid: ${pid}, reason: target validation failed"
        return 1
    fi

    kill "-${sig}" "$pid" >/dev/null 2>&1 || true
    log_msg "INFO" "signal ${sig} sent, pid: ${pid}"
    return 0
}

# wait_pid_exit <pid> [tries]
# Polls until pid is gone. Default 30 tries at 0.2s intervals.
wait_pid_exit() {
    local pid="$1"
    local tries="${2:-30}"
    local i

    for ((i=0; i<tries; i++)); do
        if ! is_pid_running "$pid"; then
            return 0
        fi
        sleep 0.2
    done
    return 1
}

# --- TOCTOU-safe KILL helpers ---

# get_pid_starttime <pid>
# Prints the kernel starttime (clock ticks since boot) for a PID.
# Returns 1 if /proc/$pid/stat cannot be read.
get_pid_starttime() {
    local pid="$1"
    local stat_content
    stat_content="$(cat "/proc/${pid}/stat" 2>/dev/null)" || return 1
    # Field 22 (starttime) = 20th field after the (comm) field.
    # Handle comm that may contain spaces by stripping up to last ')'.
    local after_comm="${stat_content##*)}"
    echo "$after_comm" | awk '{print $20}'
}

# safe_kill_after_term <pid> <expected_name> <expected_exe> <starttime_before>
# For use after TERM + sleep: verifies PID was not recycled before sending KILL.
# Returns 0 if KILL was sent (or pid already gone), 1 if PID recycled or validation failed.
safe_kill_after_term() {
    local pid="$1"
    local expected_name="$2"
    local expected_exe="$3"
    local starttime_before="$4"

    if ! is_pid_running "$pid"; then
        return 0  # already gone, no need to KILL
    fi

    local starttime_now
    starttime_now="$(get_pid_starttime "$pid")" || true
    if [ "$starttime_before" != "$starttime_now" ]; then
        log_msg "WARN" "PID ${pid} recycled (starttime changed), skip KILL"
        return 1
    fi

    signal_pid_safe "$pid" "KILL" "$expected_name" "$expected_exe"
}
