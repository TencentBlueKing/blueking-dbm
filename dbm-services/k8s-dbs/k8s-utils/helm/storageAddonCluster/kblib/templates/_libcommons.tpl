{{/*
Library of common utility functions implemented in Bash. Currently, the following functions are available:
- call_func_with_retry: Call a bash function with retry capability.
*/}}

{{/*
This function is used to execute a Bash function with retry capability.

Usage:
    call_func_with_retry <max_retries> <retry_interval> <function_name> [arg1] [arg2] ...
Arguments:
    - max_retries: The maximum number of retries if the function fails.
    - retry_interval: The interval (in seconds) between each retry attempt.
    - function_name: The name of the Bash function to execute. The function can accept any number of arguments.
    - arg1, arg2, ... (optional): Arguments to pass to the function.
Result:
    The result of the executed Bash function.
Example:
    call_func_with_retry 2 1 "my_function"
    call_func_with_retry 3 5 "my_function" "arg1" "arg2"
*/}}
{{- define "kblib.commons.call_func_with_retry" }}
call_func_with_retry() {
  local max_retries="$1"
  local retry_interval="$2"
  local function_name="$3"
  shift 3

  local retries=0
  while true; do
    if "$function_name" "$@"; then
      return 0
    else
      retries=$((retries + 1))
      if [[ $retries -eq $max_retries ]]; then
        echo "Function '$function_name' failed after $max_retries retries." >&2
        return 1
      fi
      echo "Function '$function_name' failed in $retries times. Retrying in $retry_interval seconds..." >&2
      sleep $retry_interval
    fi
  done
}
{{- end }}

{{/*
This function is used to extract the ordinal number from an object name.

Usage:
    extract_obj_ordinal <object_name>
Arguments:
    - object_name: The name of the object from which to extract the ordinal number.
Result:
    The ordinal number extracted from the object name.
Example:
    extract_obj_ordinal "my-object-1"    # Output: 1
    extract_obj_ordinal "my-object-0-1"  # Output: 1
*/}}
{{- define "kblib.commons.extract_obj_ordinal" }}
extract_obj_ordinal() {
  local object_name="$1"
  local ordinal="${object_name##*-}"
  echo "$ordinal"
}
{{- end }}