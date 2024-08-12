package mysqlcmd

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/crond"
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

type PushMySQLCrondConfigAct struct {
	*subcmd.BaseOptions
	Service crond.MySQLCrondComp
}

const PushMySQLCrondConfig = "push-mysql-crond-config"

func NewPushMySQLCrondConfigCommand() *cobra.Command {
	act := PushMySQLCrondConfigAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   PushMySQLCrondConfig,
		Short: "推送 mysql-crond 配置",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			PushMySQLCrondConfig,
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

func (c *PushMySQLCrondConfigAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

func (c *PushMySQLCrondConfigAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Params)
	return nil
}

func (c *PushMySQLCrondConfigAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "生成配置文件",
			Func:    c.Service.GenerateRuntimeConfig,
		},
		{
			FunName: "生成空任务配置",
			Func:    c.Service.TouchJobsConfig,
		},
		{
			FunName: "移除保活监控",
			Func:    c.Service.RemoveKeepAlive,
		},
		{
			FunName: "停止进程",
			Func:    c.Service.Stop,
		},
		{
			FunName: "启动进程",
			Func:    c.Service.Start,
		},
		{
			FunName: "启动后检查",
			Func:    c.Service.CheckStart,
		},
		{
			FunName: "添加保活监控",
			Func:    c.Service.AddKeepAlive,
		},
	}
	if err := steps.Run(); err != nil {
		logger.Error("推送 mysql-crond 配置失败: %s", err.Error())
		return err
	}
	logger.Info("推送 mysql-crond 配置完成")
	return nil
}
