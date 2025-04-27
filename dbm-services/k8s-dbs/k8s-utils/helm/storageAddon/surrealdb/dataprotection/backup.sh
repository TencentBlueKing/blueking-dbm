#!/bin/bash

set -exo pipefail

cat /etc/datasafed/datasafed.conf
toolConfig=/etc/datasafed/datasafed.conf

# if the script exits with a non-zero exit code, touch a file to indicate that the backup failed,
# the sync progress container will check this file and exit if it exists
function handle_exit() {
  exit_code=$?
  if [ $exit_code -ne 0 ]; then
    echo "failed with exit code $exit_code"
    touch "${DP_BACKUP_INFO_FILE}.exit"
    exit 1
  fi
}
trap handle_exit EXIT

function getToolConfigValue() {
    local var=$1
    cat $toolConfig | grep "$var" | awk '{print $NF}'
}

access_key_id=$(getToolConfigValue access_key_id)
secret_access_key=$(getToolConfigValue secret_access_key)
endpoint=$(getToolConfigValue endpoint)
bucket=$(getToolConfigValue root)

# FIXME: hardcoded port
/br backup full --pd "$DP_DB_HOST:2379" --storage "s3://$bucket$DP_BACKUP_BASE_PATH?access-key=$access_key_id&secret-access-key=$secret_access_key" --s3.endpoint "$endpoint"

# use datasafed to get backup size
# if we do not write into $DP_BACKUP_INFO_FILE, the backup job will stuck
export PATH="$PATH:$DP_DATASAFED_BIN_PATH"
export DATASAFED_BACKEND_BASE_PATH=${DP_BACKUP_BASE_PATH}
TOTAL_SIZE=$(datasafed stat / | grep TotalSize | awk '{print $2}')
echo "{\"totalSize\":\"$TOTAL_SIZE\"}" >"${DP_BACKUP_INFO_FILE}" && sync
