#!/usr/bin/env bash

# shellcheck disable=SC2034
ut_mode="false"
test || __() {
  # when running in non-unit test mode, set the options "set -ex".
  set -ex;
}

init_env() {
  PATH="$PATH:$DP_DATASAFED_BIN_PATH"
  export PATH
  DATASAFED_BACKEND_BASE_PATH="$DP_BACKUP_BASE_PATH"
  export DATASAFED_BACKEND_BASE_PATH

  endpoint="http://${DP_DB_HOST}:6333"
}

# if the script exits with a non-zero exit code, touch a file to indicate that the backup failed,
# the sync progress container will check this file and exit if it exists
handle_exit() {
  exit_code=$?
  if [ $exit_code -ne 0 ]; then
    echo "failed with exit code $exit_code"
    touch "${DP_BACKUP_INFO_FILE}.exit"
    exit 1
  fi
}

save_backup_size() {
  DATASAFED_BACKEND_BASE_PATH="$(dirname "$DP_BACKUP_BASE_PATH")"
  export DATASAFED_BACKEND_BASE_PATH

  TOTAL_SIZE=$(datasafed stat / | grep TotalSize | awk '{print $2}')
  echo "{\"totalSize\":\"$TOTAL_SIZE\"}" > "${DP_BACKUP_INFO_FILE}"
}

get_collections() {
  collections_response=$(curl "${endpoint}/collections")
  echo "${collections_response}" | jq -r '.result.collections[].name'
}

create_snapshot() {
  collection="$1"
  snapshot_response=$(curl -XPOST "${endpoint}/collections/${collection}/snapshots")
  echo "${snapshot_response}"
}

validate_snapshot_status() {
  snapshot_response="$1"
  status=$(echo "${snapshot_response}" | jq '.status')

  if [ "${status}" != "ok" ] && [ "${status}" != "\"ok\"" ]; then
    echo "backup failed, status: ${status}" >&2
    return 1
  fi
  return 0
}

upload_snapshot() {
  collection="$1"
  name="$2"

  curl -v --fail-with-body \
    "${endpoint}/collections/${collection}/snapshots/${name}" | \
    datasafed push - "/${collection}.snapshot"
}

delete_snapshot() {
  collection="$1"
  name="$2"

  curl -XDELETE "${endpoint}/collections/${collection}/snapshots/${name}"
}

backup_collection() {
  collection="$1"
  echo "INFO: start to snapshot collection ${collection}..."

  snapshot_response=$(create_snapshot "${collection}")
  validate_snapshot_status "${snapshot_response}" || return 1

  name=$(echo "${snapshot_response}" | jq -r '.result.name')
  upload_snapshot "${collection}" "${name}"
  delete_snapshot "${collection}" "${name}"

  echo "INFO: snapshot collection ${collection} successfully."
}

backup_all_collections() {
  collections=$(get_collections)
  if [ -z "${collections}" ]; then
    save_backup_size
    exit 0
  fi

  for collection in ${collections}; do
    if ! backup_collection "${collection}"; then
      echo "backup failed for collection ${collection}" >&2
      exit 1
    fi
  done

  save_backup_size
}

do_backup() {
  init_env
  backup_all_collections
}

# This is magic for shellspec ut framework.
# Sometime, functions are defined in a single shell script.
# You will want to test it. but you do not want to run the script.
# When included from shellspec, __SOURCED__ variable defined and script
# end here. The script path is assigned to the __SOURCED__ variable.
${__SOURCED__:+false} : || return 0

# main
trap handle_exit EXIT
do_backup
