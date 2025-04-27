{{/*
Expand the name of the chart.
*/}}
{{- define "risingwave.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "risingwave.fullname" -}}
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
{{- define "risingwave.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "risingwave.selectorLabels" -}}
app.kubernetes.io/name: {{ include "risingwave.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "risingwave.labels" -}}
helm.sh/chart: {{ include "risingwave.chart" . }}
{{ include "risingwave.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Common risingwave annotations
*/}}
{{- define "risingwave.annotations" -}}
{{ include "kblib.helm.resourcePolicy" . }}
{{ include "risingwave.apiVersion" . }}
{{- end }}

{{/*
API version annotation
*/}}
{{- define "risingwave.apiVersion" -}}
kubeblocks.io/crd-api-version: apps.kubeblocks.io/v1
{{- end }}

{{/*
Define risingwave compactor component definition name
*/}}
{{- define "risingwave-compactor.cmpdName" -}}
risingwave-compactor-{{ .Chart.Version }}
{{- end -}}

{{/*
Define risingwave compactor component definition regular expression name pattern
*/}}
{{- define "risingwave-compactor.cmpdRegexpPattern" -}}
^risingwave-compactor-
{{- end -}}

{{/*
Define risingwave compute component definition name
*/}}
{{- define "risingwave-compute.cmpdName" -}}
risingwave-compute-{{ .Chart.Version }}
{{- end -}}

{{/*
Define risingwave compute component definition regular expression name pattern
*/}}
{{- define "risingwave-compute.cmpdRegexpPattern" -}}
^risingwave-compute-
{{- end -}}

{{/*
Define risingwave connector component definition name
*/}}
{{- define "risingwave-connector.cmpdName" -}}
risingwave-connector-{{ .Chart.Version }}
{{- end -}}

{{/*
Define risingwave connector component definition regular expression name pattern
*/}}
{{- define "risingwave-connector.cmpdRegexpPattern" -}}
^risingwave-connector-
{{- end -}}

{{/*
Define risingwave frontend component definition name
*/}}
{{- define "risingwave-frontend.cmpdName" -}}
risingwave-frontend-{{ .Chart.Version }}
{{- end -}}

{{/*
Define risingwave frontend component definition regular expression name pattern
*/}}
{{- define "risingwave-frontend.cmpdRegexpPattern" -}}
^risingwave-frontend-
{{- end -}}

{{/*
Define risingwave meta component definition name
*/}}
{{- define "risingwave-meta.cmpdName" -}}
risingwave-meta-{{ .Chart.Version }}
{{- end -}}

{{/*
Define risingwave meta component definition regular expression name pattern
*/}}
{{- define "risingwave-meta.cmpdRegexpPattern" -}}
^risingwave-meta-
{{- end -}}

{{/*
Define risingwave config template name
*/}}
{{- define "risingwave.configTplName" -}}
risingwave-conf-tpl-{{ .Chart.Version}}
{{- end -}}

{{/*
Define risingwave compute env config template name
*/}}
{{- define "risingwave-compute.envConfigTplName" -}}
risingwave-compute-envs-tpl-{{ .Chart.Version}}
{{- end -}}

{{/*
Define risingwave connector env config template name
*/}}
{{- define "risingwave-connector.envConfigTplName" -}}
risingwave-connector-envs-tpl-{{ .Chart.Version}}
{{- end -}}

{{/*
Default config template.
*/}}
{{- define "risingwave.conftpl.default" }}
- name: risingwave-configuration
  templateRef: {{ include "risingwave.configTplName" . }}
  namespace: {{ .Release.Namespace }}
  volumeName: risingwave-configuration
{{- end }}

{{/*
Volume mount for default config template.
*/}}
{{- define "risingwave.volumeMount.conftpl.default" }}
- name: risingwave-configuration
  mountPath: /risingwave/config
{{- end }}

{{/*
Liveness probe.
*/}}
{{- define "risingwave.probe.liveness" }}
livenessProbe:
  failureThreshold: 3
  tcpSocket:
    port: svc
  initialDelaySeconds: 5
  periodSeconds: 10
  successThreshold: 1
  timeoutSeconds: 30
{{- end }}

{{/*
Readiness probe.
*/}}
{{- define "risingwave.probe.readiness" }}
readinessProbe:
  failureThreshold: 3
  tcpSocket:
    port: svc
  initialDelaySeconds: 5
  periodSeconds: 10
  successThreshold: 1
  timeoutSeconds: 30
{{- end }}

{{/*
Default security context.
*/}}
{{- define "risingwave.securityContext" }}
securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
  privileged: false
{{- end }}

{{/*
Connector service vars.
*/}}
{{- define "risingwave.vars.connector" }}
- name: CONNECTOR_SVC
  valueFrom:
    serviceVarRef:
      compDef: {{ include "risingwave-connector.cmpdRegexpPattern" . }}
      optional: false
      host: Required
{{- end }}

{{/*
Meta service vars.
*/}}
{{- define "risingwave.vars.meta" }}
- name: META_SVC
  valueFrom:
    serviceVarRef:
      compDef: {{ include "risingwave-meta.cmpdRegexpPattern" . }}
      optional: false
      host: Required
{{- end }}
