#!/usr/bin/env sh

# shellcheck disable=SC2034
ut_mode="false"
test || __() {
  # when running in non-unit test mode, set the options "set -ex".
  set -ex;
}

init_restore() {
  PATH="$PATH:$DP_DATASAFED_BIN_PATH"
  export PATH
  DATASAFED_BACKEND_BASE_PATH="$DP_BACKUP_BASE_PATH"
  export DATASAFED_BACKEND_BASE_PATH

  SNAPSHOT_DIR="${DATA_DIR}/_dp_snapshots"
  mkdir -p "${SNAPSHOT_DIR}"
}

restore_snapshot() {
  snapshot="$1"
  collection_name="${snapshot%.*}"

  echo "INFO: start to restore collection ${collection_name}..."
  datasafed pull "${snapshot}" "${SNAPSHOT_DIR}/${snapshot}"

  curl -X POST \
    "http://${DP_DB_HOST}:6333/collections/${collection_name}/snapshots/upload?priority=snapshot" \
    -H 'Content-Type:multipart/form-data' \
    -F "snapshot=@${SNAPSHOT_DIR}/${snapshot}"

  echo "upload collection ${collection_name} successfully"
}

restore_all() {
  datasafed list / | while read -r snapshot; do
    [ -n "${snapshot}" ] && restore_snapshot "${snapshot}"
  done
}

# This is magic for shellspec ut framework.
# Sometime, functions are defined in a single shell script.
# You will want to test it. but you do not want to run the script.
# When included from shellspec, __SOURCED__ variable defined and script
# end here. The script path is assigned to the __SOURCED__ variable.
${__SOURCED__:+false} : || return 0

# main
init_restore
restore_all
