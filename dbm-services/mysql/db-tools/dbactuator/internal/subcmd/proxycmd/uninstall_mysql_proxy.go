package proxycmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql_proxy"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

// UnInstallProxyAct TODO
type UnInstallProxyAct struct {
	*subcmd.BaseOptions
	Service mysql_proxy.UnInstallMySQLProxyComp
}

// NewUnInstallProxyCommand TODO
func NewUnInstallProxyCommand() *cobra.Command {
	act := UnInstallProxyAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "uninstall",
		Short:   "下架Proxy",
		Example: fmt.Sprintf(`dbactuator proxy uninstall %s`, subcmd.CmdBaseExampleStr),
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
func (d *UnInstallProxyAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.Init()
}

// Run TODO
func (d *UnInstallProxyAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "下架proxy",
			Func:    d.Service.UnInstallProxy,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("uninstall proxy successfully")
	return nil
}
