package cst

const (
	// DefaultVMEnv vm环境目录
	DefaultVMEnv = "/data/vmenv"
	// DefaultVMLogDir vm日志目录
	DefaultVMLogDir = "/data/vmlog"

	// DefaultVMSupervisorConf TODO
	DefaultVMSupervisorConf = DefaultVMEnv + "/supervisor/conf"

	// VMStorage TODO
	VMStorage = "vmstorage"
	// VMSelect TODO
	VMSelect = "vmselect"
	// VMInsert TODO
	VMInsert = "vminsert"

	// StartCommand TODO
	StartCommand = "supervisorctl start all"

	// StopCommand TODO
	StopCommand = "supervisorctl stop all"
)
