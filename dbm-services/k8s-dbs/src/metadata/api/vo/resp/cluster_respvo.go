package resp

import "time"

type K8sCrdClusterRespVo struct {
	Id                 uint64    `json:"id"`
	AddonID            uint64    `json:"addon_id"`
	K8sClusterConfigId uint64    `json:"k8s_cluster_config_id"`
	RequestId          uint64    `json:"request_id"`
	ClusterName        string    `json:"cluster_name"`
	Status             string    `json:"status"`
	Description        string    `json:"description"`
	CreatedBy          string    `json:"created_by"`
	CreatedAt          time.Time `json:"created_at"`
	UpdatedBy          string    `json:"updated_by"`
	UpdatedAt          time.Time `json:"updated_at"`
}
