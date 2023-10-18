package riakcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/components/riak"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// DeployMonitorAct 部署riak监控dbactor参数
type DeployMonitorAct struct {
	*subcmd.BaseOptions
	Payload riak.DeployMonitorComp
}

// NewDeployMonitorCommand riak搬迁数据进度
func NewDeployMonitorCommand() *cobra.Command {
	act := DeployMonitorAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "deploy-monitor",
		Short:   "部署监控",
		Example: fmt.Sprintf("dbactuator riak deploy-monitor %s", subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validator())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validator TODO
func (d *DeployMonitorAct) Validator() error {
	return d.BaseOptions.Validate()
}

// Init 反序列化并检查
func (d *DeployMonitorAct) Init() error {
	if err := d.DeserializeAndValidate(&d.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return nil
}

// Run 运行
func (d *DeployMonitorAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "解压crond和monitor介质",
			Func:    d.Payload.DeployBinary,
		},
		// riak使用mysql-crond实现定时功能
		// 生成mysql-crond与riak-monitor的配置文件，部分根据template生成
		// 部分直接生成yaml
		{
			FunName: "生成crond的runtime.yaml文件",
			Func:    d.Payload.GenerateCrondConfigYaml,
		},
		{
			FunName: "生成monitor的runtime.yaml文件",
			Func:    d.Payload.GenerateMonitorConfigYaml,
		},
		{
			FunName: "生成crond的jobs-config.yaml文件",
			Func:    d.Payload.GenerateJobsConfigYaml,
		},
		{
			FunName: "生成monitor的items-config.yaml文件",
			Func:    d.Payload.GenerateItemsConfigYaml,
		},
		// 前台预执行便于发现执行报错，然后后台正式执行
		{
			FunName: "部署监控",
			Func:    d.Payload.DeployMonitor,
		},
	}
	// 部署失败
	if err := steps.Run(); err != nil {
		return err
	}
	// 部署成功
	logger.Info("deploy monitor success")
	return nil
}
