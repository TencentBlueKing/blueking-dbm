{{/*
Expand the name of the chart.
*/}}
{{- define "dbm.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "dbm.fullname" -}}
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
{{- define "dbm.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "dbm.labels" -}}
helm.sh/chart: {{ include "dbm.chart" . }}
{{ include "dbm.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "dbm.selectorLabels" -}}
app.kubernetes.io/name: {{ include "dbm.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "dbm.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "dbm.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
environment variables
*/}}
{{- define "dbm.envs" -}}
{{- range $key, $val := .Values.envs }}
- name: {{ $key }}
  value: {{ $val | quote }}
{{- end }}
{{- end }}

{{- define "dbm.migrateJobName" -}}
{{- printf "%s-%s-%d"  (include "dbm.fullname" .) "db-migrate" .Release.Revision }}
{{- end }}

{{- define "dbm.itsmInitJobName" -}}
{{- printf "%s-%s-%d"  (include "dbm.fullname" .) "db-itsm-init" .Release.Revision }}
{{- end }}

{{- define "dbm.bkccInitJobName" -}}
{{- printf "%s-%s-%d"  (include "dbm.fullname" .) "db-bkcc-init" .Release.Revision }}
{{- end }}

{{- define "dbm.bklogInitJobName" -}}
{{- printf "%s-%s-%d"  (include "dbm.fullname" .) "db-bklog-init" .Release.Revision }}
{{- end }}

{{- define "dbm.bkmonitorInitJobName" -}}
{{- printf "%s-%s-%d"  (include "dbm.fullname" .) "db-monitor-init" .Release.Revision }}
{{- end }}

{{- define "dbm.bkjobInitJobName" -}}
{{- printf "%s-%s-%d"  (include "dbm.fullname" .) "db-job-init" .Release.Revision }}
{{- end }}

{{- define "dbm.sslInitJobName" -}}
{{- printf "%s-%s-%d"  (include "dbm.fullname" .) "db-ssl-init" .Release.Revision }}
{{- end }}

{{- define "dbm.mediumInitJobName" -}}
{{- printf "%s-%s-%d"  (include "dbm.fullname" .) "db-medium-init" .Release.Revision }}
{{- end }}

{{- define "dbm.apigwInitJobName" -}}
{{- printf "%s-%s-%d"  (include "dbm.fullname" .) "db-apigw-init" .Release.Revision }}
{{- end }}

{{- define "dbm.migration.image" -}}
{{- $registryName := .image.registry -}}
{{- if not .image.registry -}}
  {{- $registryName = .imageRoot.registry -}}
{{- end -}}
{{- $repositoryName := .image.repository -}}
{{- $tag := .image.tag | toString -}}
{{- if $registryName }}
{{- printf "%s/%s:%s" $registryName $repositoryName $tag -}}
{{- else -}}
{{- printf "%s:%s" $repositoryName $tag -}}
{{- end -}}
{{- end -}}

{{- define "dbm.migration.k8sWaitFor.image" -}}
{{- if and .Values.global .Values.global.imageRegistry -}}
  {{- include "common.images.image" (dict "imageRoot" .Values.migration.images.k8sWaitFor "global" .Values.global) -}}
{{- else -}}
  {{- include "dbm.migration.image" (dict "image" .Values.migration.images.k8sWaitFor "imageRoot" .Values.image) -}}
{{- end -}}
{{- end -}}

{{/* define saas related component name */}}
{{- define "dbm.saas-api.fullname" -}}
{{- printf "%s-%s" (include "dbm.fullname" .) "saas-api" -}}
{{- end -}}

{{- define "dbm.celery-beater.fullname" -}}
{{- printf "%s-%s" (include "dbm.fullname" .) "celery-beater" -}}
{{- end -}}

{{- define "dbm.pipeline-worker.fullname" -}}
{{- printf "%s-%s" (include "dbm.fullname" .) "pipeline-worker" -}}
{{- end -}}

{{- define "dbm.celery-worker.fullname" -}}
{{- printf "%s-%s" (include "dbm.fullname" .) "celery-worker" -}}
{{- end -}}

{{- define "dbm.initContainersWaitForSaaS" -}}
initContainers:
  - name: check-saas-api
    image: {{ include "dbm.migration.k8sWaitFor.image" . }}
    imagePullPolicy: {{ .Values.image.pullPolicy }}
    args:
      - pod
      - -lapp.kubernetes.io/component={{ include "dbm.saas-api.fullname" .}}
{{- end }}

{{- define "dbm.initContainersWaitForMigrate" -}}
initContainers:
  - name: check-migrate-job
    image: {{ include "dbm.migration.k8sWaitFor.image" . }}
    imagePullPolicy: {{ .Values.image.pullPolicy }}
    args:
      - job
      - {{ include "dbm.migrateJobName" . }}
    resources:
      {{- toYaml .Values.initJob.resources | nindent 6 }}
{{- end }}

{{- define "dbm.container_env" -}}
env:
  {{- include "dbm.envs" . | trim | nindent 2 }}
envFrom:
  {{- if .Values.extraEnvVarsCM }}
  - configMapRef:
      name: {{ .Values.extraEnvVarsCM }}
  {{- end }}
{{- end }}
