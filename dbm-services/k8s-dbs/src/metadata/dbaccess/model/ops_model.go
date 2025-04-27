package model

import (
	"k8s-dbs/src/metadata/constant"
	"time"
)

type K8sCrdOpsRequestModel struct {
	ID                 uint64    `gorm:"primaryKey;autoIncrement;column:id" json:"id"`
	CrdClusterID       uint64    `gorm:"not null;column:crd_cluster_id" json:"crd_cluster_id"`
	K8sClusterConfigId uint64    `gorm:"not null;column:k8s_cluster_config_id" json:"k8s_cluster_config_id"`
	RequestId          uint64    `gorm:"not null;column:request_id" json:"request_id"`
	OpsRequestName     string    `gorm:"size:100;not null;column:opsrequest_name" json:"opsrequest_name"`
	OpsRequestType     string    `gorm:"size:100;column:opsrequest_type" json:"opsrequest_type"`
	Metadata           string    `gorm:"type:text;column:metadata" json:"metadata"`
	Spec               string    `gorm:"type:text;column:spec" json:"spec"`
	Status             string    `gorm:"size:100;column:status" json:"status"`
	Description        string    `gorm:"size:100;column:description" json:"description"`
	CreatedBy          string    `gorm:"size:50;not null;column:created_by" json:"created_by"`
	CreatedAt          time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP;column:created_at" json:"created_at"`
	UpdatedBy          string    `gorm:"size:50;not null;column:updated_by" json:"updated_by"`
	UpdatedAt          time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP;column:updated_at" json:"updated_at"`
}

func (K8sCrdOpsRequestModel) TableName() string {
	return constant.TB_K8S_CRD_OPSREQUEST
}
