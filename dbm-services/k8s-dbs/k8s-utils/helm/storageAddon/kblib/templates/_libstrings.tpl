{{/*
Library of string functions implemented in Bash. Currently, the following functions are available:
- is_empty(string): Check if a string is empty.
- equals(string1, string2): Check if two strings are equal.
- split(string, separator): Split a string into an array of strings based on a separator.
- contains(string, substring): Check if a string contains a substring.
- has_prefix(string, prefix): Check if a string starts with a prefix.
- has_suffix(string, suffix): Check if a string ends with a suffix.
- replace(string, old, new, count): Replace a substring with a new string for a specified number of occurrences.
- replace_all(string, old, new): Replace all occurrences of a substring with a new string.
- trim(string, cutset): Remove leading and trailing characters from a string based on a set of characters.
- trim_prefix(string, prefix): Remove a prefix from a string if it exists.
- trim_suffix(string, suffix): Remove a suffix from a string if it exists.
*/}}

{{/*
This function checks if a string is empty.

Usage:
    `is_empty "string"`
Result:
    Returns 0 (true) if the string is empty, otherwise returns 1 (false).
Example:
    if is_empty ""; then
        echo "The string is empty"
    else
        echo "The string is not empty"
    fi
*/}}
{{- define "kblib.strings.is_empty" }}
is_empty() {
  local string="$1"

  if [[ -z "$string" ]]; then
    return 0
  else
    return 1
  fi
}
{{- end }}

{{/*
This function checks if two strings are equal.

Usage:
    `equals "string1" "string2"`
Result:
    Returns 0 (true) if the strings are equal, otherwise returns 1 (false).
Example:
    if equals "hello" "hello"; then
        echo "The strings are equal"
    else
        echo "The strings are not equal"
    fi
*/}}
{{- define "kblib.strings.equals" }}
equals() {
  local string1="$1"
  local string2="$2"

  if [[ "$string1" == "$string2" ]]; then
    return 0
  else
    return 1
  fi
}
{{- end }}

{{/*
This function is used to split a string into an array of strings.

Usage:
    `split "string" "separator"`
Result:
    Array of strings
Note:
    If no separator is provided, it defaults to a comma.
Example:
    result=($(split "hello,world" ","))
    echo "${result[@]}"
*/}}
{{- define "kblib.strings.split" }}
split() {
  local string="$1"
  local separator="${2:-,}"
  local array=()

  old_ifs="$IFS"
  IFS="$separator"
  set -f
  read -ra array <<< "$string"
  set +f
  IFS="$old_ifs"

  echo "${array[@]}"
}
{{- end }}


{{/*
This function checks if a string contains a substring.

Usage:
    `contains "string" "substring"`
Result:
    Returns 0 if the string contains the substring, otherwise returns 1.
Example:
    if contains "hello world" "world"; then
        echo "The string contains 'world'"
    else
        echo "The string does not contain 'world'"
    fi
*/}}
{{- define "kblib.strings.contains" }}
contains() {
  local string="$1"
  local substring="$2"

  if [[ "$string" == *"$substring"* ]]; then
    return 0
  else
    return 1
  fi
}
{{- end }}


{{/*
This function checks if a string starts with a prefix.

Usage:
    `has_prefix "string" "prefix"`
Result:
    Returns 0 (true) if the string starts with the prefix, otherwise returns 1 (false).
Example:
    if has_prefix "hello world" "hello"; then
        echo "The string starts with 'hello'"
    else
        echo "The string does not start with 'hello'"
    fi
*/}}
{{- define "kblib.strings.has_prefix" }}
has_prefix() {
  local string="$1"
  local prefix="$2"

  if [[ "$string" == "$prefix"* ]]; then
    return 0
  else
    return 1
  fi
}
{{- end }}

{{/*
This function checks if a string ends with a suffix.

Usage:
    `has_suffix "string" "suffix"`
Result:
    Returns 0 (true) if the string ends with the suffix, otherwise returns 1 (false).
Example:
    if has_suffix "hello world" "world"; then
        echo "The string ends with 'world'"
    else
        echo "The string does not end with 'world'"
    fi
*/}}
{{- define "kblib.strings.has_suffix" }}
has_suffix() {
  local string="$1"
  local suffix="$2"

  if [[ "$string" == *"$suffix" ]]; then
    return 0
  else
    return 1
  fi
}
{{- end }}

{{/*
This function replaces the first n occurrences of a substring with a replacement string.

Usage:
    `replace "string" "old" "new" n`
Result:
    Returns the modified string with the replacements.
Example:
    result=$(replace "hello world hello" "hello" "hi" 1)
    echo "$result"
*/}}
{{- define "kblib.strings.replace" }}
replace() {
  local string="$1"
  local old="$2"
  local new="$3"
  local n=$4

  if [[ -z "$old" ]]; then
    echo "$string"
    return
  fi

  local count=0
  local result=""

  while [[ "$string" == *"$old"* && (n -lt 0 || count -lt n) ]]; do
    local index=${string%%$old*}
    result+="${index}${new}"
    string="${string#*$old}"
    ((count++))
  done

  result+="$string"
  echo "$result"
}
{{- end }}


{{/*
This function replaces all occurrences of a substring with a replacement string.

Usage:
    `replace_all "string" "old" "new"`
Result:
    Returns the modified string with all the replacements.
Example:
    result=$(replace_all "hello world hello" "hello" "hi")
    echo "$result"
*/}}
{{- define "kblib.strings.replace_all" }}
replace_all() {
  local string="$1"
  local old="$2"
  local new="$3"

  if [[ -z "$old" ]]; then
    echo "$string"
    return
  fi

  echo "${string//$old/$new}"
}
{{- end }}

{{/*
Trim returns a slice of the string s with all leading and
trailing Unicode code points contained in cutset removed.

Usage:
    `trim "string" "cutset"`
Result:
    String with leading and trailing Unicode code points in cutset removed
Example:
    result=$(trim "1234string1234" "1234")
    echo "$result"
*/}}
{{- define "kblib.strings.trim" -}}
trim() {
  local string="$1"
  local cutset="$2"

  string="${string#"${string%%[^$cutset]*}"}"
  string="${string%"${string##*[^$cutset]}"}"

  echo "$string"
}
{{- end -}}

{{/*
trim_prefix returns s without the provided leading prefix string.
If s doesn't start with prefix, s is returned unchanged.

Usage:
    `trim_prefix "string" "prefix"`
Result:
    String with the provided leading prefix removed
Example:
    result=$(trim_prefix "hello world" "hello ")
    echo "$result"
*/}}
{{- define "kblib.strings.trim_prefix" -}}
trim_prefix() {
  local string="$1"
  local prefix="$2"

  if [[ "$string" == "$prefix"* ]]; then
    string="${string#"$prefix"}"
  fi

  echo "$string"
}
{{- end -}}

{{/*
trim_suffix returns s without the provided trailing suffix string.
If s doesn't end with suffix, s is returned unchanged.

Usage:
    `trim_suffix "string" "suffix"`
Result:
    String with the provided trailing suffix removed
Example:
    result=$(trim_suffix "hello world" " world")
    echo "$result"
*/}}
{{- define "kblib.strings.trim_suffix" -}}
trim_suffix() {
  local string="$1"
  local suffix="$2"

  if [[ "$string" == *"$suffix" ]]; then
    string="${string%"$suffix"}"
  fi

  echo "$string"
}
{{- end -}}