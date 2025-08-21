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
Define victoriametrics stroage component definition regular expression name prefix
*/}}
{{- define "victoriametrics-insert.cmpdRegexpPattern" -}}
^vminsert-
{{- end -}}

{{/*
Define victoriametrics select component definition name
*/}}
{{- define "victoriametrics-select.cmpdName" -}}
vmselect-{{ .Chart.Version}}
{{- end -}}

{{/*
Define victoriametrics select component definition regular expression name prefix
*/}}
{{- define "victoriametrics-select.cmpdRegexpPattern" -}}
^vmselect-
{{- end -}}

{{/*
Define victoriametrics storage component definition name
*/}}
{{- define "victoriametrics-storage.cmpdName" -}}
vmstorage-{{ .Chart.Version}}
{{- end -}}

{{/*
Define victoriametrics storage component definition regular expression name prefix
*/}}
{{- define "victoriametrics-storage.cmpdRegexpPattern" -}}
^vmstorage-
{{- end -}}

{{/*
Define victoriametrics insert component definition name
*/}}
{{- define "victoriametrics-insert.cmpvName" -}}
vminsert-cmpv
{{- end -}}

{{/*
Define victoriametrics select component definition name
*/}}
{{- define "victoriametrics-select.cmpvName" -}}
vmselect-cmpv
{{- end -}}

{{/*
Define victoriametrics storage component definition name
*/}}
{{- define "victoriametrics-storage.cmpvName" -}}
vmstorage-cmpv
{{- end -}}

{{/*
Define sidecar script
*/}}
{{- define "vm.cmScriptsName" -}}
vm-scripts-{{ .Chart.Version}}
{{- end -}}