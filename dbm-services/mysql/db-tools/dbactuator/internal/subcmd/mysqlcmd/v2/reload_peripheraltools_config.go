package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

type ReloadPeripheralToolsConfigAct struct {
	*subcmd.BaseOptions
	Service peripheraltools.Reload
}

const ReloadPeripheralToolsConfig = "reload-peripheraltools-config"

func NewReloadPeripheralToolsConfigCommand() *cobra.Command {
	act := ReloadPeripheralToolsConfigAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   ReloadPeripheralToolsConfig,
		Short: "ReloadPeripheralToolsConfig",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			ReloadPeripheralToolsConfig, subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example())),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

func (c *ReloadPeripheralToolsConfigAct) Validate() error {
	return c.BaseOptions.Validate()
}

func (c *ReloadPeripheralToolsConfigAct) Init() error {
	if err := c.Deserialize(&c.Service.Param); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Param)
	return nil
}

func (c *ReloadPeripheralToolsConfigAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "重载周边配置",
			Func:    c.Service.Run,
		},
	}
	if err := steps.Run(); err != nil {
		logger.Error(err.Error())
		return err
	}

	logger.Info("配置重载完成")
	return nil
}
