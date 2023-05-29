package dbloader

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/dbbackup"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
)

// LoaderUtil TODO
type LoaderUtil struct {
	Client string `json:"client" validate:"required"`
	// 恢复本地的目标实例
	TgtInstance native.InsObject `json:"tgt_instance"`
	IndexObj    *dbbackup.BackupIndexFile

	// 不写 binlog -without-binlog: set sql_log_bin=0
	WithOutBinlog bool   `json:"withoutBinlog"`
	IndexFilePath string `json:"index_file_path" validate:"required"`
	LoaderDir     string `json:"loader_dir"`
	TaskDir       string `json:"taskDir"`

	// 上层传递过来的filter，不包括系统过滤库
	Databases        []string `json:"databases"`
	Tables           []string `json:"tables"`
	ExcludeDatabases []string `json:"exclude_databases"`
	ExcludeTables    []string `json:"exclude_tables"`

	// 内部检查相关
	cfgFilePath string
	doDr        bool
}

/*
func (l *LoaderUtil) String() string {
	return fmt.Sprintf("LoaderUtil{Client:%s, TgtInstance:%v, IndexObj:%+v, IndexFilePath:%s, LoaderDir:%s, TaskDir:%s}",
		l.Client, l.TgtInstance, l.IndexObj, l.IndexFilePath, l.LoaderDir, l.TaskDir)
}
*/

// LoaderOpt TODO
type LoaderOpt struct {
	// 恢复哪些 db，当前只对 逻辑恢复有效
	Databases       []string `json:"databases"`
	Tables          []string `json:"tables"`
	IgnoreDatabases []string `json:"ignore_databases"`
	IgnoreTables    []string `json:"ignore_tables"`

	RecoverPrivs bool `json:"recover_privs"`
	// 在指定时间点回档场景才需要，是否恢复 binlog。在 doSlave 场景，是不需要 recover_binlog。这个选项是控制下一步恢复binlog的行为
	// 当 recover_binlog 时，要确保实例的所有库表结构都恢复。在逻辑回档场景，只回档部分库表数据时，依然要恢复所有表结构
	WillRecoverBinlog bool `json:"recover_binlog"`
	// 在库表级定点回档时有用，如果是 statement/mixed 格式，导入数据时需要全部导入；
	// 如果是 row，可只导入指定库表数据, 在 recover-binlog 时可指定 quick_mode=true 也恢复指定库表 binlog
	SourceBinlogFormat string `json:"source_binlog_format" enums:",ROW,STATEMENT,MIXED"`
}
