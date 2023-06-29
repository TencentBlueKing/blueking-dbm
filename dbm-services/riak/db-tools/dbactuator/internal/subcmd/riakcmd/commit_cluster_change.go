package riakcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/components/riak"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// CommitClusterChangeAct 安装riak dbactor参数
type CommitClusterChangeAct struct {
	*subcmd.BaseOptions
	Payload riak.CommitClusterChangeComp
}

// NewCommitClusterChangeCommand 部署riak节点
func NewCommitClusterChangeCommand() *cobra.Command {
	act := CommitClusterChangeAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "commit-cluster-change",
		Short:   "提交集群变化",
		Example: fmt.Sprintf("dbactuator riak commit-cluster-change %s", subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validator())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validator TODO
func (d *CommitClusterChangeAct) Validator() error {
	return d.BaseOptions.Validate()
}

// Init 反序列化并检查
func (d *CommitClusterChangeAct) Init() error {
	if err := d.DeserializeAndValidate(&d.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return nil
}

// Run 执行
func (d *CommitClusterChangeAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "提交集群变化",
			Func:    d.Payload.CommitClusterChange,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("commit cluster change success")
	return nil
}
