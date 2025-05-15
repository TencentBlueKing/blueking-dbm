{{/*
Define victoriametrics insert component definition name
*/}}
{{- define "victoriametrics-cdName" -}}
victoriametrics-{{ .Values.addonVersion}}
{{- end -}}

{{- define "clustername" -}}
{{ .Release.Name }}
{{- end}}

{{/*
Create the name of the service account to use
*/}}
{{- define "victoriametrics.serviceAccountName" -}}
{{- default (printf "kb-%s" (include "clustername" .)) }}
{{- end }}
