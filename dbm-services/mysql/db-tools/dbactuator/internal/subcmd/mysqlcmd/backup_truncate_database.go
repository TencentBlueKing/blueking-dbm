package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// BackupTruncateDatabaseAct 库表删除
type BackupTruncateDatabaseAct struct {
	*subcmd.BaseOptions
	Service mysql.BackupTruncateDatabaseComp
}

const (
	// BackupTruncateDatabase 命令常量
	BackupTruncateDatabase = "backup-truncate-database"
)

// NewBackupTruncateDatabaseCommand 子命令定义
func NewBackupTruncateDatabaseCommand() *cobra.Command {
	act := BackupTruncateDatabaseAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	cmd := &cobra.Command{
		Use:     BackupTruncateDatabase,
		Short:   "备份清档库",
		Example: fmt.Sprintf(`dbactuator mysql %s %s`, BackupTruncateDatabase, subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validate 参数验证
func (c *BackupTruncateDatabaseAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

// Init 初始化
func (c *BackupTruncateDatabaseAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run 运行
func (c *BackupTruncateDatabaseAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "Precheck",
			Func:    c.Service.Precheck,
		},
		{
			FunName: "Init",
			Func: func() error {
				return c.Service.Init(c.Uid)
			},
		},
		{
			FunName: "ReadBackupConf",
			Func:    c.Service.ReadBackupConf,
		},
		{
			FunName: "DumpSchema",
			Func:    c.Service.DumpSchema,
		},
		{
			FunName: "ModifyFile",
			Func:    c.Service.ModifyFile,
		},
		{
			FunName: "CleanNewDB",
			Func:    c.Service.CleanNewDB,
		},
		{
			FunName: "ImportSchema",
			Func:    c.Service.ImportSchema,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("备份成功")
	return nil
}
