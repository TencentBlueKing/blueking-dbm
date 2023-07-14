package riakcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/components/riak"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// StartAct 搬迁数据进度riak dbactor参数
type StartAct struct {
	*subcmd.BaseOptions
	Payload riak.StartComp
}

// NewStartCommand riak搬迁数据进度
func NewStartCommand() *cobra.Command {
	act := StartAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "start",
		Short:   "启动节点",
		Example: fmt.Sprintf("dbactuator riak start %s", subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validator())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validator TODO
func (d *StartAct) Validator() error {
	return d.BaseOptions.Validate()
}

// Init 反序列化并检查
func (d *StartAct) Init() error {
	if err := d.DeserializeAndValidate(&d.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return nil
}

// Run 运行
func (d *StartAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "启动节点",
			Func:    d.Payload.Start,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("start success")
	return nil
}
