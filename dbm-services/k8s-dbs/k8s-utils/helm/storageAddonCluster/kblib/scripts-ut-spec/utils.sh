#!/bin/bash

convert_tpl_to_bash() {
  local input_file="$1"
  local output_file="$2"

  sed -e '/^{{\/\*$/,/^\*\/}}$/d' \
      -e '/^{{-.*}}/d' \
      -e 's/{{- define ".*" }}//' \
      -e 's/{{- end }}//' \
      "$input_file" > "$output_file"
}