package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

type GenPeripheralToolsConfigAct struct {
	*subcmd.BaseOptions
	Service peripheraltools.GenConfig
}

const GenPeripheralToolsConfig = `gen-peripheraltools-config`

func NewGenPeripheralToolsConfigCommand() *cobra.Command {
	act := GenPeripheralToolsConfigAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   GenPeripheralToolsConfig,
		Short: "Generate peripheraltools config",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			GenPeripheralToolsConfig, subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example())),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

func (c *GenPeripheralToolsConfigAct) Validate() error {
	return c.BaseOptions.Validate()
}

func (c *GenPeripheralToolsConfigAct) Init() error {
	if err := c.Deserialize(&c.Service.Param); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Param)
	return nil
}

func (c *GenPeripheralToolsConfigAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "生成周边配置",
			Func:    c.Service.Run,
		},
	}
	if err := steps.Run(); err != nil {
		logger.Error(err.Error())
		return err
	}

	logger.Info("配置生成完成")
	return nil
}
