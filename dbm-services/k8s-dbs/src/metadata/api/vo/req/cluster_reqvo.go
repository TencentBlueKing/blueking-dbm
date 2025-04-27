package req

import "time"

type K8sCrdClusterReqVo struct {
	AddonID            uint64    `json:"addon_id" binding:"required"`
	K8sClusterConfigId uint64    `json:"k8s_cluster_config_id"`
	RequestId          uint64    `json:"request_id"`
	ClusterName        string    `json:"cluster_name" binding:"required"`
	Description        string    `json:"description" binding:"required"`
	CreatedBy          string    `json:"created_by"`
	CreatedAt          time.Time `json:"created_at"`
	UpdatedBy          string    `json:"updated_by"`
	UpdatedAt          time.Time `json:"updated_at"`
}
