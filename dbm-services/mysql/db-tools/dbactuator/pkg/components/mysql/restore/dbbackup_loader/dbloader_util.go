package dbbackup_loader

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/pkg/errors"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql/dbbackup"
	"dbm-services/mysql/db-tools/dbactuator/pkg/native"
	"dbm-services/mysql/db-tools/mysql-dbbackup/pkg/src/spider"
)

// LoaderUtil myloader / xtrabackup 恢复 通用参数
type LoaderUtil struct {
	Client string `json:"client" validate:"required"`
	// 恢复本地的目标实例
	TgtInstance native.InsObject `json:"tgt_instance"`
	IndexObj    *dbbackup.BackupIndexFile

	// EnableBinlog 导入数据时是否写binlog，默认不启用 (set sql_log_bin=0)
	EnableBinlog  bool   `json:"enable_binlog"`
	InitCommand   string `json:"init_command"`
	IndexFilePath string `json:"index_file_path" validate:"required"`
	// LoaderDir 备份解压后的目录
	LoaderDir     string `json:"loader_dir"`
	TaskDir       string `json:"task_dir"`
	BackupDir     string `json:"backup_dir"`
	RecoverGrants bool   `json:"recover_grants"`

	// 上层传递过来的filter，不包括系统过滤库
	Databases        []string `json:"databases"`
	Tables           []string `json:"tables"`
	ExcludeDatabases []string `json:"exclude_databases"`
	ExcludeTables    []string `json:"exclude_tables"`

	LogDir string `json:"-"`
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
	InitCommand       string `json:"init_command"`
	WillRecoverBinlog bool   `json:"recover_binlog"`
	// 在库表级定点回档时有用，如果是 statement/mixed 格式，导入数据时需要全部导入；
	// 如果是 row，可只导入指定库表数据, 在 recover-binlog 时可指定 quick_mode=true 也恢复指定库表 binlog
	SourceBinlogFormat string `json:"source_binlog_format" enums:",ROW,STATEMENT,MIXED"`
}

func recoverGrant(inst native.InsObject, privFiles []string, backupDir string) (err error) {
	if len(privFiles) == 0 {
		return errors.Errorf("no priv file found in %s", backupDir)
	}
	logger.Info("recover grants for port %d from sql file: %s", inst.Port, privFiles)
	comp := mysql.FastExecuteSqlComp{
		GeneralParam: &components.GeneralParam{
			RuntimeAccountParam: components.RuntimeAccountParam{
				MySQLAccountParam: components.MySQLAccountParam{
					MySQLAdminAccount: components.MySQLAdminAccount{
						AdminUser: inst.User, AdminPwd: inst.Pwd,
					},
				},
			},
		},
		Params: mysql.FastExecuteSqlParam{
			Host:       inst.Host,
			Port:       inst.Port,
			Socket:     inst.Socket,
			Force:      true,
			OnDatabase: "mysql",
			FileDir:    backupDir,
			SqlFiles:   privFiles,
		},
	}
	if err = comp.Init(); err != nil {
		return errors.WithMessagef(err, "restore-dr recover grants")
	}
	if err = comp.Run(); err != nil {
		return errors.WithMessagef(err, "restore-dr recover grants")
	}
	return nil
}

// update old backup tasks to quit
// 对于 spider remote，恢复完数据后 global_backup 可能包含废弃的 备份任务，这里把状态改成 quit 避免任务被重新发起
func (l *LoaderUtil) commonPostLoad(backupDir string) error {
	dbWorker, err := l.TgtInstance.Conn()
	if err != nil {
		return err
	}
	defer dbWorker.Stop()

	logger.Info("commonPostLoad: repair data for table global_backup")
	sqlStr := fmt.Sprintf(`update infodba_schema.global_backup SET BackupStatus ='%s' where Host ='%s' and Port =%d`,
		spider.StatusQuit, l.TgtInstance.Host, l.TgtInstance.Port)
	if _, err = dbWorker.ExecMore([]string{"set session sql_log_bin=off", sqlStr}); err != nil {
		logger.Warn("fail to repair data for table global_backup. ignore %s", err.Error())
	}

	// 清理备份下载目录
	logger.Info("commonPostLoad: remove old backup file in %s", backupDir)
	for _, oldFile := range l.IndexObj.GetTarFileList("") {
		oldFile = filepath.Join(backupDir, oldFile)
		//logger.Info("remove old backup file: %s", oldFile)
		_ = os.Remove(oldFile)
	}
	return nil
}
