package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// InstallMonitorAct 安装 mysql monitor
type InstallMonitorAct struct {
	*subcmd.BaseOptions
	Service mysql.InstallMySQLMonitorComp
}

// InstallMySQLMonitor 安装 mysql monitor
const InstallMySQLMonitor = "install-monitor"

// NewInstallMySQLMonitorCommand 安装 mysql monitor 子命令
func NewInstallMySQLMonitorCommand() *cobra.Command {
	act := InstallMonitorAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   InstallMySQLMonitor,
		Short: "安装mysql监控",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			InstallMySQLMonitor,
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

// Validate 参数验证
func (c *InstallMonitorAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

// Init 初始化
func (c *InstallMonitorAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Params)
	return nil
}

// Run 执行入口
func (c *InstallMonitorAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "执行前检查",
			Func:    c.Service.Precheck,
		},
		{
			FunName: "部署二进制程序",
			Func:    c.Service.DeployBinary,
		},
		{
			FunName: "生成二进制程序配置",
			Func:    c.Service.GenerateBinaryConfig,
		},
		{
			FunName: "生成监控项配置",
			Func:    c.Service.GenerateItemsConfig,
		},
		{
			FunName: "注册crond任务",
			Func:    c.Service.AddToCrond,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("部署mysql监控完成")
	return nil
}
