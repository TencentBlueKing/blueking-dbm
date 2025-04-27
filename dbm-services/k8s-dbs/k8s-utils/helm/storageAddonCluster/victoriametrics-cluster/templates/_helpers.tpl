{{/*
Define victoriametrics insert component definition name
*/}}
{{- define "victoriametrics-cdName" -}}
victoriametrics-{{ .Values.addonVersion}}
{{- end -}}
