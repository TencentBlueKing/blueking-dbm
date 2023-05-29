package mysqlcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// DeployMysqlCrondAct 部署
type DeployMysqlCrondAct struct {
	*subcmd.BaseOptions
	Service mysql.DeployMySQLCrondComp
}

// DeployMySQLCrond 命令常量
const DeployMySQLCrond = "deploy-mysql-crond"

// NewDeployMySQLCrondCommand 实现
func NewDeployMySQLCrondCommand() *cobra.Command {
	act := DeployMysqlCrondAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:   DeployMySQLCrond,
		Short: "部署 mysql-crond",
		Example: fmt.Sprintf(
			`dbactuator mysql %s %s %s`,
			DeployMySQLCrond,
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

// Validate 校验参数
func (c *DeployMysqlCrondAct) Validate() (err error) {
	return c.BaseOptions.Validate()
}

// Init 初始化
func (c *DeployMysqlCrondAct) Init() (err error) {
	if err = c.Deserialize(&c.Service.Params); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	c.Service.GeneralParam = subcmd.GeneralRuntimeParam
	logger.Info("extend params: %s", c.Service.Params)
	return nil
}

// Run 执行
func (c *DeployMysqlCrondAct) Run() (err error) {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    c.Service.Init,
		},
		{
			FunName: "预检查",
			Func:    c.Service.Precheck,
		},
		{
			FunName: "部署二进制",
			Func:    c.Service.DeployBinary,
		},
		{
			FunName: "生成配置文件",
			Func:    c.Service.GeneralRuntimeConfig,
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
		logger.Error("部署 mysql-crond 失败: %s", err.Error())
		return err
	}
	logger.Info("部署 mysql-crond 完成")
	return nil
}
