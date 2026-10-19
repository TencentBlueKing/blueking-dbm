# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import shlex
from typing import List, Optional, Sequence

# fast_execute_script接口固定参数
# 这里独立出来，遇到过全局变量被其他db修改，导致用户错乱的问题
redis_fast_execute_script_common_kwargs = {
    "timeout": 10800,
    "account_alias": "root",
    "is_param_sensitive": 0,
}

redis_actuator_template = """
find /home/mysql/install/dbactuator-*/ -mtime +30  -type d -name "dbactuator-*"  |xargs rm -rf
mkdir -p {{data_dir}}/install/dbactuator-{{uid}}/logs
chmod +x {{data_dir}}/install/dbactuator_redis
cd {{data_dir}}/install/dbactuator-{{uid}}
{{data_dir}}/install/dbactuator_redis --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} \
--version_id {{version_id}} --payload {{payload}} --atom-job-list {{action}}
"""

# Linux MAX_ARG_STRLEN is 131072: a single --payload argv cannot exceed that.
# Stay well below so uid/root_id/other args still fit. version_update always uses
# the file path because it now ships port_conf_configs and has already blown ARG_MAX.
REDIS_PAYLOAD_ARGV_SOFT_LIMIT = 32 * 1024


def redis_actuator_should_use_payload_file(action: str, payload: str) -> bool:
    """Whether JOB should write payload to a file and call dbactuator -f."""
    if "version_update" in (action or ""):
        return True
    return len(payload or "") >= REDIS_PAYLOAD_ARGV_SOFT_LIMIT


def select_redis_actuator_template(use_payload_file: bool) -> str:
    if use_payload_file:
        return redis_actuator_payload_file_template
    return redis_actuator_template


# Payload stays in the JOB script (already proven to fit) but is written to a file
# before execve, so dbactuator argv stays short. --payload_file must be raw JSON:
# dbactuator_redis re-base64-encodes the file contents.
redis_actuator_payload_file_template = """
find /home/mysql/install/dbactuator-*/ -mtime +30  -type d -name "dbactuator-*"  |xargs rm -rf
mkdir -p {{data_dir}}/install/dbactuator-{{uid}}/logs
chmod +x {{data_dir}}/install/dbactuator_redis
cd {{data_dir}}/install/dbactuator-{{uid}}
payload_b64=payload_{{node_id}}.b64
payload_json=payload_{{node_id}}.json
cat > "$payload_b64" <<'B64EOF'
{{payload}}
B64EOF
base64 -d "$payload_b64" > "$payload_json" 2>/dev/null || base64 --decode "$payload_b64" > "$payload_json"
if [ ! -s "$payload_json" ];then
    echo "decode payload_file $payload_json failed"
    exit 1
fi
{{data_dir}}/install/dbactuator_redis --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} \
--version_id {{version_id}} --payload_file="$payload_json" --atom-job-list {{action}}
"""


redis_data_structure_payload_template = """
{{payload}}
"""

redis_data_structure_actuator_template = """
find /home/mysql/install/dbactuator-*/ -mtime +40  -type d -name "dbactuator-*"  |xargs rm -rf
mkdir -p {{data_dir}}/install/dbactuator-{{uid}}/logs
chmod +x {{data_dir}}/install/dbactuator_redis
cd {{data_dir}}/install/dbactuator-{{uid}}
{{data_dir}}/install/dbactuator_redis --uid {{uid}} --root_id {{root_id}} --node_id {{node_id}} \
--version_id {{version_id}} --payload_file={{data_dir}}/install/{{file_name}} --atom-job-list {{action}}
"""


def make_script_common_kwargs(timeout=259200, exec_account="root", is_param_sensitive=0):
    """
    make_script_common_kwargs 生成脚本执行的公共参数
    """
    return {
        "timeout": timeout,
        "account_alias": exec_account,
        "is_param_sensitive": is_param_sensitive,
    }


