// Package consts 常量
package consts

import "time"

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
	OSAccount     = "oracle"
	OSGroup       = "oinstall"

	OracleAccount = "oracle"
	OracleGroup   = "oinstall"
	DirModeStr    = "0755"
	DBAGroup      = "dba"
)

// path dirs
const (
	UsrLocal         = "/usr/local"
	PackageCachePath = "/data/dbbak"
	PackageSavePath  = "/data/install"
	Data1Path        = "/data1"
	DataPath         = "/data"
)

// tool path
const (
	DbToolsPath = "/home/mysql/dbtools"
	ZstdBin     = "/home/mysql/dbtools/zstd"
)

// Oracle 安装日志相关常量
const (
	OraInventoryLogDir     = "/u/oraInventory/logs"
	InstallSuccessKeyword  = "The installation of Oracle Database 11g was successful."
	SetupSuccessKeyword    = "Successfully Setup Software."
	LogTailLines           = 200
	DefaultOracleHome      = "/u/ora11g/product/11.2.0/db_1"
	DbRecoveryFileDestSize = 500 * 1024 * 1024 * 1024
	RmanPath               = "/rman"
	ArchPath               = "/arch"
	// GetUserNameSql 获取db用户名
	GetUserNameSql   = "select USERNAME from dba_users where ACCOUNT_STATUS='OPEN' and "
	LogArchiveConfig = "select value from v$parameter where name='log_archive_config'"
	AvailableNumber  = `select min(n) as first_available_n from (
  select to_number(regexp_substr(p.name, '\d+$')) as n
  from v$parameter p
  where p.name like 'log_archive_dest\_%' escape '\'
    and p.name not like '%_state_%'
    and to_number(regexp_substr(p.name, '\d+$')) between 4 and 9
    and (p.value is null or trim(p.value) is null)
  minus
  select d.dest_id as n
  from v$archive_dest d
  where d.dest_id between 4 and 9
    and (d.destination is not null
         or (d.db_unique_name is not null and d.db_unique_name <> 'NONE'))
)`
	// FindDestByDbUniqueName 根据 DB_UNIQUE_NAME 反查已占用的 log_archive_dest_N 编号，用于幂等复用
	FindDestByDbUniqueName = `select dest_id from v$archive_dest
where dest_id between 4 and 9
  and db_unique_name = :1`
	CharacterSet          = "select value from v$nls_parameters where parameter='NLS_CHARACTERSET'"
	InstanceName          = "select instance_name from v$instance"
	RedoLogSize           = "SELECT COUNT(*) AS group_num, MAX(BYTES) AS max_size FROM V$LOG"
	StandbyLogSize        = "SELECT COUNT(*) AS group_num, MAX(BYTES) AS max_size FROM V$STANDBY_LOG"
	DbUniqueName          = "select value from v$parameter where name='db_unique_name'"
	ServiceNames          = "select value from v$parameter where name='service_names'"
	DatabaseRole          = "select database_role from v$database"
	SwitchLogfile         = "alter system switch logfile"
	StatisticListenerPort = 1522
	ListenerPort          = 1521
)

// 与 tnsnames.ora / DG 配置相关的常量与占位符定义，集中管理避免散落在函数体内
const (
	// NetworkAdminSubPath 相对于 ORACLE_HOME 的 tnsnames.ora 所在目录
	NetworkAdminSubPath = "/network/admin/"

	// TnsFilePerm 追加写入 tnsnames.ora 时使用的权限
	TnsFilePerm = 0644

	// TnsPingTimeout 单次 tnsping 命令的超时时间
	TnsPingTimeout = 5 * time.Second

	// TnsPingOKMarker tnsping 输出中表示连通性正常的关键字
	TnsPingOKMarker = "OK ("

	// DgConfigPrefix 用于识别/生成 DG_CONFIG=(...) 字符串的固定前缀（大小写不敏感比对）
	DgConfigPrefix = "DG_CONFIG=("

	// TnsPlaceholderDBUniqueName / Host / Port / OracleSID 是 tnsnames.ora 模板中的占位符
	TnsPlaceholderDBUniqueName = "{{db_unique_name}}"
	TnsPlaceholderHost         = "{{host}}"
	TnsPlaceholderPort         = "{{port}}"
	TnsPlaceholderOracleSID    = "{{oracle_sid}}"
)

// rman_duplicate 脚本/日志相关常量
const (
	// RmanScriptPerm 生成的 rman shell 脚本文件权限
	RmanScriptPerm = 0755

	// RmanScriptTimeout 单次 rman duplicate 执行超时
	RmanScriptTimeout = 24 * time.Hour

	// RmanLogTailLines 失败时截取的日志尾部行数
	RmanLogTailLines = 20

	// RmanTimestampLayout 用于生成脚本/日志文件名的时间戳格式
	RmanTimestampLayout = "20060102150405"

	// RmanScriptNamePattern / RmanLogNamePattern 脚本/日志文件命名模板（Sprintf 使用）
	RmanScriptNamePattern = "rman_duplicate_%s.sh"
	RmanLogNamePattern    = "rman_duplicate_%s.log"

	// RmanPasswordMask 脚本执行完毕后用于替换明文密码的掩码
	RmanPasswordMask = "******"

	// rman 脚本占位符
	RmanPlaceholderPassword        = "{{password}}"
	RmanPlaceholderMaster          = "{{master}}"
	RmanPlaceholderSlave           = "{{slave}}"
	RmanPlaceholderAvailableNumber = "{{available_number}}"

	// LagThresholdSec 延迟阈值（秒）
	LagThresholdSec = 60
)
