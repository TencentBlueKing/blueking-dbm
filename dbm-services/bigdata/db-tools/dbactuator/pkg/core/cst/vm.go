package cst

const (
	// DefaultVMEnv vm环境目录
	DefaultVMEnv = "/data/vmenv"
	// DefaultVMLogDir vm日志目录
	DefaultVMLogDir = "/data/vmlog"
	// DefaultVMDataDir vm数据目录
	DefaultVMDataDir = "/data/vmdata"
	// DefaultVMSupervisorConf TODO
	DefaultVMSupervisorConf = DefaultVMEnv + "/supervisor/conf"
	// DefaultVMSupervisorDir supervisor的目录
	DefaultVMSupervisorDir = DefaultVMEnv + "/supervisor"
	// VMHome TODO
	VMHome = DefaultVMEnv + "/vm"
	// VMStorage TODO
	VMStorage = "vmstorage"
	// VMSelect TODO
	VMSelect = "vmselect"
	// VMInsert TODO
	VMInsert = "vminsert"
	// VMAuth TODO
	VMAuth = "vmauth"
	// VMAuthInsert TODO
	VMAuthInsert = "vmauth_insert"
	// VMAuthSelect TODO
	VMAuthSelect = "vmauth_select"
	// StartCommand TODO
	StartCommand = "supervisorctl start all"
	// StopCommand TODO
	StopCommand = "supervisorctl stop all"
	// VMAuthInsertConf TODO
	VMAuthInsertConf = DefaultVMEnv + "/vm/" + "vmauth_insert.yml"
	// VMAuthSelectConf TODO
	VMAuthSelectConf = DefaultVMEnv + "/vm/" + "vmauth_select.yml"
)
