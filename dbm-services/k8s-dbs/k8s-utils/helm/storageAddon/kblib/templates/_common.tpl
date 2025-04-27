{{- define "kblib.syncer.policyRules" -}}
policyRules:
- apiGroups:
  - ""
  resources:
  - configmaps
  verbs:
  - create
  - get
  - list
  - patch
  - update
  - delete
- apiGroups:
  - ""
  resources:
  - pods
  verbs:
  - get
  - list
- apiGroups:
  - ""
  resources:
  - events
  verbs:
  - create
- apiGroups:
  - "apps.kubeblocks.io"
  resources:
  - clusters
  verbs:
  - get
  - list
{{- end -}}


{{- define "kblib.helm.resourcePolicy" -}}
{{- if eq .Values.extra.keepResource true }}
helm.sh/resource-policy: keep
{{- end -}}
{{- end -}}