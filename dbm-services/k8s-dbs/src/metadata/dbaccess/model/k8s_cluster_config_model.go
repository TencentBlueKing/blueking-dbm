package model

import (
	"k8s-dbs/src/metadata/constant"
	"time"
)

type K8sClusterConfigModel struct {
	ID           uint64    `gorm:"primaryKey;autoIncrement;column:id" json:"id"`
	ClusterName  string    `gorm:"column:cluster_name;type:varchar(255);not null" json:"cluster_name"`
	APIServerURL string    `gorm:"column:api_server_url;type:varchar(255);not null" json:"api_server_url"`
	CACert       string    `gorm:"column:ca_cert;type:text" json:"ca_cert"`
	ClientCert   string    `gorm:"column:client_cert;type:text" json:"client_cert"`
	ClientKey    string    `gorm:"column:client_key;type:text" json:"client_key"`
	Token        string    `gorm:"column:token;type:text" json:"token"`
	Username     string    `gorm:"column:username;type:varchar(255);" json:"username"`
	Password     string    `gorm:"column:password;type:varchar(255);" json:"password"`
	Active       bool      `gorm:"type:tinyint(1);not null;default:1;column:active" json:"active"`
	Description  string    `gorm:"size:100;column:description" json:"description"`
	CreatedBy    string    `gorm:"size:50;not null;column:created_by" json:"created_by"`
	CreatedAt    time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP;column:created_at" json:"created_at"`
	UpdatedBy    string    `gorm:"size:50;not null;column:updated_by" json:"updated_by"`
	UpdatedAt    time.Time `gorm:"type:timestamp;not null;default:CURRENT_TIMESTAMP on update CURRENT_TIMESTAMP;column:updated_at" json:"updated_at"`
}

func (K8sClusterConfigModel) TableName() string {
	return constant.TB_K8S_CLUSTER_CONFIG
}