# redis_actuator_template2 run dbactuator by sudo_account
redis_actuator_template2 = """
#!/bin/sh
# redis actuator script

# safe_remove_dbactuator_dir
function safe_remove_dbactuator_dir() {
    local install_dir=$1
    if [ ! -d $install_dir ];then
        echo "Error install_dir $install_dir not exist"
        return
    fi
    for old_dir in `find $install_dir -maxdepth 1  -type d -name "dbactuator-*"  -mtime +15  -print`
    do
        if [  "${old_dir/dbactuator//}" = "$old_dir" ];then
            echo "Error bad dir $old_dir"
            continue
        fi
        if [ -d $old_dir ];then
            echo "Removing old dbactuator dir $old_dir"
            rm -rf $old_dir || {echo Error Removing old dbactuator dir $old_dir}
        fi
    done
}

# safe_cpfile function.
function safe_cpfile() {
    local src_file=$1
    local dst_file=$2
    local lock_file=$3
    if [ ! -f "$src_file" ];then
         echo "Source file $src_file does not exist. Exiting."
         exit 1
    fi
    (
       flock -w 30 200 || { echo "Another process is holding the lock. Exiting."; exit 1; }
       if [[ ! -f "$dst_file" ]];then
          echo "Copying $src_file to $dst_file"
          cp $src_file $dst_file
          if [[ $? -ne 0 ]];then
                echo "Error copying $src_file to $dst_file"
                exit 1
          fi
       else
          diff $src_file $dst_file > /dev/null
          if [[ $? -ne 0 ]];then
             echo "Copying $src_file to $dst_file"
             cp $src_file $dst_file
             if [[ $? -ne 0 ]];then
                echo "Error copying $src_file to $dst_file"
                exit 1
             fi
          else
             echo "$src_file and $dst_file are the same. No need to copy."
          fi
       fi
    )  200>"$lock_file"
}

# replace var
sudo_account={{sudo_account}}
file_path={{file_path}}
uid={{uid}}
root_id={{root_id}}
node_id={{node_id}}
version_id={{version_id}}
payload='{{payload}}'
action={{action}}

if [ -z "$file_path" -o "$file_path" == "/" ];then
    echo "Error file_path is empty or /"
    exit 1
fi

exe=dbactuator_redis
install_dir=$file_path/install
workdir=$install_dir/dbactuator-$uid
exe_path=$workdir/$exe
lock_file="$workdir/$exe.cp.lock"
mkdir -p $workdir/logs

# update workdir to avoid find and remove old dbactuator dir
if [ -d "$workdir" ];then
    touch $workdir
fi

safe_remove_dbactuator_dir $install_dir
safe_cpfile $install_dir/$exe $exe_path $lock_file

common_args="--uid $uid --root_id $root_id --node_id $node_id --version_id $version_id"
cmd="./$exe $common_args --payload $payload --atom-job-list $action"

cd $workdir || { echo "Error cd $workdir"; exit 1; }
chmod +x $exe
if [ "$sudo_account" != "root" ];then
   echo "user == $sudo_account"
   chown $sudo_account $workdir -R
   su $sudo_account -c "$cmd"
else
   echo "user == root"
   $cmd
fi
"""


