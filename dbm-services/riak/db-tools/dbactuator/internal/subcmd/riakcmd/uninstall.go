package riakcmd

import (
	"fmt"

	"dbm-services/common/go-pubpkg/logger"
	"dbm-services/riak/db-tools/dbactuator/internal/subcmd"
	"dbm-services/riak/db-tools/dbactuator/pkg/components/riak"
	"dbm-services/riak/db-tools/dbactuator/pkg/util"

	"github.com/spf13/cobra"
)

// UninstallAct 搬迁数据进度riak dbactor参数
type UninstallAct struct {
	*subcmd.BaseOptions
	Payload riak.UninstallComp
}

// NewUninstallCommand riak搬迁数据进度
func NewUninstallCommand() *cobra.Command {
	act := UninstallAct{
		BaseOptions: subcmd.GBaseOptions,
	}
	cmd := &cobra.Command{
		Use:     "uninstall",
		Short:   "下架节点",
		Example: fmt.Sprintf("dbactuator riak uninstall %s", subcmd.CmdBaseExampleStr),
		Run: func(cmd *cobra.Command, args []string) {
			util.CheckErr(act.Validator())
			util.CheckErr(act.Init())
			util.CheckErr(act.Run())
		},
	}
	return cmd
}

// Validator TODO
func (d *UninstallAct) Validator() error {
	return d.BaseOptions.Validate()
}

// Init 反序列化并检查
func (d *UninstallAct) Init() error {
	if err := d.DeserializeAndValidate(&d.Payload); err != nil {
		logger.Error("DeserializeAndValidate err %s", err.Error())
		return err
	}
	return nil
}

// Run 运行
func (d *UninstallAct) Run() error {
	steps := subcmd.Steps{
		{
			FunName: "环境预检查",
			Func:    d.Payload.PreCheck,
		},
		{
			FunName: "下架节点",
			Func:    d.Payload.Uninstall,
		},
	}
	if err := steps.Run(); err != nil {
		return err
	}
	logger.Info("uninstall success")
	return nil
}
