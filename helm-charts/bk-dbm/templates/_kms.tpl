{{/*
蓝鲸 KMS 共享模板。父 chart 与子 chart 共用，统一读取 .Values.global.kms。
模板名带 bk-dbm.kms 前缀，避免与子 chart 中的同名模板冲突。
*/}}

{{- define "bk-dbm.kms.enabled" -}}
{{- $kms := (.Values.global | default dict).kms | default dict -}}
{{- if $kms.enabled -}}true{{- end -}}
{{- end -}}

{{- define "bk-dbm.kms.secretName" -}}
{{- .Values.global.kms.secretName | default "bk-dbm-kms" -}}
{{- end -}}

{{- define "bk-dbm.kms.serviceAccountName" -}}
{{- .Values.global.kms.serviceAccount.name | default "bk-dbm-kms" -}}
{{- end -}}

{{/* 容器 env 列表项：开关与私钥 */}}
{{- define "bk-dbm.kms.envs" -}}
{{- if include "bk-dbm.kms.enabled" . }}
- name: ENABLE_KMS
  value: "true"
- name: BK_DBM_KMS_PRIVATE_KEY
  valueFrom:
    secretKeyRef:
      name: {{ include "bk-dbm.kms.secretName" . }}
      key: privateKey
{{- end }}
{{- end -}}

{{/* 容器 volumeMounts 列表项：信封文件 */}}
{{- define "bk-dbm.kms.volumeMounts" -}}
{{- if include "bk-dbm.kms.enabled" . }}
- name: bk-dbm-kms
  mountPath: /etc/secrets/bk-dbm-kms
  subPath: envelope
  readOnly: true
{{- end }}
{{- end -}}

{{/* Pod volumes 列表项 */}}
{{- define "bk-dbm.kms.volumes" -}}
{{- if include "bk-dbm.kms.enabled" . }}
- name: bk-dbm-kms
  secret:
    secretName: {{ include "bk-dbm.kms.secretName" . }}
    items:
      - key: envelope
        path: envelope
    defaultMode: 0400
{{- end }}
{{- end -}}

{{/* 完整的 Pod volumes 块，供原本没有 volumes 的 Pod 使用 */}}
{{- define "bk-dbm.kms.podVolumes" -}}
{{- if include "bk-dbm.kms.enabled" . }}
volumes:
  {{- include "bk-dbm.kms.volumes" . | trim | nindent 2 }}
{{- end }}
{{- end -}}

{{/* 渲染期校验，仅在开启 KMS 时执行 */}}
{{- define "bk-dbm.kms.validate" -}}
{{- if include "bk-dbm.kms.enabled" . -}}
{{- $kms := .Values.global.kms -}}
{{- if not (.Capabilities.APIVersions.Has (printf "%s/SecretStore" $kms.esoApiVersion)) -}}
{{- fail (printf "global.kms.enabled=true 需要集群已安装 External Secrets Operator（%s）" $kms.esoApiVersion) -}}
{{- end -}}
{{- if or (not $kms.server) (not $kms.role) (not $kms.credentialKey) -}}
{{- fail "global.kms.server、global.kms.role 与 global.kms.credentialKey 不能为空" -}}
{{- end -}}
{{- $tls := $kms.tls | default dict -}}
{{- if $tls.enabled -}}
{{- if ne (not $tls.certFilename) (not $tls.certKeyFilename) -}}
{{- fail "global.kms.tls.certFilename 与 global.kms.tls.certKeyFilename 必须同时配置" -}}
{{- end -}}
{{- if and (or $tls.certCAFilename $tls.certFilename) (not $tls.existingSecret) -}}
{{- fail "global.kms.tls.enabled=true 时需要配置 global.kms.tls.existingSecret" -}}
{{- end -}}
{{- end -}}
{{- if eq (include "bk-dbm.kms.serviceAccountName" .) "default" -}}
{{- fail "global.kms.serviceAccount.name 不能使用 default ServiceAccount" -}}
{{- end -}}
{{- end -}}
{{- end -}}