redis_role_check_template = """#!/bin/bash
# Redis role check script - checks if actual Redis roles match expected meta roles

# Do NOT use set -e as we want to continue checking all instances even if some fail
set +e

# Constants
readonly REDIS_CLI_TIMEOUT=5
readonly SCRIPT_VERSION="1.0"

# Global error tracking
declare -a ERRORS=()

# Logging function
log_error() {{
    local msg="$1"
    echo "[ERROR] $msg" >&2
    ERRORS+=("$msg")
}}

log_info() {{
    local msg="$1"
    echo "[INFO] $msg" >&2
}}

# Escape string for JSON output
json_escape() {{
    local str="$1"
    # Escape backslashes, double quotes, and control characters
    printf '%s' "$str" | sed 's/\\\\/\\\\\\\\/g; s/"/\\\\"/g; s/\\t/\\\\t/g; s/\\r/\\\\r/g; s/\\n/\\\\n/g'
}}

# Validate IP address format (basic validation)
validate_ip() {{
    local ip="$1"
    local ip_pattern='^[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+$'
    if [[ ! "$ip" =~ $ip_pattern ]] && [[ "$ip" != "localhost" ]] \\
        && [[ "$ip" != "127.0.0.1" ]]; then
        return 1
    fi
    return 0
}}

# Validate port number
validate_port() {{
    local port="$1"
    if [[ ! "$port" =~ ^[0-9]+$ ]] || [ "$port" -lt 1 ] || [ "$port" -gt 65535 ]; then
        return 1
    fi
    return 0
}}

# Check if REDIS_DATA_DIR environment variable is set
if [ -z "$REDIS_DATA_DIR" ]; then
    log_error "REDIS_DATA_DIR environment variable is not set"
    echo "<ctx>"
    echo '{{"results": [], "error": "REDIS_DATA_DIR environment variable is not set"}}'
    echo "</ctx>"
    exit 1
fi

if [ ! -d "$REDIS_DATA_DIR" ]; then
    log_error "REDIS_DATA_DIR '$REDIS_DATA_DIR' does not exist"
    echo "<ctx>"
    echo '{{"results": [], "error": "REDIS_DATA_DIR does not exist"}}'
    echo "</ctx>"
    exit 1
fi

# Check if redis-cli is available
if ! command -v redis-cli &> /dev/null; then
    log_error "redis-cli command not found"
    echo "<ctx>"
    echo '{{"results": [], "error": "redis-cli command not found"}}'
    echo "</ctx>"
    exit 1
fi

# Function to get password from instance.conf or redis.conf
get_redis_password() {{
    local port="$1"
    local instance_conf="$REDIS_DATA_DIR/redis/$port/instance.conf"  # Historical reason
    local redis_conf="$REDIS_DATA_DIR/redis/$port/redis.conf"
    local password=""

    if [ -z "$port" ]; then
        echo ""
        return
    fi

    # Check instance.conf first, then fall back to redis.conf
    for conf_file in "$instance_conf" "$redis_conf"; do
        if [ -f "$conf_file" ] && [ -r "$conf_file" ]; then
            # Extract requirepass from config file
            # Handle various password formats including quoted strings
            password=$(grep -E "^requirepass\\s+" "$conf_file" 2>/dev/null | \\
            head -1 | awk '{{print $2}}' | tr -d '"' | tr -d "'" | xargs || true)
            if [ -n "$password" ]; then
                echo "$password"
                return
            fi
        fi
    done

    echo ""
}}

# Function to get role from Redis INFO REPLICATION with timeout
# Sets global variables: REDIS_ROLE_RESULT and REDIS_ROLE_DEBUG_OUTPUT
# Returns: 0 on success, 1 on error
get_redis_role() {{
    local ip="$1"
    local port="$2"
    local password="$3"
    local result=""
    local redis_output=""
    local exit_code=0

    # Initialize global output variables
    REDIS_ROLE_RESULT=""
    REDIS_ROLE_DEBUG_OUTPUT=""

    # Validate inputs
    if ! validate_ip "$ip"; then
        REDIS_ROLE_RESULT="invalid_ip"
        REDIS_ROLE_DEBUG_OUTPUT=""
        return 1
    fi

    # Build redis-cli command with timeout
    if [ -n "$password" ]; then
        # Use timeout command if available for additional safety
        if command -v timeout &> /dev/null; then
            redis_output=$(timeout "$REDIS_CLI_TIMEOUT" redis-cli -h "$ip" -p "$port" -a "$password" INFO REPLICATION 2>&1 \\
            | grep -v "Warning: Using a password" || true)
            exit_code=${{PIPESTATUS[0]}}
        else
            redis_output=$(redis-cli -h "$ip" -p "$port" -a "$password" INFO REPLICATION 2>&1 \\
            | grep -v "Warning: Using a password" || true)
            exit_code=${{PIPESTATUS[0]}}
        fi
    else
        if command -v timeout &> /dev/null; then
            redis_output=$(timeout "$REDIS_CLI_TIMEOUT" redis-cli -h "$ip" -p "$port" INFO REPLICATION 2>&1)
            exit_code=$?
        else
            redis_output=$(redis-cli -h "$ip" -p "$port" INFO REPLICATION 2>&1)
            exit_code=$?
        fi
    fi

    # Store debug output
    REDIS_ROLE_DEBUG_OUTPUT="$redis_output"

    # Check for timeout (exit code 124)
    if [ "$exit_code" -eq 124 ]; then
        REDIS_ROLE_RESULT="connection_timeout"
        return 1
    fi

    # Check for connection errors
    if echo "$redis_output" | grep -qiE "(connection refused|could not connect|no route to host|network is unreachable)"; then
        REDIS_ROLE_RESULT="connection_refused"
        return 1
    fi

    # Check for authentication errors
    if echo "$redis_output" | grep -qiE "(NOAUTH|ERR invalid password|WRONGPASS)"; then
        REDIS_ROLE_RESULT="auth_failed"
        return 1
    fi

    # Extract role from output
    result=$(echo "$redis_output" | grep "^role:" | cut -d: -f2 | tr -d '\\r\\n' || true)

    if [ -z "$result" ]; then
        # If we got output but no role, something unexpected happened
        if [ -n "$redis_output" ]; then
            REDIS_ROLE_RESULT="unexpected_response"
        else
            REDIS_ROLE_RESULT="connection_failed"
        fi
        return 1
    fi

    # Set the role result
    REDIS_ROLE_RESULT="$result"
    return 0
}}
# Normalize meta role to match Redis INFO output
normalize_role() {{
    local role="$1"
    case "$role" in
        redis_master) echo "master" ;;
        redis_slave)  echo "slave" ;;
        *)            echo "$role" ;;
    esac
}}

# Instance data: ip port meta_role (one per line, space separated)
# Format: {instances}

# Get password once from the first port's config file (all instances in a cluster share the same password)
FIRST_PORT="{first_port}"
REDIS_PASSWORD=""
if [ -n "$FIRST_PORT" ]; then
    REDIS_PASSWORD=$(get_redis_password "$FIRST_PORT") || REDIS_PASSWORD=""
    if [ -z "$REDIS_PASSWORD" ]; then
        log_info "No password found in config for port $FIRST_PORT, connecting without authentication"
    fi
fi

# Output JSON results
echo "<ctx>"
echo '{{"results": ['

first=1
{instance_checks}

echo ']}}'
echo "</ctx>"
"""


