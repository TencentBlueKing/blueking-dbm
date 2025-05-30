{{/*
Define monitor
*/}}
{{- define "kblib.componentMonitor" }}
{{- if .Values.extra.disableExporter }}
disableExporter: true
{{- else }}
disableExporter: false
{{- end }}
{{- end }}