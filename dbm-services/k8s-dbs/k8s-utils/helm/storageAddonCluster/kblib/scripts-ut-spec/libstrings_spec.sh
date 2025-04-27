#shellcheck shell=bash

source ./utils.sh

libstrings_tpl_file="../templates/_libstrings.tpl"
libstrings_file="./libstrings.sh"

convert_tpl_to_bash $libstrings_tpl_file $libstrings_file

Describe 'kubeblocks strings library tests'
  cleanup() { rm -f $libstrings_file; }
  AfterAll 'cleanup'

  Include $libstrings_file

  Describe 'is_empty'
    Context 'when the string is empty'
      It 'should return true'
        When call is_empty ""
        The status should be success
      End
    End

    Context 'when the string is not empty'
      It 'should return false'
        When call is_empty "hello"
        The status should be failure
      End
    End
  End

  Describe 'equals'
    Context 'when the strings are equal'
      It 'should return true'
        When call equals "hello" "hello"
        The status should be success
      End
    End

    Context 'when the strings are not equal'
      It 'should return false'
        When call equals "hello" "hello1"
        The status should be failure
      End
    End
  End

  Describe 'split'
    It 'should split with default separator'
      When call split "a,b,c"
      The output should eq "a b c"
    End

    It 'should split with custom separator'
      When call split "a-b-c" "-"
      The output should eq "a b c"
    End
  End

  Describe 'contains'
    It 'should return true when contains'
      When call contains "hello world" "world"
      The status should be success
    End

    It 'should return false when not contains'
      When call contains "hello world" "foo"
      The status should be failure
    End
  End

  Describe 'has_prefix'
    It 'should return true when has prefix'
      When call has_prefix "hello world" "hello"
      The status should be success
    End

    It 'should return false when no prefix'
      When call has_prefix "hello world" "world"
      The status should be failure
    End
  End

  Describe 'has_suffix'
    It 'should return true when has suffix'
      When call has_suffix "hello world" "world"
      The status should be success
    End

    It 'should return false when no suffix'
      When call has_suffix "hello world" "hello"
      The status should be failure
    End
  End

  Describe 'replace'
    It 'should replace single occurrence'
      When call replace "hello world hello" "hello" "hi" 1
      The output should eq "hi world hello"
    End

    It 'should replace multiple occurrences'
      When call replace "hello world hello" "hello" "hi" 2
      The output should eq "hi world hi"
    End

    It 'should replace with index -1'
      When call replace "hello world hello" "hello" "hi" -1
      The output should eq "hi world hi"
    End
  End

  Describe 'replace_all'
    It 'should replace all occurrences'
      When call replace_all "hello world hello" "hello" "hi"
      The output should eq "hi world hi"
    End
  End

  Describe 'trim'
    It 'should trim both sides'
      When call trim "1234string1234" "1234"
      The output should eq "string"
    End

    It 'should trim left side'
      When call trim "1234string" "1234"
      The output should eq "string"
    End

    It 'should trim right side'
      When call trim "string1234" "1234"
      The output should eq "string"
    End
  End

  Describe 'trim_prefix'
    It 'should trim prefix'
      When call trim_prefix "hello world" "hello "
      The output should eq "world"
    End

    It 'should not trim when no prefix'
      When call trim_prefix "hello world" "foo"
      The output should eq "hello world"
    End
  End

  Describe 'trim_suffix'
    It 'should trim suffix'
      When call trim_suffix "hello world" " world"
      The output should eq "hello"
    End

    It 'should not trim when no suffix'
      When call trim_suffix "hello world" "foo"
      The output should eq "hello world"
    End
  End
End