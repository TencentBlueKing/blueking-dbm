{{/*
Library of component vars related functions implemented in Bash. Currently, the following functions are available:
- get_target_pod_fqdn_from_pod_fqdn_vars: Get the target pod FQDN from a list of pod FQDN variables based on the pod name.
*/}}

{{/*
This function is used to get the target pod FQDN from a list of pod FQDN variables based on the pod name.

Usage:
    get_target_pod_fqdn_from_pod_fqdn_vars "pod_fqdn_1,pod_fqdn_2,..." "target_pod_name"
Result:
    The target pod FQDN if found, empty string otherwise
Example:
    target_pod_fqdn=$(get_target_pod_fqdn_from_pod_fqdn_vars "pod1.subdomain.namespace.svc.cluster.local,pod2.subdomain.namespace.svc.cluster.local" "pod1")
*/}}
{{- define "kblib.compvars.get_target_pod_fqdn_from_pod_fqdn_vars" }}
get_target_pod_fqdn_from_pod_fqdn_vars() {
  local pod_fqdns="$1"
  local target_pod_name="$2"

  IFS=',' read -ra pod_fqdn_array <<< "$pod_fqdns"

  for pod_fqdn in "${pod_fqdn_array[@]}"; do
    if [[ "$pod_fqdn" == "$target_pod_name."* ]]; then
      echo "$pod_fqdn"
      return 0
    fi
  done

  echo ""
  return 1
}
{{- end }}