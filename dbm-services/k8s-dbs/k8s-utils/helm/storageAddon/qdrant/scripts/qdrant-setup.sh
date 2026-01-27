#!/usr/bin/env bash

load_common_library() {
  # the common.sh scripts is mounted to the same path which is defined in the cmpd.spec.scripts
  common_library_file="/qdrant/scripts/common.sh"
  # shellcheck disable=SC1090
  source "${common_library_file}"
}

# get the min lexicographical order pod fqdn as the bootstrap node
get_boostrap_node() {
  min_lexicographical_pod_name=$(min_lexicographical_order_pod "$QDRANT_POD_NAME_LIST")
  min_lexicographical_pod_fqdn=$(get_target_pod_fqdn_from_pod_fqdn_vars "$QDRANT_POD_FQDN_LIST" "$min_lexicographical_pod_name")
  if is_empty "$min_lexicographical_pod_fqdn"; then
    echo "Error: Failed to get pod: $min_lexicographical_pod_name fqdn from pod fqdn list: $QDRANT_POD_FQDN_LIST. Exiting." >&2
    return 1
  fi
  echo $min_lexicographical_pod_fqdn
  return 0
}

start_server() {
  # check QDRANT_POD_NAME_LIST and QDRANT_POD_FQDN_LIST are set
  if is_empty "$QDRANT_POD_NAME_LIST" || is_empty "$QDRANT_POD_FQDN_LIST"; then
    echo "QDRANT_POD_NAME_LIST or QDRANT_POD_FQDN_LIST is not set, please check." >&2
    return 1
  fi

  current_pod_fqdn=$(get_target_pod_fqdn_from_pod_fqdn_vars "$QDRANT_POD_FQDN_LIST" "$CURRENT_POD_NAME")
  if is_empty "$current_pod_fqdn"; then
    echo "Error: Failed to get current pod: $CURRENT_POD_NAME fqdn from qdrant pod fqdn list: $QDRANT_POD_FQDN_LIST. Exiting." >&2
    exit 1
  fi

  # get the min lexicographical order pod fqdn as the bootstrap node
  boostrap_node_fqdn=$(get_boostrap_node)
  status=$?
  if [ $status -ne 0 ]; then
    echo "Error: Failed to get bootstrap node fqdn. Exiting." >&2
    exit 1
  fi

  if [ "$current_pod_fqdn" == "$boostrap_node_fqdn" ]; then
    ./qdrant --uri "http://${current_pod_fqdn}:6335"
  else
    until ./tools/curl http://${boostrap_node_fqdn}:6333/cluster; do
      echo "INFO: wait for bootstrap node: $boostrap_node_fqdn starting..."
      sleep 1;
    done
    ./qdrant --bootstrap "http://${boostrap_node_fqdn}:6335" --uri "http://${current_pod_fqdn}:6335"
  fi
}

# This is magic for shellspec ut framework.
# Sometime, functions are defined in a single shell script.
# You will want to test it. but you do not want to run the script.
# When included from shellspec, __SOURCED__ variable defined and script
# end here. The script path is assigned to the __SOURCED__ variable.
${__SOURCED__:+false} : || return 0

# main
load_common_library
start_server