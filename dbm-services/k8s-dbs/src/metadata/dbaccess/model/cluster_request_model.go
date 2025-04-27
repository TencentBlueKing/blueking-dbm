package model

import (
	"k8s-dbs/src/metadata/constant"
	"time"
)

type ClusterRequestRecordModel struct {
	ID            uint64    `gorm:"primaryKey;autoIncrement;column:id" json:"id"`
	RequestId     string    `gorm:"size:50;not null;column:request_id" json:"request_id"`
	RequestType   string    `gorm:"size:50;not null;column:request_type" json:"request_type"`
	RequestParams string    `gorm:"type:text;column:request_params" json:"request_params"`
	Status        string    `gorm:"size:100;column:status" json:"status"`
	Description   string    `gorm:"size:100;column:description" json:"description"`
	CreatedBy     string    `gorm:"size:50;not null;column:created_by" json:"created_by"`
	CreatedAt     time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP;column:created_at" json:"created_at"`
	UpdatedBy     string    `gorm:"size:50;not null;column:updated_by" json:"updated_by"`
	UpdatedAt     time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP;column:updated_at" json:"updated_at"`
}

func (ClusterRequestRecordModel) TableName() string {
	return constant.TB_CLUSTER_REQUEST_RECORD
}
