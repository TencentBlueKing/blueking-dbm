#shellcheck shell=bash

source ./utils.sh

libpods_tpl_file="../templates/_libpods.tpl"
libpods_file="./libpods.sh"

convert_tpl_to_bash $libpods_tpl_file $libpods_file

Describe 'kubeblocks pods library tests'
  cleanup() { rm -f $libpods_file; }
  AfterAll 'cleanup'

  Describe 'get_pod_list_from_env without setting TEST_POD_LIST env variable'
    Include $libpods_file

    It 'get_pod_list_from_env should return error'
      When call get_pod_list_from_env "TEST_POD_LIST"
      The output should eq ""
      The status should be failure
      The stderr should include "'TEST_POD_LIST' does not exist"
    End
  End

  Describe 'get_pod_list_from_env with setting TEST_POD_LIST env variable'
    Include $libpods_file

    setup() {
      export TEST_POD_LIST="pod1,pod2,pod3"
    }
    Before 'setup'

    It 'get_pod_list_from_env should return TEST_POD_LIST'
      When call get_pod_list_from_env "TEST_POD_LIST"
      The output should eq "pod1 pod2 pod3"
    End
  End

  Describe 'min_lexicographical_order_pod'
    Include $libpods_file

    It 'min_lexicographical_order_pod should return pod-1'
      When call min_lexicographical_order_pod "pod-pod-0,pod-1,pod-pod-1"
      The output should eq "pod-1"
    End

    It 'min_lexicographical_order_pod should return pod1'
      When call min_lexicographical_order_pod "pod2,pod1,pod3"
      The output should eq "pod1"
    End

    It 'min_lexicographical_order_pod should return pod-0'
      When call min_lexicographical_order_pod "pod-0,pod-0-0,pod-1-0"
      The output should eq "pod-0"
    End
  End
End