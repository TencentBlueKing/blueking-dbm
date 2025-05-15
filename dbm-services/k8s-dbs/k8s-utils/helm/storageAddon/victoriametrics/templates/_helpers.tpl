{{/*
Define victoriametrics insert component definition name
*/}}
{{- define "victoriametrics-cdName" -}}
victoriametrics-{{ .Chart.Version}}
{{- end -}}

{{/*
Define victoriametrics insert component definition name
*/}}
{{- define "victoriametrics-insert.cmpdName" -}}
vminsert-{{ .Chart.Version}}
{{- end -}}

{{/*
Define victoriametrics select component definition name
*/}}
{{- define "victoriametrics-select.cmpdName" -}}
vmselect-{{ .Chart.Version}}
{{- end -}}

{{/*
Define victoriametrics storage component definition name
*/}}
{{- define "victoriametrics-storage.cmpdName" -}}
vmstorage-{{ .Chart.Version}}
{{- end -}}

{{/*
Define victoriametrics insert component definition name
*/}}
{{- define "victoriametrics-insert.cmpvName" -}}
vminsert-{{ .Chart.Version}}
{{- end -}}

{{/*
Define victoriametrics select component definition name
*/}}
{{- define "victoriametrics-select.cmpvName" -}}
vmselect-{{ .Chart.Version}}
{{- end -}}

{{/*
Define victoriametrics storage component definition name
*/}}
{{- define "victoriametrics-storage.cmpvName" -}}
vmstorage-{{ .Chart.Version}}
{{- end -}}

{{/*
Define sidecar script
*/}}
{{- define "vm.cmScriptsName" -}}
vm-scripts-{{ .Chart.Version}}
{{- end -}}