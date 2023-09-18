package riakcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/components/riak"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// RemoveNodeAct 剔除节点 riak dbactor参数
type RemoveNodeAct struct {
	*subcmd.BaseOptions
	Payload riak.RemoveNodeComp
}

// NewRemoveNodeCommand 剔除节点 riak节点
func NewRemoveNodeCommand() *cobra.Command {
	act := RemoveNodeAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "remove-node",
		Short:   "集群剔除节点",
		Example: fmt.Sprintf("dbactuator riak remove-node %s", subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validator())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validator TODO
func (d *RemoveNodeAct) Validator() error {
	return d.BaseOptions.Validate()
}

// Init 反序列化并检查
func (d *RemoveNodeAct) Init() error {
	if err := d.DeserializeAndValidate(&d.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return nil
}

// Run 运行
func (d *RemoveNodeAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "环境预检查",
			Func:    d.Payload.PreCheck,
		},
		{
			FunName: "集群剔除节点",
			Func:    d.Payload.RemoveNode,
		},
	}

	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("remove node success")
	return nil
}
