package riakcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/components/riak"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// JoinClusterAct 安装riak dbactor参数
type JoinClusterAct struct {
	*subcmd.BaseOptions
	Payload riak.JoinClusterComp
}

// NewJoinClusterCommand 部署riak节点
func NewJoinClusterCommand() *cobra.Command {
	act := JoinClusterAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "join-cluster",
		Short:   "加入集群",
		Example: fmt.Sprintf("dbactuator riak join-cluster %s", subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validator())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validator TODO
func (d *JoinClusterAct) Validator() error {
	return d.BaseOptions.Validate()
}

// Init 反序列化并检查
func (d *JoinClusterAct) Init() error {
	if err := d.DeserializeAndValidate(&d.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return nil
}

// Run 运行
func (d *JoinClusterAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "环境预检查",
			Func:    d.Payload.PreCheck,
		},
		{
			FunName: "节点加入集群",
			Func:    d.Payload.JoinCluster,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("join cluster success")
	return nil
}
