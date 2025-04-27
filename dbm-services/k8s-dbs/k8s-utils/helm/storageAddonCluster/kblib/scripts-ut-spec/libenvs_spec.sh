#shellcheck shell=bash

source ./utils.sh

libenvs_tpl_file="../templates/_libenvs.tpl"
libenvs_file="./libenvs.sh"

convert_tpl_to_bash $libenvs_tpl_file $libenvs_file

Describe 'kubeblocks envs library tests'
  cleanup() { rm -f $libenvs_file; }
  AfterAll 'cleanup'

  Describe 'env_exist'
    Include $libenvs_file

    Context 'when the environment variable does not exist'
      It 'should return false'
        When call env_exist "NON_EXISTENT_ENV"
        The output should eq "false, NON_EXISTENT_ENV does not exist"
        The status should be failure
      End
    End

    Context 'when the environment variable exists'
      setup() {
        export EXISTENT_ENV="value"
      }
      Before 'setup'

      It 'should return true'
        When call env_exist "EXISTENT_ENV"
        The status should be success
      End
    End
  End

  Describe 'env_exists'
    Include $libenvs_file

    Context 'when all environment variables exist'
      setup() {
        export ENV1="value1"
        export ENV2="value2"
        export ENV3="value3"
      }
      Before 'setup'

      It 'should return true'
        When call env_exists "ENV1" "ENV2" "ENV3"
        The status should be success
      End
    End

    Context 'when some environment variables do not exist'
      setup() {
        export ENV1="value1"
        export ENV3="value3"
      }
      Before 'setup'

      It 'should return false'
        When call env_exists "ENV1" "ENV2" "ENV3"
        The output should eq "false, the following environment variables do not exist: ENV2"
        The status should be failure
      End
    End

    Context 'when all environment variables do not exist'
      It 'should return false'
        When call env_exists "ENV1" "ENV2" "ENV3"
        The output should eq "false, the following environment variables do not exist: ENV1 ENV2 ENV3"
        The status should be failure
      End
    End
  End
End