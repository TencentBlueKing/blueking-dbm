{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "rustfs.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "rustfs.fullname" -}}
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
{{- define "rustfs.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "rustfs.labels" -}}
helm.sh/chart: {{ include "rustfs.chart" . }}
{{ include "rustfs.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "rustfs.selectorLabels" -}}
app.kubernetes.io/name: {{ include "rustfs.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Return the appropriate apiVersion for poddisruptionbudget.
*/}}
{{- define "rustfs.pdb.apiVersion" -}}
{{- if semverCompare "<1.21-0" .Capabilities.KubeVersion.Version -}}
{{- print "policy/v1beta1" -}}
{{- else -}}
{{- print "policy/v1" -}}
{{- end -}}
{{- end -}}

{{/*
Return the appropriate apiVersion for statefulset.
*/}}
{{- define "rustfs.statefulset.apiVersion" -}}
{{- if semverCompare "<1.16-0" .Capabilities.KubeVersion.Version -}}
{{- print "apps/v1beta2" -}}
{{- else -}}
{{- print "apps/v1" -}}
{{- end -}}
{{- end -}}

{{/*
Determine secret name.
*/}}
{{- define "rustfs.secretName" -}}
{{- if .Values.existingSecret -}}
{{- .Values.existingSecret }}
{{- else -}}
{{- include "rustfs.fullname" . -}}
{{- end -}}
{{- end -}}

{{/*
Properly format optional additional arguments to RustFS binary
*/}}
{{- define "rustfs.extraArgs" -}}
{{- range .Values.extraArgs -}}
{{ " " }}{{ . }}
{{- end -}}
{{- end -}}

{{/*
Return the proper Docker Image Registry Secret Names
*/}}
{{- define "rustfs.imagePullSecrets" -}}
{{- if .Values.global }}
{{- if .Values.global.imagePullSecrets }}
imagePullSecrets:
{{- range .Values.global.imagePullSecrets }}
  - name: {{ . }}
{{- end }}
{{- else if .Values.imagePullSecrets }}
imagePullSecrets:
    {{ toYaml .Values.imagePullSecrets }}
{{- end -}}
{{- else if .Values.imagePullSecrets }}
imagePullSecrets:
    {{ toYaml .Values.imagePullSecrets }}
{{- end -}}
{{- end -}}

{{/*
Formats volumeMount for RustFS tls keys and trusted certs
*/}}
{{- define "rustfs.tlsKeysVolumeMount" -}}
{{- if .Values.tls.enabled }}
- name: cert-secret-volume
  mountPath: {{ .Values.certsPath }}
{{- end }}
{{- end -}}

{{/*
Formats volume for RustFS tls keys and trusted certs
*/}}
{{- define "rustfs.tlsKeysVolume" -}}
{{- if .Values.tls.enabled }}
- name: cert-secret-volume
  secret:
    secretName: {{ .Values.tls.certSecret }}
    items:
    - key: {{ .Values.tls.publicCrt }}
      path: public.crt
    - key: {{ .Values.tls.privateKey }}
      path: private.key
{{- end }}
{{- end -}}

{{/*
Expand the name of the clusterdefinition.
*/}}
{{- define "rustfs.cdName" -}}
rustfs-{{ .Chart.Version }}
{{- end -}}

{{/*
Expand the name of the componentdefinition.
*/}}
{{- define "rustfs.cmpdName" -}}
rustfs-{{ .Chart.Version }}
{{- end -}}

{{/*
Expand the name of the componentversion.
*/}}
{{- define "rustfs.cmpvName" -}}
rustfs-{{ .Chart.Version }}
{{- end -}}

{{/*
Expand the name of the configmap.
*/}}
{{- define "rustfs.config" -}}
rustfs-configuration-{{ .Chart.Version }}
{{- end -}}
