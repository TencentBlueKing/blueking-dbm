package mysqlcmd

import (
	"github.com/spf13/cobra"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
)

type StandardizeProxyAct struct {
	*subcmd.BaseOptions
	Payload mysql.StandardizeProxyComp
}

const (
	StandardizeProxy = "standardize-proxy"
)

func NewStandardizeProxyCommand() *cobra.Command {
	act := StandardizeProxyAct{
		BaseOptions: subcmd.GBaseOptions,
	}

	cmd := &cobra.Command{
		Use:   StandardizeProxy,
		Short: "接管 tendbha 接入层",

		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}

	return cmd
}

func (c *StandardizeProxyAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

func (c *StandardizeProxyAct) Init() (err error) {
	//if err = c.Deserialize(&c.Payload.Params); err != nil {
	//	logger.Error("DeserializeAndValidate err %s", err.Error())
	//	return err
	//}
	//c.Payload.GeneralParam = subcmd.GeneralRuntimeParam
	//logger.Info("extend params: %s", c.Payload.Params)
	return nil
}

func (c *StandardizeProxyAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "清理就系统crontab",
			Func:    c.Payload.ClearOldCrontab,
		},
	}

	if err := steps.Run(); err != nil {
		logger.Error("run adopt scr tendbha proxy failed: %s", err.Error())
		return err
	}
	logger.Info("接管tendbha接入层完成")
	return nil
}
