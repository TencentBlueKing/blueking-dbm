package req

import "time"

type K8sCrdOpsRequestReqVo struct {
	CrdClusterID       uint64    `json:"crd_cluster_id" binding:"required"`
	K8sClusterConfigId uint64    `json:"k8s_cluster_config_id"`
	RequestId          uint64    `json:"request_id"`
	OpsRequestName     string    `json:"opsrequest_name" binding:"required"`
	OpsRequestType     string    `json:"opsrequest_type" binding:"required"`
	Metadata           string    `json:"metadata"`
	Spec               string    `json:"spec"`
	Description        string    `json:"description" binding:"required"`
	CreatedBy          string    `json:"created_by"`
	CreatedAt          time.Time `json:"created_at"`
	UpdatedBy          string    `json:"updated_by"`
	UpdatedAt          time.Time `json:"updated_at"`
}
