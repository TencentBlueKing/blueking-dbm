package spiderctlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// UnInstallSpiderCtlAct TODO
type UnInstallSpiderCtlAct struct {
	*subcmd.BaseOptions
	Service mysql.UnInstallMySQLComp
}

// NewUnInstallSpiderCtlCommand TODO
func NewUnInstallSpiderCtlCommand() *cobra.Command {
	act := UnInstallSpiderCtlAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "uninstall",
		Short:   "下架Spider-ctl",
		Example: fmt.Sprintf(`dbactuator spiderctl uninstall %s`, subcmd.CmdBaseExampleStr),
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
func (d *UnInstallSpiderCtlAct) Init() (err error) {
	logger.Info("UnInstallSpiderCtlAct Init")
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.Init()
}

// Run TODO
func (d *UnInstallSpiderCtlAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "停止Spider-ctl实例",
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
	logger.Info("uninstall spider-ctl successfully")
	return nil
}
