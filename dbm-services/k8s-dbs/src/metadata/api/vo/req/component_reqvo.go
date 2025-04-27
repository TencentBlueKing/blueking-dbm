package req

import "time"

type K8sCrdComponentReqVo struct {
	CrdClusterID  uint64    `json:"crd_cluster_id" binding:"required"`
	ComponentName string    `json:"component_name" binding:"required"`
	Description   string    `json:"description" binding:"required"`
	CreatedBy     string    `json:"created_by"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedBy     string    `json:"updated_by"`
	UpdatedAt     time.Time `json:"updated_at"`
}
