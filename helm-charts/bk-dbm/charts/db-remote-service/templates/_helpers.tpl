{{/*
Expand the name of the chart.
*/}}
{{- define "db-remote-service.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "db-remote-service.fullname" -}}
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
{{- define "db-remote-service.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "db-remote-service.labels" -}}
helm.sh/chart: {{ include "db-remote-service.chart" . }}
{{ include "db-remote-service.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "db-remote-service.selectorLabels" -}}
app.kubernetes.io/name: {{ include "db-remote-service.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "db-remote-service.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "db-remote-service.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
environment variables
*/}}
{{- define "envs" -}}
{{- range $key, $val := .Values.envs }}
- name: {{ $key }}
  value: {{ $val | quote }}
{{- end }}
{{- end }}

{{- define "db-remote-service.container_env" -}}
env:
  {{- include "dbm.envs" . | trim | nindent 2 }}
envFrom:
  {{- if .Values.extraEnvVarsCM }}
  - configMapRef:
      name: {{ .Values.extraEnvVarsCM }}
  {{- end }}
{{- end }}

{{- define "db-remote_service.initDnsNodeIp" -}}
- name: init-dns-node-ips
  image: bitnami/kubectl:latest
  command: ["/bin/sh", "-c"]
  args:
    - |
      #!/bin/sh
      LABEL_SELECTOR="cloud-component=dns"
      NODE_IPS=$(kubectl get nodes -l $LABEL_SELECTOR -o jsonpath='{.items[*].status.addresses[?(@.type=="InternalIP")].address}')
      NODE_IPS_CSV=$(echo $NODE_IPS | tr ' ' ',')
      echo $NODE_IPS_CSV > /data/install/shard_env/dns_ip
  volumeMounts:
    - name: shared-env
      mountPath: /data/install/shard_env/
{{- end }}
