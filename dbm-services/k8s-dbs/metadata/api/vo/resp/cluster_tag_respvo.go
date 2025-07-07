package resp

import (
	"time"
)

// K8sCrdClusterTagRespVo 集群标签信息返回结构
type K8sCrdClusterTagRespVo struct {
	ID           uint64    `json:"id"`
	CrdClusterID uint64    `json:"crdClusterId"`
	ClusterTag   string    `json:"clusterTag"`
	Active       bool      `json:"active"`
	CreatedBy    string    `json:"createdBy"`
	CreatedAt    time.Time `json:"createdAt"`
	UpdatedBy    string    `json:"updatedBy"`
	UpdatedAt    time.Time `json:"updatedAt"`
}
