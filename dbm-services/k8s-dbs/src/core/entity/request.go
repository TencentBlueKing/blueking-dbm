package entity

import (
	corev1 "k8s.io/api/core/v1"
)

// OpsRequestParams OpsRequest Params
type OpsRequestParams struct {
	Metadata      Metadata            `json:"metadata,omitempty"`
	ComponentList []ComponentResource `json:"componentList,omitempty"`
}

// Request Receive request structure
type Request struct {
	K8sClusterName string `json:"k8sClusterName,omitempty"`
	Metadata       `json:",inline"`
	Spec           `json:",omitempty"`
}

type ExternalEndpoint struct {
	ServiceType string            `json:"serviceType,omitempty"`
	Annotations map[string]string `json:"annotations,omitempty"`
	Entries     []string          `json:"entries,omitempty"`
}

type OpsService struct {
	ComponentName string         `json:"componentName,omitempty"`
	Enable        bool           `json:"enable,omitempty"`
	Service       ClusterService `json:"service,omitempty"`
}

type ClusterService struct {
	Name         string             `json:"name,omitempty"`
	ServiceType  corev1.ServiceType `json:"serviceType,omitempty"`
	Annotations  map[string]string  `json:"annotations,omitempty"`
	Ports        []int32            `json:"ports,omitempty"`
	RoleSelector string             `json:"roleSelector,omitempty"`
}
