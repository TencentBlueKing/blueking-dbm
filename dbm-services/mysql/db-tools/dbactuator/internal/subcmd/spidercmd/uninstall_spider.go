package spidercmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// UnInstallSpiderAct TODO
type UnInstallSpiderAct struct {
	*subcmd.BaseOptions
	Service mysql.UnInstallMySQLComp
}

// NewUnInstallSpiderCommand TODO
func NewUnInstallSpiderCommand() *cobra.Command {
	act := UnInstallSpiderAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "uninstall",
		Short:   "下架Spider",
		Example: fmt.Sprintf(`dbactuator spider uninstall %s`, subcmd.CmdBaseExampleStr),
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
func (d *UnInstallSpiderAct) Init() (err error) {
	logger.Info("UnInstallSpiderAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.Init()
}

// Run TODO
func (d *UnInstallSpiderAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "停止Spider实例",
			Func:    d.Service.ShutDownMySQLD,
		},
		{
			FunName: "清理机器数据&日志目录",
			Func:    d.Service.ClearMachine,
		},
		{
			FunName: "清理可能残存的spider相关进程",
			Func:    d.Service.KillDirtyProcess,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("uninstall spider successfully")
	return nil
}
