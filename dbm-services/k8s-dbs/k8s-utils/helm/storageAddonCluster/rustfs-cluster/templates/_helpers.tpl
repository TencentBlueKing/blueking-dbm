{{/*
Expand the name of the clusterdefinition.
*/}}
{{- define "rustfs.cdName" -}}
rustfs-{{ .Values.addonVersion }}
{{- end -}}
