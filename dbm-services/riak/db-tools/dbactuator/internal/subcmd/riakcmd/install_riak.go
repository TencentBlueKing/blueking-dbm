package riakcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/components/riak"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// InstallRiakAct 安装riak dbactor参数
type InstallRiakAct struct {
	*subcmd.BaseOptions
	Payload riak.InstallRiakComp
}

// NewDeployRiakCommand 部署riak节点
func NewDeployRiakCommand() *cobra.Command {
	act := InstallRiakAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "deploy",
		Short:   "部署riak节点",
		Example: fmt.Sprintf("dbactuator riak deploy %s", subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validator())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validator TODO
func (d *InstallRiakAct) Validator() error {
	return d.BaseOptions.Validate()
}

// Init 反序列化并检查
func (d *InstallRiakAct) Init() error {
	if err := d.DeserializeAndValidate(&d.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return nil
}

// Run 运行
func (d *InstallRiakAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "初始化",
			Func:    d.Payload.Init,
		},
		{
			FunName: "环境预检查",
			Func:    d.Payload.PreCheck,
		},
		{
			FunName: "安装riak包",
			Func:    d.Payload.InstallRiakPackage,
		},
		{
			FunName: "生成riak.conf配置",
			Func:    d.Payload.CreateConfigFile,
		},
		{
			FunName: "启动Riak",
			Func:    d.Payload.Start,
		},
		{
			FunName: "检查状态",
			Func:    d.Payload.CheckRiakStatus,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("install riak success")
	return nil
}
