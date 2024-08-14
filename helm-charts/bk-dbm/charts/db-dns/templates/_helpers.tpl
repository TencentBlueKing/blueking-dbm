{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "db-dns.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "db-dns.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "db-dns.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "db-dns.labels" -}}
app.kubernetes.io/name: {{ include "db-dns.name" . }}
helm.sh/chart: {{ include "db-dns.chart" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "db-dns.selectorLabels" -}}
app.kubernetes.io/name: {{ include "db-dns.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}


{{/*
Create the name of the service account to use
*/}}
{{- define "db-dns.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
    {{ default (include "db-dns.fullname" .) .Values.serviceAccount.name }}
{{- else -}}
    {{ default "default" .Values.serviceAccount.name }}
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

{{- define "k8sEnvs" -}}
- name: NODE_IP
  valueFrom:
    fieldRef:
      fieldPath: status.hostIP
{{- end}}


{{- define "db-dns-podSpec" -}}
{{- with .Values.global.imagePullSecrets }}
imagePullSecrets:
{{- toYaml . | nindent 8 }}
{{- end }}
serviceAccountName: {{ include "db-dns.serviceAccountName" . }}
securityContext:
{{- toYaml .Values.podSecurityContext | nindent 2 }}
initContainers:
{{- include "initContainersWaitFor" (list . "bk-dbm-backend-api") | nindent 2}}
containers:
  - name: {{ .Chart.Name }}
    securityContext:
      {{- toYaml .Values.securityContext | nindent 6 }}
    image: "{{ .Values.global.imageRegistry | default .Values.image.registry }}/{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
    imagePullPolicy: {{ .Values.image.pullPolicy }}
    ports:
      - containerPort: 53
        hostPort: 53
        protocol: UDP
      - containerPort: 53
        hostPort: 53
        protocol: TCP
    env:
      {{- include "k8sEnvs" . | nindent 6}}
      {{- if .Values.envs -}}
        {{- include "envs" . | trim | nindent 6 }}
      {{- end }}
    envFrom:
      {{- if .Values.extraEnvVarsCM }}
      - configMapRef:
          name: {{ .Values.extraEnvVarsCM }}
      {{- end }}
    resources:
      {{- toYaml .Values.resources | nindent 6 }}
{{- with .Values.nodeSelector }}
nodeSelector:
{{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.affinity }}
affinity:
{{- toYaml . | nindent 2 }}
{{- end }}
{{- with .Values.tolerations }}
tolerations:
{{- toYaml . | nindent 2 }}
{{- end }}
{{- end }}
