package model

import (
	"k8s-dbs/src/metadata/constant"
	"time"
)

type K8sClusterServiceModel struct {
	ID            uint64    `gorm:"primaryKey;autoIncrement;column:id" json:"id"` // 主键
	CrdClusterID  uint64    `gorm:"not null;column:crd_cluster_id" json:"crd_cluster_id"`
	ComponentName string    `gorm:"type:varchar(100);not null;column:component_name" json:"component_name"`
	ServiceName   string    `gorm:"type:varchar(100);not null;column:service_name" json:"service_name"`
	ServiceType   string    `gorm:"type:varchar(32);not null;column:service_type" json:"service_type"`
	Annotations   string    `gorm:"type:varchar(512);column:annotations" json:"annotations"`
	InternalAddrs string    `gorm:"type:varchar(255);column:internal_addrs" json:"internal_addrs"`
	ExternalAddrs string    `gorm:"type:varchar(255);column:external_addrs" json:"external_addrs"`
	Domains       string    `gorm:"type:varchar(255);column:domains" json:"domains"`
	Description   string    `gorm:"size:100;column:description" json:"description"`
	CreatedBy     string    `gorm:"size:50;not null;column:created_by" json:"created_by"`
	CreatedAt     time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP;column:created_at" json:"created_at"`
	UpdatedBy     string    `gorm:"size:50;not null;column:updated_by" json:"updated_by"`
	UpdatedAt     time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP;column:updated_at" json:"updated_at"`
}

func (K8sClusterServiceModel) TableName() string {
	return constant.TB_K8S_CLUSTER_SERVICE
}
