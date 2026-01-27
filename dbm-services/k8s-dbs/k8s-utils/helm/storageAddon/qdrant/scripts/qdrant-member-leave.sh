#!/usr/bin/env sh

# shellcheck disable=SC2034
ut_mode="false"
test || __() {
  # when running in non-unit test mode, set the options "set -ex".
  set -ex;
}

init_cluster_info() {
  leave_peer_uri="http://${KB_LEAVE_MEMBER_POD_FQDN}:6333"
  cluster_info=$(curl -s "${leave_peer_uri}/cluster")
  leave_peer_id=$(echo "${cluster_info}" | jq -r .result.peer_id)
  leader_peer_id=$(echo "${cluster_info}" | jq -r .result.raft_info.leader)
}

move_shards() {
  cols=$(curl -s "${leave_peer_uri}/collections")
  col_count=$(echo "${cols}" | jq -r '.result.collections | length')

  if [ "${col_count}" -eq 0 ]; then
    echo "no collections found in the cluster"
    return
  fi

  col_names=$(echo "${cols}" | jq -r '.result.collections[].name')
  for col_name in ${col_names}; do
    col_cluster_info=$(curl -s "${leave_peer_uri}/collections/${col_name}/cluster")
    col_shard_count=$(echo "${col_cluster_info}" | jq -r '.result.local_shards[] | length')

    if [ "${col_shard_count}" -eq 0 ]; then
      echo "no shards found in collection ${col_name}"
      continue
    fi

    leave_shard_ids=$(echo "${col_cluster_info}" | jq -r '.result.local_shards[].shard_id')
    for shard_id in ${leave_shard_ids}; do
      echo "move shard ${shard_id} in col_name ${col_name} from ${leave_peer_id} to ${leader_peer_id}"
      curl -s -X POST -H "Content-Type: application/json" \
        -d "{\"move_shard\":{\"shard_id\": ${shard_id},\"to_peer_id\": ${leader_peer_id},\"from_peer_id\": ${leave_peer_id}}}" \
        "${leave_peer_uri}/collections/${col_name}/cluster"
    done

    check_leave_shard_ids "${leave_peer_uri}" "${col_name}"
  done
}

check_leave_shard_ids() {
  leave_peer_uri=$1
  col_name=$2

  while true; do
    col_cluster_info=$(curl -s "${leave_peer_uri}/collections/${col_name}/cluster")
    leave_shard_ids=$(echo "${col_cluster_info}" | jq -r '.result.local_shards[].shard_id')
    if [ -z "${leave_shard_ids}" ]; then
      echo "all shards in collection ${col_name} has been moved"
      break
    fi
    echo "shards ${leave_shard_ids} in collection ${col_name} are still moving..."
    sleep 1
  done
}

remove_peer() {
  echo "remove peer ${leave_peer_id} from cluster"
  curl -v -XDELETE "${leave_peer_uri}/cluster/peer/${leave_peer_id}"
}

leave_member() {
  echo "scaling in, we need to move local shards to other peers and remove local peer from the cluster"
  echo "cluster info: ${cluster_info}"
  move_shards
  remove_peer
}

# This is magic for shellspec ut framework.
# Sometime, functions are defined in a single shell script.
# You will want to test it. but you do not want to run the script.
# When included from shellspec, __SOURCED__ variable defined and script
# end here. The script path is assigned to the __SOURCED__ variable.
${__SOURCED__:+false} : || return 0

# lock file to prevent concurrent leave_member
# flock will return 1 if the lock is already held by another process, this is expected
init_cluster_info
(
  if ! flock -n -x 9; then
    echo "member is already in leaving"
    exit 1
  fi
  set -o errexit && leave_member
) 9>/var/lock/qdrant-leave-member-lock