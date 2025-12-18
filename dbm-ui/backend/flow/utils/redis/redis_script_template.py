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
get_redis_role() {{
    local ip="$1"
    local port="$2"
    local password="$3"
    local result=""
    local redis_output=""
    local exit_code=0

    # Validate inputs
    if ! validate_ip "$ip"; then
        echo "invalid_ip"
        return
    fi

    if ! validate_port "$port"; then
        echo "invalid_port"
        return
    fi

    # Build redis-cli command with timeout
    local cli_cmd="redis-cli -h $ip -p $port"
    local auth_opts=""
    if [ -n "$password" ]; then
        auth_opts="-a $password --no-auth-warning"
    fi

    if [ -n "$password" ]; then
        # Use timeout command if available for additional safety
        if command -v timeout &> /dev/null; then
            redis_output=$(timeout "$REDIS_CLI_TIMEOUT" $cli_cmd $auth_opts INFO REPLICATION 2>&1) || exit_code=$?
        else
            redis_output=$($cli_cmd $auth_opts INFO REPLICATION 2>&1) || exit_code=$?
        fi
    else
        if command -v timeout &> /dev/null; then
            redis_output=$(timeout "$REDIS_CLI_TIMEOUT" redis-cli -h "$ip" -p "$port" INFO REPLICATION 2>&1) || exit_code=$?
        else
            redis_output=$(redis-cli -h "$ip" -p "$port" INFO REPLICATION 2>&1) || exit_code=$?
        fi
    fi

    # Check for timeout (exit code 124)
    if [ "$exit_code" -eq 124 ]; then
        echo "connection_timeout"
        return
    fi

    # Check for connection errors
    if echo "$redis_output" | grep -qiE "(connection refused|could not connect|no route to host|network is unreachable)"; then
        echo "connection_refused"
        return
    fi

    # Check for authentication errors
    if echo "$redis_output" | grep -qiE "(NOAUTH|ERR invalid password|WRONGPASS)"; then
        echo "auth_failed"
        return
    fi

    # Extract role from output
    result=$(echo "$redis_output" | grep "^role:" | cut -d: -f2 | tr -d '\\r\\n' || true)

    if [ -z "$result" ]; then
        # If we got output but no role, something unexpected happened
        if [ -n "$redis_output" ]; then
            echo "unexpected_response"
        else
            echo "connection_failed"
        fi
        return
    fi

    echo "$result"
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
    actual_role=""
    actual_role=$(get_redis_role "$ip" "$port" "$REDIS_PASSWORD") || actual_role="check_failed"

    # Normalize the expected role
    normalized_meta_role=""
    normalized_meta_role=$(normalize_role "$meta_role") || normalized_meta_role="$meta_role"

    # Determine if roles match
    match="false"
    error_msg=""

    # Check for various error conditions in actual_role
    case "$actual_role" in
        "connection_failed"|"connection_refused"|"connection_timeout"|"auth_failed"|"invalid_ip"|"invalid_port"|"unexpected_response"|"check_failed"|"")
            match="false"
            error_msg="$actual_role"
            if [ -z "$actual_role" ]; then
                actual_role="unknown"
                error_msg="unknown_error"
            fi
            ;;
        *)
            if [ "$actual_role" = "$normalized_meta_role" ]; then
                match="true"
            else
                match="false"
            fi
            ;;
    esac

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
