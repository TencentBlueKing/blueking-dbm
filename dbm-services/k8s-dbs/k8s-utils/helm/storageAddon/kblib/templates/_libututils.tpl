{{/*
Library of unit test utils functions implemented in Bash. Currently, the following functions are available:
*/}}

{{/*
Set the xtrace option if the ut_mode is set to "false".

Usage:
    set_xtrace_when_ut_mode_false
Result:
    If the ut_mode is set to "false", the xtrace option is set.
Example:
    set_xtrace_when_ut_mode_false
*/}}
{{- define "kblib.ututils.set_xtrace_when_ut_mode_false" }}
set_xtrace_when_ut_mode_false() {
  if [ "false" == "$ut_mode" ]; then
    set -x
  fi
}
{{- end }}


{{/*
Unset the xtrace option if the ut_mode is set to "false".

Usage:
    unset_xtrace_when_ut_mode_false
Result:
    If the ut_mode is set to "false", the xtrace option is unset.
Example:
    unset_xtrace_when_ut_mode_false
*/}}
{{- define "kblib.ututils.unset_xtrace_when_ut_mode_false" }}
unset_xtrace_when_ut_mode_false() {
  if [ "false" == "$ut_mode" ]; then
    set +x
  fi
}
{{- end }}

{{/*
Sleep for a specified amount of time if the ut_mode is set to "false".

Usage:
    sleep_when_ut_mode_false <time_second>
Result:
    If the ut_mode is set to "false", the script sleeps for the specified amount of time.
Example:
    sleep_when_ut_mode_false 5
*/}}
{{- define "kblib.ututils.sleep_when_ut_mode_false" }}
sleep_when_ut_mode_false(){
  time="$1"
  if [ "false" == "$ut_mode" ]; then
    sleep "$time"
  fi
}
{{- end }}