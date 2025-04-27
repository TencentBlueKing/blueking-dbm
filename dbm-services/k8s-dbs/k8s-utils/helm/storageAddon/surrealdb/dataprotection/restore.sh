#!/bin/bash

set -exo pipefail

cat /etc/datasafed/datasafed.conf
toolConfig=/etc/datasafed/datasafed.conf

function getToolConfigValue() {
    local var=$1
    cat $toolConfig | grep "$var" | awk '{print $NF}'
}

access_key_id=$(getToolConfigValue access_key_id)
secret_access_key=$(getToolConfigValue secret_access_key)
endpoint=$(getToolConfigValue endpoint)
bucket=$(getToolConfigValue root)

# FIXME: hardcoded port
/br restore full --pd "$DP_DB_HOST:2379" --storage "s3://$bucket$DP_BACKUP_BASE_PATH?access-key=$access_key_id&secret-access-key=$secret_access_key" --s3.endpoint "$endpoint"
