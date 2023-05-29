package proxycmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql_proxy"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// RestratProxyAct TODO
type RestratProxyAct struct {
	*subcmd.BaseOptions
	Service mysql_proxy.RestartMySQLProxyComp
}

// NewRestartProxyCommand TODO
func NewRestartProxyCommand() *cobra.Command {
	act := RestratProxyAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   "restart",
		Short: "重启Proxy",
		Example: fmt.Sprintf(
			`dbactuator proxy restart %s %s`, subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.Service.Example()),
		),
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
func (d *RestratProxyAct) Init() (err error) {
	if err = d.Deserialize(&d.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate failed, %v", err)
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return
}

// Run TODO
func (d *RestratProxyAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "重启proxy",
			Func:    d.Service.RestartProxy,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("restart proxy successfully")
	return nil
}
