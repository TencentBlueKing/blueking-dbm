package proxycmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql_proxy"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

type StandardizeProxyAct struct {
	*subcmd.BaseOptions
	Service mysql_proxy.StandardizeProxyComp
}

const StandardizeProxy = `standardize-proxy`

func NewStandardizeProxyCommand() *cobra.Command {
	act := StandardizeProxyAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   StandardizeProxy,
		Short: "standard proxy commands",
		Example: fmt.Sprintf(
			`dbactuator proxy %s %s %s`,
			StandardizeProxy,
			subcmd.CmdBaseExampleStr,
			subcmd.ToPrettyJson(act.Service.Example()),
		),
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
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Params)
	return nil
}

func (c *StandardizeProxyAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "清理旧 crontab",
			Func:    c.Service.ClearOldCrontab,
		},
		{
			FunName: "标准化白名单",
			Func:    c.Service.AddUser,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("标准化 proxy 完成")
	return nil
}
