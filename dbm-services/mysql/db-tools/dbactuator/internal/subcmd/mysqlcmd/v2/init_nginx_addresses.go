package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/v2"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

const InitNginxAddressesCommand = `init-nginx-addresses`

type InitNginxAddressesAct struct {
	*subcmd.BaseOptions
	Service peripheraltools.InitNginxAddresses
}

func NewInitNginxAddressesCommand() *cobra.Command {
	act := InitNginxAddressesAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   InitNginxAddressesCommand,
		Short: "Initialize the Nginx addresses for peripheral",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			InitNginxAddressesCommand, subcmd.CmdBaseExampleStr, subcmd.ToPrettyJson(act.Service.Example())),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validate())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

func (c *InitNginxAddressesAct) Validate() error {
	return c.BaseOptions.Validate()
}

func (c *InitNginxAddressesAct) Init() error {
	if err := c.Deserialize(&c.Service.Param); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	//c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Param)
	return nil
}

func (c *InitNginxAddressesAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "初始化 nginx 地址",
			Func:    c.Service.Run,
		},
	}
	if err := steps.Run(); err != nil {
		logger.Error(err.Error())
		return err
	}

	logger.Info("初始化 nginx 地址完成")
	return nil
}
