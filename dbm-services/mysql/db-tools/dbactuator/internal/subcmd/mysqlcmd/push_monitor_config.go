package mysqlcmd

import (
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/peripheraltools/monitor"
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

type PushMySQLMonitorConfigAct struct {
	*subcmd.BaseOptions
	Service monitor.MySQLMonitorComp
}

const PushMySQLMonitorConfig = "push-mysql-monitor-config"

func NewPushMySQLMonitorConfigCommand() *cobra.Command {
	act := PushMySQLMonitorConfigAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   PushMySQLMonitorConfig,
		Short: "推送mysql监控配置",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			PushMySQLMonitorConfig,
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

func (c *PushMySQLMonitorConfigAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

func (c *PushMySQLMonitorConfigAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Params)
	return nil
}

func (c *PushMySQLMonitorConfigAct) Run() (err error) {
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
			FunName: "生成监控项配置",
			Func:    c.Service.GenerateItemsConfig,
		},
		{
			FunName: "生成exporter配置文件",
			Func:    c.Service.GenerateExporterConfig,
		},
		{
			FunName: "重载配置",
			Func:    c.Service.AddToCrond,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("推送mysql监控配置完成")
	return nil
}
