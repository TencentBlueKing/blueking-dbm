package entity

import "time"

type K8sCrdOpsRequestEntity struct {
	ID                 uint64    `json:"id"`
	CrdClusterID       uint64    `json:"crd_cluster_id"`
	K8sClusterConfigId uint64    `json:"k8s_cluster_config_id"`
	RequestId          uint64    `json:"request_id"`
	OpsRequestName     string    `json:"opsrequest_name"`
	OpsRequestType     string    `json:"opsrequest_type"`
	Metadata           string    `json:"metadata"`
	Spec               string    `json:"spec"`
	Status             string    `json:"status"`
	Description        string    `json:"description"`
	CreatedBy          string    `json:"created_by"`
	CreatedAt          time.Time `json:"created_at"`
	UpdatedBy          string    `json:"updated_by"`
	UpdatedAt          time.Time `json:"updated_at"`
}
