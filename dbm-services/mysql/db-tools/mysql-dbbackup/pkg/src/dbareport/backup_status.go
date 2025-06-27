package dbareport

// BackupStatus the status of backup
type BackupStatus struct {
	Status string `json:"status"`

	BackupId      string `json:"backup_id"`
	BackupType    string `json:"backup_type" `
	ClusterId     int    `json:"cluster_id"`
	ClusterDomain string `json:"cluster_domain"`
	BackupHost    string `json:"backup_host" `
	BackupPort    int    `json:"backup_port" `
	MysqlRole     string `json:"mysql_role" `
	// ShardValue 分片 id，仅 spider 有用
	ShardValue      int    `json:"shard_value" `
	BillId          string `json:"bill_id" `
	BkBizId         int    `json:"bk_biz_id" `
	DataSchemaGrant string `json:"data_schema_grant" `
	// IsFullBackup 是否包含数据的全备
	IsFullBackup bool `json:"is_full_backup" `
}