# Helper function to build instance check commands for redis_role_check_template
def build_redis_role_check_script(instances: list) -> str:
    """
    Build the complete role check script with instance checks

    Args:
        instances: List of dicts with ip, port, meta_role

    Returns:
        Complete shell script as string
    """
    instance_checks = []

    # Extract first port for password lookup (all instances share the same password)
    first_port = ""
    for inst in instances:
        port = "".join(c for c in str(inst.get("port", "")) if c.isdigit())
        if port:
            first_port = port
            break

    for inst in instances:
        ip = inst.get("ip", "")
        port = inst.get("port", "")
        meta_role = inst.get("meta_role", "")

        # Sanitize inputs to prevent shell injection
        # Only allow alphanumeric, dots, underscores, and hyphens for ip
        # Only allow numeric for port
        # Only allow alphanumeric and underscores for meta_role
        ip = "".join(c for c in str(ip) if c.isalnum() or c in ".")
        port = "".join(c for c in str(port) if c.isdigit())
        meta_role = "".join(c for c in str(meta_role) if c.isalnum() or c == "_")

        if not ip or not port:
            continue

        # Build check command for each instance with robust error handling
        check_cmd = f"""
# Check instance {ip}:{port}
{{
    ip="{ip}"
    port="{port}"
    meta_role="{meta_role}"

    # Get actual role with error handling
    # Function sets global variables: REDIS_ROLE_RESULT and REDIS_ROLE_DEBUG_OUTPUT
    get_redis_role "$ip" "$port" "$REDIS_PASSWORD"
    role_check_status=$?

    actual_role="$REDIS_ROLE_RESULT"
    debug_output="$REDIS_ROLE_DEBUG_OUTPUT"

    # Normalize the expected role
    normalized_meta_role=""
    normalized_meta_role=$(normalize_role "$meta_role") || normalized_meta_role="$meta_role"

    # Determine if roles match
    match="false"
    error_msg=""

    # Check if the role check failed (non-zero exit status)
    if [ "$role_check_status" -ne 0 ]; then
        match="false"
        error_msg="$actual_role"
        if [ -n "$debug_output" ]; then
            error_msg="$actual_role: $debug_output"
        else
            error_msg="$actual_role: (empty output)"
        fi
        if [ -z "$actual_role" ]; then
            actual_role="unknown"
            if [ -n "$debug_output" ]; then
                error_msg="unknown_error: $debug_output"
            else
                error_msg="unknown_error: (empty output)"
            fi
        fi
    else
        # Role check succeeded, compare roles
        if [ "$actual_role" = "$normalized_meta_role" ]; then
            match="true"
        else
            match="false"
        fi
    fi

    # Output JSON for this instance
    if [ "$first" -eq 1 ]; then
        first=0
    else
        echo ","
    fi

    # Escape any special characters in the output
    escaped_actual_role=$(json_escape "$actual_role")
    escaped_error=$(json_escape "$error_msg")

    if [ -n "$error_msg" ]; then
        echo '    {{'\
'"ip": "'"$ip"'", '\
'"port": '"$port"', '\
'"meta_role": "'"$meta_role"'", '\
'"actual_role": "'"$escaped_actual_role"'", '\
'"match": '"$match"', '\
'"error": "'"$escaped_error"'"}}'
    else
        echo '    {{'\
'"ip": "'"$ip"'", '\
'"port": '"$port"', '\
'"meta_role": "'"$meta_role"'", '\
'"actual_role": "'"$escaped_actual_role"'", '\
'"match": '"$match"'}}'
    fi
}}
"""
        instance_checks.append(check_cmd)

    script = redis_role_check_template.format(
        instances="# Generated instance checks below",
        instance_checks="\n".join(instance_checks),
        first_port=first_port,
    )

    return script


