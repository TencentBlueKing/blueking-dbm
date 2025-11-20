package dbareport

// BackupStatus the status of backup
type BackupStatus struct {
	Status string `json:"status" gorm:"type:varchar(32);NOT NULL"`
	// StatusDetail 如果失败，记录失败详情
	StatusDetail string `json:"status_detail" gorm:"type:text"`

	BackupId      string `json:"backup_id" gorm:"type:varchar(60);NOT NULL"`
	BackupType    string `json:"backup_type"  gorm:"type:varchar(32);NOT NULL"`
	ClusterId     int    `json:"cluster_id" gorm:"type:int;NOT NULL"`
	ClusterDomain string `json:"cluster_domain" gorm:"type:varchar(255);NOT NULL"`
	BackupHost    string `json:"backup_host"  gorm:"type:varchar(32);NOT NULL"`
	BackupPort    int    `json:"backup_port"  gorm:"type:int;NOT NULL"`
	MysqlRole     string `json:"mysql_role"  gorm:"type:varchar(32);NOT NULL"`
	// ShardValue 分片 id，仅 spider 有用
	ShardValue      int    `json:"shard_value"  gorm:"type:int;NOT NULL"`
	BillId          string `json:"bill_id"  gorm:"type:varchar(64);NOT NULL"`
	BkBizId         int    `json:"bk_biz_id"  gorm:"type:int;NOT NULL"`
	DataSchemaGrant string `json:"data_schema_grant"  gorm:"type:varchar(32);NOT NULL"`
	// IsFullBackup 是否包含数据的全备
	IsFullBackup bool `json:"is_full_backup"  gorm:"type:tinyint"`
}
