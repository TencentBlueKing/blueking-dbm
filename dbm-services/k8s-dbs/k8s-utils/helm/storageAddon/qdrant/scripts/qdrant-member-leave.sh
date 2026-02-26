#!/usr/bin/env sh

# Add qdrant tools (curl, jq) to PATH
export PATH="/qdrant/tools:$PATH"

# shellcheck disable=SC2034
ut_mode="false"
test || __() {
  # when running in non-unit test mode, set the options "set -ex".
  set -ex;
}

init_cluster_info() {
  # KB_LEAVE_MEMBER_POD_FQDN is not a standard KubeBlocks env var in 0.9.x
  # Fall back to KB_LEAVE_MEMBER_POD_IP (standard), or construct FQDN from KB_LEAVE_MEMBER_POD_NAME
  if [ -n "${KB_LEAVE_MEMBER_POD_FQDN}" ]; then
    leave_peer_uri="http://${KB_LEAVE_MEMBER_POD_FQDN}:6333"
  elif [ -n "${KB_LEAVE_MEMBER_POD_IP}" ]; then
    leave_peer_uri="http://${KB_LEAVE_MEMBER_POD_IP}:6333"
  elif [ -n "${KB_LEAVE_MEMBER_POD_NAME}" ]; then
    # Construct FQDN: <pod-name>.<headless-svc>.<namespace>.svc.cluster.local
    headless_svc=$(echo "${KB_LEAVE_MEMBER_POD_NAME}" | sed 's/-[0-9]*$//')-headless
    namespace=$(cat /var/run/secrets/kubernetes.io/serviceaccount/namespace 2>/dev/null || echo "default")
    leave_peer_uri="http://${KB_LEAVE_MEMBER_POD_NAME}.${headless_svc}.${namespace}.svc.cluster.local:6333"
  else
    echo "ERROR: no leave member pod info available. KB_LEAVE_MEMBER_POD_FQDN, KB_LEAVE_MEMBER_POD_IP, KB_LEAVE_MEMBER_POD_NAME are all empty"
    echo "Available KB_ env vars:"
    env | grep -i "^KB_" || echo "(none)"
    exit 1
  fi
  echo "leave_peer_uri: ${leave_peer_uri}"
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