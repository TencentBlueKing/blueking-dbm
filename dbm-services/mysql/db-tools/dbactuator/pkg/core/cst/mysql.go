package cst

import "fmt"

const (
	// UsrLocal 系统路径
	UsrLocal = "/usr/local"
	// MysqldInstallPath mysql/spider 二进制路径
	MysqldInstallPath = "/usr/local/mysql"
	// TdbctlInstallPath tdbctl 二进制路径
	TdbctlInstallPath = "/usr/local/tdbctl"
	// DefaultMysqlLogRootPath 默认存放mysql日志的根路径
	DefaultMysqlLogRootPath = "/data"
	// AlterNativeMysqlLogRootPath 备选路径
	AlterNativeMysqlLogRootPath = "/data1"
	// DefaultMysqlLogBasePath  mysql 日志路径
	DefaultMysqlLogBasePath = "mysqllog"
	// DefaultMysqlDataRootPath 默认存放mysql数据的根路径
	DefaultMysqlDataRootPath = "/data1"
	// AlterNativeMysqlDataRootPath 默认存放mysql数据的根路径
	AlterNativeMysqlDataRootPath = "/data"
	// DefaultMysqlDataBasePath 默认数据路径
	DefaultMysqlDataBasePath = "mysqldata"
	// DefaultBackupBasePath 备份路径
	DefaultBackupBasePath = "dbbak"
	// DefaultMycnfRootPath 默认配置文件路径
	DefaultMycnfRootPath = "/etc"
	// DefaultMyCnfName 默认配置文件
	DefaultMyCnfName = "/etc/my.cnf"
	// DefaultSocketName 默认 sock 文件
	DefaultSocketName = "mysql.sock"
	// DefaultMySQLPort 默认端口
	DefaultMySQLPort = 3306
	// RelayLogFileMatch relaylog 模式
	RelayLogFileMatch = `(.*)/relay-log.bin`
	// BinLogFileMatch binlog 模式
	BinLogFileMatch = `(.*)/binlog\d*.bin`
	// ReBinlogFilename binlog 文件名
	ReBinlogFilename = `binlog\d*\.\d+$`
	// DatadirMatch 实例数据目录模式
	DatadirMatch = `(.*)/mysqldata/\d+$`
	// MysqlOsUserName 系统帐号
	MysqlOsUserName = "mysql"
	// MysqlOsUserGroup 系统组
	MysqlOsUserGroup = "mysql"
	// MySQLClientPath mysqlclient 路径
	MySQLClientPath = "/usr/local/mysql/bin/mysql"
	// ChecksumInstallPath check path
	ChecksumInstallPath = "/home/mysql/checksum"
	// DbbackupGoInstallPath install path
	DbbackupGoInstallPath = "/home/mysql/dbbackup-go"
	// DBAToolkitPath dba 工具集
	DBAToolkitPath = "/home/mysql/dba-toolkit"
	// MySQLCrondInstallPath crond安装路径
	MySQLCrondInstallPath = "/home/mysql/mysql-crond"
	// MySQLMonitorInstallPath 监控安装路径
	MySQLMonitorInstallPath = "/home/mysql/mysql-monitor"
	// MysqlRotateBinlogInstallPath rotate binlog
	MysqlRotateBinlogInstallPath = "/home/mysql/mysql-rotatebinlog"
	// DBAReportBase 上报根目录
	DBAReportBase = "/home/mysql/dbareport"
)

const (
	// MIR_MASTER meta inner role
	MIR_MASTER = "master"
	// MIR_SLAVE inner role slave
	MIR_SLAVE = "slave"
	// MIR_REPEATER inner role repeater
	MIR_REPEATER = "repeater"
	// MIR_ORPHAN inner role orphan
	MIR_ORPHAN = "orphan" // 单节点集群的实例角色
)

const (
	// RoleRemoteMaster tendbcluster remote master
	RoleRemoteMaster = "remote_master"
	// RoleRemoteSlave tendbcluster remote slave
	RoleRemoteSlave = "remote_slave"
	// RoleSpiderMaster tendbcluster spider-proxy master
	RoleSpiderMaster = "spider_master"
	// RoleSpiderSlave tendbcluster spider-proxy slave
	RoleSpiderSlave = "spider_slave"
	// RoleSpiderMnt tendbcluster maintain node
	RoleSpiderMnt = "spider_mnt"

	RoleTdbctl = "spider_tdbctl"

	// RoleBackendMaster tendbha remote master
	RoleBackendMaster = "backend_master"
	// RoleBackendSlave tendbha remote slave
	RoleBackendSlave = "backend_slave"
)

const (
	TendbCluster = "tendbcluster"
	TendbHA      = "tendbha"
)

// backup .info 中的 BackupRole
const (
	BackupRoleMaster   = "MASTER"
	BackupRoleSlave    = "SLAVE"
	BackupRoleRepeater = "REPEATER"
	// BackupRoleOrphan 单节点备份行为
	BackupRoleOrphan       = "ORPHAN"
	BackupRoleSpiderMaster = "SPIDER_MASTER"
	BackupRoleSpiderSlave  = "SPIDER_SLAVE"
)

// 规范的 备份类型名
const (
	TypeGZTAB = "gztab"
	TypeXTRA  = "xtra"
)

// LooseBackupTypes 不规范的 备份类型名，不区分大小写
// dbbackup.conf 中的 backup_type
var LooseBackupTypes = map[string][]string{
	TypeGZTAB: {"GZTAB"},
	TypeXTRA:  {"XTRA", "xtrabackup"},
}

// DbbackupConfigFilename 日常备份配置文件没
func DbbackupConfigFilename(port int) string {
	return fmt.Sprintf("dbbackup.%d.ini", port)
}

const (
	// BackupTypeLogical 备份类型
	BackupTypeLogical = "logical" // mydumper
	// BackupTypePhysical TODO
	BackupTypePhysical = "physical"
)

// MySQLCrondPort crond 端口
const MySQLCrondPort = 9999
