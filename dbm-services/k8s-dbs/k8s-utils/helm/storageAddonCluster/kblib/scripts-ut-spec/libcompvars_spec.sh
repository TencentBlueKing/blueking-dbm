#shellcheck shell=bash

source ./utils.sh

libcompvars_tpl_file="../templates/_libcompvars.tpl"
libcompvars_file="./libcompvars.sh"

convert_tpl_to_bash $libcompvars_tpl_file $libcompvars_file

Describe 'kubeblocks component vars library tests'
  cleanup() { rm -f $libcompvars_file; }
  AfterAll 'cleanup'

  Include $libcompvars_file

  Describe 'get_target_pod_fqdn_from_pod_fqdn_vars'
    Context 'when the target pod FQDN exists in the pod FQDN list'
      It 'should return the target pod FQDN'
        pod_fqdns="pod1.subdomain.namespace.svc.cluster.local,pod2.subdomain.namespace.svc.cluster.local"
        pod_name="pod1"
        expected="pod1.subdomain.namespace.svc.cluster.local"

        When call get_target_pod_fqdn_from_pod_fqdn_vars "$pod_fqdns" "$pod_name"
        The output should eq "$expected"
        The status should be success
      End
    End

    Context 'when the target pod FQDN does not exist in the pod FQDN list'
      It 'should return an empty string'
        pod_fqdns="pod1.subdomain.namespace.svc.cluster.local,pod2.subdomain.namespace.svc.cluster.local"
        pod_name="pod3"
        expected=""

        When call get_target_pod_fqdn_from_pod_fqdn_vars "$pod_fqdns" "$pod_name"
        The output should eq "$expected"
        The status should be failure
      End
    End

    Context 'when the pod FQDN list is empty'
      It 'should return an empty string'
        pod_fqdns=""
        pod_name="pod1"
        expected=""

        When call get_target_pod_fqdn_from_pod_fqdn_vars "$pod_fqdns" "$pod_name"
        The output should eq "$expected"
        The status should be failure
      End
    End

    Context 'when the pod name is empty'
      It 'should return an empty string'
        pod_fqdns="pod1.subdomain.namespace.svc.cluster.local,pod2.subdomain.namespace.svc.cluster.local"
        pod_name=""
        expected=""

        When call get_target_pod_fqdn_from_pod_fqdn_vars "$pod_fqdns" "$pod_name"
        The output should eq "$expected"
        The status should be failure
      End
    End
  End
End