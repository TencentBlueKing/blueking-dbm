// Package parsecnf TODO
package parsecnf

import (
	"fmt"
	"strings"

	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/cst"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/go-pubpkg/cmutil"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/common"
)

// CnfShared the shared config
type CnfShared struct {
	BkBizId        string `ini:"BkBizId" validate:"required"`
	BkCloudId      string `ini:"BkCloudId"`
	BillId         string `ini:"BillId"`
	BackupId       string `ini:"BackupId"`
	ClusterId      string `ini:"ClusterId"`
	ClusterAddress string `ini:"ClusterAddress"`
	ShardValue     int    `ini:"ShardValue"` // 分片 id，仅 spider 有用
	MysqlHost      string `ini:"MysqlHost" validate:"required,ip"`
	MysqlPort      string `ini:"MysqlPort" validate:"required"`
	MysqlUser      string `ini:"MysqlUser" validate:"required"`
	MysqlPasswd    string `ini:"MysqlPasswd"`
	// DataSchemaGrant what to backup, comma separated, valid enums values: data,grant,priv,all
	DataSchemaGrant string `ini:"DataSchemaGrant" validate:"required"`
	BackupDir       string `ini:"BackupDir" validate:"required"`
	MysqlRole       string `ini:"MysqlRole" validate:"required"` // ,oneof=master slave"`
	MysqlCharset    string `ini:"MysqlCharset"`
	// BackupTimeOut 备份时间阈值，格式 09:00:01
	BackupTimeOut string `ini:"BackupTimeout"`
	BackupType    string `ini:"BackupType" validate:"required"` // ,oneof=logical physical"
	// OldFileLeftDay will remove old backup files before the days
	OldFileLeftDay int `ini:"OldFileLeftDay"`
	// TarSizeThreshold tar file will be split to this package size. MB
	TarSizeThreshold uint64 `ini:"TarSizeThreshold" validate:"required,gte=128"`
	// IOLimitMBPerSec tar or split default io limit, mb/s. 0 means no limit
	IOLimitMBPerSec  int    `ini:"IOLimitMBPerSec"`
	ResultReportPath string `ini:"ResultReportPath" validate:"required"`
	StatusReportPath string `ini:"StatusReportPath" validate:"required"`

	cnfFilename string
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

// CnfBackupClient the config of backupclient
type CnfBackupClient struct {
	Enable           bool   `ini:"Enable"`
	FileTag          string `ini:"FileTag"`
	RemoteFileSystem string `ini:"RemoteFileSystem"`
	DoChecksum       bool   `ini:"DoChecksum"`
}

// Cnf the config of dumping backup
type Cnf struct {
	Public         CnfShared         `ini:"Public"`
	BackupClient   CnfBackupClient   `ini:"BackupClient"`
	LogicalBackup  CnfLogicalBackup  `ini:"LogicalBackup"`
	LogicalLoad    CnfLogicalLoad    `ini:"LogicalLoad"`
	PhysicalBackup CnfPhysicalBackup `ini:"PhysicalBackup"`
	PhysicalLoad   CnfPhysicalLoad   `ini:"PhysicalLoad"`
}

/*
// LogicalBackupCnf Logical Backup Cnf
type LogicalBackupCnf struct {
	Public        CnfShared        `ini:"Public" validate:"required"`
	LogicalBackup CnfLogicalBackup `ini:"LogicalBackup" validate:"required"`
}

// LogicalLoadCnf Logical Load Cnf
type LogicalLoadCnf struct {
	LogicalBackup CnfLogicalBackup `ini:"LogicalBackup" validate:"required"`
}

// PhysicalBackupCnf Physical Backup Cnf
type PhysicalBackupCnf struct {
	Public         CnfShared         `ini:"Public" validate:"required"`
	PhysicalBackup CnfPhysicalBackup `ini:"PhysicalBackup" validate:"required"`
}

// PhysicalLoadCnf Physical Load Cnf
type PhysicalLoadCnf struct {
	PhysicalLoad CnfPhysicalLoad `ini:"PhysicalLoad" validate:"required"`
}
*/

// ParseDataSchemaGrant Check whether data|schema|grant is backed up
func (cnf *CnfShared) ParseDataSchemaGrant() error {
	valueAllowed := []string{cst.BackupGrant, cst.BackupSchema, cst.BackupData, cst.BackupAll}
	arr := strings.Split(cnf.DataSchemaGrant, ",")
	set := make(map[string]struct{}, len(arr))
	for _, v := range arr {
		v = strings.ToLower(strings.TrimSpace(v))
		if !cmutil.StringsHas(valueAllowed, v) {
			return fmt.Errorf("the part of param DataSchemaGrant [%s] is wrong", v)
		}
		set[v] = struct{}{}
	}
	if _, found := set[cst.BackupData]; found {
		common.BackupData = true
	}
	if _, found := set[cst.BackupSchema]; found {
		common.BackupSchema = true
	}
	if _, found := set[cst.BackupGrant]; found {
		common.BackupGrant = true
	}
	if _, found := set[cst.BackupAll]; found {
		// all is alias to 'grant,schema,data'
		common.BackupGrant = true
		common.BackupData = true
		common.BackupSchema = true
	}

	if !common.BackupData && !common.BackupSchema && !common.BackupGrant {
		return fmt.Errorf("need to backup at least one of %v", valueAllowed)
	}

	return nil
}

// GetCnfFileName TODO
func (cnf *CnfShared) GetCnfFileName() string {
	return cnf.cnfFilename
}

// SetCnfFileName TODO
func (cnf *CnfShared) SetCnfFileName(filename string) {
	cnf.cnfFilename = filename
}
