package resp

import "time"

type K8sCrdComponentRespVo struct {
	Id            uint64    `json:"id"`
	CrdClusterID  uint64    `json:"crd_cluster_id"`
	ComponentName string    `json:"component_name"`
	Status        string    `json:"status"`
	Description   string    `json:"description"`
	CreatedBy     string    `json:"created_by"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedBy     string    `json:"updated_by"`
	UpdatedAt     time.Time `json:"updated_at"`
}
