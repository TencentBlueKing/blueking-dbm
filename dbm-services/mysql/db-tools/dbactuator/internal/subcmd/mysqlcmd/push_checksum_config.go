package mysqlcmd

import (
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/checksum"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"
	"fmt"

	"github.com/spf13/cobra"
)

type PushChecksumConfigAct struct {
	*subcmd.BaseOptions
	Service checksum.MySQLChecksumComp
}

const PushChecksumConfig = `push-checksum-config`

func NewPushChecksumConfigCommand() *cobra.Command {
	act := PushChecksumConfigAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   PushChecksumConfig,
		Short: "推送mysql校验配置",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			PushChecksumConfig,
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

func (c *PushChecksumConfigAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

func (c *PushChecksumConfigAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Params)
	return nil
}

func (c *PushChecksumConfigAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "生成二进制程序配置",
			Func:    c.Service.GenerateRuntimeConfig,
		},
		{
			FunName: "重载配置",
			Func:    c.Service.AddToCrond,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("推送mysql校验配置完成")
	return nil
}
