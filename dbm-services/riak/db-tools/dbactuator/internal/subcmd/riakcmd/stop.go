package riakcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/components/riak"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// StopAct 搬迁数据进度riak dbactor参数
type StopAct struct {
	*subcmd.BaseOptions
	Payload riak.StopComp
}

// NewStopCommand riak搬迁数据进度
func NewStopCommand() *cobra.Command {
	act := StopAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "stop",
		Short:   "关闭节点",
		Example: fmt.Sprintf("dbactuator riak stop %s", subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validator())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validator TODO
func (d *StopAct) Validator() error {
	return d.BaseOptions.Validate()
}

// Init 反序列化并检查
func (d *StopAct) Init() error {
	if err := d.DeserializeAndValidate(&d.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return nil
}

// Run 运行
func (d *StopAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "关闭节点",
			Func:    d.Payload.Stop,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("stop success")
	return nil
}
