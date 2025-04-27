package model

import (
	"k8s-dbs/src/metadata/constant"
	"time"
)

type K8sCrdClusterDefinitionModel struct {
	ID                    uint64    `gorm:"primaryKey;autoIncrement;column:id" json:"id"`
	AddonID               uint64    `gorm:"not null;column:addon_id" json:"addon_id"`
	ClusterDefinitionName string    `gorm:"size:100;not null;column:clusterdefinition_name" json:"clusterdefinition_name"`
	Metadata              string    `gorm:"type:text;column:metadata" json:"metadata"`
	Spec                  string    `gorm:"type:text;column:spec" json:"spec"`
	Active                bool      `gorm:"type:tinyint(1);not null;default:1;column:active" json:"active"`
	Description           string    `gorm:"size:100;column:description" json:"description"`
	CreatedBy             string    `gorm:"size:50;not null;column:created_by" json:"created_by"`
	CreatedAt             time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP;column:created_at" json:"created_at"`
	UpdatedBy             string    `gorm:"size:50;not null;column:updated_by" json:"updated_by"`
	UpdatedAt             time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP;column:updated_at" json:"updated_at"`
}

func (K8sCrdClusterDefinitionModel) TableName() string {
	return constant.TB_K8S_CRD_CLUSTERDEFINITION
}
