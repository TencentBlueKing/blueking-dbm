package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

const InitCommonConfigCommand = `init-common-config`

type InitCommonConfigAct struct {
	*subcmd.BaseOptions
	Service peripheraltools.InitCommonConfig
}

func NewInitCommonConfigCommand() *cobra.Command {
	act := InitCommonConfigAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   InitCommonConfigCommand,
		Short: "Initialize the Nginx addresses for peripheral",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			InitCommonConfigCommand, subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example())),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

func (c *InitCommonConfigAct) Validate() error {
	return c.BaseOptions.Validate()
}

func (c *InitCommonConfigAct) Init() error {
	if err := c.Deserialize(&c.Service.Param); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}

	logger.Info("extend params: %s", c.Service.Param)
	return nil
}

func (c *InitCommonConfigAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "初始化公共配置",
			Func:    c.Service.Run,
		},
	}
	if err := steps.Run(); err != nil {
		logger.Error(err.Error())
		return err
	}

	logger.Info("初始化公共配置")
	return nil
}