# ==============================================================================
# REDIS_CONF_CHECK: on-host script snippets
#
# Predixy INFO Servers is read via DRS; storage instance state is read on the host
# through redis-cmd.sh. Each checker contributes a self-contained snippet that
# prints tagged blocks:
#   <CONFCHK checker="<name>" port="<port>">{json}</CONFCHK>
# The collect component concatenates all snippets for a host into one script and
# delivers a single job per host.
# ==============================================================================

CONF_CHECK_SCRIPT_HEADER = "#!/bin/bash\nset +e\n"


# Bash helper for the predixy_servers checker. Defined once per script; invoked
# once per predixy port that lives on the host.
_PREDIXY_CONF_READ_FUNC = r"""
__dbm_predixy_conf_servers() {
    local port="$1"
    local conf=""
    # Prefer the running process's actual conf path, fall back to the data dir.
    conf=$(ps aux 2>/dev/null | grep predixy | grep -w "$port" | grep predixy.conf | grep -v grep | head -1 | awk '{print $NF}')
    if [ -z "$conf" ]; then
        conf=$(ls "$REDIS_DATA_DIR/predixy/$port/predixy.conf" 2>/dev/null | head -1)
    fi
    if [ -z "$conf" ] || [ ! -f "$conf" ]; then
        echo "<CONFCHK checker=\"predixy_servers\" port=\"$port\">{\"error\": \"conf_not_found\"}</CONFCHK>"
        return
    fi
    # Servers live inside the pool block (ClusterServerPool -> Servers, StandaloneServerPool -> Masters).
    local servers
    servers=$(awk '/(Servers|Masters)[[:space:]]*\{/{f=1; next} f&&/\}/{f=0} f{print}' "$conf" \
        | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+' | sort -u)
    local json="" first=1 s
    for s in $servers; do
        if [ "$first" -eq 1 ]; then first=0; else json="$json,"; fi
        json="$json\"$s\""
    done
    echo "<CONFCHK checker=\"predixy_servers\" port=\"$port\">{\"servers\": [$json]}</CONFCHK>"
}
"""


