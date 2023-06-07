package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// BackupDatabaseTable TODO
const BackupDatabaseTable = "backup-database-table"

// BackupDatabaseTableAct TODO
type BackupDatabaseTableAct struct {
	*subcmd.BaseOptions
	Payload mysql.BackupDatabaseTableComp
}

// NewBackupDatabaseTableCommand TODO
func NewBackupDatabaseTableCommand() *cobra.Command {
	act := BackupDatabaseTableAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     BackupDatabaseTable,
		Short:   "备库库表",
		Example: fmt.Sprintf(`dbactuator mysql %s %s`, BackupDatabaseTable, subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validate TODO
func (c *BackupDatabaseTableAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

// Init TODO
func (c *BackupDatabaseTableAct) Init() (err error) {
	if err = c.DeserializeAndValidate(&c.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return
}

// Run TODO
func (c *BackupDatabaseTableAct) Run() (err error) {
	defer util.LoggerErrorStack(logger.Error, err)
	// subcmd.Steps 顺序执行，某个步骤error，剩下步骤不执行
	steps := subcmd.Steps{
		{
			FunName: "Precheck",
			Func:    c.Payload.Precheck,
		},
		{
			FunName: "CreateBackupConfigFile",
			Func:    c.Payload.CreateBackupConfigFile,
		},
		{
			FunName: "DoBackup",
			Func:    c.Payload.DoBackup,
		},
		{
			FunName: "OutputBackupInfo",
			Func:    c.Payload.OutputBackupInfo,
		},
	}
	if err = steps.Run(); err != nil {
		return err
	}
	logger.Info("备份成功")
	return nil
}
