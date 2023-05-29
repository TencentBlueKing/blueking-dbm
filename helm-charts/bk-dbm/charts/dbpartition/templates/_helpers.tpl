{{/*
Expand the name of the chart.
*/}}
{{- define "dbpartition.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "dbpartition.fullname" -}}
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
{{- define "dbpartition.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "dbpartition.labels" -}}
helm.sh/chart: {{ include "dbpartition.chart" . }}
{{ include "dbpartition.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "dbpartition.selectorLabels" -}}
app.kubernetes.io/name: {{ include "dbpartition.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "dbpartition.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "dbpartition.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
k8sWaitFor Image
*/}}
{{- define "dbpartition.k8sWaitFor.image" -}}
{{- if and .Values.global .Values.global.imageRegistry -}}
  {{- include "common.images.image" (dict "imageRoot" .Values.image.k8sWaitFor "global" .Values.global) -}}
{{- else -}}
  {{- include "dbm.migration.image" (dict "image" .Values.image.k8sWaitFor "imageRoot" .Values.image) -}}
{{- end -}}
{{- end -}}

{{/*
environment variables
*/}}
{{- define "envs" -}}
{{- range $key, $val := .Values.envs }}
- name: {{ $key }}
  value: {{ $val | quote }}
{{- end }}
{{- end }}

