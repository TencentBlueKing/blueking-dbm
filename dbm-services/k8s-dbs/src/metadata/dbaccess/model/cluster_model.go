package model

import (
	"k8s-dbs/src/metadata/constant"
	"time"
)

type K8sCrdClusterModel struct {
	ID                 uint64    `gorm:"primaryKey;autoIncrement;column:id" json:"id"`
	AddonID            uint64    `gorm:"not null;column:addon_id" json:"addon_id"`
	K8sClusterConfigId uint64    `gorm:"not null;column:k8s_cluster_config_id" json:"k8s_cluster_config_id"`
	RequestId          uint64    `gorm:"not null;column:request_id" json:"request_id"`
	ClusterName        string    `gorm:"size:100;not null;column:cluster_name" json:"cluster_name"`
	Namespace          string    `gorm:"size:100;not null;column:namespace" json:"namespace"`
	Status             string    `gorm:"size:100;column:status" json:"status"`
	Description        string    `gorm:"size:100;column:description" json:"description"`
	CreatedBy          string    `gorm:"size:50;not null;column:created_by" json:"created_by"`
	CreatedAt          time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP;column:created_at" json:"created_at"`
	UpdatedBy          string    `gorm:"size:50;not null;column:updated_by" json:"updated_by"`
	UpdatedAt          time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP;column:updated_at" json:"updated_at"`
}

func (K8sCrdClusterModel) TableName() string {
	return constant.TB_K8S_CRD_CLUSTER
}
