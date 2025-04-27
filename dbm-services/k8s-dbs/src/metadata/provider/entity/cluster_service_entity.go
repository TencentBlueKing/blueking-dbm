package entity

import (
	"time"
)

type K8sClusterServiceEntity struct {
	ID            uint64    `json:"id"` // 主键
	CrdClusterID  uint64    `json:"crd_cluster_id"`
	ComponentName string    `json:"component_name"`
	ServiceName   string    `json:"service_name"`
	ServiceType   string    `json:"service_type"`
	Annotations   string    `json:"annotations"`
	InternalAddrs string    `json:"internal_addrs"`
	ExternalAddrs string    `json:"external_addrs"`
	Domains       string    `json:"domains"`
	Description   string    `json:"description"`
	CreatedBy     string    `json:"created_by"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedBy     string    `json:"updated_by"`
	UpdatedAt     time.Time `json:"updated_at"`
}
