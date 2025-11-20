{{/*
Define risingwave cluster definition name
*/}}
{{- define "risingwave-cdName" -}}
risingwave-{{ .Values.addonVersion}}
{{- end -}}
