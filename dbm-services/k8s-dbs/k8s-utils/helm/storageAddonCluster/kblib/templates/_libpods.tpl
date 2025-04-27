{{/*
Library of pods related functions implemented in Bash. Currently, the following functions are available:
- get_pod_list_from_env: Get the list of pods from the provided environment variable.
- min_lexicographical_order_pod: Get the minimum lexicographically pod name from the given pod list.
*/}}

{{/*
This function is used to get the list of pods from the provided environment variable.
If the environment variable does not exist, an error is returned.

Usage:
    get_pod_list_from_env "ENV_VAR_NAME"
Result:
    An array of pod names
Example:
    pods=$(get_pod_list_from_env "MY_POD_LIST")
*/}}
{{- define "kblib.pods.get_pod_list_from_env" }}
get_pod_list_from_env() {
  local env_name="${1}"

  if [[ -z "${!env_name}" ]]; then
    echo "failed to get pod list cause environment variable '$env_name' does not exist" >&2
    return 1
  fi

  local pod_list_str="${!env_name}"
  local pod_list=()

  old_ifs="$IFS"
  IFS=','
  set -f
  read -ra pod_list <<< "$pod_list_str"
  set +f
  IFS="$old_ifs"

  echo "${pod_list[@]}"
}
{{- end }}

{{/*
This function is used to get the minimum lexicographically pod name from the pod list.

Usage:
    min_lexicographical_order_pod "pod1,pod2,pod3"
Result:
    The minimum lexicographically order pod name
Example:
    minimum_pod=$(min_lexicographical_order_pod "pod-0,pod-1,pod-2") # pod0
*/}}
{{- define "kblib.pods.min_lexicographical_order_pod" }}
min_lexicographical_order_pod() {
  local pod_list_str="${1}"
  local pod_list=()

  old_ifs="$IFS"
  IFS=','
  set -f
  read -ra pod_list <<< "$pod_list_str"
  set +f
  IFS="$old_ifs"

  local minimum_pod="${pod_list[0]}"
  for pod in "${pod_list[@]}"; do
    if [[ "$pod" < "$minimum_pod" ]]; then
      minimum_pod="$pod"
    fi
  done

  echo "$minimum_pod"
}
{{- end }}