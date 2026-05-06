# shellcheck shell=bash
# shellcheck disable=SC2034

# validate_shell_type_and_version defined in shellspec/spec_helper.sh used to validate the expected shell type and version this script needs to run.
if ! validate_shell_type_and_version "bash" 4 &>/dev/null; then
  echo "qdrant_setup_spec.sh skip cases because dependency bash version 4 or higher is not installed."
  exit 0
fi

source ./utils.sh

# The unit test needs to rely on the common library functions defined in kblib.
# Therefore, we first dynamically generate the required common library files from the kblib library chart.
common_library_file="./common.sh"
generate_common_library $common_library_file

Describe "Qdrant Server Setup Script Tests"
  # Load the script to be tested
  Include $common_library_file
  Include ../scripts/qdrant-setup.sh

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
    unset QDRANT_POD_NAME_LIST
    unset QDRANT_POD_FQDN_LIST
    unset CURRENT_POD_NAME
  }

  Describe "get_boostrap_node()"
    It "returns the minimum lexicographical pod fqdn"
      un_setup
      QDRANT_POD_NAME_LIST="pod-a,pod-b,pod-c"
      QDRANT_POD_FQDN_LIST="pod-a.example.com,pod-b.example.com,pod-c.example.com"
      When run get_boostrap_node
      The output should equal "pod-a.example.com"
      The status should be success
    End

    It "returns an error if the fqdn cannot be found"
      un_setup
      QDRANT_POD_NAME_LIST="pod-x,pod-y,pod-z"
      QDRANT_POD_FQDN_LIST="pod-a.example.com,pod-y.example.com,pod-z.example.com"
      When run get_boostrap_node
      The stderr should include "Error: Failed to get pod: pod-x fqdn from pod fqdn list:"
      The status should be failure
    End
  End

  Describe "start_server()"
    It "starts server with bootstrap node when current pod is not bootstrap"
      un_setup
      CURRENT_POD_NAME="pod-b"
      QDRANT_POD_NAME_LIST="pod-a,pod-b,pod-c"
      QDRANT_POD_FQDN_LIST="pod-a.example.com,pod-b.example.com,pod-c.example.com"
      ./tools/curl() {
        echo "mock func get params: $1"
        return 0  # Simulate successful curl
      }
      ./qdrant() {
        echo "mock qdrant func get params: $1 $2 $3 $4"
        return 0  # Simulate successful curl
      }
      When run start_server
      The output should include "mock func get params: http://pod-a.example.com:6333/cluster"
      The output should include "mock qdrant func get params: --bootstrap http://pod-a.example.com:6335 --uri http://pod-b.example.com:6335"
      The status should be success
    End

    It "starts server with bootstrap node when current pod is bootstrap"
      un_setup
      CURRENT_POD_NAME="pod-a"
      QDRANT_POD_NAME_LIST="pod-a,pod-b,pod-c"
      QDRANT_POD_FQDN_LIST="pod-a.example.com,pod-b.example.com,pod-c.example.com"
      ./qdrant() {
        echo "mock qdrant func get params: $1 $2"
        return 0  # Simulate successful curl
      }
      When run start_server
      The output should include "mock qdrant func get params: --uri http://pod-a.example.com:6335"
      The status should be success
    End

    It "exits with error if QDRANT_POD_NAME_LIST is not set"
      un_setup
      QDRANT_POD_FQDN_LIST="pod-a.example.com,pod-b.example.com,pod-c.example.com"
      When run start_server
      The stderr should include "QDRANT_POD_NAME_LIST or QDRANT_POD_FQDN_LIST is not set, please check."
      The status should be failure
    End

    It "exits with error if QDRANT_POD_FQDN_LIST is not set"
      un_setup
      QDRANT_POD_NAME_LIST="pod-a,pod-b,pod-c"
      When run start_server
      The stderr should include "QDRANT_POD_NAME_LIST or QDRANT_POD_FQDN_LIST is not set, please check."
      The status should be failure
    End
  End
End