{{/*
Expand the name of the chart.
*/}}
{{- define "bk-dbm.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "bk-dbm.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "bk-dbm.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "bk-dbm.labels" -}}
helm.sh/chart: {{ include "bk-dbm.chart" . }}
{{ include "bk-dbm.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "bk-dbm.selectorLabels" -}}
app.kubernetes.io/name: {{ include "bk-dbm.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "bk-dbm.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "bk-dbm.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}


{{/*
MySQL数据库配置变量
*/}}
{{- define "bk-dbm.database" -}}
{{- $root := first . -}}
{{- $name := last . -}}
{{- $values := $root.Values -}}

{{- if $values.mysql.enabled -}}
name: {{ $name | required "mysql.name is required" }}
user: {{ $values.mysql.auth.username | required "mysql.auth.username is required" }}
password: {{ $values.mysql.auth.password | required "mysql.auth.password is required" }}
host: {{ include "mysql.primary.fullname" (dict "Values" $values.mysql "Chart" $root.Chart "Release" $root.Release) }}
port: {{ $values.mysql.primary.service.port | required "mysql.primary.service.port is required" }}
{{- else -}}
{{- $dbDefault := $values.externalDatabase -}}
{{- $db := index $values.externalDatabase $name -}}
name: {{ $db.name | default $dbDefault.name | required "externalDatabase.name is required" }}
user: {{ $db.username | default $dbDefault.username | required "externalDatabase.username is required" }}
password: {{ $db.password | default $dbDefault.password | required "externalDatabase.password is required" }}
host: {{ $db.host | default $dbDefault.host  | required "externalDatabase.host is required" }}
port: {{ $db.port | default $dbDefault.port | required "externalDatabase.port is required" }}
{{- end -}}
{{- end -}}


{{/*
ETCD 配置
*/}}
{{/*
内建 Etcd 名称
*/}}
{{- define "bk-dbm.etcdName" -}}
{{- include "common.names.fullname" (dict "Values" .Values.etcd "Chart" .Chart "Release" .Release) -}}
{{- end -}}

{{- define "bk-dbm.etcd" -}}
{{- $root := first . -}}
{{- $name := last . -}}
{{- $values := $root.Values -}}
{{- $etcd := $values.externalEtcd  -}}


{{- if $values.etcd.enabled -}}
schema: http
host: {{ include "bk-dbm.etcdName" $root }}
port: {{ $values.etcd.service.ports.client }}
username: root
password: {{ $values.etcd.auth.rbac.rootPassword }}
{{- else -}}
schema: {{ $etcd.schema | default "http" }}
host: {{ $etcd.host }}
port: {{ $etcd.port }}
username: {{ $etcd.username }}
password: {{ $etcd.password }}
{{- end -}}
{{- end -}}
