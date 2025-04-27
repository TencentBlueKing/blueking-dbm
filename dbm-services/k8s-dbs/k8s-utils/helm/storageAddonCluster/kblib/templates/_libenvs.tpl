{{/*
Library of envs related functions implemented in Bash. Currently, the following functions are available:
- env_exist: Check if a single environment variable exists in the system's environment variables.
- env_exists: Check if multiple environment variables exist in the system's environment variables.
*/}}

{{/*
This function is used to check if a single environment variable exists in the system's environment variables.

Usage:
    env_exist "ENV_NAME"
Result:
    true if the provided environment variable exists in the system's environment variables, false otherwise
Example:
    if env_exist "ENV1"; then
      echo "ENV1 exists"
    else
      echo "ENV1 does not exist"
    fi
*/}}
{{- define "kblib.envs.env_exist" }}
env_exist() {
  local env_name="$1"

  if [[ -z "${!env_name}" ]]; then
    echo "false, $env_name does not exist"
    return 1
  fi

  return 0
}
{{- end }}

{{/*
This function is used to check if multiple environment variables exist in the system's environment variables.

Usage:
    env_exists "ENV1" "ENV2" "ENV3"
Result:
    true if all the provided environment variables exist in the system's environment variables, false otherwise
Example:
    if env_exists "ENV1" "ENV2" "ENV3"; then
      echo "All environment variables exist"
    else
      echo "Some environment variables do not exist"
    fi
*/}}
{{- define "kblib.envs.env_exists" }}
env_exists() {
  local env_list=("$@")
  local missing_envs=()

  for env in "${env_list[@]}"; do
    if [[ -z "${!env}" ]]; then
      missing_envs+=("$env")
    fi
  done

  if [[ ${#missing_envs[@]} -eq 0 ]]; then
    return 0
  else
    echo "false, the following environment variables do not exist: ${missing_envs[*]}"
    return 1
  fi
}
{{- end }}