def build_predixy_conf_check_snippet(ports: List[int]) -> str:
    """
    Build the predixy_servers checker's on-host snippet for the given ports.

    Reads each predixy's local config file and prints one tagged block per port
    listing the configured backend servers (ip:port). Compared against live
    `INFO Servers` by ``PredixyServersChecker.evaluate`` in the report service.
    """
    calls = "\n".join('__dbm_predixy_conf_servers "{}"'.format(int(p)) for p in ports if str(p).isdigit())
    return _PREDIXY_CONF_READ_FUNC + "\n" + calls + "\n"


REDIS_CMD_SH = "/home/mysql/dbtools/redis-cmd.sh"
STORAGE_CONF_DATA_DIRS = ("/data1", "/data")
STORAGE_CONF_INCLUDE_MAX_DEPTH = 8
STORAGE_CONF_CMD_TIMEOUT = 5

# Bash helpers for the storage_conf checker (bash 3.2 compatible, no python on host).
# BK-Job keeps job logs, so nothing printed here may carry a credential:
#   - redis-cmd.sh echoes "redis-cli -a <password> ..." before running; that line and
#     the redis-cli password warning are dropped before any further processing.
#   - requirepass/masterauth/masteruser/user values are dropped from runtime config
#     by key name regardless of key/value position; blank lines stay because an empty
#     value is a blank line.
#   - failures are reported as fixed tokens, never as captured output.
# Commands are fed to redis-cmd.sh on stdin: it runs `$REDIS $@` unquoted, so a `*`
# passed as an argument is glob-expanded against the working directory. It is run via
# `bash <path>` because its shebang is not on the first line.
_STORAGE_CONF_FUNCS = r"""
__DBM_SCC_REDIS_CMD=__DBM_SCC_REDIS_CMD_VALUE__

__dbm_scc_b64() {
    gzip -c 2>/dev/null | base64 2>/dev/null | tr -d '\n\r'
}

__dbm_scc_canon() {
    local d
    d=$(cd "$(dirname "$1")" 2>/dev/null && pwd -P) || { printf '%s' "$1"; return; }
    printf '%s/%s' "$d" "$(basename "$1")"
}

__dbm_scc_json_path() {
    case "$1" in
        *[!A-Za-z0-9_./-]*) printf 'unsafe_path' ;;
        *) printf '%s' "$1" ;;
    esac
}

__dbm_scc_expand() {
    local f="$1" depth="$2" stack="$3" base="$4" line inc canon re bare
    re='^[[:space:]]*[Ii][Nn][Cc][Ll][Uu][Dd][Ee][[:space:]]+([^[:space:]]+)'
    bare='^[[:space:]]*[Ii][Nn][Cc][Ll][Uu][Dd][Ee][[:space:]]*$'
    while IFS= read -r line || [ -n "$line" ]; do
        if [[ $line =~ $bare ]]; then
            echo "#CONFCHK_ERR include_no_path $f"
        elif [[ $line =~ $re ]]; then
            inc="${BASH_REMATCH[1]}"
            inc="${inc#\"}"
            inc="${inc%\"}"
            case "$inc" in
                *'*'*|*'?'*|*'['*) echo "#CONFCHK_ERR include_glob $inc"; continue ;;
            esac
            case "$inc" in
                /*) ;;
                *) inc="$base/$inc" ;;
            esac
            if [ "$depth" -gt __DBM_SCC_MAX_DEPTH__ ]; then
                echo "#CONFCHK_ERR include_too_deep $inc"
                continue
            fi
            canon=$(__dbm_scc_canon "$inc")
            case "$stack" in
                *":$canon:"*) echo "#CONFCHK_ERR include_cycle $inc"; continue ;;
            esac
            if [ ! -f "$inc" ] || [ ! -r "$inc" ]; then
                echo "#CONFCHK_ERR include_unreadable $inc"
                continue
            fi
            __dbm_scc_expand "$inc" $((depth + 1)) "$stack$canon:" "$base"
        else
            printf '%s\n' "$line"
        fi
    done < "$f"
}

__dbm_scc_strip_disk() {
    awk '{
        l = $0
        sub(/^[ \t#]+/, "", l)
        n = l
        sub(/[ \t].*$/, "", n)
        n = tolower(n)
        if (n == "requirepass" || n == "masterauth" || n == "masteruser" || n == "user" || n == "rename-command") next
        print
    }'
}

__dbm_scc_strip_wrapper() {
    awk '{
        if (index($0, "redis-cli") > 0 && index($0, " -a ") > 0) next
        if (index($0, "Warning: Using a password") == 1) next
        print
    }'
}

__dbm_scc_strip_mem() {
    awk 'BEGIN { skip = 0 }
    {
        if (skip) { skip = 0; next }
        k = tolower($0)
        sub(/\r$/, "", k)
        if (k == "requirepass" || k == "masterauth" || k == "masteruser" || k == "user") { skip = 1; next }
        print
    }'
}

# Sets __DBM_SCC_BODY (wrapper lines removed, trailing newlines kept) and __DBM_SCC_ERR.
__dbm_scc_query() {
    local port="$1" cmd="$2" raw rc first
    __DBM_SCC_BODY=""
    __DBM_SCC_ERR=""
    raw=$(
        if command -v timeout >/dev/null 2>&1; then
            printf '%s\n' "$cmd" | timeout __DBM_SCC_TIMEOUT__ bash "$__DBM_SCC_REDIS_CMD" "$port" 2>&1
        else
            # without timeout(1) the Job script timeout (10800s) is the only bound
            printf '%s\n' "$cmd" | bash "$__DBM_SCC_REDIS_CMD" "$port" 2>&1
        fi
        echo "__DBM_SCC_RC=$?"
    )
    rc="${raw##*__DBM_SCC_RC=}"
    raw="${raw%__DBM_SCC_RC=*}"
    __DBM_SCC_BODY=$(printf '%s' "$raw" | __dbm_scc_strip_wrapper; echo x)
    __DBM_SCC_BODY="${__DBM_SCC_BODY%x}"
    raw=""
    if [ "$rc" = "124" ]; then
        __DBM_SCC_ERR="redis_cmd_timeout"
        return
    fi
    first=$(printf '%s' "$__DBM_SCC_BODY" | head -n 1 | tr -d '\r' | tr '[:upper:]' '[:lower:]')
    case "$first" in
        *"unknown command"*) __DBM_SCC_ERR="unknown_command" ;;
        err*|noauth*|wrongpass*|auth*|"(error)"*|"could not connect"*|*"unkown redis server type"*)
            __DBM_SCC_ERR="redis_cmd_failed" ;;
    esac
    if [ -z "$__DBM_SCC_ERR" ] && [ "$rc" != "0" ]; then
        __DBM_SCC_ERR="redis_cmd_failed"
    fi
    if [ -z "$__DBM_SCC_ERR" ] && [ -z "$(printf '%s' "$__DBM_SCC_BODY" | tr -d '[:space:]')" ]; then
        __DBM_SCC_ERR="redis_cmd_empty"
    fi
}

__dbm_scc_port() {
    local port="$1" d p canon conf="" found="" conf_paths="" disk="" repl="" mem="" mem_cmd=""
    local disk_err="" repl_err="" mem_err=""
    for d in "${REDIS_DATA_DIR:-}" __DBM_SCC_DATA_DIRS__; do
        [ -n "$d" ] || continue
        p="${d%/}/redis/$port/redis.conf"
        [ -f "$p" ] || continue
        canon=$(__dbm_scc_canon "$p")
        case " $found " in
            *" $canon "*) continue ;;
        esac
        found="${found:+$found }$canon"
        conf_paths="${conf_paths:+$conf_paths,}\"$(__dbm_scc_json_path "$p")\""
        [ -n "$conf" ] || conf="$p"
    done

    if [ -z "$conf" ]; then
        disk_err="conf_not_found"
    elif [ ! -r "$conf" ]; then
        disk_err="conf_unreadable"
    else
        disk=$(__dbm_scc_expand "$conf" 1 ":$(__dbm_scc_canon "$conf"):" "$(dirname "$conf")" \
            | __dbm_scc_strip_disk | __dbm_scc_b64)
    fi

    __dbm_scc_query "$port" "info replication"
    if [ -n "$__DBM_SCC_ERR" ]; then
        repl_err="$__DBM_SCC_ERR"
        [ "$repl_err" = "unknown_command" ] && repl_err="redis_cmd_failed"
    else
        repl=$(printf '%s' "$__DBM_SCC_BODY" | __dbm_scc_b64)
    fi

    mem_cmd="confxx"
    __dbm_scc_query "$port" "confxx get *"
    if [ "$__DBM_SCC_ERR" = "unknown_command" ]; then
        mem_cmd="config"
        __dbm_scc_query "$port" "config get *"
    fi
    if [ -n "$__DBM_SCC_ERR" ]; then
        mem_err="$__DBM_SCC_ERR"
        [ "$mem_err" = "unknown_command" ] && mem_err="redis_cmd_failed"
    else
        mem=$(printf '%s' "$__DBM_SCC_BODY" | __dbm_scc_strip_mem | __dbm_scc_b64)
    fi
    __DBM_SCC_BODY=""

    local fmt='<CONFCHK checker="storage_conf" port="%s">{"conf_path":"%s","conf_paths":[%s],'
    fmt="$fmt"'"disk":"%s","repl":"%s","mem":"%s","mem_cmd":"%s",'
    fmt="$fmt"'"disk_err":"%s","repl_err":"%s","mem_err":"%s"}</CONFCHK>\n'
    printf "$fmt" \
        "$port" "$(__dbm_scc_json_path "$conf")" "$conf_paths" "$disk" "$repl" "$mem" "$mem_cmd" \
        "$disk_err" "$repl_err" "$mem_err"
}
"""


