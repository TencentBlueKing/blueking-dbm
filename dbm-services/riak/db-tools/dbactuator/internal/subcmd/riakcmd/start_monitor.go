package riakcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/components/riak"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// StartMonitorAct 启动监控riak dbactor参数
type StartMonitorAct struct {
	*subcmd.BaseOptions
	Payload riak.StartMonitorComp
}

// NewStartMonitorCommand riak搬迁数据进度
func NewStartMonitorCommand() *cobra.Command {
	act := StartMonitorAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "start-monitor",
		Short:   "启动监控",
		Example: fmt.Sprintf("dbactuator riak start-monitor %s", subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validator())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validator TODO
func (d *StartMonitorAct) Validator() error {
	return d.BaseOptions.Validate()
}

// Init 反序列化并检查
func (d *StartMonitorAct) Init() error {
	if err := d.DeserializeAndValidate(&d.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return nil
}

// Run 运行
func (d *StartMonitorAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "启动监控",
			Func:    d.Payload.StartMonitor,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("start monitor success")
	return nil
}
