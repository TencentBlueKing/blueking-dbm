package riakcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/components/riak"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// StopMonitorAct 关闭监控riak dbactor参数
type StopMonitorAct struct {
	*subcmd.BaseOptions
	Payload riak.StopMonitorComp
}

// NewStopMonitorCommand riak关闭监控
func NewStopMonitorCommand() *cobra.Command {
	act := StopMonitorAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "stop-monitor",
		Short:   "关闭监控",
		Example: fmt.Sprintf("dbactuator riak stop-monitor %s", subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validator())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validator TODO
func (d *StopMonitorAct) Validator() error {
	return d.BaseOptions.Validate()
}

// Init 反序列化并检查
func (d *StopMonitorAct) Init() error {
	if err := d.DeserializeAndValidate(&d.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return nil
}

// Run 运行
func (d *StopMonitorAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "关闭监控",
			Func:    d.Payload.StopMonitor,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("stop monitor success")
	return nil
}
