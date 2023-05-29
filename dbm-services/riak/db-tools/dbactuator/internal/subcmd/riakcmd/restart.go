package riakcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/components/riak"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// RestartAct 重启riak dbactor参数
type RestartAct struct {
	*subcmd.BaseOptions
	Payload riak.RestartComp
}

// NewRestartCommand riak重启节点
func NewRestartCommand() *cobra.Command {
	act := RestartAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "restart",
		Short:   "重启节点",
		Example: fmt.Sprintf("dbactuator riak restart %s", subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validator())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validator TODO
func (d *RestartAct) Validator() error {
	return d.BaseOptions.Validate()
}

// Init 反序列化并检查
func (d *RestartAct) Init() error {
	if err := d.DeserializeAndValidate(&d.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return nil
}

// Run 运行，重启节点
func (d *RestartAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "重启节点",
			Func:    d.Payload.Restart,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("restart success")
	return nil
}
