package dbbackup

// LogicBackupDataOption TODO
type LogicBackupDataOption struct {
	// "grant,schema,data"
	DataSchemaGrant string `json:"DataSchemaGrant"`
}

// Cnf the config of dumping backup
type Cnf struct {
	Public        CnfShared        `json:"Public" ini:"Public" validate:"required"`
	BackupClient  CnfBackupClient  `json:"BackupClient" ini:"BackupClient" validate:"required"`
	LogicalBackup CnfLogicalBackup `json:"LogicalBackup" ini:"LogicalBackup" validate:"required"`
	// LogicalLoad          CnfLogicalLoad          `json:"LogicalLoad" ini:"LogicalLoad"`
	PhysicalBackup CnfPhysicalBackup `json:"PhysicalBackup" ini:"PhysicalBackup"`
}

// CnfShared TODO
type CnfShared struct {
	BkBizId         string `ini:"BkBizId"`
	BkCloudId       string `ini:"BkCloudId"`
	BillId          string `ini:"BillId"`
	BackupId        string `ini:"BackupId"`
	ClusterAddress  string `ini:"ClusterAddress"`
	ClusterId       string `ini:"ClusterId"`
	MysqlHost       string `ini:"MysqlHost"`
	MysqlPort       string `ini:"MysqlPort"`
	MysqlUser       string `ini:"MysqlUser"`
	MysqlPasswd     string `ini:"MysqlPasswd"`
	DataSchemaGrant string `ini:"DataSchemaGrant"`
	BackupDir       string `ini:"BackupDir" validate:"required"`
	MysqlRole       string `ini:"MysqlRole"`
	MysqlCharset    string `ini:"MysqlCharset"`
	BackupTimeOut   string `ini:"BackupTimeout" validate:"required,time"`
	BackupType      string `ini:"BackupType"`
	OldFileLeftDay  string `ini:"OldFileLeftDay"`
	// TarSizeThreshold tar file will be split to this package size. MB
	TarSizeThreshold uint64 `ini:"TarSizeThreshold" validate:"required,gte=128"`
	// IOLimitMBPerSec tar or split default io limit, mb/s. 0 means no limit
	IOLimitMBPerSec  int    `ini:"IOLimitMBPerSec"`
	ResultReportPath string `ini:"ResultReportPath"`
	StatusReportPath string `ini:"StatusReportPath"`
}

// CnfBackupClient TODO
type CnfBackupClient struct {
	FileTag          string `ini:"FileTag"`
	RemoteFileSystem string `ini:"RemoteFileSystem"`
	DoChecksum       string `ini:"DoChecksum"`
}

// CnfLogicalBackup the config of logical backup
type CnfLogicalBackup struct {
	// ChunkFilesize Split tables into chunks of this output file size. This value is in MB
	ChunkFilesize   uint64 `ini:"ChunkFilesize"`
	Regex           string `ini:"Regex"`
	Threads         int    `ini:"Threads"`
	DisableCompress bool   `ini:"DisableCompress"`
	FlushRetryCount int    `ini:"FlushRetryCount"`
	DefaultsFile    string `ini:"DefaultsFile"`
	// ExtraOpt other mydumper options string to be appended
	ExtraOpt string `ini:"ExtraOpt"`
}

// CnfPhysicalBackup the config of physical backup
type CnfPhysicalBackup struct {
	// Threads –parallel to copy files
	Threads int `ini:"Threads"`
	// SplitSpeed tar split limit in MB/s, default 300
	SplitSpeed int64 `ini:"SplitSpeed"`
	// Throttle limits the number of chunks copied per second. The chunk size is 10 MB, 0 means no limit
	Throttle     int    `ini:"Throttle"`
	DefaultsFile string `ini:"DefaultsFile" validate:"required,file"`
	// ExtraOpt other xtrabackup options string to be appended
	ExtraOpt string `ini:"ExtraOpt"`
}

// CnfLogicalLoad the config of logical loading
type CnfLogicalLoad struct {
	MysqlHost     string `ini:"MysqlHost"`
	MysqlPort     string `ini:"MysqlPort"`
	MysqlUser     string `ini:"MysqlUser"`
	MysqlPasswd   string `ini:"MysqlPasswd"`
	MysqlCharset  string `ini:"MysqlCharset"`
	MysqlLoadDir  string `ini:"MysqlLoadDir"`
	Threads       int    `ini:"Threads"`
	Regex         string `ini:"Regex"`
	EnableBinlog  bool   `ini:"EnableBinlog"`
	IndexFilePath string `ini:"IndexFilePath" validate:"required"`
	// ExtraOpt other myloader options string to be appended
	ExtraOpt string `json:"ExtraOpt"`
}

// CnfPhysicalLoad the config of physical loading
type CnfPhysicalLoad struct {
	MysqlLoadDir string `ini:"MysqlLoadDir" validate:"required"`
	Threads      int    `ini:"Threads"`
	// CopyBack use copy-back or move-back
	CopyBack      bool   `ini:"CopyBack"`
	IndexFilePath string `ini:"IndexFilePath" validate:"required,file"`
	DefaultsFile  string `ini:"DefaultsFile" validate:"required"`
	// ExtraOpt other xtrabackup recover options string to be appended
	ExtraOpt string `json:"ExtraOpt"`
}
