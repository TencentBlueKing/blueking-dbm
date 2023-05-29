package cst

const (
	// UsrLocal TODO
	UsrLocal = "/usr/local"
	// MysqldInstallPath TODO
	MysqldInstallPath = "/usr/local/mysql"
	// DefaultMysqlLogRootPath TODO
	DefaultMysqlLogRootPath = "/data" // 默认存放mysql日志的根路径
	// AlterNativeMysqlLogRootPath TODO
	AlterNativeMysqlLogRootPath = "/data1" // 备选路径
	// DefaultMysqlLogBasePath TODO
	DefaultMysqlLogBasePath = "mysqllog"
	// DefaultMysqlDataRootPath TODO
	DefaultMysqlDataRootPath = "/data1" // 默认存放mysql数据的根路径
	// AlterNativeMysqlDataRootPath TODO
	AlterNativeMysqlDataRootPath = "/data"
	// DefaultMysqlDataBasePath TODO
	DefaultMysqlDataBasePath = "mysqldata"
	// DefaultBackupBasePath TODO
	DefaultBackupBasePath = "dbbak"
	// DefaultMycnfRootPath 默认配置文件路径
	DefaultMycnfRootPath = "/etc"
	// DefaultMyCnfName TODO
	DefaultMyCnfName = "/etc/my.cnf"
	// DefaultSocketName TODO
	DefaultSocketName = "mysql.sock"
	// DefaultMySQLPort TODO
	DefaultMySQLPort = 3306
	// RelayLogFileMatch TODO
	RelayLogFileMatch = `(.*)/relay-log.bin`
	// BinLogFileMatch TODO
	BinLogFileMatch = `(.*)/binlog\d*.bin`
	// DatadirMatch TODO
	DatadirMatch = `(.*)/mysqldata/\d+$`
	// MysqlOsUserName TODO
	MysqlOsUserName = "mysql"
	// MysqlOsUserGroup TODO
	MysqlOsUserGroup = "mysql"
	// MySQLClientPath TODO
	MySQLClientPath = "/usr/local/mysql/bin/mysql"
)

const (
	// MIR_MASTER TODO
	// MIR : meta inner role
	MIR_MASTER = "master"
	// MIR_SLAVE TODO
	MIR_SLAVE = "slave"
	// MIR_REPEATER TODO
	MIR_REPEATER = "repeater"
	// MIR_ORPHAN TODO
	MIR_ORPHAN = "orphan" // 单节点集群的实例角色
)

// backup .info 中的 BackupRole
const (
	BackupRoleMaster = "MASTER"
	BackupRoleSlave  = "SLAVE"
)

// 规范的 备份类型名
const (
	TypeGZTAB = "gztab"
	TypeXTRA  = "xtra"
)

// LooseBackupTypes 不规范的 备份类型名，不区分大小写
// dbbackup.conf 中的 backup_type
var LooseBackupTypes = map[string][]string{
	TypeGZTAB: []string{"GZTAB"},
	TypeXTRA:  []string{"XTRA", "xtrabackup"},
}
