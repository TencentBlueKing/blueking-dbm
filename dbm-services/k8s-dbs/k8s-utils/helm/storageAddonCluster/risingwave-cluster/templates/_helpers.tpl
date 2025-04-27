{{/*
Define victoriametrics insert component definition name
*/}}
{{- define "risingwave-cdName" -}}
risingwave-{{ .Values.addonVersion}}
{{- end -}}
