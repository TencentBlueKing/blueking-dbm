{{/*
Define cluster affinity
*/}}
{{- define "kblib.affinity" }}
affinity:
  {{- if .Values.extra.affinityNodeLabels }}
  nodeLabels:
  {{- range $key, $value := .Values.extra.affinityNodeLabels }}
    {{ $key }}: {{ $value | quote }}
  {{- end }}
  {{- end }}
  podAntiAffinity: {{ .Values.extra.podAntiAffinity }}
  topologyKeys:
  {{- if eq .Values.extra.availabilityPolicy "zone" }}
    - topology.kubernetes.io/zone
  {{- else if eq .Values.extra.availabilityPolicy "node" }}
    - kubernetes.io/hostname
  {{- end }}
  tenancy: {{ .Values.extra.tenancy }}
{{- end -}}
