package dbbackup

// BackupOptions
// 这个类型被 dbbackup 引用了
// 这样设计感觉不太对, 更合理的应该是把这个类型定义到 dbbackup 代码那边
// 暂时先不改
type BackupOptions struct {
	BackupType  string `json:"BackupType" validate:"required"`
	CrontabTime string `json:"CrontabTime" validate:"required"`
	IgnoreObjs  struct {
		// "mysql,test,db_infobase,information_schema,performance_schema,sys"
		IgnoreDatabases string `json:"ExcludeDatabases"`
		IgnoreTables    string `json:"ExcludeTables"`
	} `json:"Logical"`
	Master logicBackupDataOption `json:"Master" validate:"required"`
	Slave  logicBackupDataOption `json:"Slave"`
}

type logicBackupDataOption struct {
	// "grant,schema,data"
	DataSchemaGrant string `json:"DataSchemaGrant"`
}
