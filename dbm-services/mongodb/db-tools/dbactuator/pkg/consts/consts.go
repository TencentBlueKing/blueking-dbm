// Package consts 常量
package consts

// time layout
const (
	UnixtimeLayout     = "2006-01-02 15:04:05"
	FilenameTimeLayout = "20060102-150405"
	FilenameDayLayout  = "20060102"
)

// account
const (
	MysqlAaccount = "mysql"
	MysqlGroup    = "mysql"
	OSAccount     = "mysql"
	OSGroup       = "mysql"
)

// path dirs
const (
	UsrLocal         = "/usr/local"
	PackageCachePath = "/data/dbbak"
	PackageSavePath  = "/data/install"
	Data1Path        = "/data1"
	DataPath         = "/data"
	DbaReportSaveDir = "/home/mysql/dbareport/"
	ExporterConfDir  = "/home/mysql/.exporter"
)

// tool path
const (
	DbToolsPath = "/home/mysql/dbtools"

	ZstdBin = "/home/mysql/dbtools/zstd"
)

// bk-dbmon path
const (
	BkDbmonPath        = "/home/mysql/bk-dbmon"
	BkDbmonBin         = "/home/mysql/bk-dbmon/bk-dbmon"
	BkDbmonConfFile    = "/home/mysql/bk-dbmon/dbmon-config.yaml"
	BkDbmonPort        = 6677
	BkDbmonHTTPAddress = "127.0.0.1:6677"
)

// backup
const (
	NormalBackupType  = "normal_backup"
	ForeverBackupType = "forever_backup"
	BackupClient      = "/usr/local/bin/backup_client"
)

// payload format
const (
	// PayloadFormatRaw raw
	PayloadFormatRaw = "raw"
	// PayloadFormatBase64 base64
	PayloadFormatBase64 = "base64"
)
