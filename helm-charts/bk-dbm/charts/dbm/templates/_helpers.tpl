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

{{- define "dbm.dbmServicesInitJobName" -}}
{{- printf "%s-%s-%d"  (include "dbm.fullname" .) "db-dbmservices-init" .Release.Revision }}
{{- end }}

{{- define "dbm.iamInitJobName" -}}
{{- printf "%s-%s-%d"  (include "dbm.fullname" .) "db-iam-init" .Release.Revision }}
{{- end }}

{{- define "dbm.bknoticeInitJobName" -}}
{{- printf "%s-%s-%d"  (include "dbm.fullname" .) "db-notice-init" .Release.Revision }}
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

{{- define "dbm.backend-api.fullname" -}}
{{- printf "%s-%s" (include "dbm.fullname" .) "backend-api" -}}
{{- end -}}

{{- define "dbm.celery-beater.fullname" -}}
{{- printf "%s-%s" (include "dbm.fullname" .) "celery-beater" -}}
{{- end -}}

{{- define "dbm.pipeline-worker.fullname" -}}
{{- printf "%s-%s" (include "dbm.fullname" .) "pipeline-worker" -}}
{{- end -}}

{{- define "dbm.pipeline-schedule.fullname" -}}
{{- printf "%s-%s" (include "dbm.fullname" .) "pipeline-schedule" -}}
{{- end -}}

{{- define "dbm.celery-worker.fullname" -}}
{{- printf "%s-%s" (include "dbm.fullname" .) "celery-worker" -}}
{{- end -}}

{{- define "dbm.initContainersWaitForSaaS" -}}
- name: check-saas-api
  image: {{ include "dbm.migration.k8sWaitFor.image" . }}
  imagePullPolicy: {{ .Values.image.pullPolicy }}
  args:
    - pod
    - -lapp.kubernetes.io/component={{ include "dbm.saas-api.fullname" .}}
  resources:
    {{- toYaml .Values.initJob.resources | nindent 4 }}
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

{{- define "dbm.initContainerMediumInstall" -}}
{{- $root := index . 0 -}}
{{- $db_type := index . 1 -}}
{{- $tag := index . 2 -}}
- name: dbm-medium-install-{{ $db_type }}
  image: "{{ $root.Values.global.imageRegistry | default $root.Values.dbmedium.installImage.registry }}/{{ $root.Values.dbmedium.installImage.repository }}-{{ $db_type }}:{{ $tag }}"
  imagePullPolicy: {{ $root.Values.dbmedium.installImage.pullPolicy }}
  volumeMounts:
    - mountPath: /install
      name: medium-install
{{- end }}

{{- define "dbm.initMedium" -}}
{{- $root := first . -}}
{{- $db_type := last . -}}
- name: dbm-medium-init-{{ $db_type }}
  image: "{{ $root.Values.global.imageRegistry | default $root.Values.dbmedium.image.registry }}/{{ $root.Values.dbmedium.image.repository }}:{{ $root.Values.dbmedium.image.tag | default $root.Chart.AppVersion }}"
  imagePullPolicy: {{ $root.Values.dbmedium.image.pullPolicy }}
  command:
    - /bin/bash
    - -c
  args:
    {{- if eq $db_type "monitor" }}
    - "python main.py --type sync_monitor"
    {{- else }}
    - "python main.py --type upload --db {{ $db_type }} && python main.py --type sync --db {{ $db_type }}"
    {{- end }}
  envFrom:
    {{- if $root.Values.dbmedium.extraEnvVarsCM }}
    - configMapRef:
        name: {{ $root.Values.dbmedium.extraEnvVarsCM }}
    {{- end }}
  resources:
    {{- toYaml $root.Values.initJob.resources | nindent 4 }}
  volumeMounts:
    - mountPath: /install
      name: medium-install
{{- end }}

{{/* 单一域名源 dbm.saasDomain：saas/后端API/ingress 地址全部由其派生，切换根/子路径只改此一处 */}}
{{- define "dbm.saasHost" -}}
{{- .Values.saasDomain -}}
{{- end -}}

{{/* 后端 API 入口域名：子路径模式与 saas 共用同一域名；根路径模式在首段子域名后插入 -backend-api */}}
{{- define "dbm.apiHost" -}}
{{- if eq (index .Values.envs "BK_SUBPATH_ENABLED" | default false) true }}
{{- .Values.saasDomain -}}
{{- else }}
{{- regexReplaceAll "^([^.]+)\\." .Values.saasDomain "${1}-backend-api." -}}
{{- end -}}
{{- end -}}

