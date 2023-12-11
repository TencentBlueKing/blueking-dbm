package service

import "dbm-services/mysql/db-partition/model"

var GcsDb *model.Database

// MigratePara 迁移分区规则的入参
type MigratePara struct {
	GcsDb DbConf `json:"gcs_db"`
	Apps  string `json:"apps"`
	// 是否是国内的，国内的Apps不要求包含time_zone、bk_cloud_id，国内直连区域默认填充
	// 国外的集群信息需要包含time_zone、bk_cloud_id todo
	Foreign *bool `json:"foreign"`
}

// DbConf 分区规则所在数据库的配置
type DbConf struct {
	User string `json:"user"`
	Psw  string `json:"password"`
	Name string `json:"name"`
	Host string `json:"host"`
	Port string `json:"port"`
}

type PartitionConfigWithApp struct {
	PartitionConfig
	App string `json:"app"`
}
