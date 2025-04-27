package model

import (
	"k8s-dbs/src/metadata/constant"
	"time"
)

type K8sCrdComponentModel struct {
	ID            uint64    `gorm:"primaryKey;autoIncrement;column:id" json:"id"`
	CrdClusterID  uint64    `gorm:"not null;column:crd_cluster_id" json:"crd_cluster_id"`
	ComponentName string    `gorm:"size:100;not null;column:component_name" json:"component_name"`
	Status        string    `gorm:"size:100;column:status" json:"status"`
	Description   string    `gorm:"size:100;column:description" json:"description"`
	CreatedBy     string    `gorm:"size:50;not null;column:created_by" json:"created_by"`
	CreatedAt     time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP;column:created_at" json:"created_at"`
	UpdatedBy     string    `gorm:"size:50;not null;column:updated_by" json:"updated_by"`
	UpdatedAt     time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP;column:updated_at" json:"updated_at"`
}

func (K8sCrdComponentModel) TableName() string {
	return constant.TB_K8S_CRD_COMPONENT
}
