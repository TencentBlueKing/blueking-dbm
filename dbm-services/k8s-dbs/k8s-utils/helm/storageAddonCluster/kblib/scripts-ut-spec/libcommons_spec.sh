#shellcheck shell=bash

source ./utils.sh

libcommons_tpl_file="../templates/_libcommons.tpl"
libcommons_file="./libcommons.sh"

convert_tpl_to_bash $libcommons_tpl_file $libcommons_file

Describe 'kubeblocks commons library tests'
  cleanup() { rm -f $libcommons_file; }
  AfterAll 'cleanup'

  Include $libcommons_file

  Describe 'call_func_with_retry'

    successful_function_with_one_param() {
      echo "Successful function called with one arguments: $1"
      return 0
    }

    successful_function() {
      echo "Successful function called with arguments: $*"
      return 0
    }

    failing_function() {
      echo "Failing function called with arguments: $*"
      return 1
    }

    Context 'when the function succeeds on the first attempt'
      It 'should execute the function successfully'
        When call call_func_with_retry 2 1 successful_function_with_one_param  "arg1"
        The output should include "Successful function called with one arguments: arg1"
        The status should be success
      End
    End

    Context 'when the function succeeds on the first attempt'
      It 'should execute the function successfully'
        When call call_func_with_retry 2 1 successful_function "arg1" "arg2"
        The output should include "Successful function called with arguments: arg1 arg2"
        The status should be success
      End
    End

    Context 'when the function fails and reaches the maximum retries'
      It 'should retry the function and fail after reaching the maximum retries'
        When call call_func_with_retry 2 1 failing_function "arg1" "arg2"
        The output should include "Failing function called with arguments: arg1 arg2"
        The stderr should include "Function 'failing_function' failed in 1 times. Retrying in 1 seconds..."
        The stderr should include "Function 'failing_function' failed after 2 retries."
        The status should be failure
      End
    End

    Context 'when the function fails but succeeds within the maximum retries'
      FAILS_ON_FIRST_CALL=0
      fails_on_first_call_only() {
        FAILS_ON_FIRST_CALL=$((FAILS_ON_FIRST_CALL + 1))
        if [[ $FAILS_ON_FIRST_CALL -eq 1 ]]; then
          echo "Function fails on first call"
          return 1
        else
          echo "Function succeeds on subsequent calls"
          return 0
        fi
      }

      It 'should retry the function and succeed on the second attempt'
        FAILS_ON_FIRST_CALL=0
        When call call_func_with_retry 3 1 fails_on_first_call_only
        The output should include "Function fails on first call"
        The stderr should include "Function 'fails_on_first_call_only' failed in 1 times. Retrying in 1 seconds..."
        The output should include "Function succeeds on subsequent calls"
        The status should be success
      End
    End
  End

  Describe 'extract_obj_ordinal'
    Context 'when the object ordinal is a single digit'
      It 'should extract the object ordinal'
        When call extract_obj_ordinal "my-object-1"
        The output should equal "1"
        The status should be success
      End
    End

    Context 'when the object ordinal is a single digit'
      It 'should extract the object ordinal'
        When call extract_obj_ordinal "my-object-0-1"
        The output should equal "1"
        The status should be success
      End
    End
  End
End