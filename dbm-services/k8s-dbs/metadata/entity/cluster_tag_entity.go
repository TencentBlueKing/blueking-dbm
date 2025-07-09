package entity

import (
	"time"
)

// K8sCrdClusterTagEntity 存储集群的标签信息 entity 定义
type K8sCrdClusterTagEntity struct {
	ID           uint64    `json:"id"`
	CrdClusterID uint64    `json:"crdClusterId"`
	ClusterTag   string    `json:"clusterTag"`
	Active       bool      `json:"active"`
	CreatedBy    string    `json:"createdBy"`
	CreatedAt    time.Time `json:"createdAt"`
	UpdatedBy    string    `json:"updatedBy"`
	UpdatedAt    time.Time `json:"updatedAt"`
}