def build_storage_conf_check_snippet(
    ports: List[int], redis_cmd: str = REDIS_CMD_SH, data_dirs: Optional[Sequence[str]] = None
) -> str:
    """
    Build the storage_conf checker's on-host snippet for the given storage ports.

    Per port, prints one <CONFCHK checker="storage_conf"> block whose disk (include-expanded
    redis.conf), repl (INFO REPLICATION) and mem (CONFIG GET *) sections are gzip+base64
    encoded raw text; parsing happens in dbm-ui. ``$REDIS_DATA_DIR`` is always probed
    first, then ``data_dirs``. ``redis_cmd`` and ``data_dirs`` exist so tests can point
    the script at a stub wrapper and a temp config tree.
    """
    calls = "\n".join('__dbm_scc_port "{}"'.format(int(p)) for p in ports if str(p).isdigit())
    if not calls:
        return ""
    dirs = data_dirs if data_dirs is not None else STORAGE_CONF_DATA_DIRS
    funcs = (
        _STORAGE_CONF_FUNCS.replace("__DBM_SCC_REDIS_CMD_VALUE__", shlex.quote(redis_cmd))
        .replace("__DBM_SCC_DATA_DIRS__", " ".join(shlex.quote(d) for d in dirs))
        .replace("__DBM_SCC_MAX_DEPTH__", str(STORAGE_CONF_INCLUDE_MAX_DEPTH))
        .replace("__DBM_SCC_TIMEOUT__", str(STORAGE_CONF_CMD_TIMEOUT))
    )
    return funcs + "\n" + calls + "\n"
