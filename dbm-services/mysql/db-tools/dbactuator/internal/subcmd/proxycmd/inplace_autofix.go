package proxycmd

import (
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util"
	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/autofix/proxy"
	"fmt"

	"github.com/spf13/cobra"
)

const ProxyInplaceAutofix = "proxy-inplace-autofix"

type InplaceAutofixAct struct {
	*subcmd.BaseOptions
	Service proxy.InplaceAutofixComp
}

func NewInplaceAutofixCommand() *cobra.Command {
	act := InplaceAutofixAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   ProxyInplaceAutofix,
		Short: "Inplace autofix",
		Example: fmt.Sprintf(
			`dbactuator proxy %s %s %s`,
			ProxyInplaceAutofix,
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

func (c *InplaceAutofixAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

func (c *InplaceAutofixAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Params)
	return nil
}

func (c *InplaceAutofixAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "启动proxy",
			Func:    c.Service.StartProxy,
		},
		{
			FunName: "克隆账号",
			Func:    c.Service.CloneUsers,
		},
		{
			FunName: "设置后端",
			Func:    c.Service.SetBackend,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("原地自愈proxy完成")
	return nil
}
