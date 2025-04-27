{{/*
Generate full name of a resource.
*/}}
{{- define "surreal-cluster.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Expand the name of the chart.
*/}}
{{- define "tidb-cluster.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "tidb-cluster.fullname" -}}
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
{{- define "tidb-cluster.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "tidb-cluster.labels" -}}
helm.sh/chart: {{ include "tidb-cluster.chart" . }}
{{ include "tidb-cluster.selectorLabels" . }}
app.kubernetes.io/version: {{ default .Chart.AppVersion .Values.appVersionOverride | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "tidb-cluster.selectorLabels" -}}
app.kubernetes.io/name: {{ include "tidb-cluster.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "clustername" -}}
{{ include "tidb-cluster.fullname" .}}
{{- end}}

{{/*
Create the name of the service account to use
*/}}
{{- define "tidb-cluster.serviceAccountName" -}}
{{- default (printf "kb-%s" (include "clustername" .)) .Values.serviceAccount.name }}
{{- end }}



{{/*
Define victoriametrics insert component definition name
*/}}
{{- define "surrealdb-cdName" -}}
surrealdb-{{ .Values.addonVersion}}
{{- end -}}