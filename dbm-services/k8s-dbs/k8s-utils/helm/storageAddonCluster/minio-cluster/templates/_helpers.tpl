{{/*
Expand the name of the clusterdefinition.
*/}}
{{- define "minio.cdName" -}}
minio-{{ .Values.addonVersion }}
{{- end -}}