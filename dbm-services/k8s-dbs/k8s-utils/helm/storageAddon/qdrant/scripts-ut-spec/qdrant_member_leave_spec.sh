# shellcheck shell=bash
# shellcheck disable=SC2034

# validate_shell_type_and_version defined in shellspec/spec_helper.sh used to validate the expected shell type and version this script needs to run.
if ! validate_shell_type_and_version "bash" 4 &>/dev/null; then
  echo "qdrant_member_leave_spec.sh skip cases because dependency bash version 4 or higher is not installed."
  exit 0
fi

source ./utils.sh

# The unit test needs to rely on the common library functions defined in kblib.
# Therefore, we first dynamically generate the required common library files from the kblib library chart.
common_library_file="./common.sh"
generate_common_library $common_library_file

Describe "Qdrant Member Leave Script Tests"
  # Load the script to be tested
  Include $common_library_file
  Include ../scripts/qdrant-member-leave.sh

  init() {
    # set ut_mode to true to hack control flow in the script
    ut_mode="true"
  }
  BeforeAll "init"

  cleanup() {
    rm -f $common_library_file;
  }
  AfterAll 'cleanup'

  un_setup() {
    # Reset environment variables before each test
    unset KB_LEAVE_MEMBER_POD_FQDN
    leave_peer_uri="http://test-ip:6333"
  }

  # Mock jq to simulate its output
  jq() {
    case $2 in
      *".result.peer_id"*)
        echo "leave-peer-id"
        ;;
      *".result.raft_info.leader"*)
        echo "leader-peer-id"
        ;;
      *".result.collections | length"*)
        echo 2
        ;;
      *".result.collections[].name"*)
        echo "collection1" "collection2"
        ;;
      *".result.local_shards[] | length"*)
        echo 2
        ;;
      *".result.local_shards[].shard_id"*)
        echo "shard1" "shard2"
        ;;
      *".result.local_shards"*)
        echo '["shard1","shard2"]'
        ;;
      *)
        echo "unknown jq filter"
        ;;
    esac
  }

  Describe "move_shards()"
    It "moves shards from leave peer to leader"
      un_setup
      KB_LEAVE_MEMBER_POD_FQDN="test-ip"
      cluster_info='{"result":{"peer_id":"leave-peer-id","raft_info":{"leader":"leader-peer-id"}}}'
      leave_peer_id="leave-peer-id"
      leader_peer_id="leader-peer-id"

      curl() {
        # Mock the response for collections
        if [[ $1 == *"/collections"* ]]; then
          echo '{"result":{"collections":[{"name":"collection1"},{"name":"collection2"}]}}'
        elif [[ $1 == *"/collections/collection1/cluster"* ]]; then
          echo '{"result":{"local_shards":[{"shard_id":"shard1"},{"shard_id":"shard2"}]}}'
        elif [[ $1 == *"/collections/collection2/cluster"* ]]; then
          echo '{"result":{"local_shards":[{"shard_id":"shard3"}]}}'
        fi
        return 0  # Simulate successful curl
      }

      check_leave_shard_ids() {
        echo "mock check_leave_shard_ids called"
        return 0
      }

      When run move_shards
      The output should include "move shard shard1 in col_name collection1 from leave-peer-id to leader-peer-id"
      The output should include "move shard shard2 in col_name collection1 from leave-peer-id to leader-peer-id"
      The status should be success
    End

    It "handles no collections found"
      un_setup
      KB_LEAVE_MEMBER_POD_FQDN="test-ip"
      curl() {
        echo '{"result":{"collections":[]}}'
        return 0
      }

      jq() {
        case $2 in
          *".result.collections | length"*)
            echo 0
            ;;
          *)
            echo "unknown jq filter"
            ;;
        esac
      }

      When run move_shards
      The output should include "no collections found in the cluster"
      The status should be success
    End

    It "handles no shards found in a collection"
      un_setup
      KB_LEAVE_MEMBER_POD_FQDN="test-ip"
      curl() {
        if [[ $1 == *"/collections"* ]]; then
          echo '{"result":{"collections":[{"name":"collection1"}]}}'
        elif [[ $1 == *"/collections/collection1/cluster"* ]]; then
          echo '{"result":{"local_shards":[]}}'
        fi
        return 0
      }

      jq() {
        case $2 in
          *".result.peer_id"*)
            echo "leave-peer-id"
            ;;
          *".result.raft_info.leader"*)
            echo "leader-peer-id"
            ;;
          *".result.collections | length"*)
            echo 2
            ;;
          *".result.collections[].name"*)
            echo "collection1" "collection2"
            ;;
          *".result.local_shards[] | length"*)
            echo 0
            ;;
          *)
            echo "unknown jq filter"
            ;;
        esac
      }

      When run move_shards
      The output should include "no shards found in collection collection1"
      The output should include "no shards found in collection collection2"
      The status should be success
    End
  End

  Describe "remove_peer()"
    It "removes the peer from the cluster"
      un_setup
      KB_LEAVE_MEMBER_POD_FQDN="test-ip"
      leave_peer_id="leave-peer-id"

      curl() {
        return 0  # Simulate successful delete
      }

      When run remove_peer
      The output should include "remove peer leave-peer-id from cluster"
      The status should be success
    End
  End

  Describe "leave_member()"
    It "executes the leave member process"
      un_setup
      KB_LEAVE_MEMBER_POD_FQDN="test-ip"
      cluster_info='{"result":{"peer_id":"leave-peer-id","raft_info":{"leader":"leader-peer-id"}}}'
      leave_peer_id="leave-peer-id"
      leader_peer_id="leader-peer-id"

      move_shards() {
        echo "mock move_shards called"
      }
      remove_peer() {
        echo "mock remove_peer called"
      }

      When run leave_member
      The output should include "scaling in, we need to move local shards to other peers and remove local peer from the cluster"
      The output should include "mock move_shards called"
      The output should include "mock remove_peer called"
      The status should be success
    End
  End
End