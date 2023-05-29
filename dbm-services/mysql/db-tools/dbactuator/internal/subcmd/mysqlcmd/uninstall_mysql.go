package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// UnInstallMysqlAct TODO
type UnInstallMysqlAct struct {
	*subcmd.BaseOptions
	Service mysql.UnInstallMySQLComp
}

// NewUnInstallMysqlCommand TODO
func NewUnInstallMysqlCommand() *cobra.Command {
	act := UnInstallMysqlAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "uninstall",
		Short:   "下架MySQL",
		Example: fmt.Sprintf(`dbactuator mysql uninstall %s`, subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			if act.RollBack {
				return
			}
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Init TODO
func (d *UnInstallMysqlAct) Init() (err error) {
	logger.Info("UnInstallMysqlAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.Init()
}

// Run TODO
func (d *UnInstallMysqlAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "停止数据库实例",
			Func:    d.Service.ShutDownMySQLD,
		},
		{
			FunName: "清理机器数据&日志目录",
			Func:    d.Service.ClearMachine,
		},
		{
			FunName: "清理可能残存的mysql相关进程",
			Func:    d.Service.KillDirtyProcess,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("uninstall mysql successfully")
	return nil
}
