package proxycmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/mysql/db-tools/dbactuator/internal/subcmd"
	"dbm-services/mysql/db-tools/dbactuator/pkg/components/mysql_proxy"
	"dbm-services/mysql/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// MySQLProxyAct TODO
type MySQLProxyAct struct {
	Options DeployMySQLProxyOptions
	Service mysql_proxy.InstallMySQLProxyComp
}

// DeployMySQLProxyOptions TODO
type DeployMySQLProxyOptions struct {
	*subcmd.BaseOptions
}

// NewDeployMySQLProxyCommand TODO
func NewDeployMySQLProxyCommand() *cobra.Command {
	act := MySQLProxyAct{
		Options: DeployMySQLProxyOptions{
			BaseOptions: subcmd.GBaseOptions,
		},
		Service: mysql_proxy.InstallMySQLProxyComp{
			Params: &mysql_proxy.InstallMySQLProxyParam{},
		},
	}
	cmd := &cobra.Command{
		Use:     "deploy",
		Short:   "部署mysql-proxy实例",
		Example: fmt.Sprintf("dbactuator proxy deploy %s", subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validator())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validator TODO
func (d *MySQLProxyAct) Validator() error {
	return d.Options.Validate()
}

// Init TODO
func (d *MySQLProxyAct) Init() error {
	if err := d.Options.Deserialize(&d.Service.Params); err != nil {
		logger.Error("MySQLProxyActivity Deserialize failed: %s", err.Error())
		return err
	}
	d.Service.GeneralParam = subcmd.GeneralRuntimeParam
	return d.Service.Init()
}

// Run TODO
func (d *MySQLProxyAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "环境预检查",
			Func:    d.Service.PreCheck,
		},
		{
			FunName: "初始化目录、文件",
			Func:    d.Service.InitInstanceDirs,
		},
		{
			FunName: "生成proxy.cnf配置",
			Func:    d.Service.GenerateProxycnf,
		},
		{
			FunName: "解压安装包",
			Func:    d.Service.DecompressPkg,
		},
		{
			FunName: "启动Proxy",
			Func:    d.Service.Start,
		},
		{
			FunName: "初始化默认账户",
			Func:    d.Service.InitProxyAdminAccount,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("install mysql-proxy successfully")
	return nil
}