{{/* dbm 访问地址：域名 + 子路径前缀(仅子路径模式) */}}
{{- define "dbm.saasUrl" -}}
{{- $prefix := "" -}}
{{- if eq (index .Values.envs "BK_SUBPATH_ENABLED" | default false) true }}{{- $prefix = "/bkdbm" -}}{{- end -}}
{{- printf "http://%s%s" .Values.saasDomain $prefix -}}
{{- end -}}

{{- define "dbm.container_env" -}}
env:
  {{- include "dbm.envs" . | trim | nindent 2 }}
  {{- if eq (index .Values.envs "BK_SUBPATH_ENABLED" | default false) true }}
  - name: BK_SUBPATH_PREFIX
    value: "/bkdbm"
  {{- else }}
  - name: BK_SUBPATH_PREFIX
    value: ""
  {{- end }}
  - name: bkSaasUrl
    value: "{{ include "dbm.saasUrl" . }}"
envFrom:
  {{- if .Values.extraEnvVarsCM }}
  - configMapRef:
      name: {{ .Values.extraEnvVarsCM }}
  {{- end }}
{{- end }}

{{/*
基于内存水位的 livenessProbe：当容器 working_set 内存超过 cgroup limit 的
指定百分比时，探针失败，触发 k8s 优雅重启（SIGTERM 热关闭 -> 等待terminationGracePeriodSeconds -> 超时 SIGKILL），
从而回收 celery(threads 池)长生命周期进程累积的内存。脚本对读取失败/未设内存 limit 的场景一律返回健康（exit 0），避免误触发重启。
*/}}
{{- define "dbm.memoryLivenessProbe" -}}
{{- $cfg := .Values.memoryLivenessProbe | default dict -}}
{{- if $cfg.enabled }}
livenessProbe:
  exec:
    command:
      - /bin/bash
      - -c
      - |
        ratio={{ $cfg.ratioPercent | default 60 }}
        usage=0; limit=0; inactive=0
        if [ -f /sys/fs/cgroup/memory.current ]; then
          # cgroup v2
          usage=$(cat /sys/fs/cgroup/memory.current 2>/dev/null || echo 0)
          limit=$(cat /sys/fs/cgroup/memory.max 2>/dev/null || echo max)
          [ "$limit" = "max" ] && exit 0
          inactive=$(awk '/^inactive_file /{print $2}' /sys/fs/cgroup/memory.stat 2>/dev/null)
        elif [ -f /sys/fs/cgroup/memory/memory.usage_in_bytes ]; then
          # cgroup v1
          usage=$(cat /sys/fs/cgroup/memory/memory.usage_in_bytes 2>/dev/null || echo 0)
          limit=$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes 2>/dev/null || echo 0)
          inactive=$(awk '/^total_inactive_file /{print $2}' /sys/fs/cgroup/memory/memory.stat 2>/dev/null)
        else
          exit 0
        fi
        inactive=${inactive:-0}
        case "$limit" in ''|*[!0-9]*) exit 0;; esac
        [ "$limit" -le 0 ] && exit 0
        [ "$limit" -gt 9223372036854770000 ] && exit 0
        ws=$((usage - inactive))
        threshold=$((limit * ratio / 100))
        if [ "$ws" -gt "$threshold" ]; then
          echo "[mem-liveness] working_set=${ws}B > ${ratio}% of limit(${limit}B)=${threshold}B, trigger warm restart" >&2
          exit 1
        fi
        exit 0
  initialDelaySeconds: {{ $cfg.initialDelaySeconds | default 120 }}
  periodSeconds: {{ $cfg.periodSeconds | default 30 }}
  timeoutSeconds: {{ $cfg.timeoutSeconds | default 10 }}
  failureThreshold: {{ $cfg.failureThreshold | default 3 }}
{{- end }}
{{- end -}}

{{/*
Return the appropriate apiVersion for Horizontal Pod Autoscaler.
*/}}
{{- define "dbm.capabilities.hpa.apiVersion" -}}
{{- if semverCompare "<1.23-0" .context.Capabilities.KubeVersion.GitVersion -}}
{{- if .beta2 -}}
{{- print "autoscaling/v2beta2" -}}
{{- else -}}
{{- print "autoscaling/v2beta1" -}}
{{- end -}}
{{- else -}}
{{- print "autoscaling/v2" -}}
{{- end -}}
{{- end -}